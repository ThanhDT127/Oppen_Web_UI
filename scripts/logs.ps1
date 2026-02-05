#!/usr/bin/env pwsh
# ============================================
# View Docker Stack Logs
# ============================================

param(
    [Parameter(Position=0)]
    [ValidateSet("all", "postgres", "litellm", "middleware", "open-webui")]
    [string]$Service = "all",
    
    [switch]$Follow,
    [int]$Tail = 100
)

Set-Location $PSScriptRoot\..

$args_list = @("logs")

if ($Follow) {
    $args_list += "-f"
}

$args_list += "--tail=$Tail"

if ($Service -ne "all") {
    $args_list += $Service
}

Write-Host "📋 Viewing logs for: $Service" -ForegroundColor Cyan
Write-Host "   Press Ctrl+C to exit" -ForegroundColor Gray
Write-Host ""

docker-compose @args_list
