"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { jobApi, JobItem } from "@/lib/api";

export default function JobsPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [jdText, setJdText] = useState("");
  const [parsing, setParsing] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const load = useCallback(() => {
    jobApi
      .list()
      .then(setJobs)
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
      return;
    }
    if (user) load();
  }, [loading, user, router, load]);

  const handleManual = async () => {
    if (jdText.trim().length < 20) {
      setError("JD 文本至少 20 个字符");
      return;
    }
    setError("");
    setSuccess("");
    setParsing(true);
    try {
      const res = await jobApi.manual(jdText);
      const p = res.job.parsed_json || {};
      setSuccess(
        `解析成功：${p.title || "未知岗位"} · ${p.skills?.length ?? 0} 项技能 · ${p.requirements?.length ?? 0} 条要求`
      );
      setJdText("");
      load();
    } catch (e: any) {
      setError(e.message || "解析失败");
    } finally {
      setParsing(false);
    }
  };

  const handleUpload = async (file: File | null) => {
    if (!file) return;
    setError("");
    setSuccess("");
    setParsing(true);
    try {
      const res = await jobApi.upload(file);
      const p = res.job.parsed_json || {};
      setSuccess(
        `解析成功：${p.title || "未知岗位"} · ${p.skills?.length ?? 0} 项技能`
      );
      load();
    } catch (e: any) {
      setError(e.message || "解析失败");
    } finally {
      setParsing(false);
    }
  };

  if (loading || !user) {
    return <div className="p-8 text-center text-zinc-400">加载中...</div>;
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-2xl font-bold">岗位 JD 管理</h1>
      <p className="mt-1 text-sm text-zinc-500">
        粘贴或上传招聘 JD，AI 抽取岗位、职责、技能、关键词
      </p>

      <div className="mt-6 rounded-xl border border-zinc-200 bg-white p-6">
        <label className="mb-2 block text-sm font-medium">粘贴 JD 文本</label>
        <textarea
          value={jdText}
          onChange={(e) => setJdText(e.target.value)}
          rows={8}
          className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-zinc-900"
          placeholder="粘贴招聘 JD 原文（岗位名称、职责、要求等）..."
        />
        <div className="mt-3 flex items-center gap-3">
          <button
            onClick={handleManual}
            disabled={parsing}
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-zinc-700 disabled:opacity-50"
          >
            {parsing ? "解析中..." : "解析 JD"}
          </button>
          <label className="cursor-pointer rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium transition hover:bg-zinc-100">
            上传文件
            <input
              type="file"
              accept=".pdf,.txt,.md"
              className="hidden"
              disabled={parsing}
              onChange={(e) => handleUpload(e.target.files?.[0] ?? null)}
            />
          </label>
        </div>
      </div>

      {error && (
        <div className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
          {error}
        </div>
      )}
      {success && (
        <div className="mt-4 rounded-lg bg-green-50 px-3 py-2 text-sm text-green-700">
          {success}
        </div>
      )}

      <div className="mt-8 space-y-3">
        {jobs.length === 0 ? (
          <div className="rounded-xl border border-dashed border-zinc-300 bg-white p-10 text-center">
            <p className="text-zinc-500">还没有 JD</p>
            <p className="mt-1 text-sm text-zinc-400">
              粘贴或上传第一个岗位 JD
            </p>
          </div>
        ) : (
          jobs.map((j) => {
            const p = j.parsed_json || {};
            return (
              <div
                key={j.id}
                className="flex items-center justify-between rounded-xl border border-zinc-200 bg-white p-4"
              >
                <div>
                  <div className="font-medium">{p.title || j.title || "未命名岗位"}</div>
                  <div className="mt-1 text-sm text-zinc-500">
                    {(p.company || "—")} · {p.location || "—"} ·{" "}
                    {p.salary || "薪资未标"} · {p.skills?.length ?? 0} 项技能 ·{" "}
                    {p.requirements?.length ?? 0} 条要求
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs text-zinc-400">
                  <span className="rounded bg-zinc-100 px-1.5 py-0.5">
                    {j.source === "upload" ? "上传" : "粘贴"}
                  </span>
                  {new Date(j.created_at).toLocaleString("zh-CN")}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
