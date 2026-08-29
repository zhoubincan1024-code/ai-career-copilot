"""简历接口：上传 / 列表 / 详情 / 删除"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.resume import Resume
from app.models.user import User
from app.schemas.resume import ResumeRead, ResumeUploadResponse
from app.services import resume_parser

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/upload", response_model=ResumeUploadResponse, status_code=201)
def upload_resume(
    file: UploadFile = File(...),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResumeUploadResponse:
    """上传简历：抽取文本 → LLM 结构化解析 → 存入 resumes 表（版本递增）"""
    content = file.file.read()
    try:
        raw_text = resume_parser.extract_text(file.filename or "", content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        parsed = resume_parser.parse_resume(raw_text)
        parsed = resume_parser.merge_parsed(parsed)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        # LLM 解析失败：保留 raw_text，标记 failed
        resume = Resume(
            user_id=current.id,
            file_url=str(resume_parser.save_upload(current.id, file.filename or "resume.txt", content)),
            raw_text=raw_text,
            parsed_json=None,
            status="failed",
            version=_next_version(db, current.id),
        )
        db.add(resume)
        db.commit()
        db.refresh(resume)
        raise HTTPException(status_code=422, detail=f"简历解析失败：{e}")

    resume = Resume(
        user_id=current.id,
        file_url=str(resume_parser.save_upload(current.id, file.filename or "resume.txt", content)),
        raw_text=raw_text,
        parsed_json=parsed,
        status="parsed",
        version=_next_version(db, current.id),
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    basic = parsed.get("basic_info", {})
    return ResumeUploadResponse(
        resume=ResumeRead.model_validate(resume),
        parsed_summary={
            "name": basic.get("name"),
            "skills": len(parsed.get("skills", [])),
            "education": len(parsed.get("education", [])),
            "projects": len(parsed.get("projects", [])),
            "work_experience": len(parsed.get("work_experience", [])),
        },
    )


@router.get("", response_model=list[ResumeRead])
def list_resumes(
    current: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[Resume]:
    """当前用户的简历列表（按版本倒序）"""
    return (
        db.query(Resume)
        .filter(Resume.user_id == current.id)
        .order_by(Resume.created_at.desc(), Resume.version.desc())
        .all()
    )


@router.get("/{resume_id}", response_model=ResumeRead)
def get_resume(
    resume_id: uuid.UUID,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Resume:
    """简历详情"""
    resume = db.get(Resume, resume_id)
    if resume is None or resume.user_id != current.id:
        raise HTTPException(status_code=404, detail="简历不存在")
    return resume


@router.delete("/{resume_id}", status_code=204)
def delete_resume(
    resume_id: uuid.UUID,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """删除简历（同时清理上传的源文件）"""
    resume = db.get(Resume, resume_id)
    if resume is None or resume.user_id != current.id:
        raise HTTPException(status_code=404, detail="简历不存在")

    # 尝试删除上传的源文件，失败不影响数据库删除
    if resume.file_url:
        try:
            p = Path(resume.file_url)
            if p.is_file():
                p.unlink()
        except OSError:
            pass

    db.delete(resume)
    db.commit()


def _next_version(db: Session, user_id: uuid.UUID) -> int:
    """计算该用户下一份简历的版本号"""
    latest = (
        db.query(Resume)
        .filter(Resume.user_id == user_id)
        .order_by(Resume.version.desc())
        .first()
    )
    return (latest.version + 1) if latest else 1
