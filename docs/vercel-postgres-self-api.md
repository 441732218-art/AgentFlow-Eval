# 方案 A：Vercel Postgres + 自备 API

## 架构

```
浏览器 → Vercel 前端 (静态)
              ↓ VITE_API_BASE_URL
         自备 API (本机穿透 / 云主机 FastAPI)
              ↓ DATABASE_URL
         Vercel Postgres (Neon)
```

## 步骤 1：创建 Vercel Postgres

1. https://vercel.com/dashboard → 打开 **AgentFlow-Eval** 项目  
2. **Storage** → **Create Database** → **Postgres**  
3. 创建后打开数据库 → 复制 `POSTGRES_URL`  
   形如：`postgres://user:pass@ep-xxx.region.aws.neon.tech/neondb?sslmode=require`

## 步骤 2：本机建表

PowerShell：

```powershell
cd D:\AgentFlow-Eval
.\scripts\setup-vercel-postgres.ps1 -PostgresUrl "粘贴你的POSTGRES_URL"
```

成功会生成 `backend\.env.vercel-postgres`。

## 步骤 3：启动自备 API（本机）

```powershell
cd D:\AgentFlow-Eval\backend
# 使用 vercel-postgres 配置（示例：把 DATABASE_URL 写入当前会话）
Get-Content .env.vercel-postgres | ForEach-Object {
  if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
  $k,$v = $_.Split('=',2)
  Set-Item -Path "env:$k" -Value $v
}
# 补 SECRET_KEY / OPENAI
$env:SECRET_KEY = python -c "import secrets; print(secrets.token_urlsafe(32))"
# $env:OPENAI_API_KEY = "sk-..."
# $env:CORS_ORIGINS = '["https://你的.vercel.app","http://localhost:5173"]'

.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

本机仅局域网可访问。要给 Vercel 前端用，需要公网地址：

```powershell
# 任选：ngrok / cloudflared
ngrok http 8000
# 得到 https://xxxx.ngrok-free.app
```

## 步骤 4：Vercel 前端环境变量

项目 → **Settings → Environment Variables**：

| Name | Value |
|------|--------|
| `VITE_API_BASE_URL` | `https://xxxx.ngrok-free.app/api/v1` |

保存后 **Redeploy**。

## 步骤 5：CORS

自备 API 环境变量：

```text
CORS_ORIGINS=["https://你的项目.vercel.app","http://localhost:5173"]
```

## 生产建议

本机 + ngrok 只适合演示。生产请把 API 放到云主机 / Railway，`DATABASE_URL` 仍指向同一 Vercel Postgres。
