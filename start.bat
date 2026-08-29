@echo off
REM AI Career Copilot · 本地一键启动脚本（Windows）
REM 用法：双击运行，或在 cmd 中执行 start.bat

echo ========================================
echo   AI Career Copilot · 本地启动
echo ========================================
echo.

REM 检查 PostgreSQL
echo [1/3] 检查 PostgreSQL...
pg_isready -U postgres -h localhost -p 5432 >nul 2>&1
if errorlevel 1 (
    echo [错误] PostgreSQL 未启动，请先启动 PostgreSQL 服务
    pause
    exit /b 1
)
echo PostgreSQL 运行正常
echo.

REM 启动后端
echo [2/3] 启动后端（端口 8000）...
start "AI Career Backend" cmd /k "cd /d %~dp0backend && .venv\Scripts\activate && uvicorn app.main:app --reload --port 8000"

REM 等待后端启动
timeout /t 3 /nobreak >nul

REM 启动前端
echo [3/3] 启动前端（端口 3000）...
start "AI Career Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ========================================
echo   启动完成！
echo   前端: http://localhost:3000
echo   后端: http://localhost:8000/docs
echo ========================================
echo.
pause
