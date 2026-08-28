"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { resumeApi, ResumeItem } from "@/lib/api";

export default function ResumesPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [resumes, setResumes] = useState<ResumeItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const load = useCallback(() => {
    resumeApi
      .list()
      .then(setResumes)
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
      return;
    }
    if (user) load();
  }, [loading, user, router, load]);

  const handleUpload = async (file: File | null) => {
    if (!file) return;
    setError("");
    setSuccess("");
    setUploading(true);
    try {
      const res = await resumeApi.upload(file);
      const sum = res.parsed_summary;
      setSuccess(
        `解析成功：${sum?.name || "未知"} · ${sum?.skills ?? 0} 项技能 · ${sum?.projects ?? 0} 个项目`
      );
      load();
    } catch (e: any) {
      setError(e.message || "上传失败");
    } finally {
      setUploading(false);
    }
  };

  if (loading || !user) {
    return <div className="p-8 text-center text-zinc-400">加载中...</div>;
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-2xl font-bold">简历管理</h1>
      <p className="mt-1 text-sm text-zinc-500">
        上传 PDF / TXT / MD 简历，AI 自动解析为结构化数据
      </p>

      <div className="mt-6 flex items-center gap-3">
        <label className="cursor-pointer rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-zinc-700">
          {uploading ? "解析中..." : "上传简历"}
          <input
            type="file"
            accept=".pdf,.txt,.md"
            className="hidden"
            disabled={uploading}
            onChange={(e) => handleUpload(e.target.files?.[0] ?? null)}
          />
        </label>
        <span className="text-xs text-zinc-400">支持 PDF / TXT / MD，最大 5MB</span>
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
        {resumes.length === 0 ? (
          <div className="rounded-xl border border-dashed border-zinc-300 bg-white p-10 text-center">
            <p className="text-zinc-500">还没有简历</p>
            <p className="mt-1 text-sm text-zinc-400">上传第一份简历开始吧</p>
          </div>
        ) : (
          resumes.map((r) => {
            const p = r.parsed_json || {};
            const basic = p.basic_info || {};
            return (
              <div
                key={r.id}
                className="flex items-center justify-between rounded-xl border border-zinc-200 bg-white p-4"
              >
                <div>
                  <div className="font-medium">
                    {basic.name || "未命名简历"}
                    {r.status === "failed" && (
                      <span className="ml-2 rounded bg-red-50 px-1.5 py-0.5 text-xs text-red-600">
                        解析失败
                      </span>
                    )}
                    <span className="ml-2 rounded bg-zinc-100 px-1.5 py-0.5 text-xs text-zinc-500">
                      v{r.version}
                    </span>
                  </div>
                  <div className="mt-1 text-sm text-zinc-500">
                    {basic.email || "—"} · {p.skills?.length ?? 0} 项技能 ·{" "}
                    {p.education?.length ?? 0} 段教育 · {p.projects?.length ?? 0} 个项目
                  </div>
                </div>
                <div className="text-xs text-zinc-400">
                  {new Date(r.created_at).toLocaleString("zh-CN")}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
