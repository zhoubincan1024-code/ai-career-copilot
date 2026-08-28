"""岗位匹配引擎：规则打分（可复算、透明） + LLM 解释（可读、可执行）"""
import json
import re
from datetime import datetime
from pathlib import Path

from app.services import llm as llm_service

# 项目根 = backend/app/services 上溯 3 级
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROMPT_FILE = PROJECT_ROOT / "ai" / "prompts" / "match_analyzer" / "v1.md"

# 四维度权重（总和 = 1.0）
WEIGHTS = {"skill": 0.40, "experience": 0.25, "education": 0.15, "expression": 0.20}

_EDU_LEVEL = {"高中": 0, "大专": 1, "本科": 2, "硕士": 3, "博士": 4}


def load_system_prompt() -> str:
    """读取匹配解释 Prompt（版本管理：ai/prompts/match_analyzer/v1.md）"""
    return PROMPT_FILE.read_text(encoding="utf-8")


def _norm(text: str) -> str:
    return (text or "").lower().strip()


def _skill_overlap(resume_skills: list, jd_skills: list) -> tuple[float, list, list]:
    """技能重叠：子串匹配（提高语义鲁棒性）。返回 (命中率, 命中列表, 缺失列表)"""
    jd_norm = [_norm(s) for s in jd_skills]
    resume_set = {_norm(s) for s in resume_skills}
    matched = [s for s in jd_norm if any(m in s or s in m for m in resume_set)]
    ratio = len(matched) / len(jd_norm) if jd_norm else 0.5
    missing = [s for s in jd_norm if s not in matched]
    return ratio, matched, missing


def _estimate_exp_years(resume: dict) -> int:
    """从 work_experience 的 period 解析累计工作年数（近似）"""
    now_year = datetime.now().year
    years = 0
    for we in resume.get("work_experience", []):
        period = we.get("period", "") or ""
        nums = [int(m) for m in re.findall(r"(?:19|20)\d{2}", period)]
        if len(nums) >= 2:
            years += max(0, nums[-1] - nums[0])
        elif len(nums) == 1 and "今" in period:
            years += max(0, now_year - nums[0])
    return years


def _education_score(resume: dict, jd: dict) -> float:
    """学历匹配：JD 要求学历 vs 简历最高学历"""
    jd_edu = (jd.get("education") or "").strip()
    if not jd_edu:
        return 0.8  # 未要求学历，视为良好

    req_level = max((_EDU_LEVEL[k] for k in _EDU_LEVEL if k in jd_edu), default=0)
    resume_level = 0
    for edu in resume.get("education", []):
        deg = edu.get("degree", "") or ""
        resume_level = max(resume_level, max((_EDU_LEVEL[k] for k in _EDU_LEVEL if k in deg), default=0))

    if resume_level >= req_level:
        return 1.0
    if resume_level + 1 >= req_level:
        return 0.6
    return 0.2


def _expression_score(resume: dict, jd: dict) -> float:
    """表达契合：JD 关键词在简历全文（项目/亮点/总结/经历）中的命中率"""
    jd_keywords = [_norm(k) for k in jd.get("keywords", [])]
    if not jd_keywords:
        return 0.7

    pieces = [p.get("description", "") for p in resume.get("projects", [])]
    pieces += [p.get("name", "") for p in resume.get("projects", [])]
    pieces += resume.get("highlights", [])
    pieces.append(resume.get("summary", ""))
    pieces += [w.get("description", "") for w in resume.get("work_experience", [])]
    resume_text = _norm(" ".join(pieces))

    hit = sum(1 for k in jd_keywords if k in resume_text)
    return hit / len(jd_keywords)


def rule_scoring(resume: dict, jd: dict) -> dict:
    """规则打分：返回总分、各维度分、技能重叠明细、经验对比"""
    skill_ratio, matched, missing = _skill_overlap(
        resume.get("skills", []), jd.get("skills", [])
    )
    exp = _estimate_exp_years(resume)
    req = jd.get("experience_years") or 0
    exp_score = min(1.0, exp / req) if req > 0 else (0.8 if exp > 0 else 0.5)
    edu_score = _education_score(resume, jd)
    expr_score = _expression_score(resume, jd)

    dimensions = {
        "skill": round(skill_ratio * 100, 1),
        "experience": round(exp_score * 100, 1),
        "education": round(edu_score * 100, 1),
        "expression": round(expr_score * 100, 1),
    }
    overall = sum(WEIGHTS[k] * dimensions[k] for k in WEIGHTS)
    return {
        "score": round(overall, 1),
        "dimensions": dimensions,
        "skill_overlap": {"matched": matched, "missing": missing, "matched_count": len(matched)},
        "experience": {"resume_years": exp, "required": req},
    }


def explain_with_llm(resume: dict, jd: dict, rule: dict) -> dict:
    """LLM 生成可解释的 strengths / gaps / suggestions / summary"""
    if not llm_service.llm_enabled():
        raise RuntimeError("LLM 未配置：请先在 backend/.env 设置 LLM_API_KEY 与 LLM_MODEL")
    payload = json.dumps({"resume": resume, "jd": jd, "rule_score": rule}, ensure_ascii=False)
    parsed = llm_service.chat_json(load_system_prompt(), payload)
    return {
        "strengths": parsed.get("strengths", []),
        "gaps": parsed.get("gaps", []),
        "suggestions": parsed.get("suggestions", []),
        "summary": parsed.get("summary", ""),
    }
