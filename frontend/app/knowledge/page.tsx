"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { documentApi, ragApi } from "@/lib/api";

interface DocItem {
  id: string;
  title: string;
  source: string;
  status: string;
  chunk_count: number;
  created_at: string;
}

interface Source {
  title: string;
  document_id: string;
  similarity: number;
  excerpt: string;
}

interface QARecordItem {
  id?: string;
  question: string;
  answer: string;
  sources: Source[];
  created_at?: string | null;
}

export default function KnowledgePage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [docs, setDocs] = useState<DocItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [view, setView] = useState<QARecordItem | null>(null);
  const [records, setRecords] = useState<QARecordItem[]>([]);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
      return;
    }
    if (user) {
      loadDocs();
      loadRecords();
    }
  }, [loading, user, router]);

  const loadDocs = async () => {
    try {
      const res = await documentApi.list();
      setDocs(res.documents || []);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const loadRecords = async () => {
    try {
      const res = await ragApi.records();
      setRecords(res.records || []);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      await documentApi.upload(file);
      await loadDocs();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await documentApi.remove(id);
      await loadDocs();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || asking) return;
    setAsking(true);
    setError("");
    try {
      const q = question.trim();
      const res = await ragApi.ask(q);
      const record: QARecordItem = {
        id: res.record_id,
        question: q,
        answer: res.answer,
        sources: res.sources || [],
        created_at: res.created_at || null,
      };
      setRecords((prev) => [record, ...prev]);
      setView(record);
      setQuestion("");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setAsking(false);
    }
  };

  const handleDeleteRecord = async (id: string) => {
    try {
      await ragApi.removeRecord(id);
      setRecords((prev) => prev.filter((r) => r.id !== id));
      if (view?.id === id) setView(null);
    } catch (e: any) {
      setError(e.message);
    }
  };

  if (loading || !user) {
    return <div className="p-8 text-center text-zinc-400">加载中...</div>;
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="text-2xl font-bold">AI 知识库</h1>
      <p className="mt-1 text-sm text-zinc-500">
        上传面试资料 / 岗位知识，AI 基于你的资料回答问题并标注来源
      </p>

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-600">
          {error}
        </div>
      )}

      <div className="mt-8 grid gap-8 lg:grid-cols-2">
        {/* 左侧：文档管理 */}
        <div>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold">知识库文档</h2>
            <label className="cursor-pointer rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-zinc-700">
              {uploading ? "索引中..." : "上传文档"}
              <input
                ref={fileRef}
                type="file"
                accept=".pdf,.txt,.md"
                className="hidden"
                onChange={handleUpload}
                disabled={uploading}
              />
            </label>
          </div>

          {docs.length === 0 ? (
            <div className="rounded-xl border border-dashed border-zinc-300 p-8 text-center">
              <p className="text-sm text-zinc-500">还没有文档</p>
              <p className="mt-1 text-xs text-zinc-400">
                支持 PDF / TXT / MD，上传后 AI 自动建立向量索引
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {docs.map((d) => (
                <div
                  key={d.id}
                  className="flex items-center justify-between rounded-lg border border-zinc-200 bg-white p-4"
                >
                  <div>
                    <div className="font-medium">{d.title}</div>
                    <div className="mt-1 text-xs text-zinc-500">
                      {d.status === "indexed" ? (
                        <span className="text-green-600">✓ 已索引</span>
                      ) : d.status === "processing" ? (
                        <span className="text-amber-600">处理中...</span>
                      ) : (
                        <span className="text-red-600">失败</span>
                      )}
                      {" · "}{d.chunk_count} 个切片 · {new Date(d.created_at).toLocaleDateString()}
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(d.id)}
                    className="text-sm text-zinc-400 hover:text-red-600"
                  >
                    删除
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 右侧：智能问答 + 问答记录 */}
        <div>
          <h2 className="mb-4 font-semibold">智能问答</h2>
          <form onSubmit={handleAsk} className="flex gap-2">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="问一个面试相关问题..."
              className="flex-1 rounded-lg border border-zinc-300 px-4 py-2 text-sm focus:border-zinc-900 focus:outline-none"
              disabled={asking || docs.length === 0}
            />
            <button
              type="submit"
              disabled={asking || docs.length === 0 || !question.trim()}
              className="rounded-lg bg-zinc-900 px-5 py-2 text-sm font-medium text-white transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {asking ? "思考中..." : "提问"}
            </button>
          </form>

          {docs.length === 0 && (
            <p className="mt-3 text-xs text-zinc-400">先上传文档后才能提问</p>
          )}

          {view && (
            <div className="mt-6 space-y-4">
              <div className="rounded-xl border border-zinc-200 bg-white p-5">
                <div className="text-xs text-zinc-400">问题</div>
                <p className="mt-0.5 text-sm font-medium text-zinc-800">{view.question}</p>
                <h3 className="mb-2 mt-4 text-sm font-semibold text-zinc-700">回答</h3>
                <p className="whitespace-pre-line text-sm leading-relaxed text-zinc-800">
                  {view.answer}
                </p>
              </div>

              {view.sources.length > 0 && (
                <div className="rounded-xl border border-zinc-200 bg-white p-5">
                  <h3 className="mb-3 text-sm font-semibold text-zinc-700">引用来源</h3>
                  <div className="space-y-3">
                    {view.sources.map((s, i) => (
                      <div key={i} className="border-l-2 border-zinc-300 pl-3">
                        <div className="text-xs font-medium text-zinc-600">
                          [{i + 1}] {s.title}{" "}
                          <span className="text-zinc-400">
                            (相似度 {Math.round(s.similarity * 100)}%)
                          </span>
                        </div>
                        <p className="mt-1 text-xs text-zinc-500">{s.excerpt}...</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 问答记录 */}
          <div className="mt-8">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-semibold">问答记录</h3>
              <span className="text-xs text-zinc-400">{records.length} 条</span>
            </div>
            {records.length === 0 ? (
              <div className="rounded-xl border border-dashed border-zinc-300 p-6 text-center">
                <p className="text-sm text-zinc-500">还没有问答记录</p>
                <p className="mt-1 text-xs text-zinc-400">提问后会自动保存，方便随时回看</p>
              </div>
            ) : (
              <div className="space-y-2">
                {records.map((r) => (
                  <div
                    key={r.id}
                    className="flex items-center justify-between gap-2 rounded-lg border border-zinc-200 bg-white p-3"
                  >
                    <button
                      onClick={() => setView(r)}
                      className={`min-w-0 flex-1 text-left ${
                        view?.id === r.id ? "" : "hover:opacity-80"
                      }`}
                    >
                      <div
                        className={`truncate text-sm font-medium ${
                          view?.id === r.id ? "text-zinc-900" : "text-zinc-800"
                        }`}
                      >
                        {r.question}
                      </div>
                      <div className="mt-0.5 text-xs text-zinc-400">
                        {r.created_at ? new Date(r.created_at).toLocaleString() : ""}
                      </div>
                    </button>
                    <button
                      onClick={() => r.id && handleDeleteRecord(r.id)}
                      className="shrink-0 text-sm text-zinc-400 hover:text-red-600"
                    >
                      删除
                    </button>
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
