# AgentFlow-Eval — one-shot demo against a running API (P0 playbook)
# Prerequisites: API at BaseUrl (Lite or Docker Private)
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\demo-playbook.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\demo-playbook.ps1 -BaseUrl http://127.0.0.1:8000

param(
  [string]$BaseUrl = "http://127.0.0.1:8000",
  [string]$ApiKey = ""
)

$ErrorActionPreference = "Stop"
$api = "$BaseUrl/api/v1"
$headers = @{ "Content-Type" = "application/json" }
if ($ApiKey) { $headers["X-API-Key"] = $ApiKey }

function Step($n, $title) {
  Write-Host ""
  Write-Host "[$n] $title" -ForegroundColor Cyan
}

function Call-Json($Method, $Path, $Body = $null) {
  $uri = if ($Path.StartsWith("http")) { $Path } else { "$api$Path" }
  $params = @{
    Uri         = $uri
    Method      = $Method
    Headers     = $headers
    TimeoutSec  = 30
  }
  if ($null -ne $Body) {
    $params.Body = ($Body | ConvertTo-Json -Depth 8 -Compress)
  }
  return Invoke-RestMethod @params
}

Write-Host "============================================" -ForegroundColor Green
Write-Host " AgentFlow-Eval DEMO PLAYBOOK"
Write-Host " API: $BaseUrl"
Write-Host "============================================"

Step 1 "Health / ready"
$ready = Invoke-RestMethod "$BaseUrl/health/ready" -TimeoutSec 10
Write-Host "  status=$($ready.status) deploy=$($ready.deploy | ConvertTo-Json -Compress)"

Step 2 "Identity /me"
$me = Call-Json GET "/me"
Write-Host "  actor=$($me.actor) role=$($me.role)"

Step 3 "Create evaluation task"
$task = Call-Json POST "/tasks" @{
  name         = "demo-playbook-$(Get-Date -Format 'HHmmss')"
  description  = "P0 demo task"
  agent_config = @{ runner = "echo"; prefix = "DEMO: " }
}
$tid = $task.id
Write-Host "  task_id=$tid"

Step 4 "Upload one suite (JSON)"
# Prefer API suites endpoint if present
try {
  $null = Call-Json POST "/tasks/$tid/test-suites" @(
    @{
      user_query      = "What is 2+2?"
      expected_output = "4"
      expected_tools  = @()
    }
  )
  Write-Host "  suite uploaded"
} catch {
  Write-Host "  suite upload skipped: $_" -ForegroundColor Yellow
}

Step 5 "Execute task (queue)"
try {
  $ex = Call-Json POST "/tasks/$tid/execute"
  Write-Host "  execute status=$($ex.status) job=$($ex.celery_task_id) backend=$($ex.queue_backend)"
} catch {
  Write-Host "  execute: $_" -ForegroundColor Yellow
}

Step 6 "Billing plans + mock checkout Pro"
$plans = Call-Json GET "/billing/plans"
Write-Host "  plans=$($plans.total)"
try {
  $co = Call-Json POST "/billing/checkout" @{ plan_code = "pro" }
  if ($co.checkout -and $co.checkout.mode -eq "mock") {
    $conf = Call-Json POST "/billing/checkout/mock-confirm" @{
      session_id = $co.checkout.session_id
      plan_code  = "pro"
    }
    Write-Host "  mock checkout -> plan activated ($($conf.subscription.status))"
  } elseif ($co.mode -eq "direct") {
    Write-Host "  free/direct subscribe path"
  } else {
    Write-Host "  checkout mode=$($co.stripe_mode) url=$($co.checkout.url)"
  }
} catch {
  Write-Host "  checkout skipped: $_" -ForegroundColor Yellow
}

$quota = Call-Json GET "/billing/quota"
Write-Host "  quota plan=$($quota.plan_code) tasks=$($quota.task_used)/$($quota.task_limit)"

Step 7 "Plugin market — free install + paid (should work after Pro)"
$market = Call-Json GET "/plugins/market"
Write-Host "  market total=$($market.total) plan=$($market.plan_code)"
try {
  $inst = Call-Json POST "/plugins/market/install" @{
    catalog_id = "echo_tool"
    activate   = $true
  }
  Write-Host "  installed echo_tool state=$($inst.plugin.state)"
} catch {
  Write-Host "  free plugin: $_" -ForegroundColor Yellow
}
try {
  $paid = Call-Json POST "/plugins/market/install" @{
    catalog_id = "premium_length_judge"
    activate   = $true
  }
  Write-Host "  installed premium_length_judge state=$($paid.plugin.state)"
} catch {
  Write-Host "  paid plugin (expect OK after pro): $_" -ForegroundColor Yellow
}

Step 8 "KPIs + slow-tasks"
try {
  $kpis = Call-Json GET "/observability/kpis?days=7"
  Write-Host "  kpis tasks_total=$($kpis.kpis.tasks_total) success_rate=$($kpis.kpis.success_rate)"
} catch {
  Write-Host "  kpis: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " DEMO COMPLETE"
Write-Host " UI:  http://localhost:5173  or  http://localhost/"
Write-Host " Task: $tid"
Write-Host " Docs: docs/DEMO.md"
Write-Host "============================================"
