# OpenWebUI + Middleware + LiteLLM - Hệ Thống Chat LLM (Baseline)

Hệ thống chat LLM 3 tầng với xác thực, quản lý quota và tracking usage cho ChatGPT & Gemini.

> **⚠️ PHIÊN BẢN BASELINE:** Phiên bản này tập trung vào **chat completions (streaming)** và **image generation**. Video/Audio generation sẽ được bổ sung qua OpenWebUI Tool/Pipe trong các phiên bản sau.

---

## 📋 MỤC LỤC

- [Tổng Quan](#-tổng-quan)
- [Kiến Trúc](#-kiến-trúc)  
- [Khởi Động Nhanh](#-khởi-động-nhanh)
- [Cấu Trúc Project](#-cấu-trúc-project)
- [Endpoints API](#-endpoints-api)
- [Cấu Hình](#-cấu-hình)
- [Sử Dụng](#-sử-dụng)
- [Troubleshooting](#-troubleshooting)

---

## 📋 TỔNG QUAN

**Kiến trúc:** `OpenWebUI (UI) → Middleware (Auth/Quota) → LiteLLM (Proxy) → ChatGPT/Gemini`

### Luồng Request

```
┌─────────────────┐
│   OpenWebUI     │  Port 3000 - Web chat interface
│                 │  - Chat với LLM models
│                 │  - Lưu chat history
└────────┬────────┘
         │ 
         │ POST /v1/chat/completions
         │ Header: Authorization: Bearer <subkey>
         ▼
┌─────────────────┐
│   Middleware    │  Port 5000 - Auth & Quota Management
│   (FastAPI)     │  - Xác thực subkey từ users.json
│                 │  - Kiểm tra quota (tokens/cost)
│                 │  - Track usage real-time
│                 │  - Logging & monitoring
└────────┬────────┘
         │
         │ POST /chat/completions
         │ Header: Authorization: Bearer <LITELLM_KEY>
         ▼
┌─────────────────┐
│    LiteLLM      │  Port 4000 - Unified LLM Proxy
│                 │  - Chuẩn hóa API OpenAI-compatible
│                 │  - Route requests đến providers
└────────┬────────┘
         │
         ├──────────────────┐
         ▼                  ▼
    ┌─────────┐       ┌──────────┐
    │ ChatGPT │       │  Gemini  │
    │ OpenAI  │       │  Google  │
    └─────────┘       └──────────┘
```

### Đặc Điểm Chính

✅ **Authentication:** Xác thực multi-user qua subkey  
✅ **Quota Management:** Giới hạn tokens & cost per user/period  
✅ **Streaming Support:** Real-time streaming responses  
✅ **Usage Tracking:** Theo dõi chi tiết usage & cost  
✅ **Multi-Provider:** Hỗ trợ OpenAI & Gemini qua một API  
✅ **Image Generation:** Tích hợp image generation với quota tracking  

---

## 🏗 KIẾN TRÚC

### 1. LiteLLM (Port 4000)
- **Chức năng:** Proxy thống nhất cho nhiều LLM providers
- **Input:** OpenAI-compatible API requests với LITELLM_KEY
- **Output:** Chuẩn hóa responses từ ChatGPT/Gemini
- **Config:** `litellm/litellm_config.yaml`

### 2. Middleware (Port 5000)
- **Chức năng:** Authentication, Authorization & Quota Management
- **Input:** API requests với subkey
- **Output:** Validated & tracked requests to LiteLLM
- **Code:** `llm-mw/main.py` (FastAPI)
- **Database:** `llm-mw/users.json` (flat-file)

### 3. OpenWebUI (Port 3000)
- **Chức năng:** Web-based chat interface
- **Input:** User interactions
- **Output:** API calls to Middleware
- **Storage:** SQLite database in `openwebui_data/`

---

## 🚀 KHỞI ĐỘNG HỆ THỐNG

### Yêu cầu

- Python 3.11+
- Virtual environment: `D:\Works\.venv`
- Windows PowerShell
- API Keys: OpenAI & Gemini

### Bước 1: Cài đặt dependencies (chỉ lần đầu)

```powershell
# Activate virtual environment
& D:/Works/.venv/Scripts/Activate.ps1

# Install packages
pip install "litellm[proxy]" open-webui fastapi uvicorn httpx python-dotenv
```

### Bước 2: Cấu hình Environment Variables

File `.env` đã có sẵn trong project root:

```bash
# D:\Works\Oppen_Web_UI_fresh\.env

LITELLM_BASE=http://127.0.0.1:4000/v1
LITELLM_KEY=YOUR_LITELLM_KEY
ADMIN_KEY=YOUR_ADMIN_KEY
DATA_DIR=D:\Works\Oppen_Web_UI_fresh\openwebui_data

# Provider API Keys
OPENAI_API_KEY=YOUR_OPENAI_API_KEYj1Zj8aTI6YYZH_h68O7vAsAjtcRLdppNT3BlbkFJH_eeRYwEgh99vWFnPwqvcNh0Fy81XmKhR-jR2PMzOQV1NVvANfbHESzOdZxMLqhffCNGVOuYIA
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
```

### Bước 3: Chạy 3 services (3 terminals riêng biệt)

#### Terminal 1 - LiteLLM (Port 4000)

```powershell
cd D:\Works\Oppen_Web_UI_fresh

# Load environment variables
$env:OPENAI_API_KEY=(Get-Content .env | Select-String 'OPENAI_API_KEY' | ForEach-Object { $_ -replace 'OPENAI_API_KEY=', '' })
$env:GEMINI_API_KEY=(Get-Content .env | Select-String 'GEMINI_API_KEY' | ForEach-Object { $_ -replace 'GEMINI_API_KEY=', '' })
$env:LITELLM_KEY=(Get-Content .env | Select-String 'LITELLM_KEY' | ForEach-Object { $_ -replace 'LITELLM_KEY=', '' })

# Start LiteLLM
& D:/Works/.venv/Scripts/Activate.ps1
litellm --config litellm/litellm_config.yaml --port 4000
```

**Verify:**
```powershell
Invoke-WebRequest -Uri "http://localhost:4000/health" `
  -Headers @{"Authorization"="Bearer YOUR_LITELLM_KEY"}
# Should return: {"healthy_endpoints": [...]}
```

#### Terminal 2 - Middleware (Port 5000)

```powershell
cd D:\Works\Oppen_Web_UI_fresh\llm-mw

& D:/Works/.venv/Scripts/Activate.ps1
uvicorn main:app --host 0.0.0.0 --port 5000
```

**Verify:**
```powershell
Invoke-WebRequest -Uri "http://localhost:5000/health"
# Should return: {"ok": true, "time": 1234567890}
```

#### Terminal 3 - OpenWebUI (Port 3000)

```powershell
& D:/Works/.venv/Scripts/Activate.ps1
open-webui serve --port 3000
```

**Truy cập:** http://localhost:3000

### Bước 4: Cấu hình OpenWebUI

1. Mở browser: `http://localhost:3000`
2. Đăng ký/đăng nhập tài khoản đầu tiên (sẽ là admin)
3. Vào **Settings** (⚙️) **→ Connections**
4. Cấu hình:
   ```
   OpenAI API
   - API Base URL: http://127.0.0.1:5000/v1
   - API Key: YOUR_SUBKEY_ADMIN
   ```
5. Click **Save**
6. Chọn model từ dropdown (vd: `gpt-4o-mini`, `gemini-2.0-flash`)
7. Bắt đầu chat! 🎉

---

## 🔌 ENDPOINTS API

### Endpoints được hỗ trợ (Baseline)

#### ✅ Core Endpoints

| Endpoint | Method | Auth | Streaming | Description |
|----------|--------|------|-----------|-------------|
| `/health` | GET | ❌ | ❌ | Health check with system status |
| `/v1/models` | GET | ✅ | ❌ | Liệt kê models (cần subkey) |
| `/v1/chat/completions` | POST | ✅ | ✅ | Chat với streaming support |
| `/v1/images/generations` | POST | ✅ | ❌ | Image generation |

#### ✅ Admin Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/admin/usage` | GET | 🔑 Admin | Xem usage statistics (scrubbed sensitive data) |
| `/admin/reset` | POST | 🔑 Admin | Reset quota counters |
| `/admin/reconcile` | POST | 🔑 Admin | Reconcile streaming usage |
| `/v1/_mw/summary` | GET | 🔑 Admin | Aggregate usage stats from audit log |

### 🚧 Planned Features (Future)

Các tính năng sau sẽ được implement qua **OpenWebUI Tool/Pipe**:

- **Video Generation** (`/v1/video/generations`)
- **Text-to-Speech** (`/v1/audio/speech`)
- **Speech-to-Text** (`/v1/audio/transcriptions`)

---

## 📝 CHI TIẾT ENDPOINTS

### GET /health

Enhanced health check endpoint with comprehensive system status (không cần auth).

**Request:**
```bash
GET http://localhost:5000/health
```

**Response:**
```json
{
  "ok": true,
  "time": 1766047478,
  "uptime_seconds": 3600,
  "litellm": "ok",
  "disk_free_gb": 125.45,
  "active_users": 3
}
```

**Status Codes:**
- `200`: System healthy
- `503`: System degraded (LiteLLM unavailable or low disk space)

---

### GET /v1/models

Liệt kê các models khả dụng. **Yêu cầu authentication.**

**Request:**
```bash
GET http://localhost:5000/v1/models
Authorization: Bearer YOUR_SUBKEY_ADMIN
```

**Response:**
```json
{
  "data": [
    {
      "id": "gpt-5",
      "object": "model",
      "created": 1234567890,
      "owned_by": "openai"
    },
    {
      "id": "gpt-4o-mini",
      "object": "model",
      "created": 1234567890,
      "owned_by": "openai"
    },
    {
      "id": "gemini-2.0-flash",
      "object": "model",
      "created": 1234567890,
      "owned_by": "google"
    }
  ]
}
```

---

### POST /v1/chat/completions

Chat completions với streaming support.

**Request (Non-streaming):**
```json
POST http://localhost:5000/v1/chat/completions
Authorization: Bearer YOUR_SUBKEY_ADMIN
Content-Type: application/json

{
  "model": "gpt-4o-mini",
  "messages": [
    {
      "role": "user",
      "content": "Hello in Vietnamese"
    }
  ],
  "stream": false
}
```

**Response:**
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1766047478,
  "model": "gpt-4o-mini",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Xin chào!"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 5,
    "completion_tokens": 3,
    "total_tokens": 8
  },
  "_mw_user": "admin",
  "_mw_request_id": "mw_abc123",
  "_mw_added_tokens": 8,
  "_mw_added_cost_usd": 0.000012
}
```

**Special Handling:**
- **GPT-5 models:** Auto-convert `max_tokens` → `max_completion_tokens`
- **Streaming:** Usage tracking qua log reconciliation

---

### POST /v1/images/generations

Generate images với quota tracking.

**Request:**
```json
POST http://localhost:5000/v1/images/generations
Authorization: Bearer YOUR_SUBKEY_ADMIN
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
    "subkey": "YOUR_SUBKEY_ADMIN",
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
  -Headers @{"Authorization"="Bearer YOUR_SUBKEY_ADMIN"}

# Check OpenWebUI Settings → Connections
# Base URL: http://127.0.0.1:5000/v1
# API Key: YOUR_SUBKEY_ADMIN
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
  -Headers @{"Authorization"="Bearer YOUR_ADMIN_KEY"; "Content-Type"="application/json"} `
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
