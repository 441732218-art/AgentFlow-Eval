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
DEPLOY_PROFILE=private
BILLING_ENABLED=false
STRIPE_MODE=mock
PLUGINS_ENABLED=true
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

# Ensure all deploy env files exist (docker / vercel-postgres / frontend .env.local)
$gen = Join-Path $Root "scripts\generate-deploy-env.ps1"
if (Test-Path $gen) {
  & powershell -ExecutionPolicy Bypass -File $gen
}

Ensure-EnvDocker

if ($Rebuild) {
  Write-Host "==> Building images (this can take a while)..."
  docker build -t agentflow-backend:local .
  docker build -t agentflow-frontend:local ../frontend
}

Write-Host "==> Starting full stack (migrate service runs alembic upgrade head)..."
# backend depends_on migrate (service_completed_successfully)
docker compose --env-file .env.docker up -d --build

Write-Host "==> Waiting for backend readiness (/health/ready)..."
$ok = $false
for ($i = 1; $i -le 45; $i++) {
  try {
    $h = Invoke-RestMethod "http://127.0.0.1:8000/health/ready" -TimeoutSec 3
    if ($h.status -eq "ready") { $ok = $true; break }
  } catch {}
  Start-Sleep -Seconds 2
}

# Optional seed (idempotent-ish)
if ($ok) {
  Write-Host "==> Seeding demo data (best-effort)..."
  docker compose --env-file .env.docker exec -T backend python -m app.core.seed 2>$null
}

docker compose --env-file .env.docker ps
Write-Host ""
Write-Host "============================================"
if ($ok) {
  Write-Host " Docker Private stack is READY"
} else {
  Write-Host " Backend not ready — check: docker compose --env-file .env.docker logs backend migrate"
}
Write-Host " Frontend : http://localhost/"
Write-Host " API docs : http://localhost:8000/docs"
Write-Host " Ready    : http://localhost:8000/health/ready"
Write-Host " Me       : http://localhost:8000/api/v1/me"
Write-Host " Flower   : http://localhost:5555  (admin / see .env.docker)"
Write-Host " Verify   : powershell -File scripts\post-deploy-verify.ps1"
Write-Host " Demo     : powershell -File scripts\demo-playbook.ps1"
Write-Host " Stop     : powershell -File scripts\docker-up.ps1 -Down"
Write-Host "============================================"
