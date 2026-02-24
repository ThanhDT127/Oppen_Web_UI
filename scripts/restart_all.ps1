#!/usr/bin/env pwsh
# ============================================
# Restart Open WebUI Docker Stack
# ============================================

Set-Location $PSScriptRoot\..

Write-Host "`n🔄 Restarting Open WebUI Docker Stack..." -ForegroundColor Cyan

& "$PSScriptRoot\stop_all.ps1"
Start-Sleep -Seconds 3
& "$PSScriptRoot\start_all.ps1"
