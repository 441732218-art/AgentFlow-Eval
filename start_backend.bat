@echo off
cd /d "%~dp0..\backend"

set DATABASE_URL=sqlite+aiosqlite:///./data/agentflow_lite.db
set AUTH_ENABLED=false
set BILLING_ENABLED=false
set CELERY_TASK_ALWAYS_EAGER=true
set TASK_QUEUE_BACKEND=eager
set DEPLOY_PROFILE=lite
set ENV=dev
set PYTHONPATH=%~dp0..\backend

mkdir data 2>nul

echo === Starting AgentFlow-Eval Backend (Lite) ===
echo DB: %DATABASE_URL%
echo Auth: %AUTH_ENABLED%
echo Port: 8000
echo.

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
