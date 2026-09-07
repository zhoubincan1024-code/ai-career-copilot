"""RAG API：带来源引用的知识库问答 + 问答记录管理"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.qa import QARecord
from app.models.user import User
from app.services.rag import ask

router = APIRouter(prefix="/rag", tags=["rag"])


class AskRequest(BaseModel):
    question: str


def _serialize(record: QARecord) -> dict:
    return {
        "id": str(record.id),
        "question": record.question,
        "answer": record.answer,
        "sources": record.sources_json or [],
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


@router.post("/ask")
def rag_ask(
    body: AskRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """RAG 问答：基于用户知识库检索 + LLM 回答 + 来源引用，并保存为问答记录"""
    question = body.question.strip()
    if not question:
        return {"answer": "请输入问题", "sources": [], "retrieved": [], "record_id": None, "created_at": None}
    if len(question) < 4:
        return {"answer": "问题太短了，请描述得更具体一些", "sources": [], "retrieved": [], "record_id": None, "created_at": None}
    result = ask(db, user, question)
    record = QARecord(
        user_id=user.id,
        question=question,
        answer=result.get("answer", ""),
        sources_json=result.get("sources", []),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    result["record_id"] = str(record.id)
    result["created_at"] = record.created_at.isoformat() if record.created_at else None
    return result


@router.get("/records")
def list_qa_records(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """问答记录列表（按时间倒序）"""
    records = (
        db.query(QARecord)
        .filter(QARecord.user_id == user.id)
        .order_by(QARecord.created_at.desc())
        .all()
    )
    return {"records": [_serialize(r) for r in records]}


@router.delete("/records/{record_id}")
def delete_qa_record(
    record_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """删除一条问答记录"""
    record = db.get(QARecord, record_id)
    if not record or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(record)
    db.commit()
    return {"ok": True}
