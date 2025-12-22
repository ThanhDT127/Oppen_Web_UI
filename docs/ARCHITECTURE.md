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
    ├─ Validates quota (subkey_manager.py)
    ├─ Increments pending count
    ├─ Proxies to LiteLLM → POST http://localhost:4000/v1/chat/completions
    ├─ Receives response (stream or non-stream)
    ├─ Decrements pending, increments completed
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
    ├─ auth_guard.py validates JWT
    ├─ admin.py aggregates metrics from subkey_store
    └─ Returns JSON: {llm_calls_total, admin_ops_total, pending_count, breakdown}
    ↓
Dashboard displays metrics
```

---

## 💾 Persistence Layer

### Subkey Storage (`logs/subkeys.json`)

```json
{
  "sk_user_abc123": {
    "enabled": true,
    "quota": 100,
    "llm_calls": 45,
    "admin_ops": 2,
    "pending": 0,
    "created_at": "2025-12-22T10:30:00Z"
  }
}
```

**Operations:**
- Read: `subkey_store.py` loads on startup
- Write: Auto-saves after every quota change (debounced 1 second)
- Atomic: Uses temp file + rename for crash safety

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
   ├─ Lookup subkey in subkey_store
   └─ Check quota availability

2. Proxy to LiteLLM (50-200ms first token)
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
| `admin.py` | `/v1/_mw/subkey/*`, `/v1/_mw/summary` | Subkey CRUD & metrics |
| `models.py` | `/v1/models` | Model list aggregation from LiteLLM |
| `dashboard_login.py` | `/dashboard/login`, `/dashboard/logout` | JWT authentication |

### Core Logic (`core/`)

| Module | Purpose |
|--------|---------|
| `subkey_manager.py` | In-memory quota tracking & validation |
| `subkey_store.py` | Persistent JSON storage with atomic writes |
| `auth_guard.py` | JWT validation decorator for protected endpoints |
| `jwt_auth.py` | JWT token generation & cookie management |

### Utilities (`utils/`)

| Module | Purpose |
|--------|---------|
| `audit_logger.py` | JSONL audit trail writer |
| `stream_processor.py` | SSE parsing & forwarding |
| `audio_handler.py` | Whisper transcription via LiteLLM |
| `image_processor.py` | Vision API requests (GPT-4V, Gemini Pro Vision) |

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
