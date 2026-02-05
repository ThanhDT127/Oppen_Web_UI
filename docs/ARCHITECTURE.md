# 🏗️ ARCHITECTURE - OPPEN WEB UI

## 📐 System Overview

The Oppen Web UI system consists of three main services working together to provide a secure, multi-model AI chat interface with usage tracking and quota management.

```
┌─────────────────────────────────────────────────────────────┐
│                         USER BROWSER                         │
│                     http://localhost:3000                    │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                       OPENWEBUI (Port 3000)                  │
│  - Web Chat Interface                                        │
│  - User Authentication & Profiles                            │
│  - Conversation History                                      │
└────────────────────────────┬────────────────────────────────┘
                             │ OpenAI API Format
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                   LLM MIDDLEWARE (Port 5000)                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ API Layer (api/)                                       │  │
│  │  - chat.py: Chat completion & streaming               │  │
│  │  - admin.py: Admin operations & monitoring            │  │
│  │  - models.py: Model list management                   │  │
│  │  - dashboard_login.py: Auth endpoints                 │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ Core Logic (core/)                                     │  │
│  │  - subkey_manager.py: User quota tracking             │  │
│  │  - auth_guard.py: Token validation                    │  │
│  │  - jwt_auth.py: JWT session management                │  │
│  │  - subkey_store.py: Persistent storage                │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ Utilities (utils/)                                     │  │
│  │  - audio_handler.py: Audio transcription              │  │
│  │  - image_processor.py: Vision API handling            │  │
│  │  - audit_logger.py: Audit trail (logs/audit.jsonl)    │  │
│  │  - stream_processor.py: SSE stream handling           │  │
│  └───────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │ LiteLLM Proxy Format
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                    LITELLM PROXY (Port 4000)                 │
│  - Multi-provider routing (OpenAI, Gemini, Anthropic)       │
│  - Load balancing & fallback                                │
│  - Rate limiting & cost tracking                            │
│  - Model aliasing & transformation                          │
└────────────────────────────┬────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ↓              ↓              ↓
         [OpenAI API]   [Gemini API]  [Other Providers]
```

---

## 🔐 Security Architecture

### Authentication Flow

```
1. User Login
   ├─→ POST /dashboard/login {username, password}
   ├─→ Middleware validates ADMIN_KEY
   └─→ Returns JWT token (4-hour expiry) in HTTP-only cookie

2. Authenticated Requests
   ├─→ Browser sends JWT cookie automatically
   ├─→ auth_guard.py validates token signature & expiry
   └─→ Request proceeds or returns 403 Forbidden

3. API Key Management
   ├─→ Subkeys: User-specific tokens with quotas
   ├─→ Admin Key: Full access to admin endpoints
   └─→ LiteLLM Key: Backend proxy authentication
```

### Secret Management

| Secret | Purpose | Location | Loaded By |
|--------|---------|----------|-----------|
| `JWT_SECRET` | Signs JWT tokens for dashboard sessions | `.env` | `config.py` |
| `MW_SECRET` | Internal middleware encryption | `.env` | `config.py` |
| `ADMIN_KEY` | Admin endpoint authentication | `.env` | `config.py` |
| `LITELLM_KEY` | LiteLLM proxy authentication | `.env` | `config.py` |
| Provider API Keys | OpenAI, Gemini, etc. | `.env` | LiteLLM config |

**Security Best Practices:**
- All secrets stored in `.env` (never committed to git)
- `.env.example` provides templates without real values
- `config.py` warns if default values detected
- JWT tokens expire after 4 hours
- Audit logs track all admin operations

---

## 📊 Data Flow

### Chat Completion Request

```
User sends message in OpenWebUI
    ↓
POST /v1/chat/completions
    ├─ Headers: Authorization: Bearer <subkey>
    ├─ Body: {model, messages, stream: true/false}
    ↓
Middleware (chat.py)
    ├─ Extracts subkey from Authorization header
    ├─ Validates user & quota (core/auth.py + core/quota.py)
    ├─ Checks period-based limits (tokens/cost)
    ├─ Records pending request to data/pending.csv
    ├─ Proxies to LiteLLM → POST http://localhost:4000/v1/chat/completions
    ├─ Receives response (stream or non-stream)
    ├─ Calculates cost (core/cost.py)
    ├─ Updates user quota in data/users.json
    └─ Returns to OpenWebUI
    ↓
LiteLLM Proxy
    ├─ Routes to appropriate provider (OpenAI, Gemini, etc.)
    ├─ Handles retries & fallbacks
    └─ Returns formatted response
```

### Admin Dashboard Request

```
User accesses http://localhost:5000/dashboard
    ↓
GET /dashboard
    ├─ main.py serves dashboard/index.html
    └─ Returns HTML page
    ↓
JavaScript loads
    ↓
GET /v1/_mw/summary
    ├─ Includes JWT cookie
    ├─ utils/auth_guard.py validates JWT
    ├─ api/summary.py aggregates metrics from logs/audit.jsonl
    └─ Returns JSON: {llm_calls_total, admin_ops_total, pending_count, breakdown}
    ↓
Dashboard displays metrics
```

---

## 💾 Persistence Layer

### User Database (`llm-mw/data/users.json`)

```json
[
  {
    "user_id": "admin",
    "subkey": "sk_admin_hashed_...",
    "active": true,
    "allowed_models": ["*"],
    "used_tokens": 45000,
    "used_cost_usd": 0.125,
    "quota": {
      "period": "monthly",
      "timezone": "Asia/Bangkok",
      "limit_tokens": 0,
      "limit_cost_usd": 0,
      "period_start": 1735027200000,
      "used_tokens": 12000,
      "used_cost_usd": 0.035
    }
  }
]
```

**Features:**
- Subkeys stored as HMAC-SHA256 hashes
- Period-based quota (weekly/monthly) with auto-reset
- Lifetime tracking (used_tokens, used_cost_usd)
- Per-period tracking (quota.used_tokens, quota.used_cost_usd)

**Operations:**
- Read: `core/auth.py` → load_users()
- Write: `core/auth.py` → save_users() with thread lock
- Quota enforcement: `core/quota.py` → maybe_reset_quota()

### Audit Log (`logs/audit.jsonl`)

```jsonl
{"timestamp":"2025-12-22T10:35:22Z","event":"subkey_create","subkey":"sk_user_abc123","admin_key":"admin_***456"}
{"timestamp":"2025-12-22T10:40:15Z","event":"chat_completion","subkey":"sk_user_abc123","model":"gpt-4","tokens":1234}
```

**Features:**
- JSONL format (one JSON object per line)
- Append-only for tamper-resistance
- Indexed by timestamp for fast queries
- Rotated at 10MB with 5 backup files

---

## 🔄 Request Lifecycle

### Streaming Chat (95% of traffic)

```
1. Request Validation (10ms)
   ├─ Extract Authorization header
   ├─ Hash subkey and lookup user in data/users.json
   ├─ Check user.active status
   └─ Enforce period-based quota limits

2. Record Pending (5ms)
   ├─ Write to data/pending.csv (request_id, timestamp, model)
   └─ Used for reconciling streaming requests

3. Proxy to LiteLLM (50-200ms first token)
   ├─ Forward request to http://localhost:4000/v1/chat/completions
   ├─ Set stream=true in request body
   └─ Receive Server-Sent Events (SSE) stream

3. Stream Processing (duration varies)
   ├─ Read SSE chunks line by line
   ├─ Parse data: {delta: {content: "..."}}
   ├─ Forward to client immediately
   └─ Track [DONE] signal

4. Quota Update (5ms)
   ├─ Decrement pending_count
   ├─ Increment llm_calls
   └─ Trigger autosave
```

### Non-Streaming Chat

```
1. Validation (10ms)
2. Proxy Request (2-10 seconds)
   ├─ Wait for complete response
   └─ Parse JSON body
3. Quota Update (5ms)
4. Return full response
```

---

## 🧩 Module Responsibilities

### API Layer (`api/`)

| Module | Endpoints | Purpose |
|--------|-----------|---------|
| `chat.py` | `/v1/chat/completions` | Main chat proxy with quota enforcement |
| `admin.py` | `/admin/usage`, `/admin/reset`, `/admin/reconcile` | Usage stats & quota management |
| `models.py` | `/v1/models` | Model list aggregation from LiteLLM |
| `dashboard_login.py` | `/dashboard/login`, `/dashboard/logout` | JWT authentication |
| `summary.py` | `/v1/_mw/summary` | Dashboard metrics from audit.jsonl |
| `stream.py` | `/v1/_mw/stream` | Real-time SSE audit events |
| `health.py` | `/health` | System health check |
| `images.py` | `/v1/images/generations` | Image generation proxy |
| `audio.py` | `/v1/audio/transcriptions` | Audio transcription proxy |
| `media.py` | `/media/*` | Static file serving |

### Core Logic (`core/`)

| Module | Purpose |
|--------|---------|
| `auth.py` | User authentication, subkey hashing, users.json management |
| `quota.py` | Period-based quota tracking (weekly/monthly), auto-reset |
| `cost.py` | Token cost calculation, pricing data (prices.json) |
| `audit_state.py` | Request state management for audit logging |

### Utilities (`utils/`)

| Module | Purpose |
|--------|---------|
| `auth_guard.py` | JWT validation decorator for protected endpoints |
| `jwt_auth.py` | JWT token generation & cookie management |
| `logging.py` | Structured logging (detail_log, audit_log) |
| `helpers.py` | Utility functions (rate limiting, request parsing) |
| `media.py` | Media file handling (upload, storage) |

### Services (`services/`)

| Module | Purpose |
|--------|---------|
| `litellm.py` | LiteLLM proxy client (HTTP communication) |

---

## 🔌 Service Dependencies

```
┌────────────┐
│  OpenWebUI │  Depends on: Middleware running on port 5000
└──────┬─────┘              SQLite database in DATA_DIR
       │
       ↓
┌────────────┐
│ Middleware │  Depends on: LiteLLM proxy on port 4000
└──────┬─────┘              .env file with secrets
       │                   logs/ directory writable
       ↓
┌────────────┐
│  LiteLLM   │  Depends on: litellm_config.yaml
└────────────┘              Provider API keys in .env
```

**Startup Order:**
1. Ensure `.env` exists with all secrets
2. Start LiteLLM proxy (port 4000)
3. Start Middleware (port 5000)
4. Start OpenWebUI (port 3000)

**Health Checks:**
- LiteLLM: `GET http://localhost:4000/health` → `{"status":"ok"}`
- Middleware: `GET http://localhost:5000/health` → `{"status":"ok"}`
- OpenWebUI: `GET http://localhost:3000` → HTML response

---

## 🧪 Testing Strategy

### Unit Tests (`tests/`)
- `test_subkey_manager.py`: Quota logic, concurrency
- `test_auth_guard.py`: JWT validation, expiry
- `test_stream_processor.py`: SSE parsing edge cases

### Integration Tests
- `test_fixes.py`: End-to-end chat completion (13 tests)
- `test_dashboard_improvements.py`: Dashboard API & auth (9 tests)

### Load Testing
```bash
# Simulate 100 concurrent users
pytest tests/test_load.py --workers 100
```

---

## 🚀 Deployment Considerations

### Production Checklist

- [ ] Generate secure random values for `JWT_SECRET` and `MW_SECRET`
- [ ] Never use default values in `.env`
- [ ] Set strong `ADMIN_KEY` (min 20 characters)
- [ ] Restrict file permissions on `.env` (owner read-only)
- [ ] Enable HTTPS (use reverse proxy like Nginx)
- [ ] Set up log rotation (10MB per file, 5 backups)
- [ ] Monitor `logs/audit.jsonl` for suspicious activity
- [ ] Configure firewall rules (only expose port 3000 externally)

### Scaling

**Vertical:**
- Increase worker count in `uvicorn` (default: 1)
- Add Redis for distributed subkey storage

**Horizontal:**
- Load balance multiple Middleware instances
- Share `logs/subkeys.json` via NFS or S3

**Monitoring:**
- Prometheus metrics from `/metrics` endpoint (TODO)
- Grafana dashboards for quota usage trends

---

## 📚 Additional Documentation

- [API Reference](API_REFERENCE.md) - Complete endpoint documentation
- [Dashboard Guide](DASHBOARD.md) - Admin UI usage & metrics
- [Quick Start](QUICKSTART.md) - Installation & first run
- [README](../README.md) - Project overview

---

**Last Updated:** December 22, 2025  
**Version:** 2.0 (Refactored with 15-module architecture)
