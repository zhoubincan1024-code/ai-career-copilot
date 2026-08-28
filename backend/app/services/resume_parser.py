"""简历解析服务：文本抽取 + LLM 结构化解析"""
import json
import uuid
from pathlib import Path

import pypdf

from app.core.config import settings
from app.services import llm as llm_service

# 项目根 = backend/app/services 上溯 3 级
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROMPT_FILE = PROJECT_ROOT / "ai" / "prompts" / "resume_parser" / "v1.md"

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def load_system_prompt() -> str:
    """读取解析 Prompt（版本管理：ai/prompts/resume_parser/v1.md）"""
    return PROMPT_FILE.read_text(encoding="utf-8")


def extract_text(filename: str, content: bytes) -> str:
    """从上传文件抽取纯文本：支持 PDF / txt / md"""
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支持的文件类型: {suffix}，仅支持 {sorted(ALLOWED_EXTENSIONS)}")
    if len(content) > MAX_FILE_SIZE:
        raise ValueError("文件超过 5MB 限制")

    if suffix == ".pdf":
        reader = pypdf.PdfReader(__import__("io").BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages).strip()
    # txt / md
    return content.decode("utf-8", errors="replace").strip()


def parse_resume(raw_text: str) -> dict:
    """调用 LLM 将简历文本解析为结构化 JSON"""
    if not llm_service.llm_enabled():
        raise RuntimeError("LLM 未配置：请先在 backend/.env 设置 LLM_API_KEY 与 LLM_MODEL")
    return llm_service.chat_json(load_system_prompt(), raw_text)


def save_upload(user_id: uuid.UUID, filename: str, content: bytes) -> Path:
    """保存上传文件到 backend/uploads/{user_id}/{uuid}.{ext}，返回路径"""
    suffix = Path(filename).suffix.lower()
    base_dir = PROJECT_ROOT / "backend" / "uploads"
    user_dir = base_dir / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    dest = user_dir / f"{uuid.uuid4().hex}{suffix}"
    dest.write_bytes(content)
    return dest


def merge_parsed(parsed: dict) -> dict:
    """归一化 LLM 输出：确保所有顶层字段存在、类型正确"""
    template = {
        "basic_info": {},
        "education": [],
        "skills": [],
        "work_experience": [],
        "projects": [],
        "highlights": [],
        "summary": "",
    }
    if not isinstance(parsed, dict):
        parsed = {}
    for key, default in template.items():
        if key not in parsed or parsed[key] is None:
            parsed[key] = default
    return parsed
