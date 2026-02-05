# ====================================================
#  KHOI CHAY NHANH - OPPEN WEB UI (PowerShell)
#  Usage: .\scripts\start.ps1 [-NoPrompt]
# ====================================================

param(
    [switch]$NoPrompt
)

Write-Host "`n====================================================" -ForegroundColor Cyan
Write-Host "  STARTING ALL SERVICES" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

# Set working directory to project root
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot ".." )).Path
Set-Location $ProjectRoot

# Load environment variables from .env file
if (Test-Path ".env") {
    Write-Host "[+] Loading environment variables..." -ForegroundColor Yellow
    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            Set-Item -Path "env:$key" -Value $value
        }
    }
}

# Open firewall ports for external access
Write-Host "[+] Opening firewall ports..." -ForegroundColor Yellow
try {
    # Remove existing rules if any
    Remove-NetFirewallRule -DisplayName "OpenWebUI - Port 3000" -ErrorAction SilentlyContinue
    Remove-NetFirewallRule -DisplayName "OpenWebUI - Port 5000" -ErrorAction SilentlyContinue
    
    # Add new firewall rules
    New-NetFirewallRule -DisplayName "OpenWebUI - Port 3000" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow -ErrorAction Stop | Out-Null
    New-NetFirewallRule -DisplayName "OpenWebUI - Port 5000" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow -ErrorAction Stop | Out-Null
    Write-Host "    Ports 3000 and 5000 opened successfully" -ForegroundColor Green
} catch {
    Write-Host "    Firewall: Cần mở thủ công hoặc chạy PowerShell as Administrator" -ForegroundColor Yellow
    Write-Host "    Lệnh thủ công: netsh advfirewall firewall add rule name=`"OpenWebUI`" dir=in action=allow protocol=TCP localport=3000,5000" -ForegroundColor Gray
}

# Get IP addresses (exclude Docker/WSL virtual adapters)
$IpAddresses = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { 
    $_.InterfaceAlias -notlike "*Loopback*" -and 
    $_.InterfaceAlias -notlike "*WSL*" -and 
    $_.InterfaceAlias -notlike "*vEthernet*" -and
    $_.InterfaceAlias -notlike "*Docker*" -and
    $_.IPAddress -ne "127.0.0.1" -and
    ($_.IPAddress -like "192.168.*" -or $_.IPAddress -like "10.*" -or $_.IPAddress -like "172.16.*" -or $_.IPAddress -like "172.31.*")
} | Select-Object -ExpandProperty IPAddress -First 1

# Activate virtual environment (shared at C:\Code\.venv)
Write-Host "[+] Activating virtual environment..." -ForegroundColor Yellow
$VenvActivate = "C:\\Code\\.venv\\Scripts\\Activate.ps1"
if (-not (Test-Path $VenvActivate)) {
    Write-Host "[!] Shared venv not found at: $VenvActivate" -ForegroundColor Red
    Write-Host "    Create it with: py -3.11 -m venv C:\Code\.venv" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

& $VenvActivate
if (-not $?) {
    Write-Host "[!] Failed to activate venv" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Start LiteLLM in new window
Write-Host "`n[1/3] Starting LiteLLM (Port 4000)..." -ForegroundColor Green
$litellm = Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$ProjectRoot'; & '$VenvActivate'; `$host.UI.RawUI.WindowTitle = 'LiteLLM - Port 4000'; litellm --config litellm/litellm_config.yaml --port 4000"
) -PassThru
Start-Sleep -Seconds 8

# Start Middleware in new window
Write-Host "[2/3] Starting Middleware (Port 5000)..." -ForegroundColor Green
$middleware = Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$ProjectRoot\llm-mw'; & '$VenvActivate'; `$host.UI.RawUI.WindowTitle = 'Middleware - Port 5000'; python main.py"
) -PassThru
Start-Sleep -Seconds 5

# Start OpenWebUI in new window with environment variables
Write-Host "[3/3] Starting OpenWebUI (Port 3000)..." -ForegroundColor Green
$envVars = @()
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            $envVars += "`$env:$key='$value';"
        }
    }
}
$envCmd = $envVars -join " "
$openwebui = Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$ProjectRoot'; $envCmd & '$VenvActivate'; `$host.UI.RawUI.WindowTitle = 'OpenWebUI - Port 3000'; open-webui serve --port 3000 --host 0.0.0.0"
) -PassThru
Start-Sleep -Seconds 3

Write-Host "`n====================================================" -ForegroundColor Cyan
Write-Host "  ALL SERVICES STARTED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Local Access:" -ForegroundColor Yellow
Write-Host "    LiteLLM:    " -NoNewline
Write-Host "http://localhost:4000" -ForegroundColor Blue
Write-Host "    Middleware: " -NoNewline
Write-Host "http://localhost:5000" -ForegroundColor Blue
Write-Host "    OpenWebUI:  " -NoNewline
Write-Host "http://localhost:3000" -ForegroundColor Blue
Write-Host ""
Write-Host "  Network Access (for other devices):" -ForegroundColor Yellow
if ($IpAddresses) {
    Write-Host "    OpenWebUI:  " -NoNewline
    Write-Host "http://${IpAddresses}:3000" -ForegroundColor Cyan
    Write-Host "    Middleware: " -NoNewline
    Write-Host "http://${IpAddresses}:5000" -ForegroundColor Cyan
} else {
    Write-Host "    No network IP found" -ForegroundColor Gray
}
Write-Host ""
Write-Host "  Process IDs:" -ForegroundColor Yellow
Write-Host "    LiteLLM:    $($litellm.Id)" -ForegroundColor Gray
Write-Host "    Middleware: $($middleware.Id)" -ForegroundColor Gray
Write-Host "    OpenWebUI:  $($openwebui.Id)" -ForegroundColor Gray
Write-Host ""
Write-Host "  To stop all services, run: .\scripts\stop.ps1" -ForegroundColor Yellow
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""

if (-not $NoPrompt) {
    Read-Host "Press Enter to exit (services will continue running in background)"
}
