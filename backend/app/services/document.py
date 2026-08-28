"""文档文本抽取公共模块：PDF / txt / md → 纯文本"""
import io
from pathlib import Path

import pypdf

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def extract_text(filename: str, content: bytes) -> str:
    """从文件内容抽取纯文本；支持 PDF / txt / md"""
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支持的文件类型: {suffix}，仅支持 {sorted(ALLOWED_EXTENSIONS)}")
    if len(content) > MAX_FILE_SIZE:
        raise ValueError("文件超过 5MB 限制")

    if suffix == ".pdf":
        reader = pypdf.PdfReader(io.BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages).strip()
    # txt / md
    return content.decode("utf-8", errors="replace").strip()
