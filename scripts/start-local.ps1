# Launch backend + frontend for local development (Windows)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Scripts = Join-Path $Root "scripts"

Write-Host "=== AgentFlow-Eval local start ===" -ForegroundColor Green
Write-Host "Backend:  http://localhost:8000/docs"
Write-Host "Frontend: http://localhost:5173"
Write-Host ""

# Start backend in new window
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $Scripts "start-backend.ps1")
)

Start-Sleep -Seconds 2

# Start frontend in new window
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $Scripts "start-frontend.ps1")
)

Write-Host "Two terminals opened. Wait a few seconds then open http://localhost:5173" -ForegroundColor Cyan
Write-Host "Optional: set OPENAI_API_KEY in backend\.env for real Agent runs." -ForegroundColor Yellow
