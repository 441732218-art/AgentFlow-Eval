# Link local Docker backend to Vercel frontend (Option A: ngrok)
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\vercel-connect.ps1 -VercelHost "https://your-app.vercel.app"
#   powershell -ExecutionPolicy Bypass -File scripts\vercel-connect.ps1 -VercelHost "https://your-app.vercel.app" -NgrokUrl "https://xxxx.ngrok-free.app"
#
# What it does:
#   1) Ensures backend\.env.docker CORS includes your Vercel host
#   2) Prints exact VITE_API_BASE_URL for Vercel dashboard
#   3) Optionally starts ngrok if -StartNgrok and ngrok is installed

param(
  [Parameter(Mandatory = $true)]
  [string]$VercelHost,
  [string]$NgrokUrl = "",
  [switch]$StartNgrok,
  [switch]$RestartBackend
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$EnvDocker = Join-Path $Root "backend\.env.docker"

function Normalize-HttpsUrl([string]$u) {
  $u = $u.Trim().TrimEnd("/")
  if ($u -notmatch "^https?://") { $u = "https://$u" }
  return $u
}

$vh = Normalize-HttpsUrl $VercelHost

# Ensure env.docker exists
$gen = Join-Path $Root "scripts\generate-deploy-env.ps1"
if (-not (Test-Path $EnvDocker)) {
  & powershell -ExecutionPolicy Bypass -File $gen -Force -VercelHost $vh
} else {
  # Patch CORS line to include Vercel host
  $lines = Get-Content $EnvDocker -Encoding UTF8
  $out = @()
  $patched = $false
  foreach ($line in $lines) {
    if ($line -match '^\s*CORS_ORIGINS=(.*)$') {
      $raw = $Matches[1].Trim()
      $origins = @()
      if ($raw -match '^\s*\[(.*)\]\s*$') {
        $inner = $Matches[1]
        foreach ($part in ($inner -split ',')) {
          $o = $part.Trim().Trim('"').Trim("'")
          if ($o) { $origins += $o }
        }
      }
      foreach ($must in @(
          "http://localhost", "http://localhost:80", "http://127.0.0.1", "http://127.0.0.1:80",
          "http://localhost:5173", "http://127.0.0.1:5173", $vh
        )) {
        if ($origins -notcontains $must) { $origins += $must }
      }
      $json = "[" + (($origins | ForEach-Object { "`"$_`"" }) -join ",") + "]"
      $out += "CORS_ORIGINS=$json"
      $patched = $true
    } else {
      $out += $line
    }
  }
  if (-not $patched) {
    $out += "CORS_ORIGINS=[`"$vh`",`"http://localhost`",`"http://localhost:5173`"]"
  }
  $utf8 = New-Object System.Text.UTF8Encoding $false
  [System.IO.File]::WriteAllText($EnvDocker, ($out -join "`n") + "`n", $utf8)
  Write-Host "Updated CORS in backend\.env.docker" -ForegroundColor Green
}

if ($RestartBackend) {
  Set-Location (Join-Path $Root "backend")
  docker compose --env-file .env.docker up -d --force-recreate backend
  Write-Host "Backend recreated with new CORS." -ForegroundColor Green
}

if ($StartNgrok) {
  $ng = Get-Command ngrok -ErrorAction SilentlyContinue
  if (-not $ng) {
    Write-Host "ngrok not found in PATH. Install: https://ngrok.com/download" -ForegroundColor Yellow
    Write-Host "Then run: ngrok http 8000" -ForegroundColor Yellow
  } else {
    Write-Host "Starting ngrok http 8000 in a new window..." -ForegroundColor Cyan
    Start-Process ngrok -ArgumentList "http","8000"
    Write-Host "Copy the https://....ngrok-free.app URL from the ngrok window." -ForegroundColor Yellow
  }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Vercel 环境变量（复制到控制台）" -ForegroundColor Cyan
Write-Host "============================================"
if ($NgrokUrl) {
  $api = Normalize-HttpsUrl $NgrokUrl
  if ($api -notmatch "/api/v1$") { $api = "$api/api/v1" }
  Write-Host "Key:   VITE_API_BASE_URL"
  Write-Host "Value: $api" -ForegroundColor Green
  Set-Clipboard -Value $api -ErrorAction SilentlyContinue
  Write-Host "(已尝试写入剪贴板)" -ForegroundColor DarkGray
} else {
  Write-Host "Key:   VITE_API_BASE_URL"
  Write-Host "Value: https://【你的-ngrok或Railway域名】/api/v1" -ForegroundColor Yellow
  Write-Host ""
  Write-Host "本机先开后端，再开穿透："
  Write-Host "  cd $Root\backend"
  Write-Host "  docker compose --env-file .env.docker up -d"
  Write-Host "  ngrok http 8000"
  Write-Host "把 ngrok 的 https 地址填回："
  Write-Host "  powershell -File scripts\vercel-connect.ps1 -VercelHost `"$vh`" -NgrokUrl `"https://xxxx.ngrok-free.app`" -RestartBackend"
}
Write-Host ""
Write-Host "CORS 已包含: $vh"
Write-Host "改完 Vercel 变量后: Deployments → ... → Redeploy"
Write-Host "============================================"
