# AI Career Copilot · Backend Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 系统依赖（psycopg 二进制版无需额外编译工具）
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 安装依赖
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# 复制代码（backend + ai prompts + db schema）
COPY backend/ ./backend/
COPY ai/ ./ai/
COPY db/ ./db/

# 创建上传目录
RUN mkdir -p /app/backend/uploads

WORKDIR /app/backend

EXPOSE 8000

# 启动时自动建表（Base.metadata.create_all）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
