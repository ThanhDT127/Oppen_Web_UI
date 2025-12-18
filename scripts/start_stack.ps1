param(
  [int]$LiteLLMPort = 4000,
  [int]$MiddlewarePort = 5000,
  [int]$OpenWebUIPort = 3000,
  [string]$OpenWebUIHost = "0.0.0.0"
)

$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$logsDir = Join-Path $root 'logs'
if (!(Test-Path -LiteralPath $logsDir)) {
  New-Item -ItemType Directory -Path $logsDir | Out-Null
}

$venvActivateCandidates = @()
if ($env:VIRTUAL_ENV) {
  $venvActivateCandidates += (Join-Path $env:VIRTUAL_ENV 'Scripts\Activate.ps1')
}
$venvActivateCandidates += @(
  (Join-Path $root '.venv\Scripts\Activate.ps1'),
  (Join-Path $root '..\..\venv\Scripts\Activate.ps1')
)

$venvActivate = $venvActivateCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if ($venvActivate) {
  . $venvActivate
  Write-Host "Activated venv: $venvActivate" -ForegroundColor Green
} else {
  Write-Warning "No venv activate script found (checked: $($venvActivateCandidates -join '; ')). Commands may run in the wrong Python environment."
}

function Test-PortListening([int]$Port) {
  try {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    return [bool]$conn
  } catch {
    return $false
  }
}

function Get-ListeningAddresses([int]$Port) {
  try {
    return @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty LocalAddress -Unique)
  } catch {
    return @()
  }
}

function Stop-ByPort([int]$Port, [string]$Name) {
  try {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $conn) {
      return
    }

    $processId = $conn.OwningProcess
    if ($processId -and $processId -gt 0) {
      Write-Host "Stopping $Name (PID $processId) on :${Port} ..." -ForegroundColor Cyan
      Stop-Process -Id $processId -Force
      Start-Sleep -Seconds 1
    }
  } catch {
    Write-Warning "Failed stopping $Name on :${Port}: $($_.Exception.Message)"
  }
}

function Start-IfNotListening(
  [string]$Name,
  [int]$Port,
  [string]$FilePath,
  [string[]]$ArgumentList,
  [string]$WorkingDirectory,
  [string]$StdoutPath,
  [string]$StderrPath
) {
  if (Test-PortListening -Port $Port) {
    Write-Host "$Name already listening on :$Port (skip)" -ForegroundColor Yellow
    return
  }

  Write-Host "Starting $Name on :$Port ..." -ForegroundColor Cyan
  Start-Process -FilePath $FilePath -ArgumentList $ArgumentList -WorkingDirectory $WorkingDirectory -RedirectStandardOutput $StdoutPath -RedirectStandardError $StderrPath -WindowStyle Hidden | Out-Null
}

# 1) LiteLLM
$litellmOut = Join-Path $logsDir 'litellm.stdout.log'
$litellmErr = Join-Path $logsDir 'litellm.stderr.log'
$litellmScript = Join-Path $PSScriptRoot 'run_litellm_with_env.ps1'
Start-IfNotListening -Name 'LiteLLM' -Port $LiteLLMPort -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File', $litellmScript, '-Port', "$LiteLLMPort") -WorkingDirectory $root -StdoutPath $litellmOut -StderrPath $litellmErr

# 2) Middleware
$mwOut = Join-Path $logsDir 'middleware.stdout.log'
$mwErr = Join-Path $logsDir 'middleware.stderr.log'
$mwDir = Join-Path $root 'llm-mw'
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
$pythonExe = if ($pythonCmd) { $pythonCmd.Source } else { $null }
if (-not $pythonExe) {
  throw "python executable not found on PATH. Ensure your venv is activated or install Python."
}
Start-IfNotListening -Name 'Middleware' -Port $MiddlewarePort -FilePath $pythonExe -ArgumentList @('-m','uvicorn','main:app','--host','0.0.0.0','--port',"$MiddlewarePort") -WorkingDirectory $mwDir -StdoutPath $mwOut -StderrPath $mwErr

# 3) OpenWebUI
$webuiOut = Join-Path $logsDir 'openwebui.stdout.log'
$webuiErr = Join-Path $logsDir 'openwebui.stderr.log'
$openWebUiCmd = Get-Command open-webui -ErrorAction SilentlyContinue
$openWebUiExe = if ($openWebUiCmd) { $openWebUiCmd.Source } else { $null }
if (-not $openWebUiExe) {
  throw "open-webui command not found. Install it in your Python environment: pip install open-webui"
}

$dataDir = Join-Path $root 'openwebui_data'



# OpenWebUI prints a unicode banner on startup. When stdout/stderr is redirected on Windows,
# the default encoding may be a legacy codepage (e.g. cp1252), causing UnicodeEncodeError.
# Force UTF-8 for the child process.
$webuiCmd = @(
  '$env:PYTHONUTF8=''1'';'
  '$env:PYTHONIOENCODING=''utf-8'';'
  "`$env:DATA_DIR='$dataDir';"
  '[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new();'
  "& '$openWebUiExe' serve --host $OpenWebUIHost --port $OpenWebUIPort"
) -join ' '

# If OpenWebUI is already listening but only on loopback (127.0.0.1/::1),
# restart it so it can bind to the desired host (e.g. 0.0.0.0) for LAN access.
if (Test-PortListening -Port $OpenWebUIPort) {
  $addrs = Get-ListeningAddresses -Port $OpenWebUIPort
  $isLoopbackOnly = ($addrs.Count -gt 0) -and ($addrs | Where-Object { $_ -notin @('127.0.0.1','::1') } | Measure-Object).Count -eq 0
  $wantsNonLoopback = ($OpenWebUIHost -eq '0.0.0.0' -or $OpenWebUIHost -eq '::' -or $OpenWebUIHost -eq '::0')
  if ($wantsNonLoopback -and $isLoopbackOnly) {
    Write-Host "OpenWebUI is listening on loopback only ($($addrs -join ', ')). Restarting for LAN access..." -ForegroundColor Yellow
    Stop-ByPort -Port $OpenWebUIPort -Name 'OpenWebUI'
  }
}

Start-IfNotListening -Name 'OpenWebUI' -Port $OpenWebUIPort -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-Command', $webuiCmd) -WorkingDirectory $root -StdoutPath $webuiOut -StderrPath $webuiErr

foreach ($portToWait in @($LiteLLMPort, $MiddlewarePort, $OpenWebUIPort)) {
  $maxWaitSeconds = if ($portToWait -eq $OpenWebUIPort) { 180 } else { 10 }
  $waited = 0
  while (-not (Test-PortListening -Port $portToWait) -and $waited -lt $maxWaitSeconds) {
    Start-Sleep -Seconds 1
    $waited += 1
  }
}

Write-Host "\nStatus:" -ForegroundColor Green
Write-Host ("  LiteLLM     :{0}  {1}" -f $LiteLLMPort, (Test-PortListening -Port $LiteLLMPort))
Write-Host ("  Middleware  :{0}  {1}" -f $MiddlewarePort, (Test-PortListening -Port $MiddlewarePort))
Write-Host ("  OpenWebUI   :{0}  {1}" -f $OpenWebUIPort, (Test-PortListening -Port $OpenWebUIPort))

Write-Host "\nOpen (local) : http://127.0.0.1:$OpenWebUIPort" -ForegroundColor Green
Write-Host "Open (LAN)   : http://<your-ip>:$OpenWebUIPort  (e.g. http://192.168.x.x:$OpenWebUIPort)" -ForegroundColor Green
Write-Host "Logs: $logsDir" -ForegroundColor Green
