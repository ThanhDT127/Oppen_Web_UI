param(
  [int]$LiteLLMPort = 4000,
  [int]$MiddlewarePort = 5000,
  [int]$OpenWebUIPort = 3000
)

$ErrorActionPreference = 'SilentlyContinue'

function Stop-ByPort([int]$Port, [string]$Name) {
  try {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $conn) {
      Write-Host "$Name not listening on :${Port} (skip)" -ForegroundColor Yellow
      return
    }

    $processId = $conn.OwningProcess
    if ($processId -and $processId -gt 0) {
      Write-Host "Stopping $Name (PID $processId) on :${Port} ..." -ForegroundColor Cyan
      Stop-Process -Id $processId -Force
    }
  } catch {
    Write-Warning "Failed stopping $Name on :${Port}: $($_.Exception.Message)"
  }
}

Stop-ByPort -Port $OpenWebUIPort -Name 'OpenWebUI'
Stop-ByPort -Port $MiddlewarePort -Name 'Middleware'
Stop-ByPort -Port $LiteLLMPort -Name 'LiteLLM'
