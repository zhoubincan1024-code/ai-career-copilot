"""匹配接口：创建/更新匹配、列表、详情"""
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.job import Job
from app.models.match import Match
from app.models.resume import Resume
from app.models.user import User
from app.schemas.match import MatchCreate, MatchRead
from app.services import matcher

router = APIRouter(prefix="/matches", tags=["matches"])


@router.post("", response_model=MatchRead, status_code=201)
def create_match(
    payload: MatchCreate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Match:
    """生成匹配：规则打分 + LLM 解释；同一(简历,岗位)重复调用会更新结果"""
    resume = db.get(Resume, payload.resume_id)
    job = db.get(Job, payload.job_id)
    if resume is None or resume.user_id != current.id:
        raise HTTPException(status_code=404, detail="简历不存在")
    if job is None or job.user_id != current.id:
        raise HTTPException(status_code=404, detail="JD 不存在")

    match = (
        db.query(Match)
        .filter(Match.resume_id == resume.id, Match.job_id == job.id)
        .first()
    )

    # 1. 规则打分（可复算）
    rule = matcher.rule_scoring(resume.parsed_json or {}, job.parsed_json or {})
    # 2. LLM 可解释分析
    try:
        explanation = matcher.explain_with_llm(resume.parsed_json or {}, job.parsed_json or {}, rule)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"匹配解释生成失败：{e}")

    suggestion_text = explanation.get("summary", "")
    suggestions = explanation.get("suggestions", [])
    if suggestions:
        suggestion_text += "\n建议：" + "；".join(s.get("title", "") for s in suggestions)

    if match is None:
        match = Match(
            resume_id=resume.id,
            job_id=job.id,
            score=Decimal(str(rule["score"])),
            dimension_json=rule["dimensions"],
            strength_json=explanation["strengths"],
            gap_json=explanation["gaps"],
            suggestion=suggestion_text,
        )
        db.add(match)
    else:
        match.score = Decimal(str(rule["score"]))
        match.dimension_json = rule["dimensions"]
        match.strength_json = explanation["strengths"]
        match.gap_json = explanation["gaps"]
        match.suggestion = suggestion_text

    db.commit()
    db.refresh(match)
    return match


@router.get("", response_model=list[MatchRead])
def list_matches(
    current: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[Match]:
    """当前用户的全部匹配记录（按时间倒序）"""
    return (
        db.query(Match)
        .join(Resume, Match.resume_id == Resume.id)
        .join(Job, Match.job_id == Job.id)
        .filter(Resume.user_id == current.id, Job.user_id == current.id)
        .order_by(Match.created_at.desc())
        .all()
    )


@router.get("/{match_id}", response_model=MatchRead)
def get_match(
    match_id: uuid.UUID,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Match:
    """匹配详情"""
    match = db.get(Match, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="匹配记录不存在")
    resume = db.get(Resume, match.resume_id)
    if resume is None or resume.user_id != current.id:
        raise HTTPException(status_code=404, detail="匹配记录不存在")
    return match
