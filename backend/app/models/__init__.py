"""导入所有 ORM 模型（供 Base.metadata 建表）"""
from app.models.application import Application
from app.models.document import Chunk, Document
from app.models.interview import Interview, Message
from app.models.job import Job
from app.models.match import Match
from app.models.resume import Resume
from app.models.user import User

__all__ = ["User", "Resume", "Job", "Match", "Document", "Chunk", "Interview", "Message", "Application"]
