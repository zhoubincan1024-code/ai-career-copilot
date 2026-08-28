"""Match ORM 模型（对应 db/schema.sql 的 matches 表）"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("resume_id", "job_id", name="uq_match_resume_job"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    dimension_json: Mapped[dict | None] = mapped_column(JSONB)
    strength_json: Mapped[dict | None] = mapped_column(JSONB)
    gap_json: Mapped[dict | None] = mapped_column(JSONB)
    suggestion: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
