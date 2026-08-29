"""Evaluation 评测引擎：量化评估简历解析/JD解析/匹配/RAG/面试五大模块

指标体系：
- 准确率：字段抽取正确比例
- 召回率：期望字段被抽中的比例
- F1：准确率和召回率的调和平均
- 幻觉率：RAG 中无来源支撑的回答比例
- 延迟：p50 / p95 / p99
- 成本：token 消耗估算（输入+输出）
"""
import json
import logging
import time
import uuid
from pathlib import Path
from statistics import mean, median

from sqlalchemy.orm import Session

from app.services import jd_parser, resume_parser
from app.services.matcher import explain_with_llm, rule_scoring

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EVAL_DIR = PROJECT_ROOT / "tests" / "eval"

# 成本估算（doubao 模型，粗略单价：输入 0.0008元/千token，输出 0.002元/千token）
COST_PER_1K_INPUT = 0.0008
COST_PER_1K_OUTPUT = 0.002


# ---------- 通用工具 ----------

def _percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * p / 100
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_data) else f
    return sorted_data[f] + (sorted_data[c] - sorted_data[f]) * (k - f)


def _latency_stats(latencies: list[float]) -> dict:
    if not latencies:
        return {"count": 0, "p50_ms": 0, "p95_ms": 0, "p99_ms": 0, "avg_ms": 0}
    return {
        "count": len(latencies),
        "p50_ms": round(_percentile(latencies, 50), 1),
        "p95_ms": round(_percentile(latencies, 95), 1),
        "p99_ms": round(_percentile(latencies, 99), 1),
        "avg_ms": round(mean(latencies), 1),
    }


def _estimate_tokens(text: str) -> int:
    """粗略估算 token 数（中文约 1.5 字/token，英文约 4 字符/token）"""
    if not text:
        return 0
    chinese = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other = len(text) - chinese
    return int(chinese / 1.5 + other / 4)


def _cost_estimate(input_text: str, output_text: str) -> dict:
    input_tokens = _estimate_tokens(input_text)
    output_tokens = _estimate_tokens(output_text)
    cost = input_tokens / 1000 * COST_PER_1K_INPUT + output_tokens / 1000 * COST_PER_1K_OUTPUT
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cost_yuan": round(cost, 4),
    }


def _precision_recall_f1(expected: list[str], actual: list[str]) -> dict:
    """计算技能抽取的精确率/召回率/F1"""
    if not expected:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "matched": 0, "expected": 0, "actual": 0}
    expected_lower = {s.lower() for s in expected}
    actual_lower = {s.lower() for s in actual}
    matched = len(expected_lower & actual_lower)
    precision = matched / len(actual_lower) if actual_lower else 0.0
    recall = matched / len(expected_lower) if expected_lower else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "matched": matched,
        "expected": len(expected_lower),
        "actual": len(actual_lower),
    }


def _load_cases(filename: str) -> dict:
    path = EVAL_DIR / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _get_resume_text(case: dict) -> str:
    if case.get("input_file"):
        path = PROJECT_ROOT / case["input_file"]
        return path.read_text(encoding="utf-8")
    return case.get("input_text", "")


# ---------- 1. 简历解析评测 ----------

def evaluate_resume_parsing() -> dict:
    """评测简历解析：字段准确率 + 技能F1 + 延迟 + 成本"""
    data = _load_cases("resume_cases.json")
    results = []
    latencies = []
    total_input_tokens = 0
    total_output_tokens = 0

    for case in data["cases"]:
        text = _get_resume_text(case)
        expected = case["expected"]

        t0 = time.perf_counter()
        parsed = resume_parser.parse_resume(text)
        parsed = resume_parser.merge_parsed(parsed)
        elapsed = (time.perf_counter() - t0) * 1000
        latencies.append(elapsed)

        # 字段级检查
        field_checks = {}
        # 姓名
        name_ok = parsed.get("name", "").strip() == expected["name"]
        field_checks["name"] = {"expected": expected["name"], "actual": parsed.get("name"), "correct": name_ok}
        # 学校
        edu = parsed.get("education", [])
        schools = [e.get("school", "") for e in edu] if isinstance(edu, list) else []
        school_ok = any(exp_s in "".join(schools) for exp_s in expected["education_schools"])
        field_checks["school"] = {"expected": expected["education_schools"], "actual": schools, "correct": school_ok}
        # 专业
        majors = [e.get("major", "") for e in edu] if isinstance(edu, list) else []
        major_ok = any(exp_m in "".join(majors) for exp_m in expected["education_majors"])
        field_checks["major"] = {"expected": expected["education_majors"], "actual": majors, "correct": major_ok}
        # 技能 F1
        skills = parsed.get("skills", [])
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]
        all_expected = expected["skills_expected"] + expected.get("skills_optional", [])
        skill_metrics = _precision_recall_f1(expected["skills_expected"], skills)
        field_checks["skills"] = skill_metrics
        # 实习数
        internships = parsed.get("internships", parsed.get("work_experience", []))
        intern_count = len(internships) if isinstance(internships, list) else 0
        intern_ok = intern_count >= expected["internship_count"]
        field_checks["internship_count"] = {"expected": expected["internship_count"], "actual": intern_count, "correct": intern_ok}
        # 项目数
        projects = parsed.get("projects", [])
        proj_count = len(projects) if isinstance(projects, list) else 0
        proj_ok = proj_count >= expected["project_count_min"]
        field_checks["project_count"] = {"expected_min": expected["project_count_min"], "actual": proj_count, "correct": proj_ok}

        # 成本估算
        output_str = json.dumps(parsed, ensure_ascii=False)
        cost = _cost_estimate(text, output_str)
        total_input_tokens += cost["input_tokens"]
        total_output_tokens += cost["output_tokens"]

        correct_fields = sum(1 for k, v in field_checks.items() if isinstance(v, dict) and v.get("correct", False))
        total_fields = sum(1 for k, v in field_checks.items() if isinstance(v, dict) and "correct" in v)

        results.append({
            "id": case["id"],
            "name": case["name"],
            "latency_ms": round(elapsed, 1),
            "field_accuracy": round(correct_fields / total_fields, 3) if total_fields else 0,
            "skill_f1": skill_metrics["f1"],
            "fields": field_checks,
        })

    avg_field_acc = mean(r["field_accuracy"] for r in results)
    avg_skill_f1 = mean(r["skill_f1"] for r in results)

    return {
        "module": "resume_parsing",
        "cases": len(results),
        "avg_field_accuracy": round(avg_field_acc, 3),
        "avg_skill_f1": round(avg_skill_f1, 3),
        "latency": _latency_stats(latencies),
        "cost": {
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_cost_yuan": round(total_input_tokens / 1000 * COST_PER_1K_INPUT + total_output_tokens / 1000 * COST_PER_1K_OUTPUT, 4),
        },
        "details": results,
    }


# ---------- 2. JD 解析评测 ----------

def evaluate_jd_parsing() -> dict:
    """评测 JD 解析：技能F1 + 学历/经验抽取 + 延迟 + 成本"""
    data = _load_cases("jd_cases.json")
    results = []
    latencies = []
    total_input_tokens = 0
    total_output_tokens = 0

    for case in data["cases"]:
        text = _get_resume_text(case)  # 复用，input_file / input_text 通用
        expected = case["expected"]

        t0 = time.perf_counter()
        parsed = jd_parser.parse_jd(text)
        parsed = jd_parser.merge_parsed(parsed)
        elapsed = (time.perf_counter() - t0) * 1000
        latencies.append(elapsed)

        # 技能 F1
        skills = parsed.get("skills", [])
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]
        skill_metrics = _precision_recall_f1(expected["skills_expected"], skills)

        # 学历
        edu = parsed.get("education", "")
        edu_ok = expected["education_min"] in str(edu) if edu else False

        # 经验年限
        exp_years = parsed.get("experience_years", 0)
        exp_ok = exp_years >= expected["experience_years_min"] if exp_years else False

        # 职位关键词
        title = parsed.get("title", "")
        title_ok = any(kw in title for kw in expected["title_keywords"]) if title else False

        output_str = json.dumps(parsed, ensure_ascii=False)
        cost = _cost_estimate(text, output_str)
        total_input_tokens += cost["input_tokens"]
        total_output_tokens += cost["output_tokens"]

        correct = sum([skill_metrics["f1"] > 0.5, edu_ok, exp_ok, title_ok])
        results.append({
            "id": case["id"],
            "name": case["name"],
            "latency_ms": round(elapsed, 1),
            "skill_f1": skill_metrics["f1"],
            "education_ok": edu_ok,
            "experience_ok": exp_ok,
            "title_ok": title_ok,
            "field_accuracy": round(correct / 4, 3),
        })

    return {
        "module": "jd_parsing",
        "cases": len(results),
        "avg_skill_f1": round(mean(r["skill_f1"] for r in results), 3),
        "avg_field_accuracy": round(mean(r["field_accuracy"] for r in results), 3),
        "latency": _latency_stats(latencies),
        "cost": {
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_cost_yuan": round(total_input_tokens / 1000 * COST_PER_1K_INPUT + total_output_tokens / 1000 * COST_PER_1K_OUTPUT, 4),
        },
        "details": results,
    }


# ---------- 3. 匹配引擎评测 ----------

def evaluate_matching(resume_map: dict, jd_map: dict) -> dict:
    """评测匹配引擎：分数区间校验 + 等级判断 + 延迟"""
    data = _load_cases("match_cases.json")
    results = []
    latencies = []

    for case in data["cases"]:
        resume = resume_map.get(case["resume_case"], {})
        jd = jd_map.get(case["jd_case"], {})
        if not resume or not jd:
            results.append({"id": case["id"], "error": "missing resume/jd data"})
            continue

        t0 = time.perf_counter()
        rule = rule_scoring(resume, jd)
        try:
            llm_explain = explain_with_llm(resume, jd, rule)
        except Exception as e:
            llm_explain = {"error": str(e)}
        elapsed = (time.perf_counter() - t0) * 1000
        latencies.append(elapsed)

        score = rule.get("total_score", 0)
        expected_level = case["expected_level"]

        # 等级判断
        if score >= 70:
            actual_level = "high"
        elif score >= 45:
            actual_level = "medium"
        else:
            actual_level = "low"
        level_ok = actual_level == expected_level

        # 分数区间校验
        score_in_range = True
        if "expected_score_min" in case:
            score_in_range = score_in_range and score >= case["expected_score_min"]
        if "expected_score_max" in case:
            score_in_range = score_in_range and score <= case["expected_score_max"]

        # gap 主题检查
        gaps = llm_explain.get("gaps", []) if isinstance(llm_explain, dict) else []
        gap_text = " ".join(str(g) for g in gaps)
        gap_themes_ok = any(theme in gap_text for theme in case.get("expected_gap_themes", [])) if case.get("expected_gap_themes") else True

        results.append({
            "id": case["id"],
            "name": case["name"],
            "score": round(score, 1),
            "expected_level": expected_level,
            "actual_level": actual_level,
            "level_correct": level_ok,
            "score_in_range": score_in_range,
            "gap_themes_ok": gap_themes_ok,
            "latency_ms": round(elapsed, 1),
            "rule_breakdown": {k: v for k, v in rule.items() if isinstance(v, (int, float))},
        })

    level_accuracy = mean(1 if r.get("level_correct") else 0 for r in results if "level_correct" in r)
    range_accuracy = mean(1 if r.get("score_in_range") else 0 for r in results if "score_in_range" in r)

    return {
        "module": "matching",
        "cases": len(results),
        "level_accuracy": round(level_accuracy, 3),
        "score_range_accuracy": round(range_accuracy, 3),
        "latency": _latency_stats(latencies),
        "details": results,
    }


# ---------- 4. RAG 评测 ----------

def evaluate_rag(db: Session, user) -> dict:
    """评测 RAG：检索命中率 + 答案关键词覆盖 + 幻觉率 + 引用准确率"""
    from app.services.rag import ask, index_document
    from app.models.document import Document

    data = _load_cases("rag_cases.json")
    results = []
    latencies = []

    # 上传知识库文档
    doc_path = PROJECT_ROOT / data["knowledge_doc"]
    doc_content = doc_path.read_text(encoding="utf-8")
    doc = Document(user_id=user.id, title=doc_path.stem, source="upload", status="processing")
    db.add(doc)
    db.flush()
    doc_id = doc.id
    db.commit()

    try:
        index_document(db, doc, doc_content)
    except Exception as e:
        logger.warning("RAG index failed: %s", e)

    for case in data["cases"]:
        t0 = time.perf_counter()
        try:
            answer_data = ask(db, user, case["question"])
        except Exception as e:
            answer_data = {"answer": f"ERROR: {e}", "sources": [], "retrieved": []}
        elapsed = (time.perf_counter() - t0) * 1000
        latencies.append(elapsed)

        answer = answer_data.get("answer", "")
        sources = answer_data.get("sources", [])
        retrieved = answer_data.get("retrieved", [])

        # 检索命中
        retrieved_count = len(retrieved)
        should_retrieve = case.get("should_retrieve", True)
        retrieval_ok = (retrieved_count > 0) if should_retrieve else (retrieved_count == 0)

        # 答案关键词覆盖
        expected_kw = case.get("expected_keywords", [])
        if expected_kw:
            kw_matched = sum(1 for kw in expected_kw if kw in answer)
            kw_coverage = kw_matched / len(expected_kw)
        else:
            kw_coverage = 1.0 if case.get("expect_refusal") else None

        # 幻觉检测：should_retrieve=False 时，答案应拒绝或说明无法回答
        hallucination = False
        if not should_retrieve and case.get("expect_refusal"):
            refusal_signals = ["无法回答", "没有相关", "不在知识", "无法提供", "抱歉"]
            if not any(sig in answer for sig in refusal_signals):
                hallucination = True

        # 引用准确率：有来源时答案应标注引用
        citation_ok = len(sources) > 0 if should_retrieve else True

        results.append({
            "id": case["id"],
            "name": case["name"],
            "latency_ms": round(elapsed, 1),
            "retrieval_ok": retrieval_ok,
            "retrieved_count": retrieved_count,
            "keyword_coverage": round(kw_coverage, 3) if kw_coverage is not None else None,
            "hallucination": hallucination,
            "citation_ok": citation_ok,
            "answer_preview": answer[:150],
        })

    # 清理测试文档
    db.query(Document).filter(Document.id == doc_id).delete()
    db.commit()

    valid_kw = [r["keyword_coverage"] for r in results if r["keyword_coverage"] is not None]
    hallucination_rate = mean(1 if r["hallucination"] else 0 for r in results)

    return {
        "module": "rag",
        "cases": len(results),
        "retrieval_accuracy": round(mean(1 if r["retrieval_ok"] else 0 for r in results), 3),
        "avg_keyword_coverage": round(mean(valid_kw), 3) if valid_kw else None,
        "hallucination_rate": round(hallucination_rate, 3),
        "citation_accuracy": round(mean(1 if r["citation_ok"] else 0 for r in results), 3),
        "latency": _latency_stats(latencies),
        "details": results,
    }


# ---------- 5. 面试评测 ----------

def evaluate_interview(db: Session, user, resume_map: dict, jd_map: dict) -> dict:
    """评测面试：问题数 + 问题相关性 + 评分合理性 + 延迟"""
    from app.services import interview as interview_service

    data = _load_cases("interview_cases.json")
    results = []
    latencies = []

    for case in data["cases"]:
        # 找 JD（简化：用第一个已上传的 JD 或不指定）
        job_id = None  # 简化：不指定 job_id，用通用面试

        t0 = time.perf_counter()
        try:
            iv = interview_service.create_interview(db, user, job_id)
            iv_id = iv.id

            # 回答预设的几轮
            for ans in case.get("test_answers", [])[:3]:
                interview_service.answer_interview(db, iv_id, user, ans)

            # 结束
            interview_service.end_interview(db, iv_id, user)
            elapsed = (time.perf_counter() - t0) * 1000
            latencies.append(elapsed)

            detail = interview_service.get_interview(db, iv_id, user)
            msg_count = len(detail["messages"])
            question_count = sum(1 for m in detail["messages"] if m["role"] == "assistant")
            score = detail.get("score")
            feedback = detail.get("feedback") or {}
            dims = feedback.get("dimensions", {})
            suggestions = feedback.get("suggestions", [])

            results.append({
                "id": case["id"],
                "name": case["name"],
                "latency_ms": round(elapsed, 1),
                "total_messages": msg_count,
                "ai_questions": question_count,
                "min_questions_met": question_count >= case.get("min_questions_before_end", 3),
                "has_score": score is not None,
                "score": score,
                "has_dimensions": len(dims) >= 3,
                "has_suggestions": len(suggestions) >= 2,
                "dimensions": dims,
            })
        except Exception as e:
            results.append({"id": case["id"], "name": case["name"], "error": str(e)})

    return {
        "module": "interview",
        "cases": len(results),
        "avg_questions": round(mean(r.get("ai_questions", 0) for r in results if "ai_questions" in r), 1),
        "min_questions_pass_rate": round(mean(1 if r.get("min_questions_met") else 0 for r in results if "min_questions_met" in r), 3),
        "score_generated_rate": round(mean(1 if r.get("has_score") else 0 for r in results if "has_score" in r), 3),
        "latency": _latency_stats(latencies),
        "details": results,
    }


# ---------- 汇总 ----------

def run_all(db: Session, user) -> dict:
    """运行全部评测，返回汇总报告"""
    logger.info("Starting evaluation suite...")

    # 预解析简历和 JD（供匹配引擎使用）
    resume_data = _load_cases("resume_cases.json")
    jd_data = _load_cases("jd_cases.json")
    resume_map = {}
    jd_map = {}

    for case in resume_data["cases"]:
        text = _get_resume_text(case)
        parsed = resume_parser.parse_resume(text)
        resume_map[case["id"]] = resume_parser.merge_parsed(parsed)

    for case in jd_data["cases"]:
        text = _get_resume_text(case)
        parsed = jd_parser.parse_jd(text)
        jd_map[case["jd_case"] if "jd_case" in case else case["id"]] = jd_parser.merge_parsed(parsed)

    report = {
        "eval_version": "1.0",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "modules": {},
    }

    logger.info("Evaluating resume parsing...")
    report["modules"]["resume_parsing"] = evaluate_resume_parsing()

    logger.info("Evaluating JD parsing...")
    report["modules"]["jd_parsing"] = evaluate_jd_parsing()

    logger.info("Evaluating matching engine...")
    report["modules"]["matching"] = evaluate_matching(resume_map, jd_map)

    logger.info("Evaluating RAG...")
    try:
        report["modules"]["rag"] = evaluate_rag(db, user)
    except Exception as e:
        report["modules"]["rag"] = {"error": str(e)}

    logger.info("Evaluating interview...")
    try:
        report["modules"]["interview"] = evaluate_interview(db, user, resume_map, jd_map)
    except Exception as e:
        report["modules"]["interview"] = {"error": str(e)}

    # 汇总指标
    report["summary"] = {
        "total_cases": sum(m.get("cases", 0) for m in report["modules"].values() if isinstance(m, dict)),
        "avg_latency_p95_ms": {
            k: m.get("latency", {}).get("p95_ms")
            for k, m in report["modules"].items()
            if isinstance(m, dict) and "latency" in m
        },
    }

    # 保存报告
    report_dir = EVAL_DIR / "reports"
    report_dir.mkdir(exist_ok=True)
    report_file = report_dir / f"eval_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    report["report_file"] = str(report_file)

    logger.info("Evaluation complete. Report saved to %s", report_file)
    return report
