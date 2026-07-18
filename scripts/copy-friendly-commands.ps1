# AgentFlow-Eval — 可直接在 PowerShell 里整段运行（避免从聊天窗口复制失败）
# 用法：
#   powershell -ExecutionPolicy Bypass -File D:\AgentFlow-Eval\scripts\copy-friendly-commands.ps1
# 或在资源管理器中进入 D:\AgentFlow-Eval 后：
#   .\scripts\copy-friendly-commands.ps1

$ErrorActionPreference = "Stop"
Set-Location "D:\AgentFlow-Eval"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 1) 生成部署环境文件" -ForegroundColor Cyan
Write-Host "========================================"
powershell -ExecutionPolicy Bypass -File ".\scripts\generate-deploy-env.ps1"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 2) 启动 / 确认 Docker 全栈" -ForegroundColor Cyan
Write-Host "========================================"
powershell -ExecutionPolicy Bypass -File ".\scripts\docker-up.ps1"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 3) 健康检查" -ForegroundColor Cyan
Write-Host "========================================"
try {
  $h = Invoke-RestMethod "http://127.0.0.1:8000/health" -TimeoutSec 5
  Write-Host ($h | ConvertTo-Json -Compress) -ForegroundColor Green
} catch {
  Write-Host "后端未就绪: $($_.Exception.Message)" -ForegroundColor Yellow
  Write-Host "请确认 Docker Desktop 已启动后再运行本脚本。" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "完成。前端(Docker): http://localhost/  API: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "若有 Vercel 域名，请再运行（把域名换成你的）：" -ForegroundColor Yellow
Write-Host '  powershell -ExecutionPolicy Bypass -File .\scripts\generate-deploy-env.ps1 -Force -VercelHost "https://你的项目.vercel.app"'
