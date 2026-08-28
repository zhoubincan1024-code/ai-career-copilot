"""匹配结果相关 Pydantic Schema"""
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class MatchCreate(BaseModel):
    resume_id: uuid.UUID
    job_id: uuid.UUID


class MatchRead(BaseModel):
    id: uuid.UUID
    resume_id: uuid.UUID
    job_id: uuid.UUID
    score: Decimal | None = None
    dimension_json: dict | None = None
    strength_json: list | None = None
    gap_json: list | None = None
    suggestion: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
