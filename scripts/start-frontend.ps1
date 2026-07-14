# Start AgentFlow-Eval frontend (Vite)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $Root "frontend"
Set-Location $Frontend

if (-not (Test-Path "node_modules")) {
    Write-Host "Installing frontend deps..." -ForegroundColor Yellow
    npm.cmd install
}

Write-Host "Starting frontend on http://localhost:5173 ..." -ForegroundColor Cyan
npm.cmd run dev -- --host 127.0.0.1 --port 5173
