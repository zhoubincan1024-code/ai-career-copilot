"""AI Career Copilot API 入口（第 6 步骨架版）"""
from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI Career Copilot - AI 求职决策与面试助手后端",
)


@app.get("/health", tags=["system"])
def health() -> dict:
    """健康检查：用于验证服务与部署状态"""
    return {"status": "ok", "app": settings.app_name, "version": "0.1.0"}


@app.get("/", tags=["system"])
def root() -> dict:
    return {"message": "AI Career Copilot API 运行中", "docs": "/docs", "health": "/health"}
