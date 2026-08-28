"use client";

import Link from "next/link";

export default function InterviewPage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-20 text-center">
      <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-zinc-900 text-2xl text-white">
        🎤
      </div>
      <h1 className="mt-6 text-2xl font-bold">AI 模拟面试</h1>
      <p className="mt-3 text-zinc-600">
        针对你的目标岗位进行连续追问，AI 逐题打分并输出结构化复盘报告。
      </p>
      <div className="mt-6 inline-block rounded-lg bg-amber-50 px-4 py-2 text-sm text-amber-700">
        此功能正在开发中（第 14 步），敬请期待
      </div>
      <div className="mt-8">
        <Link
          href="/matches"
          className="rounded-lg bg-zinc-900 px-6 py-2.5 text-sm font-medium text-white transition hover:bg-zinc-700"
        >
          先去完成岗位匹配 →
        </Link>
      </div>
    </div>
  );
}
