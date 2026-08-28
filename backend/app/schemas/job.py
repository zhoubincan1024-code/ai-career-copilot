"""JD 相关 Pydantic Schema"""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class JdCreate(BaseModel):
    """手动粘贴 JD 文本"""
    jd_text: str = Field(min_length=20, description="JD 原文（至少 20 字符）")


class JdRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str | None = None
    company: str | None = None
    jd_text: str | None = None
    parsed_json: dict | None = None
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


class JdUploadResponse(BaseModel):
    job: JdRead
    parsed_summary: dict | None = None
    """解析摘要：岗位名称、职责数、要求数、技能数"""
