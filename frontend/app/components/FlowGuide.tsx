"use client";

import Link from "next/link";

/**
 * 求职流程向导：把「简历→JD→匹配→优化→面试」串成主线闭环
 * 根据用户已有数据自动标记每步状态
 */
interface FlowStep {
  n: number;
  title: string;
  desc: string;
  done: boolean;
  href: string;
  soon?: boolean;
}

export default function FlowGuide({
  steps,
}: {
  steps: FlowStep[];
}) {
  const doneCount = steps.filter((s) => s.done).length;

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">求职流程</h2>
        <span className="text-sm text-zinc-500">
          已完成 {doneCount} / {steps.length} 步
        </span>
      </div>

      {/* 进度条 */}
      <div className="mb-6 h-1.5 w-full overflow-hidden rounded-full bg-zinc-100">
        <div
          className="h-full rounded-full bg-zinc-900 transition-all"
          style={{ width: `${(doneCount / steps.length) * 100}%` }}
        />
      </div>

      <ol className="space-y-1">
        {steps.map((s, i) => (
          <li key={s.n}>
            <Link
              href={s.href}
              className={`group flex items-center gap-4 rounded-lg px-3 py-3 transition ${
                s.done
                  ? "hover:bg-green-50"
                  : i === doneCount
                    ? "bg-zinc-50 hover:bg-zinc-100"
                    : "hover:bg-zinc-50"
              }`}
            >
              {/* 状态圆标 */}
              <span
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-medium ${
                  s.done
                    ? "bg-green-100 text-green-700"
                    : i === doneCount
                      ? "bg-zinc-900 text-white"
                      : "bg-zinc-100 text-zinc-400"
                }`}
              >
                {s.done ? "✓" : s.n}
              </span>

              <span className="flex-1">
                <span className="block font-medium">
                  {s.title}
                  {s.soon && (
                    <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-700">
                      即将上线
                    </span>
                  )}
                </span>
                <span className="block text-sm text-zinc-500">{s.desc}</span>
              </span>

              <span
                className={`text-sm ${
                  i === doneCount && !s.done
                    ? "font-medium text-zinc-900"
                    : s.done
                      ? "text-green-600"
                      : "text-zinc-300"
                }`}
              >
                {s.done ? "已完成" : i === doneCount ? "进行中 →" : "待办"}
              </span>
            </Link>
            {i < steps.length - 1 && (
              <div className="ml-[26px] h-3 w-px bg-zinc-200" />
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
