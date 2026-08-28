"""Embedding 服务：本地模型（bge-small-zh）或火山方舟云端，按配置切换"""
import logging
import os
from functools import lru_cache

from app.core.config import settings
from app.services.llm import get_client

logger = logging.getLogger(__name__)

# 国内 HuggingFace 镜像加速（首次下载模型用）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")


@lru_cache(maxsize=1)
def _get_local_model():
    """懒加载本地 embedding 模型（单例，首次调用下载 ~100MB）"""
    from sentence_transformers import SentenceTransformer

    logger.info("loading local embedding model: %s", settings.embedding_model)
    return SentenceTransformer(settings.embedding_model)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量文本向量化，返回与输入一一对应的向量列表"""
    if not texts:
        return []
    if settings.embedding_provider == "volcengine":
        return _embed_volcengine(texts)
    return _embed_local(texts)


def embed_text(text: str) -> list[float]:
    """单条文本向量化（检索 query 用）"""
    return embed_texts([text])[0]


# ---------- 本地模型 ----------

def _embed_local(texts: list[str]) -> list[list[float]]:
    model = _get_local_model()
    # normalize_embeddings=True 使向量归一化，余弦距离 = 1 - 点积
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    result = [v.tolist() for v in vectors]
    logger.info("local embed %d texts, dim=%d", len(texts), len(result[0]) if result else 0)
    return result


# ---------- 火山方舟云端 ----------

def _embed_volcengine(texts: list[str]) -> list[list[float]]:
    result: list[list[float]] = []
    batch_size = 16
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        resp = get_client().embeddings.create(model=settings.embedding_model, input=batch)
        ordered = [None] * len(batch)
        for item in resp.data:
            ordered[item.index] = item.embedding
        result.extend(ordered)
    logger.info("volcengine embed %d texts, dim=%d", len(texts), len(result[0]) if result else 0)
    return result
