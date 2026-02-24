#!/usr/bin/env pwsh
# ============================================
# Stop Open WebUI Docker Stack
# ============================================

Set-Location $PSScriptRoot\..

Write-Host "`n🛑 Stopping Open WebUI Docker Stack..." -ForegroundColor Yellow

docker-compose down

Write-Host "`n✅ All services stopped" -ForegroundColor Green
Write-Host "   Data is preserved in Docker volumes" -ForegroundColor Cyan
Write-Host @"

To remove data volumes (CAUTION - data loss):
   docker volume rm oppen_web_ui_postgres_data
   docker volume rm oppen_web_ui_openwebui_data
   docker volume rm oppen_web_ui_litellm_logs

"@ -ForegroundColor Gray
