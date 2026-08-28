"""LLM 客户端封装（火山方舟 OpenAI 兼容接口）"""
import json
import logging
from functools import lru_cache

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    """获取全局 LLM 客户端（复用连接）"""
    return OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)


def llm_enabled() -> bool:
    """是否已配置可用的 LLM Key"""
    return bool(settings.llm_api_key and settings.llm_model)


def chat_json(system_prompt: str, user_content: str, temperature: float = 0.2) -> dict:
    """调用 LLM 并要求返回 JSON 对象；返回解析后的 dict"""
    resp = get_client().chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        temperature=temperature,
    )
    content = resp.choices[0].message.content or "{}"
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        logger.warning("LLM 返回非 JSON: %s", content[:200])
        raise ValueError("LLM 输出无法解析为 JSON")
