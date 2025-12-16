param(
  [int]$LiteLLMPort = 4000,
  [int]$MiddlewarePort = 5000,
  [int]$OpenWebUIPort = 3000,
  [string]$OpenWebUIHost = "127.0.0.1"
)

$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$logsDir = Join-Path $root 'logs'
if (!(Test-Path -LiteralPath $logsDir)) {
  New-Item -ItemType Directory -Path $logsDir | Out-Null
}

$venvActivate = Join-Path $PSScriptRoot "..\..\..\.venv\Scripts\Activate.ps1"
if (Test-Path -LiteralPath $venvActivate) {
  . $venvActivate
  Write-Host "Activated venv: $venvActivate" -ForegroundColor Green
} else {
  Write-Warning "Venv activate script not found at $venvActivate. Commands may run in the wrong Python environment."
}

function Test-PortListening([int]$Port) {
  try {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    return [bool]$conn
  } catch {
    return $false
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
$pythonExe = 'D:\Works\.venv\Scripts\python.exe'
Start-IfNotListening -Name 'Middleware' -Port $MiddlewarePort -FilePath $pythonExe -ArgumentList @('-m','uvicorn','main:app','--host','0.0.0.0','--port',"$MiddlewarePort") -WorkingDirectory $mwDir -StdoutPath $mwOut -StderrPath $mwErr

# 3) OpenWebUI
$webuiOut = Join-Path $logsDir 'openwebui.stdout.log'
$webuiErr = Join-Path $logsDir 'openwebui.stderr.log'
$openWebUiExe = 'D:\Works\.venv\Scripts\open-webui.exe'

# OpenWebUI prints a unicode banner on startup. When stdout/stderr is redirected on Windows,
# the default encoding may be a legacy codepage (e.g. cp1252), causing UnicodeEncodeError.
# Force UTF-8 for the child process.
$webuiCmd = @(
  '$env:PYTHONUTF8=''1'';'
  '$env:PYTHONIOENCODING=''utf-8'';'
  '[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new();'
  "& '$openWebUiExe' serve --host $OpenWebUIHost --port $OpenWebUIPort"
) -join ' '

Start-IfNotListening -Name 'OpenWebUI' -Port $OpenWebUIPort -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-Command', $webuiCmd) -WorkingDirectory $root -StdoutPath $webuiOut -StderrPath $webuiErr

foreach ($portToWait in @($LiteLLMPort, $MiddlewarePort, $OpenWebUIPort)) {
  $maxWaitSeconds = if ($portToWait -eq $OpenWebUIPort) { 25 } else { 5 }
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

Write-Host "\nOpen: http://127.0.0.1:$OpenWebUIPort" -ForegroundColor Green
Write-Host "Logs: $logsDir" -ForegroundColor Green
