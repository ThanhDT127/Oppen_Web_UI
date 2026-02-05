# 🎯 OPPEN WEB UI - Multi-Model LLM Chat Platform

Professional 3-tier LLM chat system with authentication, quota management, and usage tracking for OpenAI, Gemini, and other providers.

[![Architecture](https://img.shields.io/badge/Architecture-FastAPI_+_LiteLLM-blue)](docs/ARCHITECTURE.md)
[![API Reference](https://img.shields.io/badge/API-OpenAI_Compatible-green)](docs/API_REFERENCE.md)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 📋 TABLE OF CONTENTS

- [Overview](#-overview)
- [Quick Start](#-quick-start)
- [Features](#-features)
- [Architecture](#-architecture)
- [Documentation](#-documentation)
- [Configuration](#-configuration)
- [Deployment](#-deployment)
- [Troubleshooting](#-troubleshooting)

---

## 🎯 OVERVIEW

**Oppen Web UI** is a production-ready LLM chat platform that provides:

- **Multi-User Support:** Secure subkey-based authentication with per-user quotas
- **Multi-Model Access:** Unified API for OpenAI, Gemini, Anthropic, and other providers
- **Real-Time Streaming:** Server-Sent Events for fast, responsive chat
- **Usage Tracking:** Detailed audit logs and dashboard analytics
- **Admin Dashboard:** Web-based UI for subkey management and monitoring

### System Architecture

```
┌─────────────────┐
│   OpenWebUI     │  Port 3000 - Web Chat Interface
│  (User Layer)   │  • Rich chat UI with history
│                 │  • File uploads & multimodal
└────────┬────────┘
         │ OpenAI API Format
         ↓
┌─────────────────┐
│  LLM Middleware │  Port 5000 - Auth & Quota Layer
│    (FastAPI)    │  • Subkey validation
│                 │  • Quota enforcement
│                 │  • Audit logging
│                 │  • Admin dashboard
└────────┬────────┘
         │ LiteLLM Proxy Format
         ↓
┌─────────────────┐
│  LiteLLM Proxy  │  Port 4000 - Model Router
│                 │  • Multi-provider routing
│                 │  • Load balancing
│                 │  • Cost tracking
└────────┬────────┘
         │
    ┌────┴────┬──────────┐
    ↓         ↓          ↓
 OpenAI   Gemini   Other Providers
```

### Request Flow

```
User Message → OpenWebUI → Middleware (Subkey Auth + Quota Check) → LiteLLM → Provider API → Response Stream
```

---

## 🚀 QUICK START

### Prerequisites

- **Python 3.10+** with virtual environment
- **Windows PowerShell** (for scripts)
- **API Keys:** OpenAI and/or Gemini API keys

### 1. Clone & Setup

```powershell
git clone <repository_url>
cd Oppen_Web_UI_fresh
D:\Works\.venv\Scripts\Activate.ps1  # Activate your venv
```

### 2. Configure Environment

Copy `.env.example` to `.env` and set your keys:

```bash
# .env
LITELLM_KEY=your-litellm-admin-key
ADMIN_KEY=your-admin-master-key

# Security Keys (REQUIRED - Generate random strings)
JWT_SECRET=your-jwt-secret-min-32-chars
MW_SECRET=your-middleware-secret-min-32-chars

# Provider API Keys
OPENAI_API_KEY=sk-your-openai-key
GEMINI_API_KEY=your-gemini-key
```

### 3. Start All Services (One Command)

```powershell
.\scripts\start.ps1
```

This starts:
1. **LiteLLM Proxy** (Port 4000)
2. **Middleware** (Port 5000)
3. **OpenWebUI** (Port 3000)

### 4. Access the Platform

- **Chat Interface:** http://localhost:3000
- **Admin Dashboard:** http://localhost:5000/dashboard
- **Health Check:** http://localhost:5000/health

### 5. Configure Your Subkey

**Option A: Use existing user**

Edit `llm-mw/data/users.json` and add your subkey. Example:

```json
[
  {
    "user_id": "your_username",
    "subkey": "sk_your_actual_subkey_here",
    "active": true,
    "allowed_models": ["*"],
    "used_tokens": 0,
    "used_cost_usd": 0.0,
    "quota": {
      "period": "monthly",
      "timezone": "Asia/Bangkok",
      "limit_tokens": 1000000,
      "limit_cost_usd": 50.0,
      "period_start": 0,
      "used_tokens": 0,
      "used_cost_usd": 0.0
    }
  }
]
```

**Option B: Use example file**

Copy `llm-mw/users.example.json` to `llm-mw/data/users.json` and customize.

**Then configure OpenWebUI:**
1. Open http://localhost:3000
2. Register/login (first user becomes admin)
3. Go to **Settings** → **Connections**
4. Set:
   - **API Base URL:** `http://127.0.0.1:5000/v1`
   - **API Key:** `sk_your_actual_subkey_here`
5. Save and start chatting!

---

## ✨ FEATURES

### Core Capabilities

✅ **Multi-User Authentication**
- Subkey-based access control with HMAC-SHA256 hashing
- Per-user period-based quota (weekly/monthly)
- Active/inactive user management

✅ **Real-Time Chat**
- Streaming responses via Server-Sent Events
- Support for all OpenAI-compatible models
- Multimodal support (text, images, audio)

✅ **Image Generation** 🎨
- OpenAI DALL-E 3 (`gpt-image-1`) and Gemini Image (`gemini-2.5-flash-image`)
- Automatic fallback (OpenAI → Gemini) on org verification errors
- Per-user quota limits (`limit_image_requests`, `limit_cost_usd`)
- Control-grade audit logging (provider, size, fallback tracking)
- Media endpoint for direct image serving: `/v1/_mw/media/<id>.png`
- See [docs/IMAGE_GENERATION.md](docs/IMAGE_GENERATION.md) for configuration

✅ **Admin Dashboard**
- Web-based UI at `/dashboard`
- Live metrics from audit.jsonl
- JWT authentication (4-hour sessions)

✅ **Usage Tracking**
- JSONL audit logs (`logs/audit.jsonl`)
- Per-user quota tracking (tokens & cost)
- Period-based limits with auto-reset
- Pending request reconciliation

✅ **Security**
- JWT authentication for dashboard (4-hour sessions)
- HTTP-only cookies prevent XSS attacks
- Environment-based secret management
- Warnings for default/missing secrets

✅ **Multi-Provider Support**
- OpenAI (GPT-4, GPT-3.5, DALL-E)
- Google Gemini (Gemini Pro, Gemini Pro Vision, Gemini Image)
- Anthropic Claude (via LiteLLM)
- Custom model aliases

---

## 🏗️ ARCHITECTURE

Detailed architecture documentation: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

### Service Responsibilities

| Service | Port | Purpose |
|---------|------|---------|
| **OpenWebUI** | 3000 | Web chat interface, user profiles, history |
| **Middleware** | 5000 | Auth, quota, audit, dashboard, streaming proxy |
| **LiteLLM** | 4000 | Multi-provider routing, load balancing, cost tracking |

### Middleware Modules (Refactored)

```
llm-mw/
├── api/              # Endpoint handlers (11 modules)
│   ├── chat.py       # /v1/chat/completions (main proxy)
│   ├── admin.py      # /admin/* (usage, reset, reconcile)
│   ├── models.py     # /v1/models (list)
│   ├── dashboard_login.py  # /dashboard/login|logout
│   ├── summary.py    # /v1/_mw/summary (dashboard metrics)
│   ├── stream.py     # /v1/_mw/stream (SSE audit)
│   ├── health.py     # /health (system check)
│   ├── images.py     # /v1/images/generations
│   ├── audio.py      # /v1/audio/transcriptions
│   └── media.py      # /media/* (file serving)
├── core/             # Business logic
│   ├── auth.py       # User authentication & management
│   ├── quota.py      # Quota tracking & enforcement
│   ├── cost.py       # Cost calculation & pricing
│   └── audit_state.py # Request state management
├── utils/            # Helpers
│   ├── auth_guard.py # JWT validation decorator
│   ├── jwt_auth.py   # JWT token generation
│   ├── logging.py    # Structured logging
│   ├── helpers.py    # Utility functions
│   └── media.py      # Media file handling
├── services/         # External service clients
│   └── litellm.py    # LiteLLM proxy client
├── dashboard/        # Admin UI (HTML/CSS/JS)
├── data/             # Data storage
│   ├── users.json    # User & quota database
│   ├── prices.json   # Model pricing data
│   └── pending.csv   # Streaming requests tracking
├── main.py           # FastAPI app entry point
└── config.py         # Environment & logging setup
```

---

## 📚 DOCUMENTATION

| Document | Description |
|----------|-------------|
| [README.md](README.md) | **This file** - Project overview & quick start |
| [docs/QUICKSTART.md](docs/QUICKSTART.md) | Installation guide & startup commands |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, data flow, security architecture |
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | Complete endpoint documentation with examples |
| [docs/DASHBOARD.md](docs/DASHBOARD.md) | Admin dashboard usage & metrics explained |

---

## ⚙️ CONFIGURATION

### Environment Variables

All configuration is in `.env` file:

```bash
# LiteLLM Configuration
LITELLM_BASE=http://127.0.0.1:4000/v1
LITELLM_KEY=super_admin_key_123

# Middleware Security
ADMIN_KEY=admin_master_key_456
JWT_SECRET=<generate-secure-random-32-chars>
MW_SECRET=<generate-secure-random-32-chars>

# OpenWebUI
DATA_DIR=D:\Works\Oppen_Web_UI_fresh\openwebui_data
WEBUI_SECRET_KEY=your-secret-key-here

# Provider API Keys
OPENAI_API_KEY=sk-your-openai-key
GEMINI_API_KEY=your-gemini-key
```

### Security Best Practices

⚠️ **NEVER commit `.env` to version control**

✅ **Use strong random values for:**
- `JWT_SECRET` (min 32 characters)
- `MW_SECRET` (min 32 characters)
- `ADMIN_KEY` (min 20 characters)

✅ **File permissions:** Set `.env` to owner read-only (chmod 600)

✅ **Production deployment:**
- Use HTTPS (reverse proxy)
- Rotate secrets regularly
- Monitor audit logs
- Implement IP whitelisting

---

## 🛠️ DEPLOYMENT

### Local Development

```powershell
# Start all services
.\scripts\start.ps1

# Stop all services
.\scripts\stop.ps1
```

### Manual Startup (3 Terminals)

**Terminal 1 - LiteLLM:**
```powershell
D:\Works\.venv\Scripts\Activate.ps1
litellm --config litellm/litellm_config.yaml --port 4000
```

**Terminal 2 - Middleware:**
```powershell
D:\Works\.venv\Scripts\Activate.ps1
cd llm-mw
python main.py
```

**Terminal 3 - OpenWebUI:**
```powershell
D:\Works\.venv\Scripts\Activate.ps1
open-webui serve --port 3000
```

### Production Deployment

1. **Use systemd/supervisor** for process management
2. **Set up Nginx** as reverse proxy with SSL
3. **Configure firewall** (only expose port 3000)
4. **Enable log rotation** (10MB files, 5 backups)
5. **Monitor** via Prometheus/Grafana (TODO)

---

## 🐛 TROUBLESHOOTING

### Common Issues

**1. Service won't start - "Address already in use"**
```powershell
# Check what's using the port
netstat -ano | findstr :5000

# Kill the process
taskkill /PID <PID> /F

# Restart services
.\scripts\start.ps1
```

**2. Dashboard login fails - "Invalid credentials"**
- Verify `ADMIN_KEY` in `.env` matches your login password
- Check middleware logs: `logs/middleware.log`
- Clear browser cookies and try again

**3. LiteLLM proxy returns 502 errors**
- Verify LiteLLM is running: `curl http://localhost:4000/health`
- Check `LITELLM_KEY` matches in `.env` and `litellm_config.yaml`
- Review LiteLLM logs: `litellm/litellm.log`

**4. Quota exceeded errors**
- Check subkey quota: `GET /v1/_mw/subkey/<subkey>` (admin auth)
- Increase quota: `PUT /v1/_mw/subkey/<subkey>` with `{"quota": 200}`
- Reset usage counters: `POST /v1/_mw/subkey/<subkey>/reset`

**5. JWT token expired on dashboard**
- Default expiry: 4 hours
- Re-login at http://localhost:5000/dashboard
- Tokens stored in HTTP-only cookies

**6. Missing environment variables warnings**
```
⚠️  JWT_SECRET is using default value - CHANGE IN PRODUCTION!
```
- Edit `.env` file and add secure random values
- Restart middleware to reload configuration
- Verify no warnings in `logs/middleware.log`

### Health Check Commands

```powershell
# Check all services
curl http://localhost:4000/health  # LiteLLM
curl http://localhost:5000/health  # Middleware
curl http://localhost:3000         # OpenWebUI

# Check middleware with admin auth
curl http://localhost:5000/v1/_mw/summary `
  -H "Authorization: Bearer admin_master_key_456"
```

### Log Locations

| Service | Log File | Purpose |
|---------|----------|---------|
| Middleware | `logs/middleware.log` | Main application log |
| Middleware | `logs/middleware.requests.log` | Detailed request/response (JSON) |
| Middleware | `logs/audit.jsonl` | Audit trail (JSONL format) |
| LiteLLM | `litellm/litellm.log` | Proxy operations |
| OpenWebUI | `openwebui_data/webui.log` | Web interface logs |

### Reset Everything

```powershell
# Stop all services
.\scripts\stop.ps1

# Clear logs (optional)
Remove-Item logs\* -Recurse -Force

# Clear OpenWebUI database (⚠️ DELETES ALL CHAT HISTORY)
Remove-Item openwebui_data\webui.db

# Clear subkey storage
Remove-Item logs\subkeys.json

# Restart fresh
.\scripts\start.ps1
```

---

## 🤝 CONTRIBUTING

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📄 LICENSE

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 ACKNOWLEDGMENTS

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [LiteLLM](https://github.com/BerriAI/litellm) - Multi-provider LLM proxy
- [OpenWebUI](https://github.com/open-webui/open-webui) - Beautiful chat interface

---

## 📞 SUPPORT

- **Documentation:** [docs/](docs/)
- **Issues:** [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions:** [GitHub Discussions](https://github.com/your-repo/discussions)

---

**Last Updated:** December 22, 2025  
**Version:** 2.0 (Refactored Architecture)

---

### POST /v1/images/generations

Generate images với quota tracking.

**Request:**
```json
POST http://localhost:5000/v1/images/generations
Authorization: Bearer subkey_admin_123
Content-Type: application/json

{
  "model": "gpt-image-1",
  "prompt": "A beautiful sunset over mountains",
  "n": 1,
  "size": "1024x1024",
  "quality": "medium"
}
```

**Response:**
```json
{
  "created": 1766047478,
  "data": [
    {
      "url": "http://localhost:5000/v1/_mw/media/abc123.png"
    }
  ],
  "_mw_user": "admin",
  "_mw_request_id": "mw_xyz789",
  "_mw_added_cost_usd": 0.042
}
```

**Models:**
- `gpt-image-1` (OpenAI DALL-E)
- `gemini-2.5-flash-image` (Google Imagen)

---

## ⚙️ CẤU HÌNH

### 1. LiteLLM (`litellm/litellm_config.yaml`)

```yaml
model_list:
  # ChatGPT Models
  - model_name: gpt-4o-mini
    litellm_params:
      model: openai/gpt-4o-mini
      api_key: os.environ/OPENAI_API_KEY

  # Gemini Models
  - model_name: gemini-2.0-flash
    litellm_params:
      model: gemini/gemini-2.0-flash
      api_key: os.environ/GEMINI_API_KEY

litellm_settings:
  drop_params: false

general_settings:
  master_key: os.environ/LITELLM_KEY
```

---

### 2. Users (`llm-mw/users.json`)

```json
[
  {
    "user_id": "admin",
    "subkey": "subkey_admin_123",
    "active": true,
    "allowed_models": ["*"],
    "used_tokens": 0,
    "used_cost_usd": 0.0,
    "quota": {
      "period": "monthly",
      "timezone": "Asia/Bangkok",
      "limit_tokens": 0,
      "limit_cost_usd": 0,
      "period_start": 1764522000000,
      "used_tokens": 0,
      "used_cost_usd": 0.0,
      "used_image_requests": 0
    }
  }
]
```

**Quota Fields:**
- `period`: `"weekly"` hoặc `"monthly"`
- `limit_tokens`: 0 = unlimited
- `limit_cost_usd`: 0.0 = unlimited

---

## 💬 SỬ DỤNG

### Basic Chat Flow

1. **Chọn model** từ dropdown trong OpenWebUI
2. **Nhập message** và gửi
3. Middleware sẽ:
   - ✅ Validate subkey
   - ✅ Check allowed_models
   - ✅ Check quota
   - ✅ Forward request to LiteLLM
   - ✅ Track usage
4. **Nhận response** (streaming hoặc non-streaming)

---

## 🔍 TROUBLESHOOTING

### 1. Models không hiển thị

**Giải pháp:**
```powershell
# Test middleware
Invoke-WebRequest -Uri "http://localhost:5000/v1/models" `
  -Headers @{"Authorization"="Bearer subkey_admin_123"}

# Check OpenWebUI Settings → Connections
# Base URL: http://127.0.0.1:5000/v1
# API Key: subkey_admin_123
```

### 2. "Invalid sub-key" (403)

**Giải pháp:**
```powershell
# Check users.json
Get-Content llm-mw/users.json | ConvertFrom-Json | 
  Select-Object user_id, subkey, active
```

### 3. "Quota exceeded" (403)

**Giải pháp:**
```powershell
# Reset quota
$body = @{ user_id = "admin" } | ConvertTo-Json
Invoke-WebRequest -Uri "http://localhost:5000/admin/reset" `
  -Method Post `
  -Headers @{"Authorization"="Bearer admin_master_key_456"; "Content-Type"="application/json"} `
  -Body $body
```

---

## 📊 LOGS & MONITORING

### Log Files

| File | Location | Content |
|------|----------|---------|
| Middleware | `logs/middleware.log` | Request tracking |
| Middleware Detail | `logs/middleware.requests.log` | Full request/response |
| LiteLLM | `litellm/litellm.log` | LiteLLM operations |

```powershell
# Tail logs
Get-Content logs/middleware.log -Tail 20 -Wait
```

---

## 🔐 SECURITY NOTES

### ⚠️ Production Security Checklist

**Phiên bản hiện tại chưa sẵn sàng cho production!** Cần thực hiện:

#### 1. **Subkey Security** ✅ (Implemented)
- Subkeys được hash với HMAC-SHA256 trước khi lưu `users.json`
- **CRITICAL:** Đặt biến môi trường `MW_SECRET` với secret key mạnh:
  ```bash
  export MW_SECRET="your-256-bit-secret-key-here"
  ```
- Chạy migration script để hash subkeys hiện tại:
  ```bash
  cd llm-mw
  python migrate_subkeys.py
  ```

#### 2. **Audit Logging** ✅ (Implemented)
- Tất cả requests được ghi vào `logs/audit.jsonl` (JSONL format, 50MB rotation)
- Mỗi entry chứa: timestamp, user_id, model, tokens, cost, duration, status
- Dùng `/v1/_mw/summary?minutes=60` để aggregate usage statistics

#### 3. **Quota Management** ✅ (Fixed)
- Quota reset giữ nguyên lifetime usage counters (`user["used_*"]`)
- Chỉ reset period counters (`quota["used_*"]`) khi sang chu kỳ mới
- Lifetime data không bị mất khi reset hàng tháng/hàng tuần

#### 4. **Admin Endpoint Protection** ✅ (Implemented)
- `/admin/usage` scrubs sensitive data (subkey, subkey_hash) trước khi trả về
- Không còn rủi ro leak plaintext subkeys qua admin API

#### 5. **Monitoring** ✅ (Implemented)
- Enhanced `/health` endpoint với LiteLLM connectivity check, disk space, uptime
- Trả về 503 nếu hệ thống degraded (LiteLLM down hoặc disk space < 1GB)

#### 6. **TODO: Production Hardening** ⚠️
Cần bổ sung:
1. **CORS Restriction** (không dùng `["*"]`)
2. **HTTPS Only** với reverse proxy (nginx/traefik)
3. **Secrets Management** (không commit `.env` vào git)
4. **Database Migration** (PostgreSQL thay vì JSON files)
5. **Rate Limiting** per IP/user (tích hợp slowapi hoặc nginx)
6. **Backup Strategy** cho `users.json` và `audit.jsonl`

---

**Version:** 3.0 Baseline  
**Last Updated:** December 18, 2025  
**Status:** ✅ Ready for Development
