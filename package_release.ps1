param(
    [string]$OutputRoot = ".\dist",
    [switch]$IncludeDockerImages,
    [switch]$IncludeRawEvents
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$packageName = "douyin_live_analytics_source_bundle_$timestamp"
$stageDir = Join-Path $OutputRoot $packageName
$zipPath = Join-Path $OutputRoot "$packageName.zip"

$crawlerDir = Get-ChildItem -Path $root -Directory | Where-Object {
    Test-Path (Join-Path $_.FullName "Tiktok-live")
} | Select-Object -First 1

$includePaths = @(
    "apps",
    "services",
    "infra",
    "docs",
    "tests",
    "offline_wheels",
    "requirements-core.txt",
    "requirements-pipeline.txt",
    "run_system.ps1",
    "start_collectors.ps1",
    "stop_collectors.ps1",
    "download_wheels.ps1",
    "package_release.ps1"
)

if ($crawlerDir) {
    $includePaths += $crawlerDir.Name
}

$optionalFiles = @(
    "data\system.db"
)

if ($IncludeRawEvents) {
    $optionalFiles += "data\raw_events.jsonl"
}

if ($IncludeDockerImages) {
    $optionalFiles += "docker_images_offline.tar"
}

New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
if (Test-Path $stageDir) {
    Remove-Item -Path $stageDir -Recurse -Force
}
if (Test-Path $zipPath) {
    Remove-Item -Path $zipPath -Force
}

New-Item -ItemType Directory -Path $stageDir -Force | Out-Null

foreach ($relativePath in $includePaths + $optionalFiles) {
    $source = Join-Path $root $relativePath
    if (-not (Test-Path $source)) {
        continue
    }

    $destination = Join-Path $stageDir $relativePath
    $destinationParent = Split-Path -Parent $destination
    if ($destinationParent) {
        New-Item -ItemType Directory -Path $destinationParent -Force | Out-Null
    }

    Copy-Item -Path $source -Destination $destination -Recurse -Force
}

$manifestLines = @(
    "Package time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
    "Package type: source bundle",
    "Include docker_images_offline.tar: $($IncludeDockerImages.IsPresent)",
    "Include data/raw_events.jsonl: $($IncludeRawEvents.IsPresent)",
    "",
    "Excluded by default:",
    "- .git",
    "- .idea",
    "- .pytest_cache",
    "- .venv",
    "- .venv311",
    "",
    "Startup guide: docs\reproduce-package.md"
)

$manifest = $manifestLines -join [Environment]::NewLine
Set-Content -Path (Join-Path $stageDir "PACKAGE_MANIFEST.txt") -Value $manifest -Encoding UTF8

Compress-Archive -Path (Join-Path $stageDir "*") -DestinationPath $zipPath -Force

Write-Host "Package created: $zipPath"
