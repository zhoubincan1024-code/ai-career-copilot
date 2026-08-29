"use client";

import { useEffect, useRef, useState } from "react";
import { interviewApi, jobApi, type InterviewDetail } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Phase = "idle" | "active" | "finished";

export default function InterviewPage() {
  const { user } = useAuth();
  const [phase, setPhase] = useState<Phase>("idle");
  const [jobs, setJobs] = useState<any[]>([]);
  const [selectedJob, setSelectedJob] = useState<string>("");
  const [interview, setInterview] = useState<InterviewDetail | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (user) {
      jobApi.list().then((r: any) => {
        const list = Array.isArray(r) ? r : r.jobs || [];
        setJobs(list);
        if (list.length > 0) setSelectedJob(list[0].id);
      });
    }
  }, [user]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [interview?.messages]);

  if (!user) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-20 text-center">
        <p className="text-zinc-600">请先登录后使用模拟面试</p>
      </div>
    );
  }

  const startInterview = async () => {
    setLoading(true);
    try {
      const iv = await interviewApi.create(selectedJob || undefined);
      setInterview(iv);
      setPhase("active");
    } finally {
      setLoading(false);
    }
  };

  const sendAnswer = async () => {
    if (!input.trim() || !interview || loading) return;
    const answer = input.trim();
    setInput("");
    setLoading(true);
    try {
      const res = await interviewApi.answer(interview.id, answer);
      setInterview(res.interview);
      if (res.interview.finished_at) setPhase("finished");
    } finally {
      setLoading(false);
    }
  };

  const endInterview = async () => {
    if (!interview) return;
    setLoading(true);
    try {
      const iv = await interviewApi.end(interview.id);
      setInterview(iv);
      setPhase("finished");
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setInterview(null);
    setPhase("idle");
    setInput("");
  };

  // ========== 未开始 ==========
  if (phase === "idle") {
    return (
      <div className="mx-auto max-w-2xl px-4 py-12">
        <div className="rounded-2xl border border-zinc-200 bg-white p-8">
          <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-zinc-900 text-2xl text-white">
            🎤
          </div>
          <h1 className="mt-5 text-2xl font-bold">AI 模拟面试</h1>
          <p className="mt-2 text-sm text-zinc-600">
            基于你的目标岗位 JD，AI 面试官将进行多轮连续追问，结束后输出结构化评分与复盘报告。
          </p>

          <div className="mt-6">
            <label className="block text-sm font-medium text-zinc-700">选择目标岗位</label>
            <select
              value={selectedJob}
              onChange={(e) => setSelectedJob(e.target.value)}
              className="mt-2 w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-zinc-900 focus:outline-none"
            >
              {jobs.length === 0 && <option value="">（请先上传岗位 JD）</option>}
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.title || "未命名岗位"} {j.company ? `· ${j.company}` : ""}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={startInterview}
            disabled={loading || jobs.length === 0}
            className="mt-6 w-full rounded-lg bg-zinc-900 px-6 py-2.5 text-sm font-medium text-white transition hover:bg-zinc-700 disabled:opacity-50"
          >
            {loading ? "正在生成面试题..." : "开始面试"}
          </button>
        </div>
      </div>
    );
  }

  // ========== 已结束：复盘报告 ==========
  if (phase === "finished" && interview) {
    const fb = interview.feedback;
    return (
      <div className="mx-auto max-w-3xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-xl font-bold">面试复盘报告</h1>
          <button
            onClick={reset}
            className="rounded-lg border border-zinc-300 px-4 py-1.5 text-sm transition hover:bg-zinc-100"
          >
            再来一场
          </button>
        </div>

        {/* 综合评分 */}
        <div className="rounded-2xl border border-zinc-200 bg-white p-6">
          <div className="flex items-center gap-6">
            <div className="flex h-20 w-20 flex-col items-center justify-center rounded-full bg-zinc-900 text-white">
              <span className="text-2xl font-bold">{interview.score ?? "--"}</span>
              <span className="text-xs opacity-70">综合分</span>
            </div>
            <div className="flex-1">
              <p className="text-sm text-zinc-500">能力维度评分</p>
              <div className="mt-2 space-y-2">
                {fb?.dimensions &&
                  Object.entries(fb.dimensions).map(([k, v]) => (
                    <div key={k} className="flex items-center gap-3">
                      <span className="w-16 text-xs text-zinc-600">{k}</span>
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-zinc-100">
                        <div
                          className="h-full rounded-full bg-zinc-900 transition-all"
                          style={{ width: `${v}%` }}
                        />
                      </div>
                      <span className="w-8 text-right text-xs font-medium">{v}</span>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        </div>

        {/* 逐题反馈 */}
        {fb?.per_question && fb.per_question.length > 0 && (
          <div className="mt-6 rounded-2xl border border-zinc-200 bg-white p-6">
            <h2 className="text-sm font-semibold text-zinc-900">逐题反馈</h2>
            <div className="mt-4 space-y-4">
              {fb.per_question.map((q, i) => (
                <div key={i} className="rounded-lg bg-zinc-50 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm font-medium text-zinc-800">Q{i + 1}. {q.question}</p>
                    <span className="shrink-0 rounded-full bg-zinc-900 px-2 py-0.5 text-xs text-white">
                      {q.score}分
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-zinc-500">回答：{q.answer}</p>
                  <p className="mt-1 text-xs text-zinc-600">点评：{q.feedback}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 改进建议 */}
        {fb?.suggestions && fb.suggestions.length > 0 && (
          <div className="mt-6 rounded-2xl border border-zinc-200 bg-white p-6">
            <h2 className="text-sm font-semibold text-zinc-900">改进建议</h2>
            <ul className="mt-3 space-y-2">
              {fb.suggestions.map((s, i) => (
                <li key={i} className="flex gap-2 text-sm text-zinc-600">
                  <span className="font-medium text-zinc-900">{i + 1}.</span>
                  <span>{s}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  // ========== 进行中：聊天界面 ==========
  return (
    <div className="mx-auto flex h-[calc(100vh-3.5rem)] max-w-3xl flex-col px-4">
      <div className="flex items-center justify-between border-b border-zinc-200 py-3">
        <div>
          <h1 className="text-sm font-semibold">AI 模拟面试进行中</h1>
          <p className="text-xs text-zinc-500">认真回答每一个问题，AI 会连续追问</p>
        </div>
        <button
          onClick={endInterview}
          disabled={loading}
          className="rounded-lg border border-zinc-300 px-3 py-1.5 text-xs transition hover:bg-zinc-100 disabled:opacity-50"
        >
          结束面试
        </button>
      </div>

      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto py-4">
        {interview?.messages.map((m) => (
          <div
            key={m.id}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                m.role === "user"
                  ? "rounded-br-sm bg-zinc-900 text-white"
                  : "rounded-bl-sm bg-zinc-100 text-zinc-800"
              }`}
            >
              <p className="whitespace-pre-wrap">{m.content}</p>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-bl-sm bg-zinc-100 px-4 py-3 text-sm text-zinc-500">
              AI 正在思考...
            </div>
          </div>
        )}
      </div>

      <div className="border-t border-zinc-200 py-3">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendAnswer();
              }
            }}
            placeholder="输入你的回答，Enter 发送..."
            rows={2}
            className="flex-1 resize-none rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-zinc-900 focus:outline-none"
          />
          <button
            onClick={sendAnswer}
            disabled={loading || !input.trim()}
            className="rounded-lg bg-zinc-900 px-5 text-sm font-medium text-white transition hover:bg-zinc-700 disabled:opacity-50"
          >
            发送
          </button>
        </div>
      </div>
    </div>
  );
}
