# AgentFlow-Eval — local full Docker stack (same shape as cloud)
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\docker-up.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\docker-up.ps1 -Rebuild

param(
  [switch]$Rebuild,
  [switch]$Down
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Backend = Join-Path $Root "backend"
$EnvFile = Join-Path $Backend ".env.docker"

function Ensure-Docker {
  $v = docker version --format "{{.Server.Version}}" 2>$null
  if ($LASTEXITCODE -ne 0 -or -not $v) {
    Write-Host "Docker engine not ready. Starting Docker Desktop..."
    $dd = "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dd) { Start-Process $dd }
    for ($i = 1; $i -le 60; $i++) {
      Start-Sleep -Seconds 3
      $v = docker version --format "{{.Server.Version}}" 2>$null
      if ($LASTEXITCODE -eq 0 -and $v) {
        Write-Host "Docker ready: $v"
        return
      }
    }
    throw "Docker Desktop did not become ready. Open Docker Desktop and retry."
  }
}

function Ensure-EnvDocker {
  if (Test-Path $EnvFile) { return }
  Write-Host "Creating backend\.env.docker from deploy.env.example + local OPENAI key..."
  $localEnv = Join-Path $Backend ".env"
  $openai = ""
  $base = "https://api.openai.com/v1"
  if (Test-Path $localEnv) {
    Get-Content $localEnv | ForEach-Object {
      if ($_ -match '^\s*OPENAI_API_KEY=(.+)$') { $openai = $Matches[1].Trim() }
      if ($_ -match '^\s*OPENAI_BASE_URL=(.+)$') { $base = $Matches[1].Trim() }
    }
  }
  $sk = python -c "import secrets; print(secrets.token_urlsafe(48))" 2>$null
  if (-not $sk) { $sk = -join ((48..57 + 65..90 + 97..122 | Get-Random -Count 48 | ForEach-Object { [char]$_ })) }
  $db = python -c "import secrets; print(secrets.token_urlsafe(24))" 2>$null
  if (-not $db) { $db = -join ((48..57 + 65..90 + 97..122 | Get-Random -Count 24 | ForEach-Object { [char]$_ })) }

  @"
ENV=prod
DEBUG=false
SECRET_KEY=$sk
CORS_ORIGINS=["http://localhost","http://localhost:80","http://127.0.0.1","http://127.0.0.1:80"]
POSTGRES_USER=agentflow
POSTGRES_PASSWORD=$db
POSTGRES_DB=agentflow_eval
DATABASE_URL=postgresql+asyncpg://agentflow:${db}@postgres:5432/agentflow_eval
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
CELERY_TASK_ALWAYS_EAGER=false
OPENAI_API_KEY=$openai
OPENAI_BASE_URL=$base
LOG_LEVEL=INFO
LOG_FORMAT=json
AUTH_ENABLED=false
API_KEYS=
TENANCY_ENABLED=false
ADMIN_ACTORS=admin
FLOWER_USER=admin
FLOWER_PASSWORD=flower_local_change_me
"@ | Set-Content -Path $EnvFile -Encoding utf8
  if (-not $openai) {
    Write-Host "WARNING: OPENAI_API_KEY empty — edit backend\.env.docker before running evaluations."
  }
}

Ensure-Docker
Set-Location $Backend

if ($Down) {
  docker compose --env-file .env.docker down
  Write-Host "Stack stopped."
  exit 0
}

Ensure-EnvDocker

if ($Rebuild) {
  Write-Host "==> Building images (this can take a while)..."
  docker build -t agentflow-backend:local .
  docker build -t agentflow-frontend:local ../frontend
}

Write-Host "==> Starting full stack..."
docker compose --env-file .env.docker up -d

Write-Host "==> Waiting for backend health..."
$ok = $false
for ($i = 1; $i -le 40; $i++) {
  try {
    $h = Invoke-RestMethod "http://127.0.0.1:8000/health" -TimeoutSec 3
    if ($h.status -eq "healthy") { $ok = $true; break }
  } catch {}
  Start-Sleep -Seconds 2
}

docker compose --env-file .env.docker ps
Write-Host ""
Write-Host "============================================"
if ($ok) {
  Write-Host " Docker stack is up"
} else {
  Write-Host " Backend not healthy yet — check: docker compose --env-file .env.docker logs backend"
}
Write-Host " Frontend : http://localhost/"
Write-Host " API docs : http://localhost:8000/docs"
Write-Host " Health   : http://localhost:8000/health"
Write-Host " Flower   : http://localhost:5555  (admin / see .env.docker)"
Write-Host " Stop     : powershell -File scripts\docker-up.ps1 -Down"
Write-Host "============================================"
