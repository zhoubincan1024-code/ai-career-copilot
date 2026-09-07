"""QARecord ORM 模型（对应 db/schema.sql 的 qa_records 表）"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class QARecord(Base):
    """知识库智能问答记录（问题 + 回答 + 引用来源）"""

    __tablename__ = "qa_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    sources_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # 引用来源 [{title, document_id, similarity, excerpt}]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
