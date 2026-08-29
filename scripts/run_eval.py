#!/usr/bin/env python
"""Evaluation 评测运行脚本

用法：
    cd backend
    python ../scripts/run_eval.py

输出：
    - 控制台打印各模块汇总指标
    - tests/eval/reports/eval_YYYYMMDD_HHMMSS.json 完整报告
"""
import sys
import uuid
from pathlib import Path

# 确保 backend 在 path 中
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import SessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.evaluation import run_all  # noqa: E402
from app.core.security import hash_password  # noqa: E402


def get_or_create_eval_user(db) -> User:
    """获取或创建评测专用用户"""
    email = "eval@test.local"
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            password_hash=hash_password("eval123456"),
            name="评测用户",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def print_summary(report: dict):
    """打印评测汇总到控制台"""
    print("\n" + "=" * 70)
    print("  AI Career Copilot — Evaluation 评测报告")
    print(f"  时间：{report['timestamp']}   版本：{report['eval_version']}")
    print("=" * 70)

    for module_name, mod in report.get("modules", {}).items():
        if "error" in mod:
            print(f"\n  [{module_name}] 错误：{mod['error']}")
            continue

        print(f"\n  ┌─ {module_name} ({mod.get('cases', 0)} 个用例)")
        print(f"  │")

        # 核心指标
        if module_name == "resume_parsing":
            print(f"  │  字段准确率：{mod.get('avg_field_accuracy', 'N/A')}")
            print(f"  │  技能 F1：  {mod.get('avg_skill_f1', 'N/A')}")
        elif module_name == "jd_parsing":
            print(f"  │  技能 F1：  {mod.get('avg_skill_f1', 'N/A')}")
            print(f"  │  字段准确率：{mod.get('avg_field_accuracy', 'N/A')}")
        elif module_name == "matching":
            print(f"  │  等级判断准确率：{mod.get('level_accuracy', 'N/A')}")
            print(f"  │  分数区间准确率：{mod.get('score_range_accuracy', 'N/A')}")
        elif module_name == "rag":
            print(f"  │  检索准确率：  {mod.get('retrieval_accuracy', 'N/A')}")
            print(f"  │  关键词覆盖率：{mod.get('avg_keyword_coverage', 'N/A')}")
            print(f"  │  幻觉率：      {mod.get('hallucination_rate', 'N/A')}")
            print(f"  │  引用准确率：  {mod.get('citation_accuracy', 'N/A')}")
        elif module_name == "interview":
            print(f"  │  平均问题数：  {mod.get('avg_questions', 'N/A')}")
            print(f"  │  最少问题达标率：{mod.get('min_questions_pass_rate', 'N/A')}")
            print(f"  │  评分生成率：  {mod.get('score_generated_rate', 'N/A')}")

        # 延迟
        lat = mod.get("latency", {})
        if lat:
            print(f"  │")
            print(f"  │  延迟：p50={lat.get('p50_ms', 0)}ms  p95={lat.get('p95_ms', 0)}ms  avg={lat.get('avg_ms', 0)}ms")

        # 成本
        cost = mod.get("cost")
        if cost:
            print(f"  │  成本：{cost.get('total_cost_yuan', 0)} 元（{cost.get('total_tokens', 0)} tokens）")

        print(f"  └{'─' * 60}")

    print(f"\n  完整报告已保存：{report.get('report_file', 'N/A')}")
    print("=" * 70 + "\n")


def main():
    print("初始化数据库连接...")
    db = SessionLocal()
    try:
        user = get_or_create_eval_user(db)
        print(f"评测用户：{user.email} (id={user.id})")
        print("开始运行评测（可能需要 2-5 分钟，含多次 LLM 调用）...\n")

        report = run_all(db, user)
        print_summary(report)

    finally:
        db.close()


if __name__ == "__main__":
    main()
