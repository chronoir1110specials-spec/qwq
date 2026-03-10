param(
    [string]$ProjectRoot = $PSScriptRoot,
    [string]$PythonPath = "",
    [string]$Bootstrap = "localhost:9092",
    [string]$Topic = "live_events",
    [double]$Interval = 1.0
)

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = $PSScriptRoot
}

$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path

if ([string]::IsNullOrWhiteSpace($PythonPath)) {
    $candidates = @(
        (Join-Path $ProjectRoot ".venv311\Scripts\python.exe"),
        (Join-Path $ProjectRoot ".venv_flink\Scripts\python.exe"),
        (Join-Path $ProjectRoot ".venv\Scripts\python.exe")
    )
    foreach ($p in $candidates) {
        if (Test-Path $p) {
            $PythonPath = $p
            break
        }
    }
}

if ([string]::IsNullOrWhiteSpace($PythonPath) -or -not (Test-Path -LiteralPath $PythonPath)) {
    Write-Error "Python executable not found. Use -PythonPath to specify it."
    exit 1
}

$collector = Join-Path $ProjectRoot "services\collector\collector.py"
if (-not (Test-Path -LiteralPath $collector)) {
    Write-Error "Collector script not found: $collector"
    exit 1
}

$liveIds = @("live_001", "live_002", "live_003")
$seedMap = @{
    "live_001" = 2026030901
    "live_002" = 2026030902
    "live_003" = 2026030903
}

foreach ($liveId in $liveIds) {
    $seed = $seedMap[$liveId]
    $cmd = "cd `"$ProjectRoot`"; & `"$PythonPath`" `"$collector`" --bootstrap $Bootstrap --topic $Topic --live-id $liveId --interval $Interval --seed $seed"
    Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile", "-NoExit", "-Command", $cmd | Out-Null
}

Write-Host "Collectors started for: $($liveIds -join ', ')"
Write-Host "Bootstrap: $Bootstrap, Topic: $Topic, Interval: $Interval"
