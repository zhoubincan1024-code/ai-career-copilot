"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { jobApi, matchApi, resumeApi } from "@/lib/api";

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [stats, setStats] = useState({ resumes: 0, jobs: 0, matches: 0 });
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

  const cards = [
    { label: "简历", value: stats.resumes, href: "/resumes", action: "上传简历" },
    { label: "岗位 JD", value: stats.jobs, href: "/jobs", action: "添加 JD" },
    { label: "匹配记录", value: stats.matches, href: "/matches", action: "发起匹配" },
  ];

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-2xl font-bold">
        你好，{user.name || user.email}
      </h1>
      <p className="mt-1 text-sm text-zinc-500">
        {user.target_role ? `目标岗位：${user.target_role}` : "完善简历和目标岗位，开始匹配"}
      </p>

      <div className="mt-8 grid gap-4 sm:grid-cols-3">
        {cards.map((c) => (
          <Link
            key={c.label}
            href={c.href}
            className="rounded-xl border border-zinc-200 bg-white p-6 transition hover:shadow-sm"
          >
            <div className="text-sm text-zinc-500">{c.label}</div>
            <div className="mt-2 text-3xl font-bold">{c.value}</div>
            <div className="mt-3 text-sm font-medium text-zinc-900">
              {c.action} →
            </div>
          </Link>
        ))}
      </div>

      <section className="mt-12">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">最近匹配</h2>
          <Link href="/matches" className="text-sm text-zinc-500 hover:text-zinc-900">
            全部 →
          </Link>
        </div>
        {loadingData ? (
          <p className="text-sm text-zinc-400">加载中...</p>
        ) : recentMatches.length === 0 ? (
          <div className="rounded-xl border border-dashed border-zinc-300 bg-white p-10 text-center">
            <p className="text-zinc-500">还没有匹配记录</p>
            <p className="mt-1 text-sm text-zinc-400">
              先上传简历和 JD，然后去「匹配」页发起一次匹配
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {recentMatches.map((m: any) => (
              <div
                key={m.id}
                className="flex items-center justify-between rounded-xl border border-zinc-200 bg-white p-4"
              >
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
      </section>
    </div>
  );
}
