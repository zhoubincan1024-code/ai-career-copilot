"""Interview API：模拟面试创建 / 回答 / 结束 / 列表 / 详情"""
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.services import interview as interview_service

router = APIRouter(prefix="/interviews", tags=["interview"])


class CreateInterviewRequest(BaseModel):
    job_id: str | None = None


class AnswerRequest(BaseModel):
    answer: str


@router.post("")
def create_interview(
    body: CreateInterviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """创建一场模拟面试（AI 生成开场白 + 第一题）"""
    job_id = uuid.UUID(body.job_id) if body.job_id else None
    interview = interview_service.create_interview(db, user, job_id)
    return interview_service.get_interview(db, interview.id, user)


@router.get("")
def list_interviews(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """面试列表"""
    return {"interviews": interview_service.list_interviews(db, user)}


@router.get("/{interview_id}")
def get_interview(
    interview_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """面试详情（含对话历史和复盘）"""
    return interview_service.get_interview(db, interview_id, user)


@router.post("/{interview_id}/answer")
def answer_interview(
    interview_id: uuid.UUID,
    body: AnswerRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """回答面试问题，AI 追问或下一题"""
    msg = interview_service.answer_interview(db, interview_id, user, body.answer)
    interview = interview_service.get_interview(db, interview_id, user)
    return {"message": {"id": str(msg.id), "role": msg.role, "content": msg.content}, "interview": interview}


@router.post("/{interview_id}/end")
def end_interview(
    interview_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """结束面试并生成复盘报告"""
    interview_service.end_interview(db, interview_id, user)
    return interview_service.get_interview(db, interview_id, user)
