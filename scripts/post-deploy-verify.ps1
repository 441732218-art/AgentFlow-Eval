# AgentFlow-Eval — post-deploy health & config verification (P0)
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\post-deploy-verify.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\post-deploy-verify.ps1 -BaseUrl http://127.0.0.1:8000

param(
  [string]$BaseUrl = "http://127.0.0.1:8000",
  [switch]$Strict
)

$ErrorActionPreference = "Continue"
$failed = 0

function Ok($msg) { Write-Host "  OK   $msg" -ForegroundColor Green }
function Bad($msg) { Write-Host "  FAIL $msg" -ForegroundColor Red; $script:failed++ }
function Info($msg) { Write-Host "  --   $msg" -ForegroundColor DarkGray }

Write-Host "==> Post-deploy verify: $BaseUrl" -ForegroundColor Cyan

# 1) Liveness
try {
  $live = Invoke-RestMethod "$BaseUrl/health/live" -TimeoutSec 5
  if ($live.status -eq "alive") { Ok "/health/live alive" } else { Bad "/health/live unexpected: $($live.status)" }
} catch {
  Bad "/health/live unreachable: $_"
}

# 2) Readiness
try {
  $ready = Invoke-RestMethod "$BaseUrl/health/ready" -TimeoutSec 8
  if ($ready.status -eq "ready") {
    Ok "/health/ready ready"
    if ($ready.deploy) {
      Info ("deploy=" + ($ready.deploy | ConvertTo-Json -Compress))
    }
    if ($ready.services) {
      Info ("services=" + ($ready.services | ConvertTo-Json -Compress))
    }
  } else {
    Bad "/health/ready not_ready: $($ready | ConvertTo-Json -Compress)"
  }
} catch {
  Bad "/health/ready failed: $_"
}

# 3) Composite health
try {
  $h = Invoke-RestMethod "$BaseUrl/health" -TimeoutSec 5
  if ($h.status -in @("healthy", "degraded")) {
    Ok "/health status=$($h.status)"
  } else {
    Bad "/health unexpected: $($h.status)"
  }
} catch {
  Bad "/health failed: $_"
}

# 4) Me / permissions contract
try {
  $me = Invoke-RestMethod "$BaseUrl/api/v1/me" -TimeoutSec 5
  if ($me.permissions -and $me.permissions.Count -gt 0) {
    Ok "/api/v1/me actor=$($me.actor) role=$($me.role) perms=$($me.permissions.Count)"
  } else {
    Bad "/api/v1/me missing permissions"
  }
} catch {
  Bad "/api/v1/me failed: $_"
}

# 5) Billing plans seed path
try {
  $plans = Invoke-RestMethod "$BaseUrl/api/v1/billing/plans" -TimeoutSec 8
  if ($plans.total -ge 1) {
    Ok "/api/v1/billing/plans total=$($plans.total)"
  } else {
    Bad "billing plans empty"
  }
} catch {
  Bad "/api/v1/billing/plans failed: $_"
}

# 6) Plugin market
try {
  $m = Invoke-RestMethod "$BaseUrl/api/v1/plugins/market" -TimeoutSec 8
  if ($m.total -ge 1) {
    Ok "/api/v1/plugins/market total=$($m.total)"
  } else {
    Bad "plugin market empty"
  }
} catch {
  # May require system:config when AUTH on — still warn
  if ($Strict) { Bad "/api/v1/plugins/market failed: $_" }
  else { Info "plugins/market skipped or forbidden: $_" }
}

# 7) Local check-prod (if backend venv present)
$Root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $Root "backend\.venv\Scripts\python.exe"
if (Test-Path $py) {
  Write-Host "==> check_prod (local venv)" -ForegroundColor Cyan
  Push-Location (Join-Path $Root "backend")
  & $py -m app.cli.check_prod 2>&1 | ForEach-Object { Info $_ }
  if ($LASTEXITCODE -ne 0 -and $Strict) { $failed++ }
  Pop-Location
} else {
  Info "skip check_prod (no backend\.venv)"
}

Write-Host ""
if ($failed -eq 0) {
  Write-Host "VERIFY PASSED" -ForegroundColor Green
  exit 0
} else {
  Write-Host "VERIFY FAILED ($failed)" -ForegroundColor Red
  exit 1
}
