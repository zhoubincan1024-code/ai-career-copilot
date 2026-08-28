"""导入所有 ORM 模型（供 Base.metadata 建表）"""
from app.models.resume import Resume
from app.models.user import User

__all__ = ["User", "Resume"]
