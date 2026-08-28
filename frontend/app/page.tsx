"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";

export default function Home() {
  const { user, loading } = useAuth();

  const features = [
    {
      title: "简历解析",
      desc: "上传简历，AI 自动抽取教育、技能、项目等结构化信息",
    },
    {
      title: "岗位匹配",
      desc: "粘贴/上传 JD，获取可解释的匹配分、差距分析和改进建议",
    },
    {
      title: "AI 模拟面试",
      desc: "针对目标岗位连续追问，输出结构化评分与复盘（即将上线）",
    },
  ];

  return (
    <div className="mx-auto max-w-6xl px-4">
      {/* Hero */}
      <section className="flex flex-col items-center py-20 text-center">
        <h1 className="max-w-3xl text-4xl font-bold leading-tight sm:text-5xl">
          AI 求职助手
          <span className="block text-zinc-500">从简历到面试的一站式闭环</span>
        </h1>
        <p className="mt-6 max-w-xl text-lg text-zinc-600">
          用 AI 解析你的简历、匹配心仪岗位、指出差距并给出改进建议，
          让每一次投递都更有把握。
        </p>
        <div className="mt-8 flex gap-3">
          {!loading && user ? (
            <Link
              href="/dashboard"
              className="rounded-lg bg-zinc-900 px-6 py-3 text-white transition hover:bg-zinc-700"
            >
              进入仪表盘
            </Link>
          ) : (
            <>
              <Link
                href="/register"
                className="rounded-lg bg-zinc-900 px-6 py-3 text-white transition hover:bg-zinc-700"
              >
                免费注册
              </Link>
              <Link
                href="/login"
                className="rounded-lg border border-zinc-300 px-6 py-3 transition hover:bg-zinc-100"
              >
                登录
              </Link>
            </>
          )}
        </div>
      </section>

      {/* 流程 */}
      <section className="mb-16">
        <div className="grid gap-4 sm:grid-cols-3">
          {[
            { n: "01", t: "上传简历", d: "PDF / 文本，AI 结构化解析" },
            { n: "02", t: "匹配岗位", d: "粘贴或上传 JD，获得可解释匹配度" },
            { n: "03", t: "优化投递", d: "根据差距分析补齐短板、定向优化" },
          ].map((s) => (
            <div
              key={s.n}
              className="rounded-xl border border-zinc-200 bg-white p-6"
            >
              <div className="text-sm font-semibold text-zinc-400">{s.n}</div>
              <div className="mt-2 text-lg font-semibold">{s.t}</div>
              <div className="mt-1 text-sm text-zinc-600">{s.d}</div>
            </div>
          ))}
        </div>
      </section>

      {/* 特性 */}
      <section className="mb-20">
        <h2 className="mb-6 text-2xl font-bold">核心能力</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          {features.map((f) => (
            <div
              key={f.title}
              className="rounded-xl border border-zinc-200 bg-white p-6"
            >
              <div className="font-semibold">{f.title}</div>
              <div className="mt-1 text-sm text-zinc-600">{f.desc}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
