"""应用配置（基于 pydantic-settings，支持 .env 覆盖）"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Career Copilot API"
    app_version: str = "0.1.0"

    # 数据库连接（本地开发默认；部署时由 docker-compose / .env 覆盖）
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_career_copilot"

    # LLM（第 8 步起使用）
    llm_api_key: str = ""
    llm_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    llm_model: str = ""


settings = Settings()
