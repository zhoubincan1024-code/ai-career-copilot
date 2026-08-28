"""Embedding 服务：支持火山多模态 / 火山标准文本 / 本地模型，按配置切换"""
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

import httpx

from app.core.config import settings
from app.services.llm import get_client

logger = logging.getLogger(__name__)

# 国内 HuggingFace 镜像加速（本地模型首次下载用）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")


@lru_cache(maxsize=1)
def _get_local_model():
    """懒加载本地 embedding 模型（单例）"""
    from sentence_transformers import SentenceTransformer

    logger.info("loading local embedding model: %s", settings.embedding_model)
    return SentenceTransformer(settings.embedding_model)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量文本向量化，返回与输入一一对应的向量列表"""
    if not texts:
        return []
    if settings.embedding_provider == "volcengine_multimodal":
        return _embed_multimodal(texts)
    if settings.embedding_provider == "volcengine":
        return _embed_volcengine(texts)
    return _embed_local(texts)


def embed_text(text: str) -> list[float]:
    """单条文本向量化（检索 query 用）"""
    return embed_texts([text])[0]


# ---------- 火山多模态 embedding（纯文本可用）----------

def _embed_multimodal(texts: list[str]) -> list[list[float]]:
    """调用 /embeddings/multimodal，纯文本输入；并发批量调用"""
    url = f"{settings.llm_base_url.rstrip('/')}/embeddings/multimodal"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {settings.llm_api_key}"}

    def _one(text: str) -> list[float]:
        payload = {"model": settings.embedding_model, "input": [{"type": "text", "text": text}]}
        resp = httpx.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()["data"]["embedding"]

    # 多模态接口一次返回一个向量，用线程池并发
    with ThreadPoolExecutor(max_workers=4) as pool:
        result = list(pool.map(_one, texts))
    logger.info("multimodal embed %d texts, dim=%d", len(texts), len(result[0]) if result else 0)
    return result


# ---------- 火山标准文本 embedding ----------

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


# ---------- 本地模型 ----------

def _embed_local(texts: list[str]) -> list[list[float]]:
    model = _get_local_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    result = [v.tolist() for v in vectors]
    logger.info("local embed %d texts, dim=%d", len(texts), len(result[0]) if result else 0)
    return result
