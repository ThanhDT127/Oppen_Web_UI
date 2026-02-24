#!/usr/bin/env pwsh
# ============================================
# Start Open WebUI Docker Stack
# ============================================

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host "`n🚀 Starting Open WebUI Docker Stack..." -ForegroundColor Green

# Check if Docker is running
try {
    docker info > $null 2>&1
} catch {
    Write-Host "❌ Docker is not running! Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  .env file not found!" -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Write-Host "📋 Copying from .env.example..." -ForegroundColor Cyan
        Copy-Item ".env.example" ".env"
        Write-Host "⚠️  Please edit .env file with your actual API keys!" -ForegroundColor Yellow
        Write-Host "   Then run this script again." -ForegroundColor Yellow
        notepad ".env"
        exit 1
    } else {
        Write-Host "❌ .env.example not found either!" -ForegroundColor Red
        exit 1
    }
}

# Pull latest images
Write-Host "`n📥 Pulling latest images..." -ForegroundColor Cyan
docker-compose pull

# Build custom images
Write-Host "`n🔨 Building middleware image..." -ForegroundColor Cyan
docker-compose build middleware

# Start services
Write-Host "`n🔧 Starting services..." -ForegroundColor Cyan
docker-compose up -d

# Wait for health checks
Write-Host "`n⏳ Waiting for services to be healthy (30s)..." -ForegroundColor Cyan
Start-Sleep -Seconds 30

# Check status
Write-Host "`n📊 Service Status:" -ForegroundColor Green
docker-compose ps

# Health check results
Write-Host "`n🔍 Health Checks:" -ForegroundColor Cyan

$services = @(
    @{ Name = "PostgreSQL"; Url = "localhost:5432"; Check = "docker-compose exec -T postgres pg_isready -U openwebui_user -d openwebui" },
    @{ Name = "LiteLLM"; Url = "http://localhost:4000/health"; Check = "curl -s http://localhost:4000/health" },
    @{ Name = "Middleware"; Url = "http://localhost:5000/health"; Check = "curl -s http://localhost:5000/health" },
    @{ Name = "Open WebUI"; Url = "http://localhost:3000"; Check = "curl -s http://localhost:3000" }
)

foreach ($svc in $services) {
    try {
        $result = Invoke-Expression $svc.Check 2>$null
        if ($result) {
            Write-Host "  ✅ $($svc.Name): OK" -ForegroundColor Green
        } else {
            Write-Host "  ⏳ $($svc.Name): Starting..." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  ⏳ $($svc.Name): Starting..." -ForegroundColor Yellow
    }
}

Write-Host "`n✅ Stack started successfully!" -ForegroundColor Green
Write-Host @"

📍 Access Points:
   🌐 Open WebUI:  http://localhost:3000
   🔧 Middleware:  http://localhost:5000/health
   🤖 LiteLLM:     http://localhost:4000/health
   🗄️  PostgreSQL: localhost:5432

📝 Next Steps:
   1. Open http://localhost:3000 in your browser
   2. Create an admin account (first user)
   3. Go to Settings → Connections
   4. Set API Base URL: http://middleware:5000/v1
   5. Set API Key: (your SUBKEY_ADMIN from users.json)
   6. Start chatting!

📋 Useful Commands:
   View logs:     docker-compose logs -f
   Stop stack:    .\scripts\stop_all.ps1
   Restart:       .\scripts\restart_all.ps1

"@ -ForegroundColor Cyan
