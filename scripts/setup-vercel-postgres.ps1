# AgentFlow-Eval — 将 Vercel Postgres 连接串转为后端可用配置并建表
# 用法（PowerShell）:
#   .\scripts\setup-vercel-postgres.ps1 -PostgresUrl "postgres://user:pass@host/db?sslmode=require"
# 或先设置环境变量:
#   $env:POSTGRES_URL = "postgres://..."
#   .\scripts\setup-vercel-postgres.ps1

param(
  [string]$PostgresUrl = $env:POSTGRES_URL
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
Set-Location $Backend

if (-not $PostgresUrl) {
  Write-Host @"

缺少连接串。请先在 Vercel 创建 Postgres，然后执行：

  .\scripts\setup-vercel-postgres.ps1 -PostgresUrl "postgres://USER:PASS@HOST/DB?sslmode=require"

连接串在：Vercel 项目 → Storage → 你的 Postgres → .env 或 Connect

"@ -ForegroundColor Yellow
  exit 1
}

# postgres:// 或 postgresql:// → postgresql+asyncpg://
$url = $PostgresUrl.Trim()
if ($url -match '^postgres(ql)?://') {
  $url = $url -replace '^postgres(ql)?://', 'postgresql+asyncpg://'
}
# asyncpg 常用 ssl=require；若带 sslmode=require 也保留一份兼容
if ($url -match 'sslmode=require' -and $url -notmatch '[?&]ssl=') {
  $url = $url + $(if ($url.Contains('?')) { '&' } else { '?' }) + 'ssl=require'
}

Write-Host "==> DATABASE_URL (asyncpg):" -ForegroundColor Cyan
# 脱敏打印
$safe = $url -replace '://([^:]+):([^@]+)@', '://$1:***@'
Write-Host "    $safe"

if (-not (Test-Path ".venv\Scripts\python.exe")) {
  Write-Host "创建 venv 并安装依赖..." -ForegroundColor Yellow
  python -m venv .venv
  .\.venv\Scripts\pip.exe install -r requirements.txt
}

$env:DATABASE_URL = $url
# 建表（create_all + 列补齐与启动时一致）
Write-Host "==> 创建/同步表结构..." -ForegroundColor Cyan
.\.venv\Scripts\python.exe -c @"
import asyncio
import os
import app.models  # noqa: F401
from sqlalchemy.ext.asyncio import create_async_engine
from app.models.base import Base
from app.main import _ensure_sqlite_columns

url = os.environ['DATABASE_URL']
engine = create_async_engine(url, echo=False)

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        try:
            await conn.run_sync(_ensure_sqlite_columns)
        except Exception as e:
            print('column backfill skip/note:', e)
    print('OK: tables created/synced')
    await engine.dispose()

asyncio.run(main())
"@

# 写入 backend/.env.vercel-postgres（不覆盖本地 sqlite .env）
$envFile = Join-Path $Backend ".env.vercel-postgres"
@"
# Auto-generated for Vercel Postgres — do not commit
ENV=prod
DEBUG=false
DATABASE_URL=$url
CELERY_TASK_ALWAYS_EAGER=true
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
# 把下面换成你的 Vercel 前端域名
CORS_ORIGINS=["https://你的项目.vercel.app","http://localhost:5173"]
OPENAI_API_KEY=
SECRET_KEY=change-me
"@ | Set-Content -Path $envFile -Encoding utf8

Write-Host ""
Write-Host "完成。" -ForegroundColor Green
Write-Host "  连接配置已写入: backend\.env.vercel-postgres"
Write-Host ""
Write-Host "下一步："
Write-Host "  1) 编辑 backend\.env.vercel-postgres 填入 OPENAI_API_KEY / SECRET_KEY / CORS"
Write-Host "  2) 启动自备 API:"
Write-Host "     cd backend"
Write-Host "     copy .env.vercel-postgres .env.local.prod   # 或手动导出 DATABASE_URL"
Write-Host "     `$env:DATABASE_URL = (Get-Content .env.vercel-postgres | Where-Object { `$_ -match '^DATABASE_URL=' }) -replace '^DATABASE_URL=',''"
Write-Host "     .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
Write-Host "  3) 公网访问需内网穿透(ngrok)或部署到云主机，再把地址填到 Vercel 的 VITE_API_BASE_URL"
