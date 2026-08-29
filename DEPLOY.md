# AI Career Copilot · 部署指南

## 方式一：Docker 部署（推荐，一键启动）

### 前置要求
- 安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)（Windows / Mac）
- 确保 Docker Desktop 已启动

### 启动步骤

```bash
# 1. 进入项目根目录
cd ai-career-copilot

# 2. 确认 .env 已配置（LLM_API_KEY 等）
cp .env.example .env   # 首次需要，编辑填入真实 Key

# 3. 构建并启动所有服务（PostgreSQL + 后端 + 前端）
docker compose up --build -d

# 4. 查看日志
docker compose logs -f backend
docker compose logs -f frontend

# 5. 停止
docker compose down
```

### 访问地址
- 前端：http://localhost:3000
- 后端 API 文档：http://localhost:8000/docs
- PostgreSQL：localhost:5432（用户 postgres / 密码 postgres）

### 服务说明
| 服务 | 镜像/构建 | 端口 | 说明 |
|---|---|---|---|
| db | pgvector/pgvector:pg17 | 5432 | PostgreSQL + pgvector 扩展，首次启动自动执行 schema.sql |
| backend | 本地构建 backend/Dockerfile | 8000 | FastAPI + uvicorn，启动时自动建表 |
| frontend | 本地构建 frontend/Dockerfile | 3000 | Next.js production build |

### 数据持久化
- PostgreSQL 数据：Docker volume `pgdata`
- 后端上传文件：Docker volume `backend_uploads`

---

## 方式二：本地启动（无需 Docker，开发调试用）

### 前置要求
- Python 3.12+
- Node.js 20+
- PostgreSQL 17 + pgvector 扩展（需手动安装）

### 启动步骤

**1. 启动 PostgreSQL**
```bash
# 确保 PostgreSQL 服务已启动，并创建数据库
psql -U postgres -c "CREATE DATABASE ai_career_copilot;"
psql -U postgres -d ai_career_copilot -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 执行 schema
psql -U postgres -d ai_career_copilot -f db/schema.sql
```

**2. 启动后端**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**3. 启动前端（另开终端）**
```bash
cd frontend
npm install
npm run dev
```

### 访问地址
- 前端：http://localhost:3000
- 后端：http://localhost:8000

---

## 验证部署

1. 打开 http://localhost:3000，看到登录页
2. 注册账号并登录
3. 上传简历 → 上传 JD → 查看匹配 → 开始模拟面试
4. 后端健康检查：http://localhost:8000/health 返回 `{"status":"ok"}`

---

## 环境变量说明（.env）

| 变量 | 说明 | 示例 |
|---|---|---|
| `POSTGRES_USER` | 数据库用户名 | postgres |
| `POSTGRES_PASSWORD` | 数据库密码 | postgres |
| `POSTGRES_DB` | 数据库名 | ai_career_copilot |
| `DATABASE_URL` | 数据库连接串 | postgresql+psycopg://... |
| `SECRET_KEY` | JWT 签名密钥（生产务必修改） | 随机长字符串 |
| `LLM_API_KEY` | 火山方舟 API Key | ark-xxx |
| `LLM_BASE_URL` | LLM API 地址 | https://ark.cn-beijing.volces.com/api/v3 |
| `LLM_MODEL` | 对话模型 | doubao-seed-2-1-pro-260628 |
| `EMBEDDING_PROVIDER` | Embedding 提供方 | volcengine_multimodal |
| `EMBEDDING_MODEL` | Embedding 模型 | doubao-embedding-vision-251215 |
| `NEXT_PUBLIC_API_URL` | 前端访问后端地址 | http://localhost:8000 |

---

## 常见问题

**Q: 前端能打开但请求后端失败？**
A: 检查 `NEXT_PUBLIC_API_URL` 是否正确（浏览器访问的地址，不是容器内地址）。Docker 部署用 `http://localhost:8000`。

**Q: pgvector 扩展创建失败？**
A: Docker 方式用 `pgvector/pgvector:pg17` 镜像已预装。本地方式需手动安装 pgvector。

**Q: 如何重置数据库？**
A: `docker compose down -v`（删除 volume），然后 `docker compose up --build` 重新初始化。

**Q: LLM 调用失败？**
A: 检查 `.env` 中 `LLM_API_KEY` 是否正确、模型是否已开通权限。
