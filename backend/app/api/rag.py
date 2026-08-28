"""RAG API：带来源引用的知识库问答"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.services.rag import ask

router = APIRouter(prefix="/rag", tags=["rag"])


class AskRequest(BaseModel):
    question: str


@router.post("/ask")
def rag_ask(
    body: AskRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """RAG 问答：基于用户知识库检索 + LLM 回答 + 来源引用"""
    question = body.question.strip()
    if not question:
        return {"answer": "请输入问题", "sources": [], "retrieved": []}
    if len(question) < 4:
        return {"answer": "问题太短了，请描述得更具体一些", "sources": [], "retrieved": []}
    return ask(db, user, question)
