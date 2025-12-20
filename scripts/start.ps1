# ====================================================
#  KHOI CHAY NHANH - OPPEN WEB UI (PowerShell)
#  Usage: .\scripts\start.ps1
# ====================================================

Write-Host "`n====================================================" -ForegroundColor Cyan
Write-Host "  STARTING ALL SERVICES" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

# Set working directory to project root
Set-Location "$PSScriptRoot\.."

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

# Activate virtual environment
Write-Host "[+] Activating virtual environment..." -ForegroundColor Yellow
& "D:\Works\.venv\Scripts\Activate.ps1"
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
    "Set-Location '$PWD'; D:\Works\.venv\Scripts\Activate.ps1; `$host.UI.RawUI.WindowTitle = 'LiteLLM - Port 4000'; litellm --config litellm/litellm_config.yaml --port 4000"
) -PassThru
Start-Sleep -Seconds 8

# Start Middleware in new window
Write-Host "[2/3] Starting Middleware (Port 5000)..." -ForegroundColor Green
$middleware = Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$PWD\llm-mw'; D:\Works\.venv\Scripts\Activate.ps1; `$host.UI.RawUI.WindowTitle = 'Middleware - Port 5000'; python main.py"
) -PassThru
Start-Sleep -Seconds 5

# Start OpenWebUI in new window
Write-Host "[3/3] Starting OpenWebUI (Port 3000)..." -ForegroundColor Green
$openwebui = Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$PWD'; D:\Works\.venv\Scripts\Activate.ps1; `$env:DATA_DIR='$PWD\openwebui_data'; `$env:WEBUI_SECRET_KEY='your-secret-key-here'; `$host.UI.RawUI.WindowTitle = 'OpenWebUI - Port 3000'; open-webui serve --port 3000"
) -PassThru
Start-Sleep -Seconds 3

Write-Host "`n====================================================" -ForegroundColor Cyan
Write-Host "  ALL SERVICES STARTED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  LiteLLM:    " -NoNewline
Write-Host "http://localhost:4000" -ForegroundColor Blue
Write-Host "  Middleware: " -NoNewline
Write-Host "http://localhost:5000" -ForegroundColor Blue
Write-Host "  OpenWebUI:  " -NoNewline
Write-Host "http://localhost:3000" -ForegroundColor Blue
Write-Host ""
Write-Host "  Process IDs:" -ForegroundColor Yellow
Write-Host "    LiteLLM:    $($litellm.Id)" -ForegroundColor Gray
Write-Host "    Middleware: $($middleware.Id)" -ForegroundColor Gray
Write-Host "    OpenWebUI:  $($openwebui.Id)" -ForegroundColor Gray
Write-Host ""
Write-Host "  To stop all services, run: .\scripts\stop.ps1" -ForegroundColor Yellow
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""

Read-Host "Press Enter to exit (services will continue running in background)"
