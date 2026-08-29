"""Applications API：投递管理 CRUD + 状态流转 + 漏斗统计（零 LLM 调用）"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.application import Application, VALID_STATUSES
from app.models.job import Job
from app.models.user import User

router = APIRouter(prefix="/applications", tags=["applications"])

# 漏斗顺序（从投递到 Offer）
FUNNEL_ORDER = ["applied", "online_test", "interview", "offer"]
STATUS_LABELS = {
    "applied": "已投递",
    "online_test": "笔试中",
    "interview": "面试中",
    "offer": "已 Offer",
    "rejected": "已拒绝",
}


class CreateApplicationRequest(BaseModel):
    job_id: str
    status: str = "applied"
    note: str | None = None


class UpdateApplicationRequest(BaseModel):
    status: str | None = None
    note: str | None = None


def _serialize(app: Application) -> dict:
    return {
        "id": str(app.id),
        "job_id": str(app.job_id),
        "job_title": app.job.title if app.job else None,
        "job_company": app.job.company if app.job else None,
        "status": app.status,
        "status_label": STATUS_LABELS.get(app.status, app.status),
        "note": app.note,
        "applied_at": app.applied_at.isoformat() if app.applied_at else None,
        "created_at": app.created_at.isoformat() if app.created_at else None,
    }


@router.post("")
def create_application(
    body: CreateApplicationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """创建投递记录"""
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"无效状态：{body.status}")
    job = db.get(Job, uuid.UUID(body.job_id))
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="岗位不存在")
    # 防重复投递
    existing = (
        db.query(Application)
        .filter(Application.user_id == user.id, Application.job_id == job.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="该岗位已投递")
    app = Application(
        user_id=user.id,
        job_id=job.id,
        status=body.status,
        note=body.note,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return _serialize(app)


@router.get("")
def list_applications(
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """投递列表，支持按状态筛选"""
    q = db.query(Application).filter(Application.user_id == user.id)
    if status:
        if status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"无效状态：{status}")
        q = q.filter(Application.status == status)
    apps = q.order_by(Application.applied_at.desc()).all()
    return {"applications": [_serialize(a) for a in apps]}


@router.patch("/{app_id}")
def update_application(
    app_id: uuid.UUID,
    body: UpdateApplicationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """更新投递状态或备注"""
    app = db.get(Application, app_id)
    if not app or app.user_id != user.id:
        raise HTTPException(status_code=404, detail="投递记录不存在")
    if body.status is not None:
        if body.status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"无效状态：{body.status}")
        app.status = body.status
    if body.note is not None:
        app.note = body.note
    db.commit()
    db.refresh(app)
    return _serialize(app)


@router.delete("/{app_id}")
def delete_application(
    app_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """删除投递记录"""
    app = db.get(Application, app_id)
    if not app or app.user_id != user.id:
        raise HTTPException(status_code=404, detail="投递记录不存在")
    db.delete(app)
    db.commit()
    return {"deleted": True}


@router.get("/stats")
def application_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """投递漏斗统计：各状态数量 + 转化率（纯 SQL，零 LLM）"""
    # 各状态计数
    rows = (
        db.query(Application.status, func.count(Application.id))
        .filter(Application.user_id == user.id)
        .group_by(Application.status)
        .all()
    )
    counts = {status: 0 for status in VALID_STATUSES}
    for status, cnt in rows:
        counts[status] = cnt

    total = sum(counts.values())

    # 漏斗转化率（基于 applied 为基数）
    funnel = []
    applied_count = counts.get("applied", 0)
    for i, status in enumerate(FUNNEL_ORDER):
        cnt = counts.get(status, 0)
        # 从 applied 到当前阶段的累计转化率
        from_start = round(cnt / applied_count * 100, 1) if applied_count > 0 else 0.0
        # 从上一阶段到当前阶段的转化率
        if i == 0:
            from_prev = 100.0
        else:
            prev_cnt = counts.get(FUNNEL_ORDER[i - 1], 0)
            from_prev = round(cnt / prev_cnt * 100, 1) if prev_cnt > 0 else 0.0
        funnel.append({
            "status": status,
            "label": STATUS_LABELS[status],
            "count": cnt,
            "from_start_pct": from_start,
            "from_prev_pct": from_prev,
        })

    # Offer 率
    offer_rate = round(counts.get("offer", 0) / total * 100, 1) if total > 0 else 0.0
    # 拒绝率
    reject_rate = round(counts.get("rejected", 0) / total * 100, 1) if total > 0 else 0.0
    # 在途（未结束）数量
    active = total - counts.get("offer", 0) - counts.get("rejected", 0)

    return {
        "total": total,
        "active": active,
        "offer_rate": offer_rate,
        "reject_rate": reject_rate,
        "counts": {STATUS_LABELS.get(k, k): v for k, v in counts.items()},
        "funnel": funnel,
    }
