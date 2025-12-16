param(
  [string]$EnvFile = "$PSScriptRoot\..\llm-mw\.env",
  [int]$Port = 4000
)

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

Push-Location (Join-Path $PSScriptRoot '..')
try {
  litellm --config .\litellm\litellm_config.yaml --port $Port
}
finally {
  Pop-Location
}
