#!/usr/bin/env pwsh
# ==============================================================================
# Script: backup_db.ps1
# Description: Automated PostgreSQL database backup for OpenWebUI & Middleware
# ==============================================================================

$ErrorActionPreference = "Stop"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

# Resolve absolute path for backups directory
$BackupDir = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\backups"))
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

$LogFile = Join-Path $BackupDir "backup_log.txt"
$LogMsg = ""

Write-Host "Checking openwebui-postgres container status..." -ForegroundColor Cyan
try {
    $Running = docker inspect -f '{{.State.Running}}' openwebui-postgres 2>$null
    if ($Running -ne "true") {
        $LogMsg = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - ERROR: Container openwebui-postgres is not running!"
        Add-Content -Path $LogFile -Value $LogMsg
        Write-Error "Container openwebui-postgres is not running! Cannot perform backup."
        exit 1
    }
} catch {
    $LogMsg = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - ERROR: Docker command failed to check status."
    Add-Content -Path $LogFile -Value $LogMsg
    Write-Error "Docker is not running or status check failed."
    exit 1
}

# Define temporary backup paths on host
$OpenWebUIFile = Join-Path $BackupDir "openwebui_$Timestamp.sql"
$MiddlewareFile = Join-Path $BackupDir "middleware_$Timestamp.sql"
$ZipFile = Join-Path $BackupDir "backup_$Timestamp.zip"

Write-Host "Starting database backup process..." -ForegroundColor Cyan

try {
    # 1. Backup openwebui database
    Write-Host "  -> Dumping database 'openwebui' inside container..." -ForegroundColor Cyan
    docker exec openwebui-postgres pg_dump -U openwebui_user -d openwebui -f /tmp/openwebui.sql
    
    Write-Host "  -> Copying dump file to host..." -ForegroundColor Cyan
    docker cp openwebui-postgres:/tmp/openwebui.sql "$OpenWebUIFile"
    docker exec openwebui-postgres rm /tmp/openwebui.sql

    # 2. Backup middleware database
    Write-Host "  -> Dumping database 'middleware' inside container..." -ForegroundColor Cyan
    docker exec openwebui-postgres pg_dump -U openwebui_user -d middleware -f /tmp/middleware.sql
    
    Write-Host "  -> Copying dump file to host..." -ForegroundColor Cyan
    docker cp openwebui-postgres:/tmp/middleware.sql "$MiddlewareFile"
    docker exec openwebui-postgres rm /tmp/middleware.sql

    # 3. Compress files into ZIP
    Write-Host "  -> Compressing SQL dumps into ZIP archive..." -ForegroundColor Cyan
    Compress-Archive -Path $OpenWebUIFile, $MiddlewareFile -DestinationPath $ZipFile -Force

    # 4. Clean up temporary host SQL files
    Remove-Item $OpenWebUIFile, $MiddlewareFile -Force

    Write-Host "Backup completed successfully: backup_$Timestamp.zip" -ForegroundColor Green
    $LogMsg = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Backup completed successfully: backup_$Timestamp.zip"
    Add-Content -Path $LogFile -Value $LogMsg

    # 5. Clean up backups older than 7 days
    Write-Host "Cleaning up old backups (older than 7 days)..." -ForegroundColor Cyan
    Get-ChildItem -Path $BackupDir -Filter "backup_*.zip" | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } | ForEach-Object {
        $OldFile = $_.FullName
        $OldName = $_.Name
        Remove-Item $OldFile -Force
        Write-Host "  -> Deleted old backup: $OldName" -ForegroundColor Yellow
        Add-Content -Path $LogFile -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Cleanup: Deleted old backup $OldName"
    }

} catch {
    Write-Host "Database backup failed!" -ForegroundColor Red
    $LogMsg = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - ERROR: Backup failed. Reason: $_"
    Add-Content -Path $LogFile -Value $LogMsg
    
    # Clean up temporary host SQL files if they exist
    if (Test-Path $OpenWebUIFile) { Remove-Item $OpenWebUIFile -Force }
    if (Test-Path $MiddlewareFile) { Remove-Item $MiddlewareFile -Force }
    
    exit 1
}
