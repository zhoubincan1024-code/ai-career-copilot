"""简历相关 Pydantic Schema"""
import uuid
from datetime import datetime

from pydantic import BaseModel


class ResumeRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    file_url: str | None = None
    parsed_json: dict | None = None
    version: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeUploadResponse(BaseModel):
    resume: ResumeRead
    parsed_summary: dict | None = None
    """解析结果的简要摘要（如基本信息、技能数量）"""
