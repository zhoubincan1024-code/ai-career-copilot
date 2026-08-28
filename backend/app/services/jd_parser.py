"""JD 解析服务：文本抽取 + LLM 结构化解析"""
from pathlib import Path

from app.services import llm as llm_service

# 项目根 = backend/app/services 上溯 3 级
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROMPT_FILE = PROJECT_ROOT / "ai" / "prompts" / "jd_parser" / "v1.md"


def load_system_prompt() -> str:
    """读取 JD 解析 Prompt（版本管理：ai/prompts/jd_parser/v1.md）"""
    return PROMPT_FILE.read_text(encoding="utf-8")


def parse_jd(jd_text: str) -> dict:
    """调用 LLM 将 JD 文本解析为结构化 JSON"""
    if not llm_service.llm_enabled():
        raise RuntimeError("LLM 未配置：请先在 backend/.env 设置 LLM_API_KEY 与 LLM_MODEL")
    return llm_service.chat_json(load_system_prompt(), jd_text)


def merge_parsed(parsed: dict) -> dict:
    """归一化 LLM 输出：确保所有顶层字段存在、类型正确"""
    template = {
        "title": "",
        "company": "",
        "location": "",
        "salary": "",
        "experience_years": 0,
        "education": "",
        "responsibilities": [],
        "requirements": [],
        "skills": [],
        "keywords": [],
        "summary": "",
    }
    if not isinstance(parsed, dict):
        parsed = {}
    for key, default in template.items():
        if key not in parsed or parsed[key] is None:
            parsed[key] = default
    return parsed
