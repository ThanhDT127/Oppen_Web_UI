# 📚 API REFERENCE - OPPEN WEB UI

Complete documentation for all API endpoints in the LLM Middleware (Port 5000).

---

## 🌐 Base URL

```
http://localhost:5000
```

All endpoints use OpenAI-compatible format unless specified otherwise.

---

## 🔓 Public Endpoints (No Auth Required)

### Health Check

```http
GET /health
```

**Description:** Check if middleware service is running.

**Response:**
```json
{
  "status": "ok"
}
```

**Status Codes:**
- `200 OK` - Service healthy

---

### Model List

```http
GET /v1/models
```

**Description:** Get list of available LLM models from LiteLLM proxy.

**Response:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "gpt-4-turbo",
      "object": "model",
      "created": 1234567890,
      "owned_by": "openai"
    },
    {
      "id": "gemini-pro",
      "object": "model",
      "created": 1234567890,
      "owned_by": "google"
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Models retrieved successfully
- `502 Bad Gateway` - LiteLLM proxy unavailable

---

## 🔐 Authenticated Endpoints (Subkey Required)

All chat endpoints require a valid subkey in the `Authorization` header:

```
Authorization: Bearer sk_user_abc123def456
```

### Chat Completion (Non-Streaming)

```http
POST /v1/chat/completions
Content-Type: application/json
Authorization: Bearer <subkey>
```

**Request Body:**
```json
{
  "model": "gpt-4-turbo",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "Hello, how are you?"
    }
  ],
  "temperature": 0.7,
  "max_tokens": 1000,
  "stream": false
}
```

**Response:**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "gpt-4-turbo",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! I'm doing well, thank you for asking. How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 18,
    "total_tokens": 43
  }
}
```

**Status Codes:**
- `200 OK` - Completion successful
- `401 Unauthorized` - Invalid or missing subkey
- `403 Forbidden` - Quota exceeded
- `502 Bad Gateway` - LiteLLM proxy error

---

### Chat Completion (Streaming)

```http
POST /v1/chat/completions
Content-Type: application/json
Authorization: Bearer <subkey>
```

**Request Body:**
```json
{
  "model": "gpt-4-turbo",
  "messages": [
    {
      "role": "user",
      "content": "Tell me a short story."
    }
  ],
  "stream": true
}
```

**Response:** Server-Sent Events (SSE) stream

```
data: {"id":"chatcmpl-xyz","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4-turbo","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}

data: {"id":"chatcmpl-xyz","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4-turbo","choices":[{"index":0,"delta":{"content":"Once"},"finish_reason":null}]}

data: {"id":"chatcmpl-xyz","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4-turbo","choices":[{"index":0,"delta":{"content":" upon"},"finish_reason":null}]}

...

data: [DONE]
```

**Status Codes:**
- `200 OK` - Stream started successfully
- `401 Unauthorized` - Invalid subkey
- `403 Forbidden` - Quota exceeded

---

### Audio Transcription

```http
POST /v1/audio/transcriptions
Content-Type: multipart/form-data
Authorization: Bearer <subkey>
```

**Request Body:**
```
--boundary
Content-Disposition: form-data; name="file"; filename="audio.mp3"
Content-Type: audio/mpeg

<binary audio data>
--boundary
Content-Disposition: form-data; name="model"

whisper-1
--boundary--
```

**Response:**
```json
{
  "text": "This is the transcribed text from the audio file."
}
```

**Supported Formats:** MP3, MP4, WAV, M4A, WEBM

**Status Codes:**
- `200 OK` - Transcription successful
- `400 Bad Request` - Invalid file format
- `401 Unauthorized` - Invalid subkey

---

## 🔒 Admin Endpoints (Admin Key Required)

All admin endpoints require ADMIN_KEY in the `Authorization` header:

```
Authorization: Bearer YOUR_ADMIN_KEY
```

### Dashboard Login

```http
POST /dashboard/login
Content-Type: application/json
```

**Request Body:**
```json
{
  "username": "admin",
  "password": "YOUR_ADMIN_KEY"
}
```

**Response:**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Sets Cookie:**
```
mw_dashboard_token=<jwt_token>; Path=/; HttpOnly; Max-Age=14400
```

**Status Codes:**
- `200 OK` - Login successful (JWT cookie set)
- `401 Unauthorized` - Invalid credentials

---

### Dashboard Logout

```http
POST /dashboard/logout
```

**Response:**
```json
{
  "success": true
}
```

**Clears Cookie:** `mw_dashboard_token`

**Status Codes:**
- `200 OK` - Logout successful

---

### Summary Dashboard (JWT Auth)

```http
GET /v1/_mw/summary
Cookie: mw_dashboard_token=<jwt_token>
```

**Description:** Get aggregated metrics for dashboard display.

**Response:**
```json
{
  "llm_calls_total": 1245,
  "admin_ops_total": 23,
  "pending_count": 5,
  "breakdown": {
    "chat_completions": 1200,
    "audio_transcriptions": 30,
    "image_generations": 15
  }
}
```

**Status Codes:**
- `200 OK` - Summary retrieved
- `403 Forbidden` - Invalid or expired JWT token

---

### Create Subkey

```http
POST /v1/_mw/subkey
Content-Type: application/json
Authorization: Bearer <admin_key>
```

**Request Body:**
```json
{
  "quota": 100,
  "note": "Test user subkey"
}
```

**Response:**
```json
{
  "subkey": "sk_user_abc123def456",
  "quota": 100,
  "enabled": true,
  "created_at": "2025-12-22T10:30:00Z"
}
```

**Status Codes:**
- `200 OK` - Subkey created
- `401 Unauthorized` - Invalid admin key
- `400 Bad Request` - Invalid quota value

---

### List All Subkeys

```http
GET /v1/_mw/subkeys
Authorization: Bearer <admin_key>
```

**Response:**
```json
{
  "subkeys": [
    {
      "subkey": "sk_user_abc123",
      "enabled": true,
      "quota": 100,
      "llm_calls": 45,
      "admin_ops": 2,
      "pending": 0,
      "created_at": "2025-12-22T10:30:00Z"
    },
    {
      "subkey": "sk_user_xyz789",
      "enabled": false,
      "quota": 50,
      "llm_calls": 50,
      "admin_ops": 0,
      "pending": 0,
      "created_at": "2025-12-21T15:20:00Z"
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Subkeys retrieved
- `401 Unauthorized` - Invalid admin key

---

### Get Subkey Details

```http
GET /v1/_mw/subkey/<subkey>
Authorization: Bearer <admin_key>
```

**Example:**
```
GET /v1/_mw/subkey/sk_user_abc123
```

**Response:**
```json
{
  "subkey": "sk_user_abc123",
  "enabled": true,
  "quota": 100,
  "llm_calls": 45,
  "admin_ops": 2,
  "pending": 0,
  "created_at": "2025-12-22T10:30:00Z"
}
```

**Status Codes:**
- `200 OK` - Subkey found
- `404 Not Found` - Subkey does not exist
- `401 Unauthorized` - Invalid admin key

---

### Update Subkey

```http
PUT /v1/_mw/subkey/<subkey>
Content-Type: application/json
Authorization: Bearer <admin_key>
```

**Request Body:**
```json
{
  "quota": 200,
  "enabled": true
}
```

**Response:**
```json
{
  "subkey": "sk_user_abc123",
  "enabled": true,
  "quota": 200,
  "llm_calls": 45,
  "admin_ops": 2,
  "pending": 0
}
```

**Status Codes:**
- `200 OK` - Subkey updated
- `404 Not Found` - Subkey does not exist
- `401 Unauthorized` - Invalid admin key

---

### Delete Subkey

```http
DELETE /v1/_mw/subkey/<subkey>
Authorization: Bearer <admin_key>
```

**Response:**
```json
{
  "success": true,
  "message": "Subkey deleted successfully"
}
```

**Status Codes:**
- `200 OK` - Subkey deleted
- `404 Not Found` - Subkey does not exist
- `401 Unauthorized` - Invalid admin key

---

### Reset Subkey Usage

```http
POST /v1/_mw/subkey/<subkey>/reset
Authorization: Bearer <admin_key>
```

**Response:**
```json
{
  "subkey": "sk_user_abc123",
  "llm_calls": 0,
  "admin_ops": 0,
  "pending": 0,
  "message": "Usage counters reset successfully"
}
```

**Status Codes:**
- `200 OK` - Counters reset
- `404 Not Found` - Subkey does not exist
- `401 Unauthorized` - Invalid admin key

---

### Stream Admin Operations (SSE)

```http
GET /v1/_mw/stream
Cookie: mw_dashboard_token=<jwt_token>
```

**Description:** Real-time stream of admin operations for dashboard monitoring.

**Response:** Server-Sent Events

```
event: subkey_created
data: {"subkey":"sk_user_new123","quota":100,"timestamp":"2025-12-22T10:35:00Z"}

event: quota_exceeded
data: {"subkey":"sk_user_abc123","attempted":101,"quota":100,"timestamp":"2025-12-22T10:36:00Z"}

event: subkey_deleted
data: {"subkey":"sk_user_old456","timestamp":"2025-12-22T10:37:00Z"}
```

**Event Types:**
- `subkey_created` - New subkey created
- `subkey_updated` - Quota or enabled status changed
- `subkey_deleted` - Subkey removed
- `quota_exceeded` - User hit quota limit
- `chat_completion` - Chat request processed

**Status Codes:**
- `200 OK` - Stream started
- `403 Forbidden` - Invalid JWT token

---

## 📋 Common Parameters

### Chat Completion Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `model` | string | ✅ | - | Model ID (e.g., "gpt-4-turbo") |
| `messages` | array | ✅ | - | Conversation history |
| `temperature` | float | ❌ | 0.7 | Sampling temperature (0-2) |
| `max_tokens` | integer | ❌ | - | Maximum response length |
| `stream` | boolean | ❌ | false | Enable streaming response |
| `top_p` | float | ❌ | 1.0 | Nucleus sampling threshold |
| `frequency_penalty` | float | ❌ | 0.0 | Repetition penalty (-2 to 2) |
| `presence_penalty` | float | ❌ | 0.0 | Topic diversity penalty (-2 to 2) |
| `stop` | string/array | ❌ | null | Stop sequences |
| `user` | string | ❌ | - | End-user identifier for tracking |

### Message Object

```json
{
  "role": "user|assistant|system",
  "content": "Text content or array for multimodal"
}
```

**Multimodal Message (with images):**
```json
{
  "role": "user",
  "content": [
    {
      "type": "text",
      "text": "What's in this image?"
    },
    {
      "type": "image_url",
      "image_url": {
        "url": "data:image/jpeg;base64,..."
      }
    }
  ]
}
```

---

## 🚨 Error Responses

All errors follow OpenAI format:

```json
{
  "error": {
    "message": "Invalid subkey or quota exceeded",
    "type": "invalid_request_error",
    "code": "quota_exceeded"
  }
}
```

### Error Codes

| HTTP Status | Error Type | Description |
|-------------|------------|-------------|
| 400 | `invalid_request_error` | Malformed request body |
| 401 | `authentication_error` | Missing or invalid API key |
| 403 | `quota_exceeded_error` | User quota limit reached |
| 404 | `not_found_error` | Resource does not exist |
| 429 | `rate_limit_error` | Too many requests |
| 500 | `internal_error` | Server-side error |
| 502 | `gateway_error` | LiteLLM proxy unavailable |

---

## 🔄 Rate Limiting

**Current Implementation:** No global rate limiting (controlled by LiteLLM proxy).

**Per-User Limits:** Enforced via subkey quotas:
- Each subkey has a `quota` (max simultaneous requests)
- Exceeding quota returns `403 Forbidden`
- Quota resets automatically when requests complete

**Future Enhancement:** Token-based rate limiting (requests per minute).

---

## 📊 Usage Tracking

All requests are tracked in `logs/audit.jsonl`:

```jsonl
{"timestamp":"2025-12-22T10:40:15Z","event":"chat_completion","subkey":"sk_user_abc123","model":"gpt-4","tokens":1234,"duration":2.5}
{"timestamp":"2025-12-22T10:41:20Z","event":"quota_exceeded","subkey":"sk_user_abc123","attempted":101,"quota":100}
{"timestamp":"2025-12-22T10:42:00Z","event":"subkey_created","subkey":"sk_user_new456","admin_key":"admin_***456"}
```

---

## 🧪 Testing Endpoints

### cURL Examples

**Chat Completion:**
```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Authorization: Bearer sk_user_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4-turbo",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": false
  }'
```

**Create Subkey:**
```bash
curl -X POST http://localhost:5000/v1/_mw/subkey \
  -H "Authorization: Bearer YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"quota": 100, "note": "Test user"}'
```

**Dashboard Login:**
```bash
curl -X POST http://localhost:5000/dashboard/login \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"username": "admin", "password": "YOUR_ADMIN_KEY"}'
```

**Get Summary (with cookie):**
```bash
curl http://localhost:5000/v1/_mw/summary -b cookies.txt
```

---

## 🔗 Related Documentation

- [Architecture Overview](ARCHITECTURE.md) - System design & data flow
- [Dashboard Guide](DASHBOARD.md) - Admin UI usage
- [Quick Start](QUICKSTART.md) - Installation & setup
- [README](../README.md) - Project overview

---

**Last Updated:** December 22, 2025  
**API Version:** 1.0 (OpenAI-compatible)
