# AgentFlow Intelligence — multi-target release builder
# Builds: Web/PWA dist, optional Electron installers, optional Docker offline package.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\build-release.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\build-release.ps1 -Targets web,desktop,offline
#   powershell -ExecutionPolicy Bypass -File scripts\build-release.ps1 -Targets web -SkipInstall
#
# Targets:
#   web      — frontend PWA/static (installable on phone + PC browsers)
#   desktop  — Electron Windows (on Win) / Linux (on Linux) / mac (on macOS)
#   offline  — Docker image tarball delivery package

param(
  [string]$Targets = "web,desktop",
  [switch]$SkipInstall,
  [switch]$SkipTypeCheck,
  [string]$OutDir = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
if (-not $OutDir) {
  $OutDir = Join-Path $Root "artifacts\release\agentflow-$stamp"
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$want = @{}
foreach ($t in ($Targets -split "[,\s]+")) {
  if ($t) { $want[$t.ToLowerInvariant()] = $true }
}

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Ok($msg) { Write-Host "  OK  $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "  !!  $msg" -ForegroundColor Yellow }

Step "Release output: $OutDir"
Write-Host "  targets: $($want.Keys -join ', ')"

# ---- Web / PWA ----
if ($want["web"] -or $want["desktop"] -or $want["pwa"]) {
  Step "Frontend PWA / web build"
  Push-Location (Join-Path $Root "frontend")
  try {
    if (-not $SkipInstall) {
      if (Test-Path "package-lock.json") { npm ci } else { npm install }
    }
    if (-not $SkipTypeCheck) {
      npm run type-check
    }
    if ($want["desktop"]) {
      npm run build:electron
      Ok "electron-mode dist (base ./)"
    } else {
      npm run build:web
      Ok "web/PWA dist"
    }
    $webOut = Join-Path $OutDir "web"
    New-Item -ItemType Directory -Force -Path $webOut | Out-Null
    Copy-Item -Path "dist\*" -Destination $webOut -Recurse -Force
    Ok "copied frontend/dist -> $webOut"
  } finally {
    Pop-Location
  }
}

# ---- Desktop (Electron) ----
if ($want["desktop"]) {
  Step "Desktop Electron package"
  $desk = Join-Path $Root "desktop"
  if (-not (Test-Path (Join-Path $Root "frontend\dist\index.html"))) {
    throw "frontend/dist missing — web/electron build must succeed first"
  }
  Push-Location $desk
  try {
    if (-not $SkipInstall) {
      if (Test-Path "package-lock.json") { npm ci } else { npm install }
    }
    $platform = $PSVersionTable.Platform
    if ($IsWindows -or $env:OS -match "Windows") {
      npm run dist:win
    } elseif ($IsMacOS) {
      npm run dist:mac
    } elseif ($IsLinux) {
      npm run dist:linux
    } else {
      # Windows PowerShell 5.x
      npm run dist:win
    }
    $rel = Join-Path $desk "release"
    $deskOut = Join-Path $OutDir "desktop"
    New-Item -ItemType Directory -Force -Path $deskOut | Out-Null
    if (Test-Path $rel) {
      Copy-Item -Path "$rel\*" -Destination $deskOut -Recurse -Force
      Ok "desktop artifacts -> $deskOut"
    } else {
      Warn "no desktop/release output (electron-builder may have failed)"
    }
  } finally {
    Pop-Location
  }
}

# ---- Offline Docker ----
if ($want["offline"]) {
  Step "Offline Docker delivery package"
  $offlineScript = Join-Path $Root "scripts\export-offline-package.ps1"
  if (-not (Test-Path $offlineScript)) {
    throw "missing $offlineScript"
  }
  $offOut = Join-Path $OutDir "offline"
  powershell -ExecutionPolicy Bypass -File $offlineScript -OutDir $offOut
  Ok "offline package -> $offOut"
}

# ---- Manifest ----
$manifest = @{
  product = "AgentFlow Intelligence"
  version = "1.0.0"
  built_at = (Get-Date).ToString("o")
  targets = @($want.Keys)
  paths = @{
    web = (Join-Path $OutDir "web")
    desktop = (Join-Path $OutDir "desktop")
    offline = (Join-Path $OutDir "offline")
  }
  install = @{
    phone = "Open web build via HTTPS (or LAN IP), browser Install / Add to Home Screen (PWA)"
    windows = "Run desktop/*.exe (NSIS or portable)"
    macos = "Open desktop/*.dmg"
    linux = "Run desktop/*.AppImage or install .deb"
    server = "Docker offline package or docker compose private profile"
  }
}
$manifest | ConvertTo-Json -Depth 6 | Set-Content -Path (Join-Path $OutDir "manifest.json") -Encoding UTF8

$readme = @"
# AgentFlow Intelligence Release

Built: $($manifest.built_at)
Version: 1.0.0

## Contents

| Path | Audience |
|------|----------|
| web/ | PWA / static hosting — phone + PC browsers (adaptive UI) |
| desktop/ | Native installers (built on this OS) |
| offline/ | Docker image tarball for air-gapped servers |

## Install matrix

| Client | How |
|--------|-----|
| Android phone | Chrome open site → Install app / 添加到主屏幕 |
| iPhone / iPad | Safari → Share → Add to Home Screen |
| Windows PC | desktop NSIS installer or portable exe; or PWA in Edge/Chrome |
| macOS | desktop dmg; or PWA in Safari/Chrome |
| Linux | AppImage / deb; or PWA in Chromium |

## API

Desktop / PWA still need a running backend (local Docker private or remote).
Default API: http://127.0.0.1:8000

See docs/跨端打包与安装交付.md
"@
Set-Content -Path (Join-Path $OutDir "README.md") -Value $readme -Encoding UTF8

Step "Done"
Write-Host "  Release folder: $OutDir" -ForegroundColor Green
Get-ChildItem $OutDir | Format-Table Name, Mode, Length
