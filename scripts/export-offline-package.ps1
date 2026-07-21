# AgentFlow Intelligence - export offline delivery package
# Copyright: Li Kaixin
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\export-offline-package.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\export-offline-package.ps1 -OutDir D:\ship\agentflow

param(
  [string]$OutDir = "",
  [switch]$SkipSave
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not $OutDir) {
  $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
  $OutDir = Join-Path $Root "artifacts\delivery\agentflow-offline-$stamp"
}

$Backend = Join-Path $Root "backend"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$ImagesDir = Join-Path $OutDir "images"
$ConfigDir = Join-Path $OutDir "config"
$ScriptsDir = Join-Path $OutDir "scripts"
New-Item -ItemType Directory -Force -Path $ImagesDir, $ConfigDir, $ScriptsDir | Out-Null

Write-Host "==> Offline package -> $OutDir" -ForegroundColor Cyan

$need = @(
  "agentflow-backend:local",
  "agentflow-frontend:local",
  "postgres:16-alpine",
  "redis:7-alpine"
)
foreach ($img in $need) {
  $null = docker image inspect $img --format "{{.Id}}" 2>$null
  if ($LASTEXITCODE -ne 0) {
    throw "Missing image: $img - build stack first"
  }
  Write-Host "  found $img"
}

if (-not $SkipSave) {
  $tar = Join-Path $ImagesDir "agentflow-images.tar"
  Write-Host "Saving images (this can take several minutes)..." -ForegroundColor Green
  & docker save -o $tar $need[0] $need[1] $need[2] $need[3]
  if (-not (Test-Path $tar)) {
    throw "docker save failed"
  }
  $sizeMb = [math]::Round((Get-Item $tar).Length / 1MB, 1)
  Write-Host "  wrote $tar ($sizeMb MB)"
} else {
  Write-Host "SkipSave: images not exported" -ForegroundColor Yellow
}

Copy-Item (Join-Path $Backend "docker-compose.yml") (Join-Path $ConfigDir "docker-compose.yml") -Force
Copy-Item (Join-Path $Backend "docker-compose.prod.yml") (Join-Path $ConfigDir "docker-compose.prod.yml") -Force
Copy-Item (Join-Path $Backend ".env.docker.example") (Join-Path $ConfigDir ".env.docker.example") -Force
$deployEx = Join-Path $Root "deploy.env.example"
if (Test-Path $deployEx) {
  Copy-Item $deployEx (Join-Path $ConfigDir "deploy.env.example") -Force
}

foreach ($s in @("start-docker-stack.ps1", "post-deploy-verify.ps1", "generate-deploy-env.ps1", "docker-up.ps1")) {
  $p = Join-Path $Root "scripts\$s"
  if (Test-Path $p) {
    Copy-Item $p (Join-Path $ScriptsDir $s) -Force
  }
}

$readmeSrc = Join-Path $Root "scripts\delivery-README.md"
if (Test-Path $readmeSrc) {
  $readmeBody = Get-Content $readmeSrc -Raw -Encoding UTF8
  $stampLine = "Exported: " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
  $readmeBody = $readmeBody -replace "\| Shape \|", "| Exported | $stampLine |`r`n| Shape |"
  $utf8 = New-Object System.Text.UTF8Encoding $false
  [System.IO.File]::WriteAllText((Join-Path $OutDir "README.md"), $readmeBody, $utf8)
} else {
  Set-Content -Path (Join-Path $OutDir "README.md") -Value "See docs/前后端联通与整体打包.md" -Encoding UTF8
}

$iso = Get-Date -Format o
$manifest = @"
{
  "product": "AgentFlow Intelligence",
  "copyright": "Li Kaixin",
  "exported_at": "$iso",
  "images": [
    "agentflow-backend:local",
    "agentflow-frontend:local",
    "postgres:16-alpine",
    "redis:7-alpine"
  ],
  "auth_default": true,
  "compose": [
    "docker-compose.yml",
    "docker-compose.prod.yml"
  ]
}
"@
$utf8 = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText((Join-Path $OutDir "manifest.json"), $manifest.Trim() + "`n", $utf8)

Write-Host ""
Write-Host "PACKAGE READY: $OutDir" -ForegroundColor Green
Get-ChildItem $OutDir -Recurse -File | ForEach-Object {
  $mb = [math]::Round($_.Length / 1MB, 2)
  $rel = $_.FullName.Substring($OutDir.Length + 1)
  Write-Host ("  {0,8} MB  {1}" -f $mb, $rel)
}
Write-Host $OutDir
