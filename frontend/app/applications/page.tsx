"use client";

import { useEffect, useState } from "react";
import {
  applicationApi,
  jobApi,
  type Application,
  type ApplicationStats,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";

const STATUS_OPTIONS = [
  { value: "applied", label: "已投递", color: "bg-blue-100 text-blue-700" },
  { value: "online_test", label: "笔试中", color: "bg-amber-100 text-amber-700" },
  { value: "interview", label: "面试中", color: "bg-purple-100 text-purple-700" },
  { value: "offer", label: "已 Offer", color: "bg-green-100 text-green-700" },
  { value: "rejected", label: "已拒绝", color: "bg-red-100 text-red-700" },
];

const FILTER_TABS = [
  { value: "", label: "全部" },
  { value: "applied", label: "已投递" },
  { value: "online_test", label: "笔试中" },
  { value: "interview", label: "面试中" },
  { value: "offer", label: "Offer" },
  { value: "rejected", label: "已拒绝" },
];

function statusColor(status: string) {
  return STATUS_OPTIONS.find((s) => s.value === status)?.color || "bg-zinc-100 text-zinc-700";
}

export default function ApplicationsPage() {
  const { user } = useAuth();
  const [apps, setApps] = useState<Application[]>([]);
  const [stats, setStats] = useState<ApplicationStats | null>(null);
  const [filter, setFilter] = useState("");
  const [jobs, setJobs] = useState<any[]>([]);
  const [selectedJob, setSelectedJob] = useState("");
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    const [listRes, statsRes] = await Promise.all([
      applicationApi.list(filter || undefined),
      applicationApi.stats(),
    ]);
    setApps(listRes.applications || []);
    setStats(statsRes);
  };

  useEffect(() => {
    if (!user) return;
    refresh();
    jobApi.list().then((r: any) => {
      const list = Array.isArray(r) ? r : r.jobs || [];
      setJobs(list);
      if (list.length > 0) setSelectedJob(list[0].id);
    });
  }, [user, filter]);

  if (!user) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-20 text-center">
        <p className="text-zinc-600">请先登录</p>
      </div>
    );
  }

  const handleCreate = async () => {
    if (!selectedJob) return;
    setLoading(true);
    try {
      await applicationApi.create(selectedJob);
      await refresh();
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (id: string, status: string) => {
    await applicationApi.update(id, { status });
    await refresh();
  };

  const handleDelete = async (id: string) => {
    await applicationApi.remove(id);
    await refresh();
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">投递管理</h1>
      </div>

      {/* 统计卡片 */}
      {stats && (
        <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="rounded-xl border border-zinc-200 bg-white p-4">
            <p className="text-xs text-zinc-500">总投递</p>
            <p className="mt-1 text-2xl font-bold">{stats.total}</p>
          </div>
          <div className="rounded-xl border border-zinc-200 bg-white p-4">
            <p className="text-xs text-zinc-500">在途</p>
            <p className="mt-1 text-2xl font-bold text-blue-600">{stats.active}</p>
          </div>
          <div className="rounded-xl border border-zinc-200 bg-white p-4">
            <p className="text-xs text-zinc-500">Offer 率</p>
            <p className="mt-1 text-2xl font-bold text-green-600">{stats.offer_rate}%</p>
          </div>
          <div className="rounded-xl border border-zinc-200 bg-white p-4">
            <p className="text-xs text-zinc-500">拒绝率</p>
            <p className="mt-1 text-2xl font-bold text-red-600">{stats.reject_rate}%</p>
          </div>
        </div>
      )}

      {/* 漏斗图 */}
      {stats && stats.funnel.length > 0 && (
        <div className="mt-6 rounded-xl border border-zinc-200 bg-white p-5">
          <h2 className="text-sm font-semibold">投递漏斗</h2>
          <div className="mt-4 space-y-3">
            {stats.funnel.map((f, i) => {
              const maxCount = Math.max(...stats.funnel.map((x) => x.count), 1);
              const width = (f.count / maxCount) * 100;
              return (
                <div key={f.status} className="flex items-center gap-3">
                  <span className="w-16 text-xs text-zinc-600">{f.label}</span>
                  <div className="h-6 flex-1 overflow-hidden rounded bg-zinc-100">
                    <div
                      className="flex h-full items-center justify-end rounded bg-zinc-900 px-2 text-xs text-white transition-all"
                      style={{ width: `${Math.max(width, 8)}%` }}
                    >
                      {f.count}
                    </div>
                  </div>
                  <span className="w-20 text-right text-xs text-zinc-500">
                    {i > 0 ? `上阶段 ${f.from_prev_pct}%` : "100%"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 新建投递 */}
      <div className="mt-6 flex items-center gap-3 rounded-xl border border-zinc-200 bg-white p-4">
        <select
          value={selectedJob}
          onChange={(e) => setSelectedJob(e.target.value)}
          className="flex-1 rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-zinc-900 focus:outline-none"
        >
          {jobs.length === 0 && <option value="">（请先上传岗位 JD）</option>}
          {jobs.map((j) => (
            <option key={j.id} value={j.id}>
              {j.title || "未命名"} {j.company ? `· ${j.company}` : ""}
            </option>
          ))}
        </select>
        <button
          onClick={handleCreate}
          disabled={loading || jobs.length === 0}
          className="rounded-lg bg-zinc-900 px-5 py-2 text-sm font-medium text-white transition hover:bg-zinc-700 disabled:opacity-50"
        >
          {loading ? "添加中..." : "+ 添加投递"}
        </button>
      </div>

      {/* 筛选标签 */}
      <div className="mt-6 flex flex-wrap gap-2">
        {FILTER_TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setFilter(tab.value)}
            className={`rounded-full px-3 py-1 text-xs transition ${
              filter === tab.value
                ? "bg-zinc-900 text-white"
                : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* 投递列表 */}
      <div className="mt-4 space-y-3">
        {apps.length === 0 && (
          <div className="rounded-xl border border-dashed border-zinc-300 p-10 text-center text-sm text-zinc-500">
            暂无投递记录
          </div>
        )}
        {apps.map((app) => (
          <div
            key={app.id}
            className="flex items-center justify-between rounded-xl border border-zinc-200 bg-white p-4"
          >
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-medium text-zinc-900">{app.job_title || "未命名岗位"}</span>
                <span className={`rounded-full px-2 py-0.5 text-xs ${statusColor(app.status)}`}>
                  {app.status_label}
                </span>
              </div>
              {app.job_company && (
                <p className="mt-0.5 text-xs text-zinc-500">{app.job_company}</p>
              )}
              {app.note && <p className="mt-1 text-xs text-zinc-600">备注：{app.note}</p>}
              <p className="mt-1 text-xs text-zinc-400">
                投递时间：{new Date(app.applied_at).toLocaleDateString("zh-CN")}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={app.status}
                onChange={(e) => handleStatusChange(app.id, e.target.value)}
                className="rounded-lg border border-zinc-300 px-2 py-1 text-xs focus:border-zinc-900 focus:outline-none"
              >
                {STATUS_OPTIONS.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
              <button
                onClick={() => handleDelete(app.id)}
                className="rounded-lg border border-zinc-300 px-2 py-1 text-xs text-zinc-500 transition hover:bg-red-50 hover:text-red-600"
              >
                删除
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
