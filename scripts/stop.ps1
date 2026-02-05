# ====================================================
#  DUNG TAT CA SERVICES - OPPEN WEB UI
#  Usage: .\scripts\stop.ps1
# ====================================================

Write-Host "`n====================================================" -ForegroundColor Cyan
Write-Host "  STOPPING ALL SERVICES" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""

# Function to stop processes on specific ports
function Stop-ServiceOnPort {
    param([int]$Port, [string]$ServiceName)

    Write-Host "[*] Stopping $ServiceName (Port $Port)..." -ForegroundColor Yellow

    $pids = netstat -ano | findstr ":$Port" | ForEach-Object {
        ($_ -split "\s+")[-1]
    } | Sort-Object -Unique

    if (-not $pids) {
        Write-Host "  [-] No process found on port $Port" -ForegroundColor Gray
        return
    }

    foreach ($processId in $pids) {
        if ($processId -match '^\d+$') {
            try {
                Stop-Process -Id $processId -Force -ErrorAction Stop
                Write-Host "  [+] Killed PID: $processId" -ForegroundColor Green
            } catch {
                Write-Host "  [!] Failed to kill PID $processId : $_" -ForegroundColor Red
            }
        }
    }
}


# Stop services
Stop-ServiceOnPort -Port 4000 -ServiceName "LiteLLM"
Stop-ServiceOnPort -Port 5000 -ServiceName "Middleware"
Stop-ServiceOnPort -Port 3000 -ServiceName "OpenWebUI"

Write-Host ""
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "  ALL SERVICES STOPPED" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""

# Verify all stopped
Write-Host "Verifying ports are free..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

$ports = @(4000, 5000, 3000)
$allClear = $true
foreach ($port in $ports) {
    $conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($conn) {
        Write-Host "  [!] Port $port still in use" -ForegroundColor Red
        $allClear = $false
    } else {
        Write-Host "  [+] Port $port is free" -ForegroundColor Green
    }
}

Write-Host ""
if ($allClear) {
    Write-Host "All ports are free. Ready to restart services." -ForegroundColor Green
} else {
    Write-Host "Some ports are still in use. You may need to manually kill processes." -ForegroundColor Yellow
}
Write-Host ""
