# AgentFlow Intelligence — full Docker stack (DB + API + Celery + Frontend)
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\start-docker-stack.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\start-docker-stack.ps1 -SkipBuild
#   powershell -ExecutionPolicy Bypass -File scripts\start-docker-stack.ps1 -Seed
#
# Browser (recommended after stack is up):
#   http://127.0.0.1/          → UI (nginx) + /api → backend (same origin)
#   http://127.0.0.1:8000/docs → API (if ENV allows)
#
# Local Vite alternate (dev hot-reload):
#   frontend/.env.local → VITE_API_BASE_URL=/api/v1  (proxied to :8000)

param(
    [switch]$SkipBuild,
    [switch]$Seed,
    [switch]$NoFrontend
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$EnvFile = Join-Path $Backend ".env.docker"

if (-not (Test-Path $EnvFile)) {
    $ex = Join-Path $Backend ".env.docker.example"
    if (Test-Path $ex) {
        Copy-Item $ex $EnvFile
        Write-Host "Created backend/.env.docker from example — edit SECRET_KEY / passwords / OPENAI_API_KEY" -ForegroundColor Yellow
    } else {
        throw "Missing backend/.env.docker and .env.docker.example"
    }
}

Set-Location $Backend

Write-Host "==> AgentFlow Docker stack (copyright: 李凯昕)" -ForegroundColor Cyan

if (-not $SkipBuild) {
    Write-Host "Building images (backend + frontend)..." -ForegroundColor Green
    docker compose --env-file .env.docker build backend celery-worker frontend
} else {
    Write-Host "SkipBuild: using existing images" -ForegroundColor Yellow
}

Write-Host "Starting postgres + redis..." -ForegroundColor Green
docker compose --env-file .env.docker up -d postgres redis

Write-Host "Waiting for postgres healthy..." -ForegroundColor Green
$ok = $false
for ($i = 0; $i -lt 30; $i++) {
    $st = docker inspect -f "{{.State.Health.Status}}" agentflow-postgres 2>$null
    if ($st -eq "healthy") { $ok = $true; break }
    Start-Sleep -Seconds 2
}
if (-not $ok) { throw "Postgres not healthy" }

Write-Host "Running migrations (best-effort)..." -ForegroundColor Green
docker compose --env-file .env.docker run --rm -e PYTHONPATH=/app migrate 2>&1 | Out-Host
# If migrate fails but DB already migrated from host, continue
Write-Host "Starting API + Celery..." -ForegroundColor Green
docker compose --env-file .env.docker up -d --no-deps backend celery-worker

if (-not $NoFrontend) {
    Write-Host "Starting frontend nginx..." -ForegroundColor Green
    docker compose --env-file .env.docker up -d --no-deps frontend
}

if ($Seed) {
    Write-Host "Seeding demo data via backend container..." -ForegroundColor Green
    docker exec -e PYTHONPATH=/app agentflow-backend python -m app.core.seed --force 2>&1 | Out-Host
}

Write-Host ""
Write-Host "Stack endpoints:" -ForegroundColor Cyan
Write-Host "  UI (unified)  http://127.0.0.1/          ← open this for cockpit"
Write-Host "  API direct    http://127.0.0.1:8000/health/ready"
Write-Host "  API via nginx http://127.0.0.1/api/v1/me"
Write-Host "  Ready via UI  http://127.0.0.1/health/ready"
Write-Host ""
Write-Host "Frontend uses VITE_API_BASE_URL=/api/v1 → browser same-origin, nginx proxies to backend." -ForegroundColor DarkGray
# Print API key secret when AUTH is on (first segment of API_KEYS)
$apiKeysLine = Get-Content $EnvFile -ErrorAction SilentlyContinue | Where-Object { $_ -match '^\s*API_KEYS=' } | Select-Object -First 1
if ($apiKeysLine -match '^\s*API_KEYS=(.+)$') {
  $secret = ($Matches[1].Trim() -split ':')[0]
  if ($secret) {
    Write-Host ""
    Write-Host "AUTH: if UI still shows Unauthorized, open Settings and paste API Key:" -ForegroundColor Yellow
    Write-Host "  $secret" -ForegroundColor Green
    Write-Host "(Private stack also auto-injects this via nginx / runtime-config.json)" -ForegroundColor DarkGray
  }
}
