"""应用配置（基于 pydantic-settings，支持 .env 覆盖）"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Career Copilot API"
    app_version: str = "0.1.0"

    # 数据库连接（本地开发默认；部署时由 docker-compose / .env 覆盖）
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_career_copilot"

    # JWT（生产环境务必通过 .env 覆盖为随机长密钥）
    secret_key: str = "dev-only-secret-key-change-in-prod-0123456789abcdef"
    jwt_algorithm: str = "HS256"
    access_token_expire_hours: int = 24

    # LLM（第 8 步起使用）
    llm_api_key: str = ""
    llm_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    llm_model: str = ""

    # RAG / Embedding（第 13 步起使用）
    # provider: volcengine = 火山方舟云端（需开通 embedding 模型）；local = 本地 bge 模型
    embedding_provider: str = "volcengine"
    embedding_model: str = "doubao-embedding-large-text-240915"  # volcengine 用模型名/接入点；local 用 BAAI/bge-small-zh-v1.5
    embedding_dim: int = 1024  # 火山 doubao-embedding 为 1024 维；本地 bge-small-zh 为 512 维
    rag_chunk_size: int = 500  # 单 chunk 目标字符数
    rag_chunk_overlap: int = 50  # 相邻 chunk 重叠字符数
    rag_top_k: int = 4  # 检索返回的相似 chunk 数量


settings = Settings()
