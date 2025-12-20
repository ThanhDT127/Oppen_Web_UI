# Tài liệu Giải Thích Dự Án - Oppen_Web_UI (Baseline)

> **Phiên bản:** 3.0 Baseline  
> **Ngày cập nhật:** December 18, 2025  
> **Trạng thái:** Production-Ready (cần security hardening)

Tài liệu này mô tả **bài toán tổng thể**, **kiến trúc hệ thống**, và giải thích **vai trò từng thành phần** trong dự án OpenWebUI + Middleware + LiteLLM.

---

## 📖 MỤC LỤC

1. [Bài Toán Tổng Thể](#1-bài-toán-tổng-thể)
2. [Kiến Trúc & Luồng Request](#2-kiến-trúc--luồng-request)
3. [Tổng Quan Cấu Trúc Repo](#3-tổng-quan-cấu-trúc-repo)
4. [Giải Thích Từng File/Thư Mục](#4-giải-thích-từng-filethư-mục)
5. [Chi Tiết Endpoints](#5-chi-tiết-endpoints)
6. [Quota & Cost Tracking](#6-quota--cost-tracking)
7. [Logging & Monitoring](#7-logging--monitoring)
8. [Những Thay Đổi So Với Version Trước](#8-những-thay-đổi-so-với-version-trước)

---

## 1) Bài Toán Tổng Thể

Dự án này xây dựng một **hệ thống chat LLM 3 tầng** với các mục tiêu sau:

### 1.1 Mục Tiêu Chính

1. **Cung cấp UI chat** thân thiện cho người dùng (OpenWebUI)
2. **Xác thực & phân quyền** người dùng theo "subkey" 
3. **Quản lý quota** (tokens/cost) và giới hạn theo user/period
4. **Proxy thống nhất** đến nhiều LLM providers (OpenAI/Gemini)
5. **Tracking chi tiết** usage & cost cho mỗi request

### 1.2 Điểm Quan Trọng

- **User không cần biết** API keys của providers (OpenAI/Gemini)
- **User chỉ dùng subkey** được cấp từ middleware
- **Middleware là điểm kiểm soát**: auth + quota + logging
- **LiteLLM đảm nhiệm chuyển đổi API**: OpenAI-compatible interface

### 1.3 Phiên Bản Baseline

Phiên bản hiện tại tập trung vào:

✅ **Chat Completions** (streaming & non-streaming)  
✅ **Image Generation** với quota tracking  
✅ **Quota Management** (tokens + cost)  
✅ **Multi-User Authentication**  
✅ **Usage Logging & Monitoring**  

🚧 **Planned (Future):**
- Video Generation qua OpenWebUI Tool/Pipe
- Audio TTS/STT qua OpenWebUI Tool/Pipe

---

## 2) Kiến Trúc & Luồng Request

### 2.1 Kiến Trúc 3 Tầng

```
┌──────────────────────────────────────────────────────────┐
│                     USER BROWSER                         │
│                  http://localhost:3000                   │
└────────────────────────┬─────────────────────────────────┘
                         │
                         │ HTTP/HTTPS
                         ▼
┌──────────────────────────────────────────────────────────┐
│                   OpenWebUI (Port 3000)                  │
│  - Web-based chat interface                              │
│  - User authentication & session management              │
│  - Chat history storage (SQLite)                         │
│  - Model selection UI                                    │
└────────────────────────┬─────────────────────────────────┘
                         │
                         │ POST /v1/chat/completions
                         │ Authorization: Bearer <SUBKEY>
                         ▼
┌──────────────────────────────────────────────────────────┐
│              Middleware (FastAPI, Port 5000)             │
│  ┌────────────────────────────────────────────────────┐  │
│  │ 1. Authentication (_require_user)                  │  │
│  │    - Validate subkey from users.json               │  │
│  │    - Check user active status                      │  │
│  ├────────────────────────────────────────────────────┤  │
│  │ 2. Authorization (_assert_model_allowed)           │  │
│  │    - Check allowed_models list                     │  │
│  │    - Filter restricted models                      │  │
│  ├────────────────────────────────────────────────────┤  │
│  │ 3. Quota Check (_enforce_and_bump_task_quota)      │  │
│  │    - Check token limit                             │  │
│  │    - Check cost limit                              │  │
│  │    - Check image request limit                     │  │
│  ├────────────────────────────────────────────────────┤  │
│  │ 4. Request Forwarding                              │  │
│  │    - Add mw_request_id                             │  │
│  │    - Add user_id to metadata                       │  │
│  │    - Forward to LiteLLM                            │  │
│  ├────────────────────────────────────────────────────┤  │
│  │ 5. Usage Tracking                                  │  │
│  │    - Extract usage from response                   │  │
│  │    - Calculate cost (LiteLLM header or fallback)   │  │
│  │    - Update users.json                             │  │
│  │    - Log to middleware.log                         │  │
│  └────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────┘
                         │
                         │ POST /chat/completions
                         │ Authorization: Bearer <LITELLM_KEY>
                         │ X-Request-ID: mw_<uuid>
                         ▼
┌──────────────────────────────────────────────────────────┐
│                LiteLLM Proxy (Port 4000)                 │
│  ┌────────────────────────────────────────────────────┐  │
│  │ 1. Request Routing                                 │  │
│  │    - Parse model name (gpt-4o-mini, gemini-*)      │  │
│  │    - Select appropriate provider                   │  │
│  ├────────────────────────────────────────────────────┤  │
│  │ 2. API Translation                                 │  │
│  │    - Convert OpenAI format → Provider format       │  │
│  │    - Handle provider-specific params               │  │
│  ├────────────────────────────────────────────────────┤  │
│  │ 3. Provider Call                                   │  │
│  │    - Add provider API key                          │  │
│  │    - Send HTTP request                             │  │
│  │    - Handle streaming if needed                    │  │
│  ├────────────────────────────────────────────────────┤  │
│  │ 4. Response Normalization                          │  │
│  │    - Convert Provider response → OpenAI format     │  │
│  │    - Add usage information                         │  │
│  │    - Add cost header (x-litellm-response-cost)     │  │
│  │    - Log to litellm.log                            │  │
│  └────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────┘
                         │
            ┌────────────┴────────────┐
            │                         │
            ▼                         ▼
    ┌──────────────┐          ┌──────────────┐
    │   OpenAI     │          │   Gemini     │
    │   ChatGPT    │          │   Google     │
    │              │          │              │
    │ gpt-4o       │          │ gemini-2.0   │
    │ gpt-4o-mini  │          │ gemini-2.5   │
    │ gpt-5        │          │              │
    └──────────────┘          └──────────────┘
```

### 2.2 Phân Tách "Các Loại Key"

| Key Type | Scope | Stored Where | Used By |
|----------|-------|--------------|---------|
| `SUBKEY` | End-user | `llm-mw/users.json` | OpenWebUI → Middleware |
| `LITELLM_KEY` | Master | `.env` (LITELLM_KEY) | Middleware → LiteLLM |
| `OPENAI_API_KEY` | Provider | `.env` | LiteLLM → OpenAI |
| `GEMINI_API_KEY` | Provider | `.env` | LiteLLM → Gemini |
| `ADMIN_KEY` | Admin | `.env` (ADMIN_KEY) | Admin tools → Middleware |

**Security Note:** End-users không bao giờ thấy provider keys hay LITELLM_KEY.

---

## 3) Tổng Quan Cấu Trúc Repo

```
D:\Works\Oppen_Web_UI_fresh/
├── .env                          # Environment variables (GIT IGNORED)
├── .gitignore                    # Git ignore rules
├── README.md                     # User-facing documentation
├── PROJECT_EXPLAINED_VI.md       # This file (technical deep-dive)
├── requirements.txt              # Python dependencies
│
├── litellm/                      # LiteLLM configuration
│   ├── litellm_config.yaml       # Model definitions & settings
│   └── litellm.log               # LiteLLM runtime logs (auto-generated)
│
├── llm-mw/                       # Middleware (FastAPI)
│   ├── main.py                   # Main application (1158 lines)
│   ├── users.json                # User database (GIT IGNORED)
│   ├── users.example.json        # User schema example
│   ├── prices.json               # Fallback pricing data
│   ├── pending.csv               # Streaming request tracker (runtime)
│   └── .env.example              # Environment variables template
│
├── logs/                         # Runtime logs (auto-generated)
│   ├── middleware.log            # Request tracking logs
│   ├── middleware.requests.log   # Detailed request/response logs
│   └── mw_media/                 # Generated image files
│
├── openwebui_data/               # OpenWebUI storage (runtime)
│   ├── webui.db                  # SQLite database
│   └── ...                       # Other OpenWebUI data
│
└── scripts/                      # Utility scripts
    ├── start_stack.ps1           # Start all 3 services
    ├── stop_stack.ps1            # Stop all services
    └── run_litellm_with_env.ps1  # Start LiteLLM with env vars
```

---

## 4) Giải Thích Từng File/Thư Mục

### 4.1 Root Files

#### `.env`
**Vai trò:** Chứa tất cả environment variables và secrets  
**Status:** ✅ Created, ❌ Git Ignored  
**Format:**
```bash
LITELLM_BASE=http://127.0.0.1:4000/v1
LITELLM_KEY=super_admin_key_123
ADMIN_KEY=admin_master_key_456
DATA_DIR=D:\Works\Oppen_Web_UI_fresh\openwebui_data

OPENAI_API_KEY=sk-proj-...
GEMINI_API_KEY=AIzaSy...
```

**Security:** File này **KHÔNG BAO GIỜ** được commit vào git.

---

#### `README.md`
**Vai trò:** User-facing documentation  
**Audience:** End-users, DevOps  
**Content:**
- Hướng dẫn setup & deployment
- API endpoint reference
- Troubleshooting guides
- Security notes

---

#### `PROJECT_EXPLAINED_VI.md`
**Vai trò:** Technical deep-dive (file này)  
**Audience:** Developers, maintainers  
**Content:**
- Kiến trúc hệ thống chi tiết
- Code flow explanations
- Design decisions
- Implementation notes

---

#### `requirements.txt`
**Vai trò:** Python dependencies  
**Content:**
```
litellm[proxy]
open-webui
fastapi
uvicorn
httpx
python-dotenv
```

**Usage:**
```powershell
pip install -r requirements.txt
```

---

### 4.2 `litellm/` Directory

#### `litellm_config.yaml`
**Vai trò:** LiteLLM proxy configuration  
**Chức năng:**
1. **Define models:** Map friendly names → provider-specific models
2. **Set API keys:** Reference environment variables
3. **Configure proxy:** Port, host, master key, logging

**Example:**
```yaml
model_list:
  - model_name: gpt-4o-mini              # Friendly name
    litellm_params:
      model: openai/gpt-4o-mini          # Provider-specific
      api_key: os.environ/OPENAI_API_KEY # From env var

litellm_settings:
  drop_params: false    # Keep all params
  host: "0.0.0.0"
  port: 4000

general_settings:
  master_key: os.environ/LITELLM_KEY  # Middleware uses this
```

**Key Points:**
- `model_name`: Name exposed to middleware/UI
- `litellm_params.model`: Format is `provider/model-name`
- `api_key: os.environ/VAR_NAME`: Load from environment

---

#### `litellm.log`
**Vai trò:** LiteLLM runtime logs  
**Content:**
- Request/response details
- Token usage per request
- Cost calculations
- Provider-specific errors

**Usage:** Used by middleware for streaming cost reconciliation.

---

### 4.3 `llm-mw/` Directory

#### `main.py` (1158 lines)
**Vai trò:** Core middleware logic  
**Framework:** FastAPI  
**Port:** 5000

**Main Components:**

##### A) Configuration & Setup (Lines 1-100)
```python
# Environment loading
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv()  # Load .env from project root or llm-mw/

# Paths
USERS_FILE = os.path.join(BASE_DIR, "users.json")
PRICES_FILE = os.path.join(BASE_DIR, "prices.json")
PENDING_CSV = os.path.join(BASE_DIR, "pending.csv")

# Logging setup
LOG_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "logs"))
MW_LOG_FILE = os.path.join(LOG_DIR, "middleware.log")
MW_DETAIL_LOG_FILE = os.path.join(LOG_DIR, "middleware.requests.log")

# LiteLLM connection
LITELLM_BASE = os.getenv("LITELLM_BASE", "http://127.0.0.1:4000/v1")
LITELLM_KEY = os.getenv("LITELLM_KEY", "")
ADMIN_KEY = os.getenv("ADMIN_KEY", "")
```

##### B) Helper Functions (Lines 100-600)

**Redaction & Logging:**
```python
def _redact(obj: Any) -> Any:
    """Redact sensitive data from logs"""
    # Remove API keys, tokens, large base64 strings
    
def _detail(event: str, **fields):
    """Log detailed request/response to middleware.requests.log"""
    # JSON format with timestamps, request IDs, user IDs
```

**Authentication:**
```python
def _require_user(request: Request) -> Dict[str, Any]:
    """Validate subkey and return user object"""
    # 1. Extract Bearer token from Authorization header
    # 2. Look up subkey in users.json
    # 3. Check active status
    # 4. Return user dict or raise HTTPException(403)
```

**Authorization:**
```python
def _assert_model_allowed(user: Dict, model: str):
    """Check if user can access model"""
    # Compare model against user's allowed_models list
    # allowed_models = ["*"] means all models
```

**Quota Management:**
```python
def _enforce_and_bump_task_quota(
    user_id: str,
    add_tokens: int = 0,
    add_cost_usd: float = 0.0,
    add_image_requests: int = 0,
    apply: bool = True
):
    """Enforce quota limits and update usage"""
    # 1. Load users.json
    # 2. Check if quota exceeded (tokens/cost/image_requests)
    # 3. If apply=True, bump counters
    # 4. Save users.json
    # 5. Thread-safe with _lock
```

**Cost Calculation:**
```python
def _calc_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate cost from usage"""
    # Look up prices in PRICES dict
    # Support both per-1K and per-1M pricing
    
def _calc_image_cost_usd(model: str, body: Dict) -> float:
    """Calculate image generation cost"""
    # Based on model, size, quality, n
```

##### C) Core Endpoints (Lines 600-1100)

**Health Check:**
```python
@app.get("/health")
def health():
    return {"ok": True, "time": int(time.time())}
```

**List Models (WITH AUTH):**
```python
@app.get("/v1/models")
async def models(request: Request):
    user = _require_user(request)  # ← NEW: Requires auth
    # Forward to LiteLLM
    # Filter restricted models
    # Return model list
```

**Chat Completions:**
```python
@app.post("/v1/chat/completions")
async def chat_proxy(request: Request):
    user = _require_user(request)
    body = await request.json()
    model = body.get("model")
    
    # Special handling for GPT-5
    if model.startswith("gpt-5"):
        if "max_tokens" in body:
            body["max_completion_tokens"] = body.pop("max_tokens")
    
    # ❌ REMOVED: max_tokens clamping (was 10000)
    # ❌ REMOVED: Image shim logic
    
    is_stream = bool(body.get("stream"))
    
    if is_stream:
        # Streaming mode
        # 1. Open upstream connection
        # 2. Stream bytes to client
        # 3. Track in pending.csv
        # 4. Remove from pending on completion
        # 5. Usage reconciled later via /admin/reconcile
    else:
        # Non-streaming mode
        # 1. Send request to LiteLLM
        # 2. Get full response with usage
        # 3. Calculate cost (LiteLLM header or fallback)
        # 4. Bump quota immediately
        # 5. Return response
```

**Image Generation:**
```python
@app.post("/v1/images/generations")
async def images_generations(request: Request):
    user = _require_user(request)
    # 1. Validate prompt
    # 2. Check image quota (before calling)
    # 3. Forward to LiteLLM
    # 4. Fallback OpenAI → Gemini if org verification error
    # 5. Materialize base64 images to HTTP URLs
    # 6. Bump image_requests & cost quota
    # 7. Return response with URLs
```

##### D) Admin Endpoints (Lines 1100-end)

**View Usage:**
```python
@app.get("/admin/usage")
def admin_usage(request: Request):
    # Validate ADMIN_KEY
    # Return users.json (full dump)
```

**Reset Quota:**
```python
@app.post("/admin/reset")
async def admin_reset(request: Request):
    # Validate ADMIN_KEY
    # Reset quota for specified user (or all)
    # Respects quota period (don't reset if still in period)
```

**Reconcile Streaming:**
```python
@app.post("/admin/reconcile")
async def admin_reconcile(request: Request):
    # Validate ADMIN_KEY
    # Look up request_id in litellm.log
    # Extract usage info
    # Bump user quota retroactively
    # Remove from pending.csv
```

---

#### `users.json`
**Vai trò:** User database (flat-file)  
**Status:** ✅ Git Ignored

**Schema:**
```json
[
  {
    "user_id": "admin",
    "subkey": "subkey_admin_123",
    "active": true,
    "allowed_models": ["*"],
    "used_tokens": 1234,
    "used_cost_usd": 0.56,
    "quota": {
      "period": "monthly",
      "timezone": "Asia/Bangkok",
      "limit_tokens": 0,
      "limit_cost_usd": 0,
      "period_start": 1764522000000,
      "used_tokens": 1234,
      "used_cost_usd": 0.56,
      "used_image_requests": 5
    }
  }
]
```

**Important Fields:**
- `subkey`: Secret token for API authentication
- `active`: Boolean, disable user without deleting
- `allowed_models`: `["*"]` or list of model names
- `quota.period`: `"weekly"` or `"monthly"`
- `quota.limit_tokens`: 0 = unlimited
- `quota.period_start`: Unix timestamp (ms) of period start

**Thread Safety:** All updates protected by `_lock` in code.

---

#### `prices.json`
**Vai trò:** Fallback pricing data  
**Khi nào dùng:** LiteLLM không trả `x-litellm-response-cost` header

**Format:**
```json
{
  "gpt-4o-mini": {
    "input_per_1m": 0.15,
    "output_per_1m": 0.15
  },
  "gpt-image-1": {
    "per_image_usd": {
      "medium": {
        "1024x1024": 0.042,
        "1024x1792": 0.063
      }
    }
  }
}
```

**Notes:**
- Prices per 1M tokens (not 1K)
- Image pricing by quality + size
- Updated manually (check provider websites)

---

#### `pending.csv`
**Vai trò:** Track streaming requests  
**Format:** `request_id,user_id,timestamp`  
**Lifecycle:**
1. Created when streaming request starts
2. Row added to CSV
3. Row removed when stream completes
4. Used by `/admin/reconcile` to find incomplete streams

---

### 4.4 `logs/` Directory

#### `middleware.log`
**Content:** High-level request tracking
```
2025-12-18 15:44:38 INFO req rid=mw_abc123 method=POST path=/v1/chat/completions status=200 ms=2049.3
2025-12-18 15:45:08 INFO stream_start rid=mw_xyz789 model=gpt-4o-mini
2025-12-18 15:45:09 INFO stream_end rid=mw_xyz789
```

---

#### `middleware.requests.log`
**Content:** Full JSON request/response logs
```json
{"ts":"2025-12-18T15:44:38+07:00","event":"chat.request","rid":"mw_abc123","user":"admin","model":"gpt-4o-mini","body":{...}}
{"ts":"2025-12-18T15:44:40+07:00","event":"chat.response","rid":"mw_abc123","status":200,"usage":{"total_tokens":20}}
```

**Usage:** Debugging, audit trails, analytics

---

#### `mw_media/`
**Content:** Generated image files  
**Format:** `<uuid>.png`, `<uuid>.jpg`, etc.  
**Access:** Via `/v1/_mw/media/<filename>` endpoint

---

### 4.5 `openwebui_data/`

**Vai trò:** OpenWebUI persistent storage  
**Content:**
- `webui.db`: SQLite database (users, chats, settings)
- `vector_db/`: Vector embeddings (if RAG enabled)
- Other OpenWebUI-specific data

**Management:** Handled entirely by OpenWebUI, not middleware.

---

## 5) Chi Tiết Endpoints

### 5.1 Authentication Flow

**All endpoints except `/health` require authentication:**

```python
@app.get("/v1/models")
async def models(request: Request):
    user = _require_user(request)  # ← This line validates subkey
    # ... rest of logic
```

**_require_user() steps:**
1. Extract `Authorization: Bearer <subkey>` header
2. Look up subkey in `users.json`
3. Check `active` field
4. Return user dict or raise `HTTPException(401/403)`

---

### 5.2 Chat Completions - Streaming vs Non-Streaming

#### Non-Streaming
**Flow:**
1. Middleware receives request
2. Forward to LiteLLM (wait for full response)
3. LiteLLM returns complete response with `usage` object
4. Middleware extracts tokens/cost
5. Bump quota immediately
6. Return response to client

**Pros:** Simple, accurate quota tracking  
**Cons:** Slow for long responses

---

#### Streaming
**Flow:**
1. Middleware receives request with `stream=true`
2. Add request to `pending.csv`
3. Open streaming connection to LiteLLM
4. Stream bytes directly to client (no buffering)
5. Remove from `pending.csv` on completion
6. Usage unknown until later

**Quota Tracking:**
- **During stream:** Cannot track (no usage info)
- **After stream:** Must reconcile via `/admin/reconcile`
- **Pending CSV:** Tracks incomplete requests

**Pros:** Fast, real-time  
**Cons:** Complex quota tracking

---

### 5.3 Image Generation - Special Cases

#### OpenAI Organization Verification
**Problem:** Many OpenAI accounts lack image generation access  
**Solution:** Automatic fallback to Gemini

```python
if resp.status_code >= 400 and model == "gpt-image-1":
    if _looks_like_org_verification_error(resp.text):
        model = "gemini-2.5-flash-image"
        # Retry with Gemini
```

#### Base64 → HTTP URL Conversion
**Problem:** OpenWebUI may not render base64 images well  
**Solution:** Convert to materialized URLs

```python
def _maybe_materialize_image_items(request, items):
    # Extract base64 from b64_json
    # Save to logs/mw_media/<uuid>.png
    # Replace with http://localhost:5000/v1/_mw/media/<uuid>.png
```

---

## 6) Quota & Cost Tracking

### 6.1 Quota Types

| Quota Type | Scope | Enforcement |
|------------|-------|-------------|
| `limit_tokens` | Chat | Per-request check |
| `limit_cost_usd` | All | Per-request check |
| `limit_image_requests` | Image | Pre-call check |

**Important:** Video/Audio quotas removed in baseline version.

---

### 6.2 Lifetime vs Period Tracking (Fixed Dec 19, 2025)

**Two-level tracking:**

1. **Lifetime Counters** (`user` level):
   - `user["used_tokens"]`: Total tokens since account creation
   - `user["used_cost_usd"]`: Total cost since account creation
   - `user["used_image_requests"]`: Total image requests since creation
   - **NEVER reset** - preserved for lifetime analytics

2. **Period Counters** (`quota` level):
   - `quota["used_tokens"]`: Tokens in current period (monthly/weekly)
   - `quota["used_cost_usd"]`: Cost in current period
   - `quota["used_image_requests"]`: Image requests in current period
   - **Reset at period boundary** (e.g., first day of month)

**Implementation:**
```python
def _enforce_and_bump_task_quota(user_id, add_tokens, add_cost, ...):
    # Both counters incremented on every request:
    stored_user["used_tokens"] += add_tokens        # Lifetime
    quota["used_tokens"] += add_tokens              # Period
    
    stored_user["used_cost_usd"] += add_cost        # Lifetime
    quota["used_cost_usd"] += add_cost              # Period

def _maybe_reset_quota(user: Dict):
    # ONLY reset period counters, NOT lifetime
    quota = user["quota"]
    current_anchor = _period_anchor_ms(quota["period"], quota["timezone"])
    
    if quota["period_start"] < current_anchor:
        # New period: reset ONLY quota level
        quota["used_tokens"] = 0
        quota["used_cost_usd"] = 0.0
        quota["used_image_requests"] = 0
        quota["period_start"] = current_anchor
        
        # ✅ Fixed: Do NOT reset user["used_*"] (lifetime data)
```

---

### 6.3 Period-Based Reset

**Anchor Calculation:**
- `monthly`: First day of month at 00:00 in user's timezone
- `weekly`: Monday at 00:00 in user's timezone

**Example (Monthly):**
```
User quota: {
  "period": "monthly",
  "timezone": "Asia/Bangkok",
  "limit_tokens": 1000000,
  "limit_cost_usd": 10.0,
  "period_start": 1735660800000,  // 2025-01-01 00:00 Bangkok
  "used_tokens": 50000,            // This month
  "used_cost_usd": 0.5
}

User lifetime: {
  "used_tokens": 5000000,          // All time (never reset)
  "used_cost_usd": 50.0
}
```

---

### 6.4 Cost Sources (Priority Order)

1. **LiteLLM header:** `x-litellm-response-cost` (most accurate)
2. **Fallback calculation:** `_calc_cost_usd()` using `prices.json`

---

## 7) Logging & Monitoring

### 7.1 Logging Architecture (Updated Dec 19, 2025)

```
Request → Middleware
    ├─→ middleware.log (high-level INFO/WARNING/ERROR)
    ├─→ middleware.requests.log (detailed JSON per-request)
    └─→ audit.jsonl (NEW: structured audit log for analytics)

Request → LiteLLM → Provider
    └─→ litellm.log (provider calls with costs)
```

---

### 7.2 Log Files Overview

#### **middleware.log**
- **Format:** Plain text
- **Rotation:** 5MB, 5 backups
- **Content:**
  - `INFO`: Normal operations (req/stream_start/stream_end)
  - `WARNING`: Recoverable errors (quota exceeded, model forbidden)
  - `ERROR`: Unrecoverable errors (provider failures)
- **Example:**
  ```
  2025-12-19 10:15:23,456 INFO req rid=mw_abc123 method=POST path=/v1/chat/completions status=200 ms=1234.5
  ```

#### **middleware.requests.log**
- **Format:** JSON (one object per line)
- **Rotation:** 20MB, 5 backups
- **Content:** Full request/response details with redacted sensitive data
- **Use Case:** Debugging, detailed investigation

#### **audit.jsonl** ✨ NEW
- **Format:** JSONL (JSON Lines - one JSON object per line)
- **Rotation:** 50MB, 5 backups
- **Content:** Structured audit entries per request
- **Fields:**
  ```json
  {
    "timestamp": "2025-12-19T10:15:23.456+07:00",
    "request_id": "mw_abc123",
    "user_id": "admin",
    "endpoint": "/v1/chat/completions",
    "model": "gpt-4o-mini",
    "tokens_in": 150,
    "tokens_out": 300,
    "cost_usd": 0.00045,
    "image_requests": 0,
    "stt_requests": 0,
    "tts_chars": 0,
    "duration_ms": 1234,
    "status": "success"
  }
  ```
- **Use Case:** Aggregation, analytics, billing reconciliation

---

### 7.3 Request ID Tracking

**Format:** `mw_<uuid>`  
**Propagation:**
- Middleware generates `mw_request_id` for each request
- Adds to request metadata
- Forwards as `X-Request-ID` header to LiteLLM
- LiteLLM logs with this ID
- Reconciliation uses this ID to match logs across systems
- **NEW:** Audit log includes request_id for correlation

---

### 7.4 Monitoring Endpoints

#### **GET /health** (Enhanced)
- **No authentication required**
- **Returns:**
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
- **Status Codes:**
  - `200`: System healthy
  - `503`: Degraded (LiteLLM down, disk space < 1GB)
- **Checks:**
  - LiteLLM connectivity (`GET /health` to LiteLLM)
  - Disk space in logs directory
  - Uptime since startup
  - Active user count

#### **GET /v1/_mw/summary?minutes=60** ✨ NEW
- **Authentication:** Requires `Authorization: Bearer <ADMIN_KEY>`
- **Query Parameters:**
  - `minutes`: Time window in minutes (default 60)
- **Returns:** Aggregated usage statistics from `audit.jsonl`
  ```json
  {
    "time_window_minutes": 60,
    "cutoff_time": "2025-12-19T09:15:23.456+07:00",
    "total_entries": 5,
    "data": [
      {
        "user_id": "admin",
        "model": "gpt-4o-mini",
        "total_requests": 10,
        "success_requests": 9,
        "error_requests": 1,
        "tokens_in": 1500,
        "tokens_out": 3000,
        "cost_usd": 0.0045,
        "image_requests": 0,
        "stt_requests": 0,
        "tts_chars": 0,
        "total_duration_ms": 12345,
        "avg_duration_ms": 1234
      }
    ]
  }
  ```
- **Use Case:** Real-time monitoring, usage analytics, billing

---

### 7.5 Security Improvements (Dec 19, 2025)

#### **Subkey Hashing** ✅
- Subkeys stored as HMAC-SHA256 hashes in `users.json`
- Uses `MW_SECRET` environment variable as HMAC key
- Fallback to plaintext comparison during migration
- **Migration:** Run `llm-mw/migrate_subkeys.py`

#### **Admin Endpoint Scrubbing** ✅
- `GET /admin/usage` now scrubs `subkey` and `subkey_hash` fields
- Prevents accidental exposure of authentication credentials
- Returns only usage statistics and user metadata

#### **Quota Bug Fix** ✅
- Fixed `_maybe_reset_quota()` to preserve lifetime usage data
- Only resets period counters (`quota["used_*"]`)
- User-level counters (`user["used_*"]`) remain intact for lifetime tracking

---

## 8) Những Thay Đổi So Với Version Trước

### 8.1 Removed Features (Baseline)

#### ❌ Video Generation
- **Endpoint:** `POST /v1/video/generations`
- **Lý do:** OpenWebUI không có native UI support
- **Future:** Sẽ implement qua Tool/Pipe

#### ❌ Audio TTS
- **Endpoint:** `POST /v1/audio/speech`
- **Lý do:** Complexity vs usage trade-off
- **Future:** Tool/Pipe implementation

#### ❌ Audio STT
- **Endpoint:** `POST /v1/audio/transcriptions`
- **Lý do:** Same as TTS
- **Future:** Tool/Pipe implementation

#### ❌ Image Shim in Chat
- **Removed:** Logic to detect image models in chat endpoint
- **Lý do:** Separation of concerns (chat ≠ image)
- **Impact:** Image generation must use `/v1/images/generations`

#### ❌ max_tokens Clamping
- **Removed:** Hard limit of 10000 tokens
- **Lý do:** Breaks UX, user should control
- **Kept:** GPT-5 special handling (max_tokens → max_completion_tokens)

---

### 8.2 Added Features

#### ✅ Authentication for /v1/models
- **Change:** Now requires `Authorization: Bearer <subkey>`
- **Lý do:** Security & per-user model filtering
- **Impact:** Must update OpenWebUI connections

---

### 8.3 Code Changes

**Simplified quota tracking:**
```python
# Before (complex)
def _enforce_and_bump_task_quota(
    add_tokens, add_cost,
    add_image, add_tts, add_stt, add_video, ...
)

# After (clean)
def _enforce_and_bump_task_quota(
    add_tokens, add_cost, add_image_requests
)
```

**Removed functions:**
- `_is_image_model()`
- `_calc_video_cost_usd()`
- `_calc_tts_cost_usd()`

---

## 9) Development Guidelines

### 9.1 Adding a New Model

**Step 1:** Add to `litellm_config.yaml`
```yaml
model_list:
  - model_name: claude-3-opus
    litellm_params:
      model: anthropic/claude-3-opus-20240229
      api_key: os.environ/ANTHROPIC_API_KEY
```

**Step 2:** Add pricing to `prices.json`
```json
{
  "claude-3-opus": {
    "input_per_1m": 15.0,
    "output_per_1m": 75.0
  }
}
```

**Step 3:** Update user `allowed_models` (if restricted)

**Step 4:** Restart LiteLLM

---

### 9.2 Adding a New Endpoint

**Example:** Add embeddings support

```python
@app.post("/v1/embeddings")
async def embeddings(request: Request):
    user = _require_user(request)  # Auth
    body = await request.json()
    model = body.get("model")
    
    _assert_model_allowed(user, model)  # Authorization
    
    # Forward to LiteLLM
    client = request.app.state.http_client
    resp = await client.post(
        f"{LITELLM_BASE}/embeddings",
        headers={"Authorization": f"Bearer {LITELLM_KEY}"},
        json=body
    )
    
    # Track usage (if needed)
    # ...
    
    return resp.json()
```

---

### 9.3 Testing Changes

**Quick test sequence:**
```powershell
# 1. Health check
Invoke-WebRequest http://localhost:5000/health

# 2. Models list
Invoke-WebRequest http://localhost:5000/v1/models `
  -Headers @{"Authorization"="Bearer subkey_admin_123"}

# 3. Chat (non-stream)
$body = @{model="gpt-4o-mini"; messages=@(@{role="user"; content="test"}); stream=$false} | ConvertTo-Json
Invoke-WebRequest http://localhost:5000/v1/chat/completions -Method Post -Headers @{"Authorization"="Bearer subkey_admin_123"; "Content-Type"="application/json"} -Body $body

# 4. Check quota
Get-Content llm-mw/users.json | ConvertFrom-Json | Select used_tokens, used_cost_usd
```

---

## 10) Future Enhancements (Post-Baseline)

### 10.1 Video Generation via Tool/Pipe
- Implement as OpenWebUI custom tool
- Direct API call bypass middleware
- Or: middleware endpoint activated via feature flag

### 10.2 Database Migration
- Replace `users.json` with PostgreSQL
- Add proper indexes for performance
- Transaction support for quota updates

### 10.3 Advanced Monitoring
- Prometheus metrics export
- Grafana dashboards
- Alert rules (quota thresholds, error rates)

### 10.4 Rate Limiting
- Per-user request limits
- Per-IP rate limiting
- DDoS protection

---

## 📚 Tài Liệu Tham Khảo

- **LiteLLM:** https://docs.litellm.ai/
- **OpenWebUI:** https://docs.openwebui.com/
- **FastAPI:** https://fastapi.tiangolo.com/
- **OpenAI API:** https://platform.openai.com/docs/api-reference
- **Gemini API:** https://ai.google.dev/docs

---

**End of Document**
