param(
  [string]$EnvFile = "$PSScriptRoot\..\llm-mw\.env",
  [int]$Port = 4000
)

$venvActivate = Join-Path $PSScriptRoot "..\..\..\.venv\Scripts\Activate.ps1"
if (Test-Path -LiteralPath $venvActivate) {
  . $venvActivate
  Write-Host "Activated venv: $venvActivate" -ForegroundColor Green
}
else {
  Write-Warning "Venv activate script not found at $venvActivate. LiteLLM may run from a different Python environment."
}

if (-not (Test-Path -LiteralPath $EnvFile)) {
  throw "Env file not found: $EnvFile"
}

Get-Content -LiteralPath $EnvFile | ForEach-Object {
  $line = $_.Trim()
  if ($line.Length -eq 0) { return }
  if ($line.StartsWith('#')) { return }

  $parts = $line -split '=', 2
  if ($parts.Count -ne 2) { return }

  $name = $parts[0].Trim()
  $value = $parts[1].Trim()

  if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
    $value = $value.Substring(1, $value.Length - 2)
  }

  [Environment]::SetEnvironmentVariable($name, $value, 'Process')
}

Write-Host "Loaded env from $EnvFile" -ForegroundColor Green

# When stdout/stderr is redirected (e.g. Start-Process -RedirectStandardOutput),
# Windows may default to a legacy encoding (cp1252), and LiteLLM's unicode banner
# can crash with UnicodeEncodeError. Force UTF-8 output.
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
try { [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new() } catch { }

# If DATABASE_URL is present in the current process environment (from a previous run),
# LiteLLM will try to initialize Prisma even if the YAML config doesn't require it.
Remove-Item -Path env:DATABASE_URL -ErrorAction SilentlyContinue

function Assert-EnvValue([string]$Name) {
  $value = [Environment]::GetEnvironmentVariable($Name, 'Process')
  if ($value.Contains('<') -or $value.Contains('>')) {
    throw "Env var '$Name' still looks like a placeholder ($value). Replace it with a real key in $EnvFile."
  }
}

$openai = [Environment]::GetEnvironmentVariable('OPENAI_API_KEY', 'Process')
$gemini = [Environment]::GetEnvironmentVariable('GEMINI_API_KEY', 'Process')

# Hard-fail only if someone left placeholders in place.
if (-not [string]::IsNullOrWhiteSpace($openai)) { Assert-EnvValue 'OPENAI_API_KEY' }
if (-not [string]::IsNullOrWhiteSpace($gemini)) { Assert-EnvValue 'GEMINI_API_KEY' }

if ([string]::IsNullOrWhiteSpace($openai) -and [string]::IsNullOrWhiteSpace($gemini)) {
  throw "No provider API keys found. Set OPENAI_API_KEY and/or GEMINI_API_KEY in $EnvFile before starting LiteLLM."
}

if ([string]::IsNullOrWhiteSpace($openai)) {
  Write-Warning "OPENAI_API_KEY is not set. OpenAI models (gpt-*) will fail with 401 until you set it."
}
if ([string]::IsNullOrWhiteSpace($gemini)) {
  Write-Warning "GEMINI_API_KEY is not set. Gemini models (gemini-*) will fail until you set it."
}

Push-Location (Join-Path $PSScriptRoot '..')
try {
  $litellmCmd = Get-Command litellm -ErrorAction SilentlyContinue
  if ($litellmCmd) {
    Write-Host "Using litellm: $($litellmCmd.Source)" -ForegroundColor Green
  }
  litellm --config .\litellm\litellm_config.yaml --port $Port
}
finally {
  Pop-Location
}
