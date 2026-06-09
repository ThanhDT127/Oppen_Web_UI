param (
    [string]$BackupFile = "C:\Users\RD03590\Downloads\backup_openwebui_2026-06-03_10-26-01.sql"
)

# 1. Check if backup file exists
if (-not (Test-Path $BackupFile)) {
    Write-Error "Backup file not found at: $BackupFile"
    exit 1
}

# 2. Get absolute path of backup file
$BackupFileAbs = (Get-Item $BackupFile).FullName
Write-Host "Found backup file at: $BackupFileAbs" -ForegroundColor Green

# 3. Stop Open WebUI application container to release connections
Write-Host "Stopping openwebui-app container..." -ForegroundColor Cyan
docker stop openwebui-app

# 4. Copy the backup file into the postgres container
Write-Host "Copying backup file to openwebui-postgres container..." -ForegroundColor Cyan
docker cp "$BackupFileAbs" openwebui-postgres:/tmp/backup.sql
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to copy backup file to container."
    docker start openwebui-app
    exit 1
}

# 5. Terminate active connections, recreate database, and restore
Write-Host "Terminating active connections and recreating database 'openwebui'..." -ForegroundColor Cyan
docker exec openwebui-postgres psql -U openwebui_user -d postgres --pset=pager=off -c "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = 'openwebui' AND pid <> pg_backend_pid();"
docker exec openwebui-postgres psql -U openwebui_user -d postgres --pset=pager=off -c "DROP DATABASE IF EXISTS openwebui;"
docker exec openwebui-postgres psql -U openwebui_user -d postgres --pset=pager=off -c "CREATE DATABASE openwebui;"
docker exec openwebui-postgres psql -U openwebui_user -d openwebui --pset=pager=off -c "CREATE EXTENSION IF NOT EXISTS vector;"

Write-Host "Restoring database from backup (this may take a minute)..." -ForegroundColor Cyan
docker exec openwebui-postgres psql -U openwebui_user -d openwebui --pset=pager=off -f /tmp/backup.sql
$RestoreStatus = $LASTEXITCODE

# 6. Cleanup temporary file in container
docker exec openwebui-postgres rm /tmp/backup.sql

# 7. Restart Open WebUI application container
Write-Host "Starting openwebui-app container..." -ForegroundColor Cyan
docker start openwebui-app

if ($RestoreStatus -eq 0) {
    Write-Host "Database restored successfully!" -ForegroundColor Green
} else {
    Write-Warning "Database restore finished, but exit code was non-zero. Please check logs above."
}
