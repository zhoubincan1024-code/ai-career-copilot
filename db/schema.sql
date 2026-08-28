-- ============================================================
-- AI Career Copilot · 数据库 Schema
-- PostgreSQL 17 + pgvector
-- 版本: v0.1  |  日期: 2026-08-28
-- 说明: 对应 docs/database.md，第 5 步产出
-- 前置: CREATE EXTENSION vector;  (pgvector，第 13 步 RAG 需要)
--       也可先去掉 vector 列/扩展后执行本文件
-- ============================================================

-- ---------- 扩展 ----------
CREATE EXTENSION IF NOT EXISTS vector;          -- pgvector（RAG 向量检索）
CREATE EXTENSION IF NOT EXISTS pg_trgm;         -- 全文/模糊检索辅助
-- uuid 使用 PostgreSQL 内置 gen_random_uuid()，无需额外扩展

-- ============================================================
-- 1. users 用户表
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name          VARCHAR(100),
    target_role   VARCHAR(100),                 -- 目标岗位（用于默认匹配）
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE users IS '用户';
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ============================================================
-- 2. resumes 简历表（含版本）
-- ============================================================
CREATE TABLE IF NOT EXISTS resumes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_url    TEXT,                            -- 原始文件（PDF）地址
    raw_text    TEXT,                            -- 抽取出的纯文本
    parsed_json JSONB,                           -- 结构化解析结果（LLM Structured Output）
    version     INT NOT NULL DEFAULT 1,
    status      VARCHAR(20) NOT NULL DEFAULT 'parsing',  -- parsing / parsed / failed
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, version)
);
COMMENT ON TABLE resumes IS '简历（含版本管理）';
CREATE INDEX IF NOT EXISTS idx_resumes_user ON resumes(user_id);

-- ============================================================
-- 3. jobs 岗位（JD）表
-- ============================================================
CREATE TABLE IF NOT EXISTS jobs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       VARCHAR(200),
    company     VARCHAR(200),
    jd_text     TEXT,                            -- JD 原文（粘贴/上传）
    parsed_json JSONB,                           -- JD 结构化解析结果
    source      VARCHAR(50) DEFAULT 'manual',    -- manual / upload
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE jobs IS '岗位/JD';
CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs(user_id);

-- ============================================================
-- 4. matches 岗位匹配结果表
-- ============================================================
CREATE TABLE IF NOT EXISTS matches (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id      UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    job_id         UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    score          NUMERIC(5,2),                 -- 匹配总分 0~100
    dimension_json JSONB,                        -- 各维度分 {skill, experience, education, expression}
    strength_json  JSONB,                        -- 优势清单
    gap_json       JSONB,                        -- Gap 差距项清单（可解释，带依据）
    suggestion     TEXT,                         -- 行动建议
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (resume_id, job_id)                   -- 同一份简历对同一岗位只保留一次
);
COMMENT ON TABLE matches IS '岗位匹配结果（可解释）';
CREATE INDEX IF NOT EXISTS idx_matches_resume ON matches(resume_id);
CREATE INDEX IF NOT EXISTS idx_matches_job ON matches(job_id);

-- ============================================================
-- 5. applications 投递管理表
-- ============================================================
CREATE TABLE IF NOT EXISTS applications (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id     UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    status     VARCHAR(20) NOT NULL DEFAULT 'applied',
               -- applied 已投 / online_test 笔试 / interview 面试 / offer / rejected 被拒
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    note       TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE applications IS '投递记录';
CREATE INDEX IF NOT EXISTS idx_apps_user ON applications(user_id, status);
CREATE INDEX IF NOT EXISTS idx_apps_job ON applications(job_id);

-- ============================================================
-- 6. interviews 模拟面试表
-- ============================================================
CREATE TABLE IF NOT EXISTS interviews (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id      UUID REFERENCES jobs(id) ON DELETE SET NULL,
    score       NUMERIC(5,2),                    -- 面试综合评分 0~100
    feedback_json JSONB,                         -- 逐题反馈 + 能力评分 + 改进建议
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ
);
COMMENT ON TABLE interviews IS '模拟面试记录';
CREATE INDEX IF NOT EXISTS idx_interviews_user ON interviews(user_id, started_at);

-- ============================================================
-- 7. messages 面试对话表
-- ============================================================
CREATE TABLE IF NOT EXISTS messages (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interview_id UUID NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
    role         VARCHAR(20) NOT NULL,           -- assistant / user
    content      TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE messages IS '面试对话消息';
CREATE INDEX IF NOT EXISTS idx_messages_interview ON messages(interview_id, created_at);

-- ============================================================
-- 8. documents 知识库文档表
-- ============================================================
CREATE TABLE IF NOT EXISTS documents (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title      VARCHAR(255),
    source     VARCHAR(20) NOT NULL DEFAULT 'upload',  -- upload / builtin / manual
    file_url   TEXT,
    status     VARCHAR(20) NOT NULL DEFAULT 'processing', -- processing / indexed / failed
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE documents IS 'RAG 知识库文档';
CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id);

-- ============================================================
-- 9. chunks RAG 切片表（向量）
-- ============================================================
CREATE TABLE IF NOT EXISTS chunks (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id  UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index  INT NOT NULL DEFAULT 0,
    content      TEXT NOT NULL,
    embedding    VECTOR(1536)                     -- 向量（1536 维，如 text-embedding-3-small）
);
COMMENT ON TABLE chunks IS 'RAG 文档切片（含向量）';
-- HNSW 向量索引（第 13 步建立；维度/距离函数按实际 embedding 调整）
-- CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops);

-- ============================================================
-- 10. evaluations AI 评测表
-- ============================================================
CREATE TABLE IF NOT EXISTS evaluations (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id        VARCHAR(100) NOT NULL,         -- 测试用例 ID（关联 evaluation/datasets）
    task_type      VARCHAR(50) NOT NULL,          -- jd_parser / resume_parser / match / rag / interview
    model          VARCHAR(100),
    prompt_version VARCHAR(50),
    input_hash     VARCHAR(64),                   -- 输入指纹（去重/审计）
    output_json    JSONB,                         -- 模型原始输出
    is_valid       BOOLEAN,                       -- JSON Validity
    score          NUMERIC(6,4),                  -- 各指标得分（0~1）
    latency_ms     INT,
    cost           NUMERIC(10,6),                 -- Token 成本（美元）
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE evaluations IS 'AI 评测记录';
CREATE INDEX IF NOT EXISTS idx_evals_task ON evaluations(task_type, model, prompt_version, created_at);
CREATE INDEX IF NOT EXISTS idx_evals_case ON evaluations(case_id);
