"""JD 接口：上传 / 手动录入 / 列表 / 详情"""
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.job import Job
from app.models.user import User
from app.schemas.job import JdCreate, JdRead, JdUploadResponse
from app.services import jd_parser
from app.services.document import extract_text

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _parse_and_save(
    db: Session, user: User, jd_text: str, source: str
) -> JdUploadResponse:
    """公共流程：LLM 解析 JD → 存库 → 返回（含解析失败处理）"""
    try:
        parsed = jd_parser.parse_jd(jd_text)
        parsed = jd_parser.merge_parsed(parsed)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        job = Job(
            user_id=user.id,
            jd_text=jd_text,
            parsed_json=None,
            source=source,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        raise HTTPException(status_code=422, detail=f"JD 解析失败：{e}")

    job = Job(
        user_id=user.id,
        title=parsed.get("title") or None,
        company=parsed.get("company") or None,
        jd_text=jd_text,
        parsed_json=parsed,
        source=source,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return JdUploadResponse(
        job=JdRead.model_validate(job),
        parsed_summary={
            "title": parsed.get("title"),
            "company": parsed.get("company"),
            "location": parsed.get("location"),
            "salary": parsed.get("salary"),
            "skills": len(parsed.get("skills", [])),
            "requirements": len(parsed.get("requirements", [])),
            "responsibilities": len(parsed.get("responsibilities", [])),
        },
    )


@router.post("/upload", response_model=JdUploadResponse, status_code=201)
def upload_jd(
    file: UploadFile = File(...),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JdUploadResponse:
    """上传 JD 文件（PDF/txt/md）并解析"""
    try:
        jd_text = extract_text(file.filename or "", file.file.read())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _parse_and_save(db, current, jd_text, source="upload")


@router.post("/manual", response_model=JdUploadResponse, status_code=201)
def manual_jd(
    payload: JdCreate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JdUploadResponse:
    """手动粘贴 JD 文本并解析"""
    return _parse_and_save(db, current, payload.jd_text, source="manual")


@router.get("", response_model=list[JdRead])
def list_jobs(
    current: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[Job]:
    """当前用户的 JD 列表（按时间倒序）"""
    return (
        db.query(Job)
        .filter(Job.user_id == current.id)
        .order_by(Job.created_at.desc())
        .all()
    )


@router.get("/{job_id}", response_model=JdRead)
def get_job(
    job_id: uuid.UUID,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Job:
    """JD 详情"""
    job = db.get(Job, job_id)
    if job is None or job.user_id != current.id:
        raise HTTPException(status_code=404, detail="JD 不存在")
    return job
