"""Document API：知识库文档上传 / 列表 / 删除"""
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.document import Document
from app.models.user import User
from app.services.document import extract_text
from app.services.rag import index_document

router = APIRouter(prefix="/documents", tags=["rag"])


@router.post("/upload")
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """上传文档并建立向量索引（面试资料 / 岗位知识等）"""
    content = file.file.read()
    try:
        text_content = extract_text(file.filename or "", content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    title = file.filename or "未命名文档"
    doc = Document(user_id=user.id, title=title, source="upload", status="processing")
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # 同步建索引（LLM 调用耗时，需稍等）
    index_document(db, doc, text_content)
    return {"document": {"id": str(doc.id), "title": doc.title, "status": doc.status, "chunk_count": doc.chunk_count}}


@router.get("")
def list_documents(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    """当前用户的知识库文档列表"""
    docs = (
        db.query(Document)
        .filter(Document.user_id == user.id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return {
        "documents": [
            {
                "id": str(d.id),
                "title": d.title,
                "source": d.source,
                "status": d.status,
                "chunk_count": d.chunk_count,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in docs
        ]
    }


@router.delete("/{document_id}")
def delete_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """删除文档（级联删除其 chunks）"""
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    db.delete(doc)
    db.commit()
    return {"ok": True, "id": str(document_id)}
