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
    
    try {
        $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        if ($connections) {
            $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
            foreach ($pid in $pids) {
                $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
                if ($process) {
                    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                    Write-Host "  [+] Stopped PID: $pid" -ForegroundColor Green
                }
            }
        } else {
            Write-Host "  [-] No process found on port $Port" -ForegroundColor Gray
        }
    } catch {
        Write-Host "  [!] Error: $_" -ForegroundColor Red
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
