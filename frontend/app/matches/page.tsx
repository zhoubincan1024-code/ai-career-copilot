"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { jobApi, matchApi, resumeApi, MatchItem, JobItem, ResumeItem } from "@/lib/api";

const DIM_LABELS: Record<string, string> = {
  skill: "技能",
  experience: "经验",
  education: "学历",
  expression: "表达",
};

export default function MatchesPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [resumes, setResumes] = useState<ResumeItem[]>([]);
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [matches, setMatches] = useState<MatchItem[]>([]);
  const [resumeId, setResumeId] = useState("");
  const [jobId, setJobId] = useState("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<MatchItem | null>(null);

  const load = useCallback(() => {
    Promise.all([resumeApi.list(), jobApi.list(), matchApi.list()])
      .then(([rs, js, ms]) => {
        setResumes(rs);
        setJobs(js);
        setMatches(ms);
        setError("");
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
      return;
    }
    if (user) load();
  }, [loading, user, router, load]);

  const handleMatch = async () => {
    if (!resumeId || !jobId) {
      setError("请先选择简历和 JD");
      return;
    }
    setError("");
    setRunning(true);
    try {
      const m = await matchApi.create(resumeId, jobId);
      setResult(m);
      load();
    } catch (e: any) {
      setError(e.message || "匹配失败");
    } finally {
      setRunning(false);
    }
  };

  const scoreNum = (s?: string) => (s ? Number(s) : 0);
  const scoreColor = (n: number) =>
    n >= 80 ? "text-green-600" : n >= 60 ? "text-amber-600" : "text-red-500";

  if (loading || !user) {
    return <div className="p-8 text-center text-zinc-400">加载中...</div>;
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-2xl font-bold">岗位匹配</h1>
      <p className="mt-1 text-sm text-zinc-500">
        选择简历和 JD，生成可解释的匹配度、优势与差距分析
      </p>

      <div className="mt-6 rounded-xl border border-zinc-200 bg-white p-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium">选择简历</label>
            <select
              value={resumeId}
              onChange={(e) => setResumeId(e.target.value)}
              className="w-full rounded-lg border border-zinc-300 px-3 py-2 outline-none focus:border-zinc-900"
            >
              <option value="">请选择简历</option>
              {resumes.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.parsed_json?.basic_info?.name || "未命名简历"} (v{r.version})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">选择 JD</label>
            <select
              value={jobId}
              onChange={(e) => setJobId(e.target.value)}
              className="w-full rounded-lg border border-zinc-300 px-3 py-2 outline-none focus:border-zinc-900"
            >
              <option value="">请选择 JD</option>
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.parsed_json?.title || j.title || "未命名岗位"}
                </option>
              ))}
            </select>
          </div>
        </div>
        <button
          onClick={handleMatch}
          disabled={running}
          className="mt-4 rounded-lg bg-zinc-900 px-5 py-2 text-sm font-medium text-white transition hover:bg-zinc-700 disabled:opacity-50"
        >
          {running ? "匹配分析中（约 10~20 秒）..." : "发起匹配"}
        </button>
      </div>

      {error && (
        <div className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
          {error}
        </div>
      )}

      {/* 匹配结果 */}
      {result && (
        <div className="mt-8">
          <div className="flex items-center gap-4 rounded-xl border border-zinc-200 bg-white p-6">
            <div className={`text-4xl font-bold ${scoreColor(scoreNum(result.score))}`}>
              {result.score}
            </div>
            <div className="flex-1">
              <div className="font-medium">综合匹配度</div>
              <div className="mt-1 text-sm text-zinc-500">
                {result.suggestion?.split("\n")[0] || ""}
              </div>
            </div>
          </div>

          {/* 维度 */}
          <div className="mt-4 grid gap-3 sm:grid-cols-4">
            {Object.entries(result.dimension_json || {}).map(([k, v]) => (
              <div
                key={k}
                className="rounded-xl border border-zinc-200 bg-white p-4"
              >
                <div className="text-sm text-zinc-500">{DIM_LABELS[k] || k}</div>
                <div className="mt-1 text-2xl font-bold">{v}</div>
              </div>
            ))}
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            {/* 优势 */}
            <section>
              <h2 className="mb-3 text-lg font-semibold">✅ 优势</h2>
              <div className="space-y-3">
                {(result.strength_json || []).map((s, i) => (
                  <div
                    key={i}
                    className="rounded-xl border border-green-100 bg-green-50/50 p-4"
                  >
                    <div className="font-medium">{s.title}</div>
                    <div className="mt-1 text-sm text-zinc-600">{s.detail}</div>
                  </div>
                ))}
              </div>
            </section>

            {/* 差距 */}
            <section>
              <h2 className="mb-3 text-lg font-semibold">⚠️ 差距</h2>
              <div className="space-y-3">
                {(result.gap_json || []).map((g, i) => (
                  <div
                    key={i}
                    className="rounded-xl border border-amber-100 bg-amber-50/50 p-4"
                  >
                    <div className="flex items-center gap-2 font-medium">
                      {g.title}
                      <span
                        className={`rounded px-1.5 py-0.5 text-xs ${
                          g.severity === "high"
                            ? "bg-red-100 text-red-700"
                            : g.severity === "medium"
                              ? "bg-amber-100 text-amber-700"
                              : "bg-zinc-100 text-zinc-600"
                        }`}
                      >
                        {g.severity === "high" ? "高" : g.severity === "medium" ? "中" : "低"}
                      </span>
                    </div>
                    <div className="mt-1 text-sm text-zinc-600">{g.detail}</div>
                  </div>
                ))}
              </div>
            </section>
          </div>

          {/* 建议 */}
          {result.suggestion && (
            <section className="mt-6 rounded-xl border border-zinc-200 bg-white p-6">
              <h2 className="mb-2 text-lg font-semibold">💡 行动建议</h2>
              <p className="whitespace-pre-line text-sm text-zinc-600">
                {result.suggestion}
              </p>
            </section>
          )}

          {/* 闭环衔接：去优化简历 */}
          <div className="mt-6 flex flex-col items-start justify-between gap-4 rounded-xl border border-zinc-200 bg-white p-6 sm:flex-row sm:items-center">
            <div>
              <div className="font-semibold">下一步：根据差距优化简历</div>
              <div className="mt-1 text-sm text-zinc-500">
                按上面的建议补齐技能关键词、完善项目描述后，重新上传一份新版本简历再匹配
              </div>
            </div>
            <Link
              href="/resumes"
              className="shrink-0 rounded-lg bg-zinc-900 px-5 py-2 text-sm font-medium text-white transition hover:bg-zinc-700"
            >
              去优化简历 →
            </Link>
          </div>
        </div>
      )}

      {/* 历史匹配 */}
      <section className="mt-12">
        <h2 className="mb-4 text-lg font-semibold">匹配记录</h2>
        {matches.length === 0 ? (
          <div className="rounded-xl border border-dashed border-zinc-300 bg-white p-10 text-center">
            <p className="text-zinc-500">还没有匹配记录</p>
          </div>
        ) : (
          <div className="space-y-3">
            {matches.map((m) => (
              <div
                key={m.id}
                className="flex items-center justify-between rounded-xl border border-zinc-200 bg-white p-4"
              >
                <div>
                  <div className={`text-lg font-bold ${scoreColor(scoreNum(m.score))}`}>
                    {m.score}
                  </div>
                  <div className="text-xs text-zinc-400">
                    {new Date(m.created_at).toLocaleString("zh-CN")}
                  </div>
                </div>
                <button
                  onClick={() => setResult(m)}
                  className="text-sm font-medium text-zinc-900 underline"
                >
                  查看详情
                </button>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
