# OpenWebUI + Middleware + LiteLLM - Hệ Thống Chat LLM với Quản Lý Quota

Hệ thống chat LLM 3 tầng với xác thực, quản lý quota và tracking usage cho ChatGPT & Gemini.

---

## 📋 TỔNG QUAN

**Kiến trúc:** `OpenWebUI (UI) → Middleware (Auth/Quota) → LiteLLM (Proxy) → ChatGPT/Gemini`

```
┌─────────────────┐
│   OpenWebUI     │  Port 3000 - Web chat interface
│                 │  - Chat với LLM models
└────────┬────────┘  - Lưu chat history
         │ 
         │ POST /v1/chat/completions
         │ Header: Authorization: Bearer <subkey>
         ▼
┌─────────────────┐
│   Middleware    │  Port 5000 - Auth & Quota
│   (FastAPI)     │  - Xác thực subkey từ users.json
│                 │  - Kiểm tra quota (tokens/cost)
└────────┬────────┘  - Track usage real-time
         │
         │ POST /v1/chat/completions
         │ Header: Authorization: Bearer <master_key>
         ▼
┌─────────────────┐
│    LiteLLM      │  Port 4000 - Unified LLM Proxy
│                 │  - Chuẩn hóa API OpenAI-compatible
└────────┬────────┘  - Route requests đến providers
         │
         ├──────────────────┐
         ▼                  ▼
    ┌─────────┐       ┌──────────┐
    │ ChatGPT │       │  Gemini  │
    │ OpenAI  │       │  Google  │
    └─────────┘       └──────────┘
```

---

## 🚀 KHỞI ĐỘNG HỆ THỐNG

### Yêu cầu
- Python 3.11+
- Virtual environment: `D:\Works\.venv`
- Windows PowerShell

### Bước 1: Cài đặt (chỉ lần đầu)

```powershell
# Activate venv
& D:/Works/.venv/Scripts/Activate.ps1

# Install dependencies
pip install litellm open-webui fastapi uvicorn httpx python-dotenv
```

### Bước 2: Chạy 3 services (3 PowerShell terminals)

**Terminal 1 - LiteLLM (Port 4000)**
```powershell
& D:/Works/.venv/Scripts/Activate.ps1
cd D:\Works\Open_Web_UI\Oppen_Web_UI
litellm --config .\litellm\litellm_config.yaml --port 4000
```

**Terminal 2 - Middleware (Port 5000)**
```powershell
& D:/Works/.venv/Scripts/Activate.ps1
cd D:\Works\Open_Web_UI\Oppen_Web_UI\llm-mw
uvicorn main:app --host 0.0.0.0 --port 5000
```

**Terminal 3 - OpenWebUI (Port 3000)**
```powershell
& D:/Works/.venv/Scripts/Activate.ps1
cd D:\Works\Open_Web_UI\Oppen_Web_UI
open-webui serve --port 3000
```

### Bước 3: Truy cập & Cấu hình

1. Mở browser: `http://localhost:3000`
2. Đăng ký/đăng nhập tài khoản admin (first user)
3. Vào **Settings → Connections**:
   ```
   OpenAI API
   - API Base URL: http://127.0.0.1:5000/v1
  - API Key: <SUBKEY_ADMIN>
   ```
4. Chọn model (dropdown): `gpt-4o`, `gemini-2.0-flash`, etc.
5. Bắt đầu chat!

---

## 🔧 CẤU HÌNH CHI TIẾT

### 1. LiteLLM (`litellm/litellm_config.yaml`)

**Chức năng:** Proxy thống nhất cho nhiều LLM providers

**Models hiện có:**
- **ChatGPT:** `gpt-4o`, `gpt-4o-mini`, `gpt-4.1`, `gpt-4.1-mini`, `gpt-4.1-nano`
- **Gemini:** `gemini-2.5-pro`, `gemini-2.0-flash`, `gemini-2.0-flash-lite`, `gemini-3-pro-preview`
- **Embeddings:** `text-embedding-3-small`, `text-embedding-3-large`

**Cấu hình quan trọng:**
```yaml
general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY  # Key dùng cho middleware gọi LiteLLM
  verbose: true
  enable_spend_logging: true

logging:
  file: "D:\\Works\\Open_Web_UI\\Oppen_Web_UI\\litellm\\litellm.log"
```

**Thêm model mới:**
```yaml
model_list:
  - model_name: <tên-model>
    litellm_params:
      model: openai/<model>      # ChatGPT: openai/gpt-4o
      # hoặc
      model: gemini/<model>       # Gemini: gemini/gemini-2.0-flash
      api_key: <your-api-key>
```

---

### 2. Middleware (`llm-mw/`)

**Chức năng:** Xác thực, quản lý quota và tracking usage

**Files chính:**
- `main.py` - FastAPI application với endpoints
- `users.json` - Database user với subkeys và quotas
- `.env` - Environment variables

**Users hiện có:**

| Username | Subkey | Quota |
|----------|--------|-------|
| `admin` | `<SUBKEY_ADMIN>` | Unlimited tokens/cost |
| `user1` | `<SUBKEY_USER1>` | 200,000 tokens/week + $10/week |
| `user2` | `<SUBKEY_USER2>` | 50,000 tokens/month + $25/month |

**Endpoints:**
- `GET /health` - Health check
- `GET /v1/models` - List available models
- `POST /v1/chat/completions` - Chat endpoint (streaming/non-streaming)
- `POST /v1/embeddings` - Embeddings endpoint
- `GET /admin/usage` - Xem usage stats (requires ADMIN_KEY)
- `POST /admin/reset` - Reset quota counters
- `POST /admin/reconcile` - Sync với LiteLLM logs

**Cấu hình (.env):**
```env
LITELLM_BASE=http://127.0.0.1:4000/v1
LITELLM_KEY=<LITELLM_MASTER_KEY>
ADMIN_KEY=<MW_ADMIN_KEY>
```

**Thêm user mới:** Chỉnh sửa `users.json`:
```json
{
  "new_user": {
    "subkey": "subkey_newuser_xyz",
    "allowed_models": ["*"],  // Hoặc ["gpt-4o", "gemini-2.0-flash"]
    "quota": {
      "tokens_per_week": 100000,
      "max_cost_per_month": 50.0
    }
  }
}
```

---

### 3. OpenWebUI Data Directory (`openwebui_data/`)

**⚠️ Lưu ý quan trọng:**
- Thư mục này **tự động được tạo** bởi OpenWebUI khi chạy lần đầu
- Không cần cấu hình `DATA_DIR` environment variable
- OpenWebUI mặc định lưu data trong thư mục project

**Nội dung:**
```
openwebui_data/
├── webui.db          # SQLite database (users, chats, messages)
├── cache/            # Cached data
├── uploads/          # User uploaded files
└── vector_db/        # ChromaDB embeddings (nếu dùng RAG)
```

**Nếu muốn thay đổi vị trí:**
```powershell
# Set environment variable trước khi chạy OpenWebUI
$env:DATA_DIR = "D:\Custom\Path\data"
open-webui serve --port 3000
```

---

## 🔑 XÁC THỰC & PHÂN QUYỀN

### Luồng authentication

1. User login vào OpenWebUI (port 3000)
2. User cấu hình OpenAI API connection:
   - Base URL: `http://127.0.0.1:5000/v1`
  - API Key: Chọn subkey từ `users.json` (ví dụ: `<SUBKEY_ADMIN>`)
3. Khi chat, OpenWebUI gửi request đến Middleware với header:
   ```
  Authorization: Bearer <SUBKEY_ADMIN>
   ```
4. Middleware validate subkey, check quota, forward đến LiteLLM với:
   ```
  Authorization: Bearer <LITELLM_MASTER_KEY>
   ```
5. LiteLLM validate master key, route đến provider

### Keys hierarchy

```
ADMIN_KEY (<MW_ADMIN_KEY>)
  └─ Quản lý middleware admin endpoints
  
LITELLM_KEY (<LITELLM_MASTER_KEY>)
  └─ Master key cho LiteLLM proxy
  
Subkeys (<SUBKEY_ADMIN>, <SUBKEY_USER1>, ...)
  └─ Keys của end-users trong users.json
```

---

## 💬 SỬ DỤNG CHAT

### Workflow cơ bản

1. Truy cập: `http://localhost:3000`
2. Chọn model từ dropdown (ví dụ: `gpt-4o`, `gemini-2.0-flash`)
3. Nhập tin nhắn và chat
4. System tự động:
   - Track tokens used
   - Kiểm tra quota
   - Log usage vào middleware

### Streaming support

- Mặc định: streaming enabled
- Response hiển thị từng chunk realtime
- Timeout: 600 seconds cho requests dài

### Models khả dụng

**ChatGPT:**
- `gpt-4o` - Multimodal, 128k context
- `gpt-4o-mini` - Faster, cheaper variant
- `gpt-4.1`, `gpt-4.1-mini`, `gpt-4.1-nano` - Latest versions

**Gemini:**
- `gemini-2.5-pro` - Google's flagship
- `gemini-2.0-flash` - Fast, long context
- `gemini-2.0-flash-lite` - Lightweight
- `gemini-3-pro-preview` - Experimental

---

## 📊 MONITORING & USAGE

### Xem usage stats

```powershell
# Gọi admin endpoint
curl http://localhost:5000/admin/usage -H "X-Admin-Key: <MW_ADMIN_KEY>"
```

Response:
```json
{
  "admin": {
    "tokens_used": 12144,
    "cost_incurred": 0.15,
    "last_reset": "2025-01-20T10:00:00"
  },
  "user1": { ... },
  "user2": { ... }
}
```

### Reset quota counters

```powershell
# Reset tokens cho user cụ thể
curl -X POST http://localhost:5000/admin/reset?username=user1 -H "X-Admin-Key: <MW_ADMIN_KEY>"

# Reset cost
curl -X POST "http://localhost:5000/admin/reset?username=user1&reset_type=cost" -H "X-Admin-Key: <MW_ADMIN_KEY>"
```

### Log files

- **LiteLLM:** `litellm/litellm.log` - Chi tiết requests/responses
- **Middleware:** Console output (có thể redirect vào file)

---

## 🔍 TROUBLESHOOTING

### 1. "Models không hiển thị trong dropdown"

**Nguyên nhân:** Middleware `/v1/models` endpoint lỗi hoặc OpenWebUI không kết nối được

**Giải pháp:**
```powershell
# Test middleware models endpoint
curl http://localhost:5000/v1/models -H "Authorization: Bearer <SUBKEY_ADMIN>"

# Kiểm tra LiteLLM
curl http://localhost:4000/v1/models -H "Authorization: Bearer <LITELLM_MASTER_KEY>"

# Kiểm tra OpenWebUI Settings → Connections
# Base URL phải là: http://127.0.0.1:5000/v1
```

---

### 2. "Response payload is not completed" / Streaming errors

**Nguyên nhân:** Timeout hoặc connection interrupted

**Giải pháp:**
- Middleware timeout đã set 600s
- Check network stability
- Xem logs trong `litellm/litellm.log`

---

### 3. "Quota exceeded"

**Nguyên nhân:** User vượt tokens_per_week hoặc max_cost

**Response:**
```json
{
  "error": "Token quota exceeded. Used: 201000/200000"
}
```

**Giải pháp:**
```powershell
# Reset quota
curl -X POST http://localhost:5000/admin/reset?username=user1 -H "X-Admin-Key: <MW_ADMIN_KEY>"

# Hoặc tăng quota trong users.json
```

---

### 4. "Invalid API key"

**Nguyên nhân:** Sai subkey hoặc chưa cấu hình

**Giải pháp:**
1. Check OpenWebUI Settings → Connections
2. API Key phải match với subkey trong `users.json`
3. Base URL phải là: `http://127.0.0.1:5000/v1`

---

### 5. "Model not found"

**Nguyên nhân:** Model không có trong `litellm_config.yaml`

**Giải pháp:**
```yaml
# Thêm vào litellm/litellm_config.yaml
model_list:
  - model_name: gpt-4o-new
    litellm_params:
      model: openai/gpt-4o-new
      api_key: <your-key>
```

Restart LiteLLM sau khi thay đổi config.

---

## 🔐 BẢO MẬT & BEST PRACTICES

### Production deployment

1. **Đổi tất cả keys mặc định:**
  - `<LITELLM_MASTER_KEY>` → Strong random key
  - `<MW_ADMIN_KEY>` → Strong random key
   - Regenerate tất cả subkeys

2. **Giới hạn network exposure:**
   ```powershell
   # Middleware chỉ bind localhost
   uvicorn main:app --host 127.0.0.1 --port 5000
   
   # LiteLLM tương tự
   litellm --config config.yaml --port 4000 --host 127.0.0.1
   ```

3. **Setup HTTPS:**
   - Sử dụng nginx/caddy làm reverse proxy
   - Terminate SSL tại proxy layer

4. **Backup database:**
   ```powershell
   # Backup users.json
   cp llm-mw\users.json llm-mw\users.json.backup
   
   # Backup OpenWebUI data
   cp openwebui_data\webui.db openwebui_data\webui.db.backup
   ```

5. **Rate limiting:**
   - Thêm rate limiting vào middleware
   - Sử dụng `slowapi` hoặc nginx limits

---

## 📖 API REFERENCE

### Middleware Endpoints

#### `GET /health`
Health check endpoint.

**Response:**
```json
{ "status": "ok" }
```

---

#### `GET /v1/models`
List available models từ LiteLLM.

**Headers:**
```
Authorization: Bearer <subkey>
```

**Response:**
```json
{
  "data": [
    { "id": "gpt-4o", "object": "model" },
    { "id": "gemini-2.0-flash", "object": "model" }
  ]
}
```

---

#### `POST /v1/chat/completions`
Chat endpoint với streaming/non-streaming support.

**Headers:**
```
Authorization: Bearer <subkey>
Content-Type: application/json
```

**Request:**
```json
{
  "model": "gpt-4o",
  "messages": [
    { "role": "user", "content": "Hello!" }
  ],
  "stream": false,
  "max_tokens": 2048
}
```

**Response (non-streaming):**
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "model": "gpt-4o",
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "Hi there!"
    }
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 5,
    "total_tokens": 15
  }
}
```

**Response (streaming):** Server-Sent Events (SSE)
```
data: {"id":"chatcmpl-123","choices":[{"delta":{"content":"Hi"}}]}

data: {"id":"chatcmpl-123","choices":[{"delta":{"content":" there!"}}]}

data: [DONE]
```

---

#### `POST /v1/embeddings`
Generate embeddings cho text.

**Request:**
```json
{
  "model": "text-embedding-3-small",
  "input": "Hello world"
}
```

**Response:**
```json
{
  "data": [{
    "embedding": [0.123, -0.456, ...],
    "index": 0
  }],
  "usage": { "prompt_tokens": 2 }
}
```

---

#### `GET /admin/usage`
Xem usage statistics cho tất cả users.

**Headers:**
```
X-Admin-Key: <admin_key>
```

---

#### `POST /admin/reset`
Reset quota counters.

**Query params:**
- `username` (required)
- `reset_type` (optional): `tokens` | `cost` | `both` (default: both)

---

## 🛠️ DEVELOPMENT

### Thêm provider mới

1. Update `litellm_config.yaml`:
```yaml
model_list:
  - model_name: claude-3-opus
    litellm_params:
      model: anthropic/claude-3-opus-20240229
      api_key: <anthropic-key>
```

2. Restart LiteLLM
3. Model tự động available trong middleware

---

### Custom middleware logic

File: `llm-mw/main.py`

**Ví dụ: Thêm custom header:**
```python
@app.post("/v1/chat/completions")
async def chat_completions(...):
    # ... validation code ...
    
    headers = {
        "Authorization": f"Bearer {LITELLM_KEY}",
        "X-Custom-Header": "MyValue"  # ← Thêm header
    }
    
    response = await client.post(...)
```

---

## 📚 TÀI LIỆU THAM KHẢO

- LiteLLM Docs: https://docs.litellm.ai/
- OpenWebUI Docs: https://docs.openwebui.com/
- FastAPI Docs: https://fastapi.tiangolo.com/

---

## 📞 HỖ TRỢ

**Issues thường gặp:**
1. Port conflicts → Đổi port trong startup commands
2. API keys invalid → Check `.env` và `litellm_config.yaml`
3. Quota errors → Reset via admin endpoints
4. Models not loading → Verify provider API keys

**Debug checklist:**
- [ ] All 3 services running? (check `http://localhost:<port>/health`)
- [ ] API keys đúng trong configs?
- [ ] OpenWebUI connection settings đúng?
- [ ] Check logs: `litellm/litellm.log` & middleware console

---

**Version:** 1.0  
**Last Updated:** 2025-01-22

**Vai trò:** Authentication, Authorization, Quota Management

**File chính:** `llm-mw/main.py`

**Kiến trúc:**

```python
FastAPI Application
│
├─── CORS Middleware (allow all origins - cấu hình cho dev)
│
├─── Endpoints:
│    ├─ GET  /health                     # Health check
│    ├─ GET  /v1/models                  # List available models
│    ├─ POST /v1/chat/completions        # Main chat endpoint (stream & non-stream)
│    ├─ GET  /admin/usage                # Admin: view all users usage
│    ├─ POST /admin/reset                # Admin: reset quotas
│    └─ POST /admin/reconcile            # Admin: reconcile pending streams
│
└─── Core Logic Modules:
     ├─ _load_users() / _save_users()   # User data persistence
     ├─ _find_user(subkey)               # Subkey validation
     ├─ _maybe_reset_quota()             # Auto quota reset (weekly/monthly)
     ├─ _calc_cost_usd()                 # Calculate cost from tokens
     ├─ _append_pending() / _remove_pending()  # Track streaming requests
     └─ _find_usage_in_litellm_log()     # Parse LiteLLM logs for reconciliation
```

**Files cấu hình:**

1. **`.env`** - Environment variables
```bash
LITELLM_BASE=http://127.0.0.1:4000/v1    # LiteLLM proxy URL
LITELLM_KEY=<LITELLM_MASTER_KEY>          # Master key to call LiteLLM
ADMIN_KEY=<MW_ADMIN_KEY>                  # Admin API key
```

2. **`users.json`** - User database
```json
[
  {
    "user_id": "admin",
    "subkey": "<SUBKEY_ADMIN>",            // API key for this user
    "active": true,                         // Enable/disable user
    "allowed_models": ["*"],                // "*" = all models, or list specific
    "used_tokens": 0,                       // Lifetime token usage
    "used_cost_usd": 0.0,                   // Lifetime cost
    "quota": {
      "period": "monthly",                  // "weekly" or "monthly"
      "timezone": "Asia/Bangkok",
      "limit_tokens": 0,                    // 0 = unlimited
      "limit_cost_usd": 0,                  // 0 = unlimited
      "period_start": <timestamp_ms>,       // Auto reset at period boundary
      "used_tokens": 0,                     // Period usage
      "used_cost_usd": 0.0
    }
  }
]
```

3. **`prices.json`** - Pricing cho các models (per 1K tokens)
```json
{
  "gpt-4": {
    "in": 0.03,      // $0.03 per 1K input tokens
    "out": 0.06      // $0.06 per 1K output tokens
  },
  "gemini-1.5-pro": {
    "in": 0.00125,
    "out": 0.00375
  }
}
```

4. **`pending.csv`** - Track streaming requests chưa hoàn thành
```csv
request_id,user_id,ts
mw_abc123,user1,1734240000
```

**Logic xử lý request:**

```python
# 1. Authentication
auth_header = request.headers.get("Authorization")
subkey = extract_bearer_token(auth_header)
user = find_user(subkey)
if not user or not user.active:
    return 403 Forbidden

# 2. Model Authorization
requested_model = body["model"]
if user.allowed_models != ["*"] and requested_model not in user.allowed_models:
    return 403 Forbidden

# 3. Quota Check (pre-flight for non-streaming)
if not is_streaming:
    if user.quota.limit_tokens > 0 and user.quota.used_tokens >= limit:
        return 403 "Token quota exceeded"
    if user.quota.limit_cost_usd > 0 and user.quota.used_cost_usd >= limit:
        return 403 "Cost quota exceeded"

# 4. Request Enrichment
request_id = f"mw_{uuid4().hex}"
body["user"] = user.user_id
body["metadata"]["mw_request_id"] = request_id
body["max_tokens"] = min(body.get("max_tokens", 512), 512)  # Cap max tokens

# 5. Proxy to LiteLLM
headers = {
    "Authorization": f"Bearer {LITELLM_KEY}",
    "X-Request-ID": request_id
}

if is_streaming:
    append_pending(request_id, user.user_id)  # Track for later reconciliation
    return StreamingResponse(...)
else:
    response = httpx.post(LITELLM_BASE + "/chat/completions", ...)

# 6. Usage Tracking (non-streaming only)
usage = response["usage"]
tokens = usage["total_tokens"]
cost = calc_cost_usd(model, usage["prompt_tokens"], usage["completion_tokens"])

# 7. Quota Enforcement (post-flight)
if limit_tokens > 0 and used_tokens + tokens > limit_tokens:
    return 403 "Quota exceeded"

# 8. Update User Data
user.quota.used_tokens += tokens
user.quota.used_cost_usd += cost
save_users()

# 9. Return Response
return response
```

**Streaming requests:**
- Được track trong `pending.csv`
- Admin phải manually reconcile bằng `/admin/reconcile` endpoint
- Middleware parse `litellm.log` để tìm usage data

---

### 3. LiteLLM Proxy (Port 4000)

**Vai trò:** Unified interface cho nhiều LLM providers

**File cấu hình:** `litellm/litellm_config.yaml`

**Cấu trúc:**

```yaml
model_list:
  # ChatGPT Models
  - model_name: gpt-4                    # Tên model trong hệ thống
    litellm_params:
      model: gpt-4                       # Model name cho OpenAI API
      api_key: os.environ/OPENAI_API_KEY # OpenAI API key

  - model_name: gpt-4o
    litellm_params:
      model: gpt-4o
      api_key: os.environ/OPENAI_API_KEY

  # Gemini Models
  - model_name: gemini-2.0-flash-exp
    litellm_params:
      model: gemini/gemini-2.0-flash-exp  # Prefix "gemini/" for provider
      api_key: os.environ/GEMINI_API_KEY   # Google API key

  - model_name: gemini-1.5-pro
    litellm_params:
      model: gemini/gemini-1.5-pro
      api_key: os.environ/GEMINI_API_KEY

server_settings:
  host: "0.0.0.0"
  port: 4000
  api_base: "/v1"                        # Base path for all endpoints
  telemetry: false                       # Disable usage telemetry to LiteLLM

general_settings:
  enable_spend_logging: true             # Log token usage
  verbose: true                          # Detailed logs
  master_key: os.environ/LITELLM_MASTER_KEY # Required for /v1/models, etc.
  log_level: "info"

logging:
  file: "D:\\Works\\Open_Web_UI\\Oppen_Web_UI\\litellm\\litellm.log"
  level: INFO
```

**Chức năng:**

1. **API Translation:**
   - Nhận OpenAI-compatible request format
   - Chuyển đổi sang format của provider tương ứng
   - Chuẩn hóa response về OpenAI format

2. **Load Balancing:**
   - Có thể define multiple deployments cho cùng 1 model
   - Round-robin hoặc weighted routing
   - Auto-failover khi deployment down

3. **Logging:**
   - Request/response logs chi tiết
   - Token usage tracking
   - Error tracking

4. **Streaming:**
   - Support SSE (Server-Sent Events) streaming
   - Backpressure handling
   - Connection management

**Log format example:**
```
2024-12-15 10:58:28 | litellm.router | INFO | request_id=mw_abc123 model=gpt-4 prompt_tokens=50 completion_tokens=200 total_tokens=250 latency=2.5s
```

---

## 🔄 LUỒNG XỬ LÝ REQUEST

### Non-Streaming Request Flow

```
1. User → OpenWebUI
   POST http://localhost:3000/api/chat
   Body: {
     "model": "gpt-4",
     "messages": [{"role": "user", "content": "Hello"}]
   }

2. OpenWebUI → Middleware
   POST http://localhost:5000/v1/chat/completions
  Headers: Authorization: Bearer <SUBKEY_USER1>
   Body: {
     "model": "gpt-4",
     "messages": [{"role": "user", "content": "Hello"}],
     "stream": false
   }

3. Middleware Processing:
  a) Validate <SUBKEY_USER1> → find user1
   b) Check user1.allowed_models contains "gpt-4" or "*"
   c) Check user1.quota.used_tokens < limit_tokens
   d) Generate request_id = mw_abc123xyz
   e) Enrich body with user_id and request_id metadata

4. Middleware → LiteLLM
   POST http://localhost:4000/v1/chat/completions
   Headers: 
  Authorization: Bearer <LITELLM_MASTER_KEY>
     X-Request-ID: mw_abc123xyz
   Body: {
     "model": "gpt-4",
     "messages": [{"role": "user", "content": "Hello"}],
     "user": "user1",
     "metadata": {"mw_request_id": "mw_abc123xyz"},
     "max_tokens": 512
   }

5. LiteLLM Processing:
  a) Find model="gpt-4" in config → api_key=os.environ/OPENAI_API_KEY
   b) Transform to OpenAI API format
   c) Call OpenAI API

6. OpenAI → LiteLLM
   Response: {
     "id": "chatcmpl-xyz",
     "model": "gpt-4",
     "choices": [{
       "message": {"role": "assistant", "content": "Hi there!"}
     }],
     "usage": {
       "prompt_tokens": 10,
       "completion_tokens": 5,
       "total_tokens": 15
     }
   }

7. LiteLLM → Middleware
   (same response + logging)

8. Middleware Processing:
   a) Extract usage: 15 tokens
   b) Calculate cost: 10*0.03/1000 + 5*0.06/1000 = $0.0006
   c) Check post-flight quota: used_tokens + 15 <= limit
   d) Update user1.quota.used_tokens += 15
   e) Update user1.quota.used_cost_usd += 0.0006
   f) Save users.json
   g) Append metadata to response

9. Middleware → OpenWebUI
   Response: {
     ... (original OpenAI response),
     "_mw_user": "user1",
     "_mw_request_id": "mw_abc123xyz",
     "_mw_added_tokens": 15,
     "_mw_added_cost_usd": 0.0006
   }

10. OpenWebUI → User
    Display assistant message in chat UI
```

### Streaming Request Flow

```
1-4. (Same as non-streaming)

5. Middleware → LiteLLM
   POST (with stream=true)
   
   a) Write to pending.csv: mw_abc123xyz,user1,<timestamp>
   b) Open async streaming connection

6. LiteLLM → OpenAI (streaming)
   SSE stream chunks:
   data: {"choices":[{"delta":{"content":"Hi"}}]}
   data: {"choices":[{"delta":{"content":" there"}}]}
   data: [DONE]

7. LiteLLM → Middleware (streaming)
   Forward SSE chunks as received

8. Middleware → OpenWebUI (streaming)
   Forward SSE chunks to client

9. Post-Stream Reconciliation:
   a) Admin calls POST /admin/reconcile
      Body: {"request_id": "mw_abc123xyz", "user_id": "user1"}
   
   b) Middleware searches litellm.log for request_id
   
   c) Extract usage from log:
      "prompt_tokens=10 completion_tokens=5 total_tokens=15 model=gpt-4"
   
   d) Calculate cost: $0.0006
   
   e) Update user1 quota
   
   f) Remove from pending.csv
   
   g) Return: {"ok": true, "tokens": 15, "cost_usd": 0.0006}
```

---

## 🔐 CƠ CHẾ BẢO MẬT

### 1. Multi-Layer Authentication

**Layer 1: OpenWebUI Internal**
- JWT-based session management
- Secret key: `.webui_secret_key`
- Cookie-based authentication

**Layer 2: Middleware Subkey Auth**
- Bearer token authentication
- Subkeys stored in `users.json`
- Format: `Authorization: Bearer subkey_xxx`
- Each user has unique subkey
- Can enable/disable users via `active` flag

**Layer 3: LiteLLM Master Key**
- Master key required for proxy access
- Middleware uses `<LITELLM_MASTER_KEY>`
- Không expose ra ngoài

**Layer 4: Provider API Keys**
- Real API keys chỉ lưu trong `litellm_config.yaml`
- Không bao giờ gửi đến client
- Rotate keys bằng cách update config và restart LiteLLM

### 2. Authorization Matrix

| Endpoint | Auth Method | Required Role |
|----------|-------------|---------------|
| `/health` | None | Public |
| `/v1/models` | None | Public |
| `/v1/chat/completions` | Subkey | Valid user |
| `/admin/usage` | Admin key | Admin |
| `/admin/reset` | Admin key | Admin |
| `/admin/reconcile` | Admin key | Admin |

**Example:**
```python
# User endpoint
if request.headers.get("Authorization") != f"Bearer {valid_subkey}":
    raise 403

# Admin endpoint
if request.headers.get("Authorization") != f"Bearer {ADMIN_KEY}":
    raise 403
```

### 3. Rate Limiting & Quota

**Per-User Quotas:**
- Token-based: limit_tokens per period
- Cost-based: limit_cost_usd per period
- Period: weekly (Monday 00:00) or monthly (1st 00:00)
- Timezone-aware (Asia/Bangkok default)

**Auto-Reset Logic:**
```python
def _period_anchor_ms(period: str, tz: str) -> int:
    """Calculate period start timestamp"""
    now = datetime.now(ZoneInfo(tz))
    if period == "weekly":
        start = now - timedelta(days=now.weekday())  # Monday
    else:
        start = datetime(now.year, now.month, 1)      # 1st of month
    return int(start.timestamp() * 1000)

def _maybe_reset_quota(user):
    """Auto-reset if period changed"""
    current_anchor = _period_anchor_ms(user.quota.period, user.quota.timezone)
    if user.quota.period_start < current_anchor:
        user.quota.period_start = current_anchor
        user.quota.used_tokens = 0
        user.quota.used_cost_usd = 0.0
```

**Enforcement Points:**
1. Pre-flight check (non-streaming)
2. Post-flight check (after getting usage)
3. Admin can override by resetting quotas

### 4. Model Access Control

**Whitelist per user:**
```json
{
  "user_id": "user1",
  "allowed_models": ["gpt-4", "gemini-1.5-flash"]  // Only these 2 models
}
```

**Wildcard access:**
```json
{
  "user_id": "admin",
  "allowed_models": ["*"]  // All models
}
```

**Validation:**
```python
if user.allowed_models != ["*"] and requested_model not in user.allowed_models:
    raise HTTPException(403, f"Model {requested_model} not allowed")
```

### 5. Security Best Practices

**CORS:**
```python
# Development (hiện tại)
allow_origins=["*"]

# Production (nên thay đổi)
allow_origins=["https://yourdomain.com"]
```

**HTTPS:**
- Development: HTTP OK
- Production: PHẢI dùng HTTPS
- Dùng reverse proxy (nginx, Caddy) để terminate SSL

**API Key Rotation:**
1. Update `litellm_config.yaml` với key mới
2. Restart LiteLLM: `Ctrl+C` và chạy lại
3. Không cần restart middleware hay OpenWebUI

**Secrets Management:**
- Không commit `.env`, `users.json` vào Git
- Add to `.gitignore`
- Dùng environment variables cho production
- Consider: HashiCorp Vault, AWS Secrets Manager

---

## 📊 HỆ THỐNG QUOTA & TRACKING

### Quota Models

**1. Token-based Quota**
```json
{
  "limit_tokens": 200000,      // Max 200K tokens per period
  "used_tokens": 15234,         // Current usage
  "period": "weekly"            // Resets every Monday 00:00
}
```

**2. Cost-based Quota**
```json
{
  "limit_cost_usd": 10.0,      // Max $10 per period
  "used_cost_usd": 2.45,        // Current cost
  "period": "monthly"           // Resets every 1st of month
}
```

**3. Unlimited**
```json
{
  "limit_tokens": 0,            // 0 = no limit
  "limit_cost_usd": 0.0
}
```

### Cost Calculation

**Formula:**
```python
cost_usd = (prompt_tokens / 1000) * price_in + (completion_tokens / 1000) * price_out
```

**Example (GPT-4):**
```
Prompt tokens: 100
Completion tokens: 50
Price: $0.03/1K in, $0.06/1K out

Cost = (100/1000)*0.03 + (50/1000)*0.06
     = 0.003 + 0.003
     = $0.006
```

**Pricing Table (prices.json):**
```json
{
  "gpt-4": {"in": 0.03, "out": 0.06},
  "gpt-4o": {"in": 0.005, "out": 0.015},
  "gpt-3.5-turbo": {"in": 0.0005, "out": 0.0015},
  "gemini-2.0-flash-exp": {"in": 0.0, "out": 0.0},
  "gemini-1.5-pro": {"in": 0.00125, "out": 0.00375},
  "gemini-1.5-flash": {"in": 0.000075, "out": 0.0003}
}
```

### Tracking Architecture

**Real-time Tracking (non-streaming):**
```
Request → Middleware → LiteLLM → Provider
                ↓
          Get usage from response
                ↓
          Calculate cost
                ↓
          Check quota
                ↓
          Update user.quota
                ↓
          Save users.json
                ↓
          Return response
```

**Deferred Tracking (streaming):**
```
Request → Middleware → LiteLLM → Provider
            ↓
      pending.csv
      (mw_id, user, ts)
            ↓
      [Stream completes]
            ↓
      Admin reconcile endpoint
            ↓
      Parse litellm.log
            ↓
      Extract usage
            ↓
      Update quota
            ↓
      Remove from pending
```

### Reconciliation Process

**Manual Reconciliation:**
```bash
# Admin API call
POST http://localhost:5000/admin/reconcile
Headers: Authorization: Bearer <MW_ADMIN_KEY>
Body: {
  "request_id": "mw_abc123xyz",
  "user_id": "user1",
  "model": "gpt-4"  # Optional, fallback if not in log
}

Response: {
  "ok": true,
  "request_id": "mw_abc123xyz",
  "user_id": "user1",
  "model": "gpt-4",
  "prompt_tokens": 100,
  "completion_tokens": 50,
  "total_tokens": 150,
  "cost_usd": 0.006
}
```

**Auto-Reconciliation (future enhancement):**
- Cron job chạy mỗi giờ
- Scan `pending.csv` cho requests > 1h
- Auto reconcile từ `litellm.log`
- Alert admin nếu không tìm thấy usage

---

## 📝 LOGGING & MONITORING

### 1. LiteLLM Logs

**File:** `litellm/litellm.log`

**Format:**
```
2024-12-15 10:58:28 | litellm.router | INFO | 
  request_id=mw_abc123xyz
  model=gpt-4
  prompt_tokens=100
  completion_tokens=50
  total_tokens=150
  latency=2.5s
  status=success
```

**Usage:**
- Debug request flow
- Reconcile streaming usage
- Performance monitoring
- Error tracking

**Rotation:**
```python
# Future: implement log rotation
import logging.handlers
handler = logging.handlers.RotatingFileHandler(
    "litellm.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

### 2. Middleware Logs

**Console output (stdout):**
```
INFO:     127.0.0.1:52434 - "POST /v1/chat/completions HTTP/1.1" 200 OK
```

**Future: Structured logging:**
```python
import structlog

logger = structlog.get_logger()
logger.info(
    "chat_request",
    user_id=user["user_id"],
    model=model,
    tokens=total_tokens,
    cost_usd=cost,
    quota_remaining=limit - used
)
```

### 3. Monitoring Metrics

**Key Metrics:**

| Metric | Description | Source |
|--------|-------------|--------|
| requests_total | Total requests per user | Middleware |
| tokens_used | Token usage per user/model | Middleware |
| cost_usd | Cost per user/period | Middleware |
| quota_remaining | Tokens/cost left | users.json |
| latency_p95 | 95th percentile latency | LiteLLM log |
| error_rate | % failed requests | LiteLLM log |

**Dashboard (future):**
- Grafana + Prometheus
- Export metrics từ middleware
- Visualize usage trends
- Alert on quota breach

### 4. Error Tracking

**Error Types:**

1. **Authentication Errors (401/403)**
```
- Invalid subkey
- User inactive
- Model not allowed
- Quota exceeded
```

2. **Provider Errors (500/502/503)**
```
- OpenAI API down
- Gemini rate limit
- Invalid API key
- Model not available
```

3. **Application Errors (500)**
```
- Database write failure
- Log parsing error
- Invalid request format
```

**Error Response Format:**
```json
{
  "error": {
    "message": "Token quota exceeded for user1 (200000/200000)",
    "type": "quota_exceeded",
    "code": 403
  }
}
```

---

## ⚙️ CẤU HÌNH CHI TIẾT

### litellm_config.yaml

**Full example:**
```yaml
model_list:
  # ChatGPT Models
  - model_name: gpt-4
    litellm_params:
      model: gpt-4
      api_key: os.environ/OPENAI_API_KEY
      # Optional per-model settings:
      # temperature: 0.7
      # max_tokens: 4096
      # timeout: 600

  - model_name: gpt-4-turbo
    litellm_params:
      model: gpt-4-turbo
      api_key: os.environ/OPENAI_API_KEY

  # Gemini Models  
  - model_name: gemini-2.0-flash-exp
    litellm_params:
      model: gemini/gemini-2.0-flash-exp
      api_key: os.environ/GEMINI_API_KEY

  # Multiple deployments for same model (load balancing)
  - model_name: gpt-3.5-turbo
    litellm_params:
      model: gpt-3.5-turbo
      api_key: os.environ/OPENAI_API_KEY
      
  - model_name: gpt-3.5-turbo
    litellm_params:
      model: gpt-3.5-turbo
      api_key: os.environ/OPENAI_API_KEY

server_settings:
  host: "0.0.0.0"              # Bind to all interfaces
  port: 4000
  api_base: "/v1"              # Base path
  telemetry: false             # Disable telemetry
  # num_workers: 4             # Uvicorn workers (default: 1)

general_settings:
  enable_spend_logging: true   # Log token usage
  verbose: true                # Detailed logs
  master_key: os.environ/LITELLM_MASTER_KEY
  log_level: "info"            # debug, info, warning, error
  # fallbacks: []              # Fallback models on error
  # retry_policy:              # Retry configuration
  #   max_retries: 3
  #   base_delay: 1.0

logging:
  file: "D:\\Works\\Open_Web_UI\\Oppen_Web_UI\\litellm\\litellm.log"
  level: INFO
  # max_bytes: 10485760        # 10MB
  # backup_count: 5            # Keep 5 old logs
```

### users.json Schema

```json
[
  {
    "user_id": "string",              // Unique user identifier
    "subkey": "string",               // API key (Bearer token)
    "active": boolean,                // Enable/disable user
    "allowed_models": string[],       // ["*"] or ["model1", "model2"]
    "used_tokens": integer,           // Lifetime token usage
    "used_cost_usd": float,           // Lifetime cost
    "quota": {
      "period": "weekly"|"monthly",   // Quota reset period
      "timezone": "string",           // IANA timezone
      "limit_tokens": integer,        // 0 = unlimited
      "limit_cost_usd": float,        // 0 = unlimited
      "period_start": integer,        // Epoch ms
      "used_tokens": integer,         // Period usage
      "used_cost_usd": float         // Period cost
    }
  }
]
```

### Environment Variables

**Middleware (.env):**
```bash
# LiteLLM connection
LITELLM_BASE=http://127.0.0.1:4000/v1
LITELLM_KEY=<LITELLM_MASTER_KEY>

# Admin API
ADMIN_KEY=<MW_ADMIN_KEY>

# Optional
# DATABASE_PATH=./users.json
# PRICES_PATH=./prices.json
# LOG_LEVEL=INFO
```

**OpenWebUI:**
```bash
# Set via UI or env vars
WEBUI_SECRET_KEY=<auto-generated>
ENABLE_RAG_WEB_SEARCH=True
ENABLE_UPLOAD_FILES=True
CORS_ALLOW_ORIGIN=*
```

---

## 🚀 HƯỚNG DẪN VẬN HÀNH

### Khởi Động Hệ Thống

**Prerequisites:**
```powershell
# 1. Activate venv
& D:/Works/.venv/Scripts/Activate.ps1

# 2. Install dependencies (one-time)
pip install -r D:\Works\Open_Web_UI\Oppen_Web_UI\requirements.txt
pip install open-webui email-validator fastapi-sso litellm-enterprise litellm-proxy-extras
```

**Start services (3 terminals):**

**Terminal 1: LiteLLM**
```powershell
cd D:\Works\Open_Web_UI\Oppen_Web_UI
litellm --config litellm\litellm_config.yaml --port 4000
```

**Terminal 2: Middleware**
```powershell
cd D:\Works\Open_Web_UI\Oppen_Web_UI\llm-mw
uvicorn main:app --host 0.0.0.0 --port 5000
```

**Terminal 3: OpenWebUI**
```powershell
cd D:\Works\Open_Web_UI\Oppen_Web_UI
open-webui serve --port 3000
```

**Verify:**
```powershell
# LiteLLM
curl http://localhost:4000/health

# Middleware
curl http://localhost:5000/health

# OpenWebUI
curl http://localhost:3000
```

### Cấu Hình OpenWebUI

1. Mở browser: http://localhost:3000
2. Đăng ký tài khoản admin (first user)
3. Settings → Connection:
   ```
   Base URL: http://127.0.0.1:5000/v1
  API Key: <SUBKEY_ADMIN>
   ```
4. Model dropdown → chọn `gpt-4`, `gemini-2.0-flash-exp`, etc.
5. Test chat: "Hello, how are you?"

### Quản Lý Users

**Add new user:**
```json
// Edit llm-mw/users.json
{
  "user_id": "user3",
  "subkey": "subkey_user3_newkey",
  "active": true,
  "allowed_models": ["gpt-3.5-turbo", "gemini-1.5-flash"],
  "used_tokens": 0,
  "used_cost_usd": 0.0,
  "quota": {
    "period": "monthly",
    "timezone": "Asia/Bangkok",
    "limit_tokens": 100000,
    "limit_cost_usd": 5.0,
    "period_start": 0,
    "used_tokens": 0,
    "used_cost_usd": 0.0
  }
}
```
No restart needed - file is reloaded on each request.

**Disable user:**
```json
{
  "user_id": "user1",
  "active": false,  // Change to false
  ...
}
```

**Reset quota:**
```powershell
curl -X POST http://localhost:5000/admin/reset \
  -H "Authorization: Bearer <MW_ADMIN_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user1"}'  # Or omit to reset all
```

### Monitoring Usage

**View all users:**
```powershell
curl http://localhost:5000/admin/usage \
  -H "Authorization: Bearer <MW_ADMIN_KEY>"
```

**Response:**
```json
[
  {
    "user_id": "user1",
    "subkey": "<SUBKEY_USER1>",
    "active": true,
    "used_tokens": 15234,
    "used_cost_usd": 2.45,
    "quota": {
      "period": "weekly",
      "limit_tokens": 200000,
      "used_tokens": 15234,
      "limit_cost_usd": 10.0,
      "used_cost_usd": 2.45
    }
  }
]
```

### Reconcile Streaming Requests

**List pending:**
```powershell
cat llm-mw/pending.csv
```

**Reconcile one:**
```powershell
curl -X POST http://localhost:5000/admin/reconcile \
  -H "Authorization: Bearer <MW_ADMIN_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "mw_abc123xyz",
    "user_id": "user1"
  }'
```

### Rotate API Keys

**ChatGPT key:**
1. Edit `litellm_config.yaml` → update `api_key`
2. Restart LiteLLM (Ctrl+C, then rerun)

**Gemini key:**
1. Edit `litellm_config.yaml` → update `api_key`  
2. Restart LiteLLM

**User subkey:**
1. Edit `users.json` → change `subkey`
2. No restart needed
3. Notify user of new key

**Admin key:**
1. Edit `llm-mw/.env` → change `ADMIN_KEY`
2. Restart Middleware

### Backup & Restore

**Backup data:**
```powershell
# Users & quotas
cp llm-mw/users.json llm-mw/users.json.backup

# Pending streams
cp llm-mw/pending.csv llm-mw/pending.csv.backup

# OpenWebUI data
cp -r .webui_secret_key webui.db vector_db/ backup/
```

**Restore:**
```powershell
cp llm-mw/users.json.backup llm-mw/users.json
# Restart middleware
```

---

## 📡 API REFERENCE

### Middleware Endpoints

#### GET /health

Health check endpoint.

**Request:**
```bash
GET http://localhost:5000/health
```

**Response:**
```json
{
  "ok": true,
  "time": 1734240000
}
```

---

#### GET /v1/models

List available models.

**Request:**
```bash
GET http://localhost:5000/v1/models
```

**Response:**
```json
{
  "data": [
    {"id": "gpt-4", "object": "model"},
    {"id": "gpt-4o", "object": "model"},
    {"id": "gemini-2.0-flash-exp", "object": "model"}
  ]
}
```

---

#### POST /v1/chat/completions

Main chat endpoint (OpenAI-compatible).

**Request:**
```bash
POST http://localhost:5000/v1/chat/completions
Headers:
  Authorization: Bearer <SUBKEY_USER1>
  Content-Type: application/json

Body:
{
  "model": "gpt-4",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  "temperature": 0.7,
  "max_tokens": 512,
  "stream": false
}
```

**Response (non-streaming):**
```json
{
  "id": "chatcmpl-xyz",
  "object": "chat.completion",
  "created": 1734240000,
  "model": "gpt-4",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Hi! How can I help you today?"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 10,
    "total_tokens": 35
  },
  "_mw_user": "user1",
  "_mw_request_id": "mw_abc123",
  "_mw_added_tokens": 35,
  "_mw_added_cost_usd": 0.0012
}
```

**Response (streaming):**
```
data: {"choices":[{"delta":{"role":"assistant"}}]}

data: {"choices":[{"delta":{"content":"Hi"}}]}

data: {"choices":[{"delta":{"content":"!"}}]}

data: [DONE]
```

**Error Responses:**
```json
// 401 Unauthorized
{
  "detail": "Missing sub-key"
}

// 403 Forbidden - Invalid key
{
  "detail": "Invalid or inactive sub-key"
}

// 403 Forbidden - Model not allowed
{
  "detail": "Model 'gpt-4' not allowed for user1"
}

// 403 Forbidden - Quota exceeded
{
  "detail": "Token quota exceeded for user1 (200000/200000)"
}
```

---

#### GET /admin/usage

View usage for all users (admin only).

**Request:**
```bash
GET http://localhost:5000/admin/usage
Headers:
  Authorization: Bearer <MW_ADMIN_KEY>
```

**Response:**
```json
[
  {
    "user_id": "user1",
    "subkey": "<SUBKEY_USER1>",
    "active": true,
    "allowed_models": ["*"],
    "used_tokens": 15234,
    "used_cost_usd": 2.45,
    "quota": {
      "period": "weekly",
      "timezone": "Asia/Bangkok",
      "limit_tokens": 200000,
      "limit_cost_usd": 10.0,
      "period_start": 1733702400000,
      "used_tokens": 15234,
      "used_cost_usd": 2.45
    }
  }
]
```

---

#### POST /admin/reset

Reset quota for one or all users (admin only).

**Request:**
```bash
POST http://localhost:5000/admin/reset
Headers:
  Authorization: Bearer <MW_ADMIN_KEY>
  Content-Type: application/json

Body:
{
  "user_id": "user1"  // Omit to reset all users
}
```

**Response:**
```json
{
  "ok": true
}
```

---

#### POST /admin/reconcile

Reconcile streaming request usage (admin only).

**Request:**
```bash
POST http://localhost:5000/admin/reconcile
Headers:
  Authorization: Bearer <MW_ADMIN_KEY>
  Content-Type: application/json

Body:
{
  "request_id": "mw_abc123xyz",
  "user_id": "user1",
  "model": "gpt-4"  // Optional fallback
}
```

**Response:**
```json
{
  "ok": true,
  "request_id": "mw_abc123xyz",
  "user_id": "user1",
  "model": "gpt-4",
  "prompt_tokens": 100,
  "completion_tokens": 50,
  "total_tokens": 150,
  "cost_usd": 0.006
}
```

**Error:**
```json
{
  "detail": "No usage found in LiteLLM log for request_id=..."
}
```

---

### LiteLLM Endpoints

LiteLLM exposes OpenAI-compatible endpoints:

- `GET /v1/models` - List models
- `POST /v1/chat/completions` - Chat completions
- `POST /v1/completions` - Text completions
- `POST /v1/embeddings` - Embeddings
- `GET /health` - Health check

Authentication: `Authorization: Bearer <LITELLM_MASTER_KEY>`

---

## 🔧 TROUBLESHOOTING

### Issue: LiteLLM fails to start

**Symptom:**
```
ModuleNotFoundError: No module named 'fastapi_sso'
```

**Solution:**
```powershell
pip install fastapi-sso litellm-enterprise litellm-proxy-extras
```

---

### Issue: Model not loading in LiteLLM

**Symptom:**
```
LLM Provider NOT provided
```

**Solution:**
Check `litellm_config.yaml`:
- ChatGPT: model name should be just `gpt-4`, NOT `openai/gpt-4`
- Gemini: model name MUST have prefix `gemini/`, e.g., `gemini/gemini-2.0-flash-exp`

---

### Issue: 403 Forbidden from middleware

**Check:**
1. Subkey correct? Compare with `users.json`
2. User active? Check `active: true`
3. Model allowed? Check `allowed_models`
4. Quota exceeded? Check `used_tokens` vs `limit_tokens`

**Debug:**
```powershell
# View user data
curl http://localhost:5000/admin/usage \
  -H "Authorization: Bearer <MW_ADMIN_KEY>"
```

---

### Issue: Streaming not working

**Symptom:**
Client hangs, no response.

**Debug:**
1. Check middleware terminal for errors
2. Check LiteLLM terminal for request logs
3. Verify `stream: true` in request body

**Reconcile afterwards:**
```powershell
curl -X POST http://localhost:5000/admin/reconcile \
  -H "Authorization: Bearer <MW_ADMIN_KEY>" \
  -d '{"request_id": "...", "user_id": "..."}'
```

---

### Issue: Quota not resetting

**Symptom:**
Monday/1st of month passed but quota still high.

**Solution:**
Quota resets on next request. To force reset:
```powershell
curl -X POST http://localhost:5000/admin/reset \
  -H "Authorization: Bearer <MW_ADMIN_KEY>" \
  -d '{"user_id": "user1"}'
```

---

### Issue: API key invalid

**Symptom:**
```
OpenAI: Invalid API key
Gemini: 401 Unauthorized
```

**Solution:**
1. Verify keys in `litellm_config.yaml`
2. Test keys directly:
   ```powershell
   # ChatGPT
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $env:OPENAI_API_KEY"
   
   # Gemini
   curl "https://generativelanguage.googleapis.com/v1beta/models?key=$env:GEMINI_API_KEY"
   ```
3. Rotate keys if needed

---

### Issue: OpenWebUI can't connect to middleware

**Symptom:**
"Failed to fetch" error in browser.

**Check:**
1. Middleware running? `curl http://localhost:5000/health`
2. Correct URL in OpenWebUI settings? Should be `http://127.0.0.1:5000/v1`
3. CORS enabled? Check middleware logs for CORS errors

**Temp fix:**
Allow CORS in middleware (already enabled):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Already set
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📚 SUMMARY

**System Flow:**
```
User → OpenWebUI → Middleware → LiteLLM → ChatGPT/Gemini
         (3000)      (5000)       (4000)
```

**Key Files:**
- `litellm/litellm_config.yaml` - LLM models & API keys
- `llm-mw/users.json` - Users, quotas, subkeys
- `llm-mw/.env` - Middleware config
- `llm-mw/prices.json` - Cost per model
- `litellm/litellm.log` - Request logs

**Security:**
- Layer 1: OpenWebUI JWT
- Layer 2: Middleware subkeys
- Layer 3: LiteLLM master key
- Layer 4: Provider API keys

**Quota:**
- Token-based or cost-based
- Weekly or monthly periods
- Auto-reset on period boundary
- Admin can manually reset

**Monitoring:**
- View usage: `GET /admin/usage`
- Reconcile streams: `POST /admin/reconcile`
- Check logs: `litellm.log`, middleware console

**Operations:**
- Start: 3 terminals (LiteLLM, Middleware, OpenWebUI)
- Add user: Edit `users.json`
- Rotate keys: Edit config, restart service
- Backup: Copy `users.json`, `webui.db`, `vector_db/`

---

Đây là hệ thống proxy LLM production-ready với đầy đủ authentication, authorization, quota management, và logging. Có thể scale bằng cách add thêm models, users, và deploy lên cloud với load balancer.

## 0) Create and activate a virtual environment (Windows PowerShell)

```powershell
cd D:\ktlt\Works\Open_Web_UI
# Option A (python on PATH)
python -m venv .venv
# Option B (py launcher)
# py -3 -m venv .venv

.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r .\requirements.txt
```

## I) Configure and run LiteLLM (proxy)

## Appendix (deprecated)

Các ghi chú cũ về Groq/Docker đã được loại bỏ để tránh nhầm lẫn. Hệ thống hiện tại chạy native trên Windows với 3 services: OpenWebUI (3000) → Middleware (5000) → LiteLLM (4000).
