# Start AgentFlow-Eval backend (local eager mode)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
Set-Location $Backend

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating venv..." -ForegroundColor Yellow
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\pip.exe install -r requirements.txt
}

if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "Edit backend\.env and set OPENAI_API_KEY + CELERY_TASK_ALWAYS_EAGER=true" -ForegroundColor Yellow
}

Write-Host "Starting API on http://localhost:8000 ..." -ForegroundColor Cyan
Write-Host "Docs: http://localhost:8000/docs" -ForegroundColor Cyan
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
