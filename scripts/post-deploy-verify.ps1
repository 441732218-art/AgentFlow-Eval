# AgentFlow-Eval — post-deploy health & config verification (P0)
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\post-deploy-verify.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\post-deploy-verify.ps1 -BaseUrl http://127.0.0.1:8000

param(
  [string]$BaseUrl = "http://127.0.0.1:8000",
  [string]$ApiKey = "",
  [switch]$Strict
)

$ErrorActionPreference = "Continue"
$failed = 0

function Ok($msg) { Write-Host "  OK   $msg" -ForegroundColor Green }
function Bad($msg) { Write-Host "  FAIL $msg" -ForegroundColor Red; $script:failed++ }
function Info($msg) { Write-Host "  --   $msg" -ForegroundColor DarkGray }

# Resolve API key: -ApiKey > env AGENTFLOW_API_KEY > first secret in backend/.env.docker API_KEYS
if (-not $ApiKey) { $ApiKey = $env:AGENTFLOW_API_KEY }
if (-not $ApiKey) {
  $envDocker = Join-Path (Split-Path -Parent $PSScriptRoot) "backend\.env.docker"
  if (Test-Path $envDocker) {
    Get-Content $envDocker -Encoding UTF8 | ForEach-Object {
      if ($_ -match '^\s*API_KEYS=(.+)$') {
        $raw = $Matches[1].Trim().Trim('"').Trim("'")
        if ($raw) { $ApiKey = ($raw -split ",")[0].Trim().Split(":")[0] }
      }
    }
  }
}

$script:ApiHeaders = @{}
if ($ApiKey) {
  $script:ApiHeaders["X-API-Key"] = $ApiKey
  Info "using X-API-Key (prefix $($ApiKey.Substring(0, [Math]::Min(4, $ApiKey.Length)))***)"
} else {
  Info "no API key — ok if AUTH_ENABLED=false"
}

function Invoke-AfRest([string]$Path) {
  $uri = "$BaseUrl$Path"
  if ($script:ApiHeaders.Count -gt 0) {
    return Invoke-RestMethod $uri -Headers $script:ApiHeaders -TimeoutSec 8
  }
  return Invoke-RestMethod $uri -TimeoutSec 8
}

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
  $me = Invoke-AfRest "/api/v1/me"
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
  $plans = Invoke-AfRest "/api/v1/billing/plans"
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
  $m = Invoke-AfRest "/api/v1/plugins/market"
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
