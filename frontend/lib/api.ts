/**
 * API 客户端：封装 fetch，自动注入 JWT token
 * 所有后端请求都通过这里，统一处理认证与错误
 */

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

const TOKEN_KEY = "aicolp_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

function extractError(data: any, status: number): string {
  if (data?.detail) {
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail
        .map((d: any) => d.msg || JSON.stringify(d))
        .join("；");
    }
    return JSON.stringify(data.detail);
  }
  if (data?.message) return data.message;
  return `请求失败 (${status})`;
}

async function request<T = any>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  // 非 FormData 时默认 JSON
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch {
    throw new Error("无法连接后端服务，请确认后端已在 8000 端口运行");
  }

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(extractError(data, res.status));
  }
  // 204 No Content 没有响应体
  if (res.status === 204) return null as unknown as T;
  return res.json() as Promise<T>;
}

// ---------- 认证 ----------
export const authApi = {
  register: (body: { email: string; password: string; name?: string; target_role?: string }) =>
    request("/auth/register", { method: "POST", body: JSON.stringify(body) }),
  login: (body: { email: string; password: string }) =>
    request<{ access_token: string; token_type: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  me: () => request("/auth/me"),
};

// ---------- 简历 ----------
export const resumeApi = {
  upload: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request("/resumes/upload", { method: "POST", body: fd });
  },
  list: () => request<any[]>("/resumes"),
  get: (id: string) => request(`/resumes/${id}`),
  remove: (id: string) => request(`/resumes/${id}`, { method: "DELETE" }),
};

// ---------- JD ----------
export const jobApi = {
  upload: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request("/jobs/upload", { method: "POST", body: fd });
  },
  manual: (jdText: string) =>
    request("/jobs/manual", {
      method: "POST",
      body: JSON.stringify({ jd_text: jdText }),
    }),
  list: () => request<any[]>("/jobs"),
  get: (id: string) => request(`/jobs/${id}`),
};

// ---------- 匹配 ----------
export const matchApi = {
  create: (resumeId: string, jobId: string) =>
    request("/matches", {
      method: "POST",
      body: JSON.stringify({ resume_id: resumeId, job_id: jobId }),
    }),
  list: () => request<any[]>("/matches"),
  get: (id: string) => request(`/matches/${id}`),
};

// ---------- 类型 ----------
export interface ResumeItem {
  id: string;
  file_url?: string;
  parsed_json?: any;
  version: number;
  status: string;
  created_at: string;
}

export interface JobItem {
  id: string;
  title?: string;
  company?: string;
  jd_text?: string;
  parsed_json?: any;
  source: string;
  created_at: string;
}

export interface MatchItem {
  id: string;
  resume_id: string;
  job_id: string;
  score: string;
  dimension_json?: { skill: number; experience: number; education: number; expression: number };
  strength_json?: any[];
  gap_json?: any[];
  suggestion?: string;
  created_at: string;
}

// ---------- 知识库文档 ----------
export const documentApi = {
  upload: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request("/documents/upload", { method: "POST", body: fd });
  },
  list: () => request<{ documents: any[] }>("/documents"),
  remove: (id: string) => request(`/documents/${id}`, { method: "DELETE" }),
};

// ---------- RAG 问答 ----------
export const ragApi = {
  ask: (question: string) =>
    request<{ answer: string; sources: any[]; retrieved: any[] }>("/rag/ask", {
      method: "POST",
      body: JSON.stringify({ question }),
    }),
};
// ---------- 模拟面试 ----------
export interface InterviewMessage {
  id: string;
  role: "assistant" | "user";
  content: string;
  created_at: string;
}

export interface InterviewDetail {
  id: string;
  job_id: string | null;
  score: number | null;
  feedback: {
    dimensions: Record<string, number>;
    per_question: Array<{ question: string; answer: string; score: number; feedback: string }>;
    suggestions: string[];
  } | null;
  started_at: string;
  finished_at: string | null;
  messages: InterviewMessage[];
}

export const interviewApi = {
  list: () => request<{ interviews: any[] }>("/interviews"),
  create: (jobId?: string) =>
    request<InterviewDetail>("/interviews", {
      method: "POST",
      body: JSON.stringify({ job_id: jobId || null }),
    }),
  get: (id: string) => request<InterviewDetail>(`/interviews/${id}`),
  answer: (id: string, answer: string) =>
    request<{ message: InterviewMessage; interview: InterviewDetail }>(
      `/interviews/${id}/answer`,
      { method: "POST", body: JSON.stringify({ answer }) }
    ),
  end: (id: string) =>
    request<InterviewDetail>(`/interviews/${id}/end`, { method: "POST" }),
};
// ---------- 投递管理 ----------
export interface Application {
  id: string;
  job_id: string;
  job_title: string | null;
  job_company: string | null;
  status: string;
  status_label: string;
  note: string | null;
  applied_at: string;
}

export interface ApplicationStats {
  total: number;
  active: number;
  offer_rate: number;
  reject_rate: number;
  counts: Record<string, number>;
  funnel: Array<{
    status: string;
    label: string;
    count: number;
    from_start_pct: number;
    from_prev_pct: number;
  }>;
}

export const applicationApi = {
  list: (status?: string) =>
    request<{ applications: Application[] }>(
      status ? "/applications?status=" + status : "/applications"
    ),
  create: (jobId: string, status = "applied", note?: string) =>
    request<Application>("/applications", {
      method: "POST",
      body: JSON.stringify({ job_id: jobId, status, note }),
    }),
  update: (id: string, data: { status?: string; note?: string }) =>
    request<Application>(`/applications/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  remove: (id: string) => request(`/applications/${id}`, { method: "DELETE" }),
  stats: () => request<ApplicationStats>("/applications/stats"),
};