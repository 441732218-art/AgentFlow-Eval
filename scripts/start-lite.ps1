# AgentFlow-Eval lite mode: SQLite + eager queue, no Redis/Celery worker required.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\start-lite.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"

Write-Host "==> AgentFlow-Eval LITE profile" -ForegroundColor Cyan

# Ensure backend .env has lite-friendly defaults (do not overwrite secrets)
$envFile = Join-Path $Backend ".env"
if (-not (Test-Path $envFile)) {
    $example = Join-Path $Backend ".env.example"
    if (Test-Path $example) {
        Copy-Item $example $envFile
        Write-Host "Created backend/.env from .env.example"
    } else {
        New-Item -Path $envFile -ItemType File | Out-Null
    }
}

function Ensure-EnvLine([string]$path, [string]$key, [string]$value) {
    $raw = if (Test-Path $path) { Get-Content $path -Raw } else { "" }
    if ($raw -match "(?m)^$key=") {
        # leave existing
        return
    }
    Add-Content -Path $path -Value "`n$key=$value"
    Write-Host "  + $key=$value"
}

Ensure-EnvLine $envFile "DEPLOY_PROFILE" "lite"
Ensure-EnvLine $envFile "CELERY_TASK_ALWAYS_EAGER" "true"
Ensure-EnvLine $envFile "TASK_QUEUE_BACKEND" "eager"
Ensure-EnvLine $envFile "AUTH_ENABLED" "false"
Ensure-EnvLine $envFile "BILLING_ENABLED" "false"
Ensure-EnvLine $envFile "DATABASE_URL" "sqlite+aiosqlite:///./agentflow_eval.db"

$venvPython = Join-Path $Backend ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Creating venv..."
    Push-Location $Backend
    python -m venv .venv
    & .\.venv\Scripts\pip.exe install -r requirements.txt
    Pop-Location
}

Write-Host "Starting backend on :8000 (lite)..." -ForegroundColor Green
Start-Process -FilePath $venvPython -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000" -WorkingDirectory $Backend

if (Test-Path (Join-Path $Frontend "package.json")) {
    Write-Host "Starting frontend on :5173..." -ForegroundColor Green
    Start-Process -FilePath "npm" -ArgumentList "run", "dev" -WorkingDirectory $Frontend
}

Write-Host ""
Write-Host "Lite stack starting:" -ForegroundColor Cyan
Write-Host "  API    http://127.0.0.1:8000/docs"
Write-Host "  Health http://127.0.0.1:8000/health/ready"
Write-Host "  UI     http://127.0.0.1:5173"
Write-Host "  Me     http://127.0.0.1:8000/api/v1/me"
