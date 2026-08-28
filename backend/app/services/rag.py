"""RAG 服务：文档切分、向量化索引、相似度检索、带来源引用的问答"""
import logging
import re
import uuid

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Chunk, Document
from app.models.user import User
from app.services.embedding import embed_text, embed_texts
from app.services.llm import chat_json

logger = logging.getLogger(__name__)


# ---------- 文档切分 ----------

def split_text(content: str, chunk_size: int | None = None, overlap: int | None = None) -> list[str]:
    """把长文本按段落切分为带重叠的 chunk（保持语义连贯）"""
    chunk_size = chunk_size or settings.rag_chunk_size
    overlap = overlap or settings.rag_chunk_overlap
    # 先按段落拆分，保留换行信息
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        # 超长段落内部再按句切
        if len(para) > chunk_size:
            sentences = re.split(r"(?<=[。！？.!?])", para)
            for sent in sentences:
                if not sent.strip():
                    continue
                if len(current) + len(sent) > chunk_size and current:
                    chunks.append(current.strip())
                    current = current[-overlap:] if overlap else ""
                current += sent
            continue
        if len(current) + len(para) > chunk_size and current:
            chunks.append(current.strip())
            current = current[-overlap:] if overlap else ""
        current += ("\n" if current else "") + para
    if current.strip():
        chunks.append(current.strip())
    return chunks or [content]


# ---------- 索引 ----------

def index_document(db: Session, doc: Document, text_content: str) -> None:
    """对文档做 切分 -> 向量化 -> 入库，并更新文档状态"""
    try:
        chunks = split_text(text_content)
        # 先删除旧 chunk（重复索引时幂等）
        db.execute(
            text("DELETE FROM chunks WHERE document_id = :did"),
            {"did": str(doc.id)},
        )
        if chunks:
            embeddings = embed_texts(chunks)
            for i, (chunk_text, vec) in enumerate(zip(chunks, embeddings)):
                db.add(Chunk(document_id=doc.id, chunk_index=i, content=chunk_text, embedding=vec))
        doc.status = "indexed"
        doc.chunk_count = len(chunks)
        db.commit()
        logger.info("indexed document %s -> %d chunks", doc.id, len(chunks))
    except Exception as e:
        db.rollback()
        doc.status = "failed"
        db.commit()
        logger.exception("index document failed: %s", e)
        raise HTTPException(status_code=500, detail=f"文档索引失败: {e}")


# ---------- 检索 ----------

def retrieve(db: Session, user: User, query: str, top_k: int | None = None) -> list[dict]:
    """基于余弦相似度检索用户知识库中最相关的 chunk"""
    top_k = top_k or settings.rag_top_k
    q = embed_text(query)
    q_vec = "[" + ",".join(str(x) for x in q) + "]"
    rows = db.execute(
        text(
            """
            SELECT c.id, c.document_id, c.content, c.embedding <=> :q AS distance,
                   d.title, d.id AS doc_id
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE d.user_id = :uid
            ORDER BY c.embedding <=> :q
            LIMIT :k
            """
        ),
        {"q": q_vec, "uid": str(user.id), "k": top_k},
    ).fetchall()
    results = []
    for row in rows:
        results.append(
            {
                "chunk_id": str(row.id),
                "document_id": str(row.doc_id),
                "title": row.title,
                "content": row.content,
                "similarity": round(1 - float(row.distance), 4),
            }
        )
    return results


# ---------- 带来源引用的问答 ----------

def ask(db: Session, user: User, question: str) -> dict:
    """RAG 问答：检索 -> LLM 基于资料回答并标注来源"""
    hits = retrieve(db, user, question)
    if not hits:
        raise HTTPException(status_code=404, detail="知识库中还没有可用的资料，请先上传面试资料或岗位知识文档")

    # 拼 context，带 [n] 来源标记
    context_parts = []
    for i, hit in enumerate(hits, 1):
        context_parts.append(f"[{i}] 来源《{hit['title']}》：\n{hit['content']}")
    context = "\n\n".join(context_parts)

    prompt = _load_prompt()
    system = prompt["system"]
    user_content = prompt["user_template"].format(context=context, question=question)

    result = chat_json(system, user_content)
    citations = result.get("citations") or []
    # 把引用编号映射回真实来源
    sources = []
    for c in citations:
        idx = int(c.get("index", 0)) - 1
        if 0 <= idx < len(hits):
            sources.append(
                {
                    "title": hits[idx]["title"],
                    "document_id": hits[idx]["document_id"],
                    "similarity": hits[idx]["similarity"],
                    "excerpt": hits[idx]["content"][:150],
                }
            )
    return {
        "answer": result.get("answer", ""),
        "citations": result.get("citations", []),
        "sources": sources,
        "retrieved": hits,
    }


def _load_prompt() -> dict:
    """读取 RAG prompt（ai/prompts/rag/v1.md，含 system 与 user 模板）"""
    import os
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    path = root / "ai" / "prompts" / "rag" / "v1.md"
    text = path.read_text(encoding="utf-8")
    # 用分隔行拆 system / user
    parts = re.split(r"^---\s*$", text, flags=re.M)
    if len(parts) >= 3:
        return {"system": parts[0].strip(), "user_template": parts[2].strip()}
    return {"system": "你是 AI 求职助手。", "user_template": text}
