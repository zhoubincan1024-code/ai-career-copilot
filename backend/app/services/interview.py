"""AI 模拟面试服务：创建面试、多轮追问、结束复盘"""
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.interview import Interview, Message
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User
from app.services.llm import chat_json

logger = logging.getLogger(__name__)

MAX_QUESTIONS = 6  # 单场面试最多问题数


# ---------- 工具 ----------

def _load_prompt(name: str) -> dict:
    """加载面试 prompt（system / user_template）"""
    root = Path(__file__).resolve().parents[3]
    path = root / "ai" / "prompts" / "interview" / f"{name}.md"
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"^---\s*$", text, flags=re.M)
    if len(parts) >= 3:
        return {"system": parts[0].strip(), "user_template": parts[2].strip()}
    return {"system": "你是资深面试官。", "user_template": text}


def _get_job_info(db: Session, job_id: uuid.UUID | None) -> str:
    if not job_id:
        return "（未指定岗位，按通用软件工程师面试）"
    job = db.get(Job, job_id)
    if not job:
        return "（未找到岗位信息）"
    parts = [f"岗位：{job.title or '未命名'}"]
    if job.company:
        parts.append(f"公司：{job.company}")
    if job.parsed_json:
        pj = job.parsed_json
        if pj.get("requirements"):
            parts.append(f"核心要求：{', '.join(pj['requirements'][:8])}")
        if pj.get("skills"):
            parts.append(f"技能要求：{', '.join(pj['skills'][:10])}")
    if job.jd_text:
        parts.append(f"JD 原文：{job.jd_text[:500]}")
    return "\n".join(parts)


def _get_resume_summary(db: Session, user_id: uuid.UUID) -> str:
    resume = (
        db.query(Resume)
        .filter(Resume.user_id == user_id, Resume.status == "parsed")
        .order_by(Resume.created_at.desc())
        .first()
    )
    if not resume or not resume.parsed_json:
        return "（暂无解析后的简历）"
    pj = resume.parsed_json
    parts = []
    if pj.get("name"):
        parts.append(f"姓名：{pj['name']}")
    if pj.get("education"):
        edu = pj["education"][0] if isinstance(pj["education"], list) else pj["education"]
        parts.append(f"教育：{edu.get('school', '')} {edu.get('major', '')} {edu.get('degree', '')}")
    if pj.get("skills"):
        parts.append(f"技能：{', '.join(pj['skills'][:12])}")
    if pj.get("projects"):
        for proj in pj["projects"][:2]:
            parts.append(f"项目：{proj.get('name', '')} - {proj.get('description', '')[:100]}")
    return "\n".join(parts) if parts else "（简历信息为空）"


def _format_conversation(messages: list[Message]) -> str:
    lines = []
    for m in messages:
        role = "面试官" if m.role == "assistant" else "候选人"
        lines.append(f"【{role}】{m.content}")
    return "\n\n".join(lines)


def _count_questions(messages: list[Message]) -> int:
    """统计 AI 提出的问题数（assistant 消息中包含 question 的轮次，简化为 assistant 消息数 - 1）"""
    return sum(1 for m in messages if m.role == "assistant")


# ---------- 核心功能 ----------

def create_interview(db: Session, user: User, job_id: uuid.UUID | None = None) -> Interview:
    """创建面试：生成开场白 + 第一题"""
    job_info = _get_job_info(db, job_id)
    resume_summary = _get_resume_summary(db, user.id)

    prompt = _load_prompt("init")
    user_content = prompt["user_template"].format(job_info=job_info, resume_summary=resume_summary)
    result = chat_json(prompt["system"], user_content)

    intro = result.get("intro", "你好，我是本次模拟面试的面试官。")
    first_question = result.get("question", "请先做个自我介绍。")
    opening = f"{intro}\n\n{first_question}"

    interview = Interview(user_id=user.id, job_id=job_id)
    db.add(interview)
    db.flush()
    db.add(Message(interview_id=interview.id, role="assistant", content=opening))
    db.commit()
    db.refresh(interview)
    logger.info("interview created: id=%s, job=%s", interview.id, job_id)
    return interview


def answer_interview(db: Session, interview_id: uuid.UUID, user: User, answer: str) -> Message:
    """用户回答：AI 评估并追问/下一题"""
    interview = db.get(Interview, interview_id)
    if not interview or interview.user_id != user.id:
        raise HTTPException(status_code=404, detail="面试不存在")
    if interview.finished_at:
        raise HTTPException(status_code=400, detail="面试已结束")

    # 保存用户回答
    user_msg = Message(interview_id=interview.id, role="user", content=answer.strip())
    db.add(user_msg)
    db.flush()

    messages = (
        db.query(Message)
        .filter(Message.interview_id == interview.id)
        .order_by(Message.created_at)
        .all()
    )
    question_count = _count_questions(messages)
    conversation = _format_conversation(messages)
    job_info = _get_job_info(db, interview.job_id)

    prompt = _load_prompt("followup")
    user_content = prompt["user_template"].format(
        job_info=job_info,
        conversation=conversation,
        question_count=question_count,
        max_questions=MAX_QUESTIONS,
    )
    result = chat_json(prompt["system"], user_content)

    feedback = result.get("feedback", "")
    question = result.get("question", "")
    should_end = result.get("should_end", False)

    ai_content = f"{feedback}\n\n{question}" if feedback else question
    ai_msg = Message(interview_id=interview.id, role="assistant", content=ai_content)
    db.add(ai_msg)
    db.commit()
    db.refresh(ai_msg)

    # 如果 AI 判定结束，自动生成复盘
    if should_end:
        _generate_review(db, interview)

    return ai_msg


def end_interview(db: Session, interview_id: uuid.UUID, user: User) -> Interview:
    """手动结束面试并生成复盘"""
    interview = db.get(Interview, interview_id)
    if not interview or interview.user_id != user.id:
        raise HTTPException(status_code=404, detail="面试不存在")
    if interview.finished_at:
        return interview
    _generate_review(db, interview)
    db.refresh(interview)
    return interview


def _generate_review(db: Session, interview: Interview) -> None:
    """生成复盘报告并更新 interview"""
    messages = (
        db.query(Message)
        .filter(Message.interview_id == interview.id)
        .order_by(Message.created_at)
        .all()
    )
    conversation = _format_conversation(messages)
    job_info = _get_job_info(db, interview.job_id)

    prompt = _load_prompt("review")
    user_content = prompt["user_template"].format(job_info=job_info, conversation=conversation)
    result = chat_json(prompt["system"], user_content)

    interview.score = result.get("overall_score", 0)
    interview.feedback_json = {
        "dimensions": result.get("dimensions", {}),
        "per_question": result.get("per_question", []),
        "suggestions": result.get("suggestions", []),
    }
    interview.finished_at = datetime.utcnow()
    db.commit()
    logger.info("interview finished: id=%s, score=%s", interview.id, interview.score)


def get_interview(db: Session, interview_id: uuid.UUID, user: User) -> dict:
    """获取面试详情（含消息和复盘）"""
    interview = db.get(Interview, interview_id)
    if not interview or interview.user_id != user.id:
        raise HTTPException(status_code=404, detail="面试不存在")
    messages = (
        db.query(Message)
        .filter(Message.interview_id == interview.id)
        .order_by(Message.created_at)
        .all()
    )
    return {
        "id": str(interview.id),
        "job_id": str(interview.job_id) if interview.job_id else None,
        "score": float(interview.score) if interview.score else None,
        "feedback": interview.feedback_json,
        "started_at": interview.started_at.isoformat() if interview.started_at else None,
        "finished_at": interview.finished_at.isoformat() if interview.finished_at else None,
        "messages": [
            {"id": str(m.id), "role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
            for m in messages
        ],
    }


def list_interviews(db: Session, user: User) -> list[dict]:
    """面试列表"""
    interviews = (
        db.query(Interview)
        .filter(Interview.user_id == user.id)
        .order_by(Interview.started_at.desc())
        .all()
    )
    return [
        {
            "id": str(i.id),
            "job_id": str(i.job_id) if i.job_id else None,
            "score": float(i.score) if i.score else None,
            "started_at": i.started_at.isoformat() if i.started_at else None,
            "finished_at": i.finished_at.isoformat() if i.finished_at else None,
            "finished": i.finished_at is not None,
        }
        for i in interviews
    ]
