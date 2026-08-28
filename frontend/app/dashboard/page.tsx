"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { jobApi, matchApi, resumeApi } from "@/lib/api";
import FlowGuide from "@/app/components/FlowGuide";

interface Stats {
  resumes: number;
  jobs: number;
  matches: number;
}

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [stats, setStats] = useState<Stats>({ resumes: 0, jobs: 0, matches: 0 });
  const [recentMatches, setRecentMatches] = useState<any[]>([]);
  const [loadingData, setLoadingData] = useState(true);

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
      return;
    }
    if (!user) return;
    Promise.all([resumeApi.list(), jobApi.list(), matchApi.list()])
      .then(([rs, js, ms]) => {
        setStats({ resumes: rs.length, jobs: js.length, matches: ms.length });
        setRecentMatches(ms.slice(0, 3));
      })
      .catch((e) => console.error(e))
      .finally(() => setLoadingData(false));
  }, [loading, user, router]);

  if (loading || !user) {
    return <div className="p-8 text-center text-zinc-400">加载中...</div>;
  }

  // 5 步主线闭环（每步状态由用户数据自动判定）
  const steps = [
    {
      n: 1,
      title: "上传简历",
      desc: "AI 自动解析为结构化数据",
      done: stats.resumes > 0,
      href: "/resumes",
    },
    {
      n: 2,
      title: "添加目标岗位 JD",
      desc: "粘贴或上传招聘 JD",
      done: stats.jobs > 0,
      href: "/jobs",
    },
    {
      n: 3,
      title: "发起岗位匹配",
      desc: "获得可解释的匹配度与差距",
      done: stats.matches > 0,
      href: "/matches",
    },
    {
      n: 4,
      title: "查看差距并优化",
      desc: "补齐短板、定向优化简历",
      done: stats.matches > 0,
      href: "/matches",
    },
    {
      n: 5,
      title: "AI 模拟面试",
      desc: "针对目标岗位连续追问",
      done: false,
      href: "/interview",
      soon: true,
    },
  ];

  // 智能推荐下一步
  let nextAction: { title: string; desc: string; href: string; btn: string } | null = null;
  if (stats.resumes === 0) {
    nextAction = {
      title: "从上传简历开始",
      desc: "AI 会解析你的教育、技能、项目，这是匹配的基础",
      href: "/resumes",
      btn: "上传简历",
    };
  } else if (stats.jobs === 0) {
    nextAction = {
      title: "添加你的目标岗位",
      desc: "粘贴或上传一个招聘 JD，AI 会抽取岗位要求",
      href: "/jobs",
      btn: "添加 JD",
    };
  } else if (stats.matches === 0) {
    nextAction = {
      title: "发起第一次匹配",
      desc: "把你的简历和目标岗位做一次完整的匹配分析",
      href: "/matches",
      btn: "去匹配",
    };
  } else {
    nextAction = {
      title: "按建议优化简历",
      desc: "查看最新匹配的差距分析，逐条补齐短板",
      href: "/matches",
      btn: "查看建议",
    };
  }

  const cards = [
    { label: "简历", value: stats.resumes, href: "/resumes" },
    { label: "岗位 JD", value: stats.jobs, href: "/jobs" },
    { label: "匹配记录", value: stats.matches, href: "/matches" },
  ];

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-2xl font-bold">你好，{user.name || user.email}</h1>
      <p className="mt-1 text-sm text-zinc-500">
        {user.target_role ? `目标岗位：${user.target_role}` : "完善目标岗位，开始你的求职闭环"}
      </p>

      {/* 智能推荐下一步 */}
      {nextAction && (
        <div className="mt-8 flex flex-col items-start justify-between gap-4 rounded-xl border border-zinc-900 bg-zinc-900 p-6 text-white sm:flex-row sm:items-center">
          <div>
            <div className="text-lg font-semibold">{nextAction.title}</div>
            <div className="mt-1 text-sm text-zinc-300">{nextAction.desc}</div>
          </div>
          <Link
            href={nextAction.href}
            className="shrink-0 rounded-lg bg-white px-5 py-2 text-sm font-medium text-zinc-900 transition hover:bg-zinc-100"
          >
            {nextAction.btn} →
          </Link>
        </div>
      )}

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        {/* 求职流程向导 */}
        <FlowGuide steps={steps} />

        {/* 数据概览 */}
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-3 gap-4">
            {cards.map((c) => (
              <Link
                key={c.label}
                href={c.href}
                className="rounded-xl border border-zinc-200 bg-white p-4 text-center transition hover:shadow-sm"
              >
                <div className="text-3xl font-bold">{c.value}</div>
                <div className="mt-1 text-sm text-zinc-500">{c.label}</div>
              </Link>
            ))}
          </div>

          <div className="flex-1 rounded-xl border border-zinc-200 bg-white p-6">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-semibold">最近匹配</h2>
              <Link href="/matches" className="text-sm text-zinc-500 hover:text-zinc-900">
                全部 →
              </Link>
            </div>
            {loadingData ? (
              <p className="text-sm text-zinc-400">加载中...</p>
            ) : recentMatches.length === 0 ? (
              <div className="py-6 text-center">
                <p className="text-sm text-zinc-500">还没有匹配记录</p>
                <p className="mt-1 text-xs text-zinc-400">
                  完成前两步后，在这里发起匹配
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {recentMatches.map((m: any) => (
                  <div key={m.id} className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">匹配度 {m.score}</div>
                      <div className="text-sm text-zinc-500">
                        {m.suggestion?.split("\n")[0] || "查看详情"}
                      </div>
                    </div>
                    <Link
                      href="/matches"
                      className="text-sm font-medium text-zinc-900 underline"
                    >
                      查看
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
