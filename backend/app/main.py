"""AI Career Copilot API 入口"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, jobs, matches, resumes
from app.core.config import settings
from app.core.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时自动建表（幂等）
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI Career Copilot - AI 求职决策与面试助手后端",
    lifespan=lifespan,
)

# 前端开发服务器跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由
app.include_router(auth.router)
app.include_router(resumes.router)
app.include_router(jobs.router)
app.include_router(matches.router)


@app.get("/health", tags=["system"])
def health() -> dict:
    """健康检查：用于验证服务与部署状态"""
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}


@app.get("/", tags=["system"])
def root() -> dict:
    return {"message": "AI Career Copilot API 运行中", "docs": "/docs", "health": "/health"}
