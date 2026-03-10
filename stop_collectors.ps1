$processes = Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -like "*services\collector\collector.py*" }

if (-not $processes) {
    Write-Host "No collector process found."
    exit 0
}

foreach ($p in $processes) {
    try {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
        Write-Host "Stopped collector PID=$($p.ProcessId)"
    } catch {
        Write-Warning "Failed to stop PID=$($p.ProcessId): $($_.Exception.Message)"
    }
}
