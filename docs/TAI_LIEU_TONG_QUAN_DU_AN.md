# TÀI LIỆU TỔNG QUAN DỰ ÁN OPEN WEBUI STACK

## 📋 Mục Lục

1. [Tổng Quan Kiến Trúc](#1-tổng-quan-kiến-trúc)
2. [Quản Lý Người Dùng](#2-quản-lý-người-dùng)
3. [Hệ Thống Models](#3-hệ-thống-models)
4. [RAG (Retrieval-Augmented Generation)](#4-rag-retrieval-augmented-generation)
5. [Database & Lưu Trữ](#5-database--lưu-trữ)
6. [Hệ Thống Quota & Chi Phí](#6-hệ-thống-quota--chi-phí)
7. [API Endpoints](#7-api-endpoints)
8. [Bảo Mật & Xác Thực](#8-bảo-mật--xác-thực)
9. [Vận Hành & Giám Sát](#9-vận-hành--giám-sát)

---

## 1. Tổng Quan Kiến Trúc

### 1.1 Kiến Trúc 3-Tier

```
┌─────────────────────────────────────────────────────────────────┐
│                         NGƯỜI DÙNG                               │
│                    (Browser, API Client)                         │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 1: PRESENTATION LAYER                                      │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │  Open WebUI v0.7.2                      Port: 3000        │   │
│  │  - Giao diện chat đa phương thức                          │   │
│  │  - Quản lý knowledge base                                  │   │
│  │  - Authentication & User management                        │   │
│  └───────────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────────┘
                          │ OpenAI-Compatible API
                          │ Authorization: Bearer <subkey>
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 2: BUSINESS LOGIC LAYER                                    │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │  Middleware (FastAPI)                   Port: 5000        │   │
│  │  - Xác thực subkey                                        │   │
│  │  - Quản lý quota & cost                                   │   │
│  │  - Rate limiting                                          │   │
│  │  - Audit logging                                          │   │
│  └───────────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────────┘
                          │ OpenAI-Compatible API
                          │ Authorization: Bearer <master_key>
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 3: DATA & INTEGRATION LAYER                                │
│  ┌────────────────────────┐  ┌─────────────────────────────┐    │
│  │  LiteLLM Proxy         │  │  PostgreSQL + PGVector      │    │
│  │  Port: 4000            │  │  Port: 5432                  │    │
│  │  - Model routing       │  │  - User data                 │    │
│  │  - Provider adapters   │  │  - Chat history              │    │
│  └───────────┬────────────┘  │  - Vector embeddings         │    │
│              │               └─────────────────────────────┘    │
│              ├──────────────────────────────────────────┐       │
│              ▼                                          ▼       │
│       ┌──────────────┐                      ┌──────────────┐    │
│       │   OpenAI     │                      │   Google     │    │
│       │   APIs       │                      │   Gemini     │    │
│       └──────────────┘                      └──────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Docker Services

| Service | Container | Image | Port | Chức Năng |
|---------|-----------|-------|------|-----------|
| **PostgreSQL** | openwebui-postgres | pgvector/pgvector:0.8.0-pg16 | 5432 | Database chính + Vector DB |
| **LiteLLM** | openwebui-litellm | ghcr.io/berriai/litellm:main-latest | 4000 | LLM Proxy |
| **Middleware** | openwebui-middleware | Custom Dockerfile | 5000 | Auth & Quota |
| **Open WebUI** | openwebui-app | ghcr.io/open-webui/open-webui:main | 3000 | UI Layer |

### 1.3 Luồng Dữ Liệu

```mermaid
sequenceDiagram
    participant U as User
    participant OW as Open WebUI
    participant MW as Middleware
    participant LL as LiteLLM
    participant P as Provider (OpenAI/Gemini)
    participant DB as PostgreSQL

    U->>OW: Chat message
    OW->>DB: Save chat context
    OW->>MW: POST /v1/chat/completions (Bearer subkey)
    MW->>MW: Validate subkey
    MW->>MW: Check quota
    MW->>LL: POST /chat/completions (Bearer master_key)
    LL->>P: API request
    P-->>LL: Response + usage
    LL-->>MW: Response + cost headers
    MW->>MW: Update usage/cost
    MW-->>OW: Response
    OW->>DB: Save response
    OW-->>U: Display response
```

---

## 2. Quản Lý Người Dùng

### 2.1 Hai Hệ Thống User

#### 2.1.1 Open WebUI Users (UI Layer)
- **Lưu trữ**: PostgreSQL (`user` table)
- **Xác thực**: Email + Password
- **Vai trò**: Admin, User
- **Quản lý qua**: Admin Panel `/admin`

**Cấu trúc User:**
```sql
user {
    id: UUID
    email: String
    name: String
    password_hash: String
    role: admin | user
    created_at: Timestamp
}
```

#### 2.1.2 Middleware Users (API Layer)
- **Lưu trữ**: JSON file (`llm-mw/users.json`)
- **Xác thực**: Subkey (API key)
- **Quản lý qua**: Chỉnh sửa file trực tiếp

**Cấu trúc User:**
```json
{
  "user_id": "admin",
  "subkey": "subkey_admin_123",
  "active": true,
  "allowed_models": ["*"],
  "quota": {
    "period": "monthly",
    "timezone": "Asia/Bangkok",
    "limit_tokens": 0,
    "limit_cost_usd": 0,
    "limit_image_requests": 100,
    "limit_tts_requests": 500,
    "limit_stt_requests": 100,
    "limit_video_requests": 10,
    "used_tokens": 1217,
    "used_cost_usd": 0.0078825
  }
}
```

### 2.2 Ma Trận Quyền

| Tính Năng | Admin | User | API Only |
|-----------|-------|------|----------|
| **Chat với LLM** | ✅ | ✅ | ✅ |
| **Xem danh sách models** | ✅ | ✅ | ✅ |
| **Upload documents (RAG)** | ✅ | ✅ | ❌ |
| **Tạo knowledge base** | ✅ | ✅ | ❌ |
| **Quản lý users** | ✅ | ❌ | ❌ |
| **Xem usage stats** | ✅ | ❌ | ✅ (Admin key) |
| **Reset quota** | ✅ | ❌ | ✅ (Admin key) |
| **Cấu hình connections** | ✅ | ❌ | ❌ |

### 2.3 Thêm/Sửa User

**Thêm user trong Open WebUI:**
1. Truy cập `/admin/users`
2. Click "Add User"
3. Nhập email, name, password, role

**Thêm user trong Middleware:**
```json
// Chỉnh sửa llm-mw/users.json
{
  "user_id": "new_user",
  "subkey": "subkey_newuser_xyz",
  "active": true,
  "allowed_models": ["gpt-4o-mini", "gemini-2.5-flash"],
  "quota": {
    "period": "weekly",
    "timezone": "Asia/Bangkok",
    "limit_tokens": 100000,
    "limit_cost_usd": 10.0
  }
}
```

---

## 3. Hệ Thống Models

### 3.1 Danh Sách Models Có Sẵn

#### 3.1.1 OpenAI Models

| Model | Loại | Giá (USD/1M tokens) | Ghi Chú |
|-------|------|---------------------|---------|
| **gpt-5** | Chat | $1.25 input/output | Flagship model |
| **gpt-5-mini** | Chat | $0.25 input/output | Nhẹ hơn, nhanh hơn |
| **gpt-5-nano** | Chat | $0.05 input/output | Siêu nhẹ |
| **gpt-4o** | Chat | $2.50 input/output | Omni model |
| **gpt-4o-mini** | Chat | $0.15 input/output | Omni mini |
| **gpt-4.1** | Chat | $2.00 input/output | Latest GPT-4 |
| **gpt-4.1-mini** | Chat | $0.40 input/output | |
| **gpt-4.1-nano** | Chat | $0.10 input/output | |
| **gpt-image-1** | Image | $0.011-$0.25/ảnh | Tùy quality/size |
| **gpt-4o-mini-tts** | TTS | $15/1M chars | Text-to-Speech |
| **gpt-4o-transcribe** | STT | $0.006/phút | Speech-to-Text |
| **gpt-4o-mini-transcribe** | STT | $0.003/phút | STT nhẹ |
| **sora-2** | Video | $0.10/giây | Video generation |
| **sora-2-pro** | Video | $0.30/giây | Video HD |

#### 3.1.2 Google Gemini Models

| Model | Loại | Giá Input (USD/1M) | Giá Output (USD/1M) |
|-------|------|---------------------|---------------------|
| **gemini-2.5-pro** | Chat | $1.25 | $10.00 |
| **gemini-2.5-flash** | Chat | $0.30 | $2.50 |
| **gemini-2.5-flash-lite** | Chat | $0.10 | $0.40 |
| **gemini-2.5-flash-image** | Image | $0.30 + $0.039/ảnh | $2.50 |
| **gemini-2.5-flash-preview-tts** | TTS | Custom pricing | |
| **gemini-2.0-flash** | Chat | $0.10 | $0.40 |
| **gemini-2.0-flash-lite** | Chat | $0.075 | $0.30 |
| **gemini-3-pro-preview** | Chat | $2.00 | $12.00 |

### 3.2 Model Routing

```yaml
# litellm/litellm_config.yaml
model_list:
  - model_name: gpt-4o
    litellm_params:
      model: openai/gpt-4o
      api_key: os.environ/OPENAI_API_KEY

  - model_name: gemini-2.5-flash
    litellm_params:
      model: gemini/gemini-2.5-flash
      api_key: os.environ/GEMINI_API_KEY
```

### 3.3 Model Governance (Middleware)

**Allowlist theo user:**
```json
{
  "user_id": "limited_user",
  "allowed_models": ["gpt-4o-mini", "gemini-2.5-flash-lite"]
}
```

**Wildcard cho admin:**
```json
{
  "user_id": "admin",
  "allowed_models": ["*"]
}
```

---

## 4. RAG (Retrieval-Augmented Generation)

### 4.1 Kiến Trúc RAG

```
┌─────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE BASE                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Documents (PDF, TXT, DOCX, MD, CSV, XLSX)          │    │
│  └────────────────────────┬────────────────────────────┘    │
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Text Splitter                                       │    │
│  │  - Chunk Size: 1000 chars                            │    │
│  │  - Chunk Overlap: 200 chars                          │    │
│  │  - Splitter: character                               │    │
│  └────────────────────────┬────────────────────────────┘    │
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Embedding Model                                     │    │
│  │  sentence-transformers/all-MiniLM-L6-v2 (local)     │    │
│  │  384 dimensions                                      │    │
│  └────────────────────────┬────────────────────────────┘    │
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Vector Database (PGVector)                          │    │
│  │  - Index Method: HNSW                                │    │
│  │  - Hybrid Search: Enabled                            │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Cấu Hình RAG (docker-compose.yml)

```yaml
environment:
  # Vector Database
  - VECTOR_DB=pgvector
  - PGVECTOR_DB_URL=postgresql://user:pass@postgres:5432/openwebui
  - PGVECTOR_CREATE_EXTENSION=true
  - PGVECTOR_INDEX_METHOD=hnsw

  # Embeddings
  - RAG_EMBEDDING_ENGINE=
  - RAG_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

  # Chunking
  - ENABLE_RAG=true
  - CHUNK_SIZE=1000
  - CHUNK_OVERLAP=200
  - RAG_TEXT_SPLITTER=character
  - ENABLE_RAG_HYBRID_SEARCH=true

  # Limits (TÙY CHỈNH ĐƯỢC)
  - RAG_FILE_MAX_SIZE=10       # MB, mặc định unlimited, có thể tăng/giảm
  - RAG_FILE_MAX_COUNT=10      # Số file/collection, có thể tăng/giảm
```

> **📝 Lưu ý**: Các giới hạn RAG đều có thể tùy chỉnh:
> - **Qua Environment Variables**: Sửa trong `docker-compose.yml`
> - **Qua Admin Panel**: `Settings > Documents > General > Max Upload Size`
> - Mặc định `RAG_FILE_MAX_SIZE` là **Unlimited** nếu không set

### 4.3 Quy Trình Sử Dụng RAG

1. **Tạo Knowledge Base**
   - Truy cập: `/workspace/knowledge`
   - Click "Create Knowledge Base"
   - Đặt tên và mô tả

2. **Upload Documents**
   - Hỗ trợ: PDF, TXT, DOCX, MD, CSV, XLSX, JSON, HTML, XML
   - Giới hạn mặc định: **Unlimited** (có thể set qua `RAG_FILE_MAX_SIZE`)
   - Cấu hình qua Admin Panel hoặc env variables

3. **Query với Context**
   - Chọn Knowledge Base trong chat
   - Gửi câu hỏi
   - AI trả lời dựa trên nội dung documents

### 4.4 Database Schema cho RAG

```sql
-- Documents table
document {
    id: UUID
    collection_id: UUID (FK)
    filename: String
    content: Text
    metadata: JSONB
    created_at: Timestamp
}

-- Vector embeddings
document_chunk {
    id: UUID
    document_id: UUID (FK)
    chunk_text: Text
    embedding: vector(384)  -- PGVector type
    chunk_index: Integer
}

-- Collections/Knowledge Bases
knowledge {
    id: UUID
    name: String
    description: Text
    user_id: UUID (FK)
    created_at: Timestamp
}
```

---

## 5. Database & Lưu Trữ

### 5.1 PostgreSQL (Chính)

**Connection:**
```
postgresql://openwebui_user:${POSTGRES_PASSWORD}@postgres:5432/openwebui
```

**Tables Chính:**

| Table | Chức Năng | Dữ Liệu Lưu |
|-------|-----------|-------------|
| **user** | Thông tin users | email, password, role |
| **chat** | Chat history | messages, timestamps |
| **document** | RAG documents | content, metadata |
| **document_chunk** | Vector chunks | embeddings (384-dim) |
| **knowledge** | Knowledge bases | collections |
| **model** | Model configs | settings, preferences |
| **tool** | Custom tools | functions, code |
| **prompt** | Prompt templates | system prompts |

### 5.2 Middleware Tables (MỚI - PostgreSQL)

> **📦 Script khởi tạo**: `scripts/init_middleware_tables.sql`

| Table | Chức Năng | Thay Thế |
|-------|-----------|----------|
| **mw_users** | Middleware users | `users.json` |
| **mw_user_quotas** | Quota limits & usage | `users.json.quota` |
| **mw_request_logs** | Chi tiết mỗi request | `middleware.log` |
| **mw_daily_usage** | Tổng hợp usage/ngày | (mới) |
| **mw_model_prices** | Bảng giá models | `prices.json` |
| **mw_pending_requests** | Streaming pending | `pending.csv` |

**Cấu trúc `mw_request_logs`:**
```sql
CREATE TABLE mw_request_logs (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(100),       -- mw_uuid
    user_id VARCHAR(100),
    endpoint VARCHAR(100),         -- /v1/chat/completions...
    model VARCHAR(100),
    status_code INTEGER,
    latency_ms NUMERIC(12,2),
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    cost_usd NUMERIC(12,6),
    cost_source VARCHAR(20),       -- 'litellm_header' | 'fallback'
    is_streaming BOOLEAN,
    created_at TIMESTAMP
);
```

**Views cho Dashboard:**
- `vw_user_usage_summary` - Tổng hợp quota/usage per user
- `vw_recent_requests` - Requests trong 24h
- `vw_weekly_usage` - Usage 7 ngày gần nhất

> **Lưu ý**: Hiện tại middleware vẫn dùng JSON files. Sau khi apply SQL script, sẽ chuyển sang dùng DB và bỏ JSON dần

### 5.2 PGVector Extension

```sql
-- Enable extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create HNSW index for fast similarity search
CREATE INDEX ON document_chunk 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

### 5.3 JSON Files (Middleware)

| File | Chức Năng |
|------|-----------|
| `users.json` | User credentials, quotas, usage |
| `prices.json` | Fallback pricing for cost calculation |
| `pending.csv` | Pending requests for reconciliation |

### 5.4 Logs

| Log File | Chức Năng | Rotation |
|----------|-----------|----------|
| `logs/middleware.log` | API requests, latency | 5MB x 5 files |
| `litellm/litellm.log` | LLM calls, responses | Configurable |

---

## 6. Hệ Thống Quota & Chi Phí

### 6.1 Loại Quota

| Quota Type | Đơn Vị | Áp Dụng Cho |
|------------|--------|-------------|
| **limit_tokens** | Tokens | Chat completions |
| **limit_cost_usd** | USD | Tất cả requests |
| **limit_image_requests** | Số ảnh | Image generation |
| **limit_tts_requests** | Số requests | Text-to-Speech |
| **limit_tts_chars** | Ký tự | TTS content |
| **limit_stt_requests** | Số requests | Speech-to-Text |
| **limit_video_requests** | Số videos | Video generation |
| **limit_video_seconds** | Giây | Video duration |

### 6.2 Chu Kỳ Reset

- **weekly**: Reset vào 00:00 Thứ Hai (theo timezone)
- **monthly**: Reset vào 00:00 ngày 1 (theo timezone)
- **Timezone mặc định**: `Asia/Bangkok`

### 6.3 Tính Chi Phí

**Ưu tiên:**
1. Header từ LiteLLM: `x-litellm-response-cost`
2. Fallback: `prices.json` với công thức

**Công thức Text/Chat:**
```
cost = (prompt_tokens × input_per_1m / 1,000,000) +
       (completion_tokens × output_per_1m / 1,000,000)
```

**Công thức Image:**
```
cost = per_image_usd[quality][size] × n
```

**Công thức TTS:**
```
cost = len(text) × tts_usd_per_1m_chars / 1,000,000
```

### 6.4 Enforce Quota Flow

```
Request nhận được
    │
    ▼
Check quota (apply=False)
    │
    ├─ Exceeded? → Return 429 Too Many Requests
    │
    ▼
Forward to LiteLLM
    │
    ├─ Failed? → Return error (không bump usage)
    │
    ▼
Success → Bump usage (apply=True)
    │
    ▼
Return response to client
```

---

## 7. API Endpoints

### 7.1 Middleware Endpoints

#### Public Endpoints (Cần subkey)

| Method | Endpoint | Chức Năng |
|--------|----------|-----------|
| GET | `/health` | Health check |
| GET | `/v1/models` | Danh sách models |
| POST | `/v1/chat/completions` | Chat (stream/non-stream) |
| POST | `/v1/images/generations` | Tạo ảnh |
| POST | `/v1/audio/speech` | Text-to-Speech |
| POST | `/v1/audio/transcriptions` | Speech-to-Text |
| POST | `/v1/video/generations` | Tạo video |

#### Admin Endpoints (Cần admin_key)

| Method | Endpoint | Chức Năng |
|--------|----------|-----------|
| GET | `/admin/usage` | Xem usage stats |
| POST | `/admin/reset` | Reset quota |
| POST | `/admin/reconcile` | Sync với LiteLLM logs |

### 7.2 Request/Response Formats

**Chat Completion Request:**
```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  "stream": false,
  "temperature": 0.7,
  "max_tokens": 1000
}
```

**Chat Completion Response:**
```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "model": "gpt-4o-mini",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Hello! How can I help you today?"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 10,
    "total_tokens": 30
  },
  "_mw_cost_usd": 0.0000045,
  "_mw_request_id": "mw_abc123"
}
```

### 7.3 Multimodal API Examples

#### Image Generation

**Request:**
```json
POST /v1/images/generations
Authorization: Bearer <subkey>

{
  "model": "gpt-image-1",
  "prompt": "A beautiful sunset over the ocean with sailboats",
  "n": 1,
  "size": "1024x1024",
  "quality": "medium"
}
```

**Response:**
```json
{
  "created": 1707150000,
  "data": [{
    "url": "https://oaidalleapiprodscus.blob.core.windows.net/...",
    "revised_prompt": "A stunning sunset over a calm ocean..."
  }],
  "_mw_user": "admin",
  "_mw_request_id": "mw_img123",
  "_mw_added_cost_usd": 0.042
}
```

#### Text-to-Speech (TTS)

**Request:**
```json
POST /v1/audio/speech
Authorization: Bearer <subkey>

{
  "model": "gpt-4o-mini-tts",
  "input": "Hello, this is a test message for text-to-speech.",
  "voice": "alloy",
  "response_format": "mp3"
}
```

**Response:** Binary audio data (MP3/WAV)

#### Speech-to-Text (STT)

**Request (multipart/form-data):**
```
POST /v1/audio/transcriptions
Authorization: Bearer <subkey>
Content-Type: multipart/form-data

file: audio.mp3
model: gpt-4o-transcribe
language: en
```

**Response:**
```json
{
  "text": "Hello, this is the transcribed text.",
  "_mw_user": "admin",
  "_mw_request_id": "mw_stt123"
}
```

#### Video Generation

**Request:**
```json
POST /v1/video/generations
Authorization: Bearer <subkey>

{
  "model": "sora-2",
  "prompt": "A cat walking gracefully on a sunny beach",
  "duration": 5,
  "size": "1024x576"
}
```

**Response:**
```json
{
  "created": 1707150000,
  "data": [{
    "url": "https://video-url..."
  }],
  "_mw_user": "admin",
  "_mw_added_cost_usd": 0.50
}
```

---

## 8. Bảo Mật & Xác Thực

### 8.1 Layers Xác Thực

```
┌─────────────────────────────────────────────┐
│ Layer 1: Open WebUI                          │
│ - Email + Password                           │
│ - Session-based auth                         │
│ - WEBUI_SECRET_KEY for JWT                   │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│ Layer 2: Middleware                          │
│ - Subkey (API key per user)                  │
│ - Admin key for management APIs              │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│ Layer 3: LiteLLM                             │
│ - Master key (single key)                    │
│ - Only Middleware can access                 │
└─────────────────────────────────────────────┘
```

### 8.2 Environment Variables

| Variable | Mô Tả | Ví Dụ |
|----------|-------|-------|
| `WEBUI_SECRET_KEY` | JWT signing key | `random_32_chars` |
| `LITELLM_KEY` | LiteLLM master key | `super_admin_key_123` |
| `ADMIN_KEY` | Middleware admin key | `mw_admin_xxx` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-xxx` |
| `GEMINI_API_KEY` | Google API key | `AIzaxxx` |
| `POSTGRES_PASSWORD` | DB password | `changeme123` |

### 8.3 Network Security

```
┌─────────────────────────────────────────────┐
│ Docker Network: openwebui-network (bridge)   │
│                                              │
│  ┌──────────────────┐  ┌──────────────────┐ │
│  │ open-webui:8080  │  │ postgres:5432    │ │
│  │ (exposes 3000)   │  │ (exposes 5432)   │ │
│  └──────────────────┘  └──────────────────┘ │
│                                              │
│  ┌──────────────────┐  ┌──────────────────┐ │
│  │ middleware:5000  │  │ litellm:4000     │ │
│  │ (exposes 5000)   │  │ (exposes 4000)   │ │
│  └──────────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────┘
```

---

## 9. Vận Hành & Giám Sát

### 9.1 Scripts Quản Lý

| Script | Chức Năng |
|--------|-----------|
| `scripts/start_all.ps1` | Khởi động stack |
| `scripts/stop_all.ps1` | Dừng stack |
| `scripts/restart_all.ps1` | Restart stack |
| `scripts/logs.ps1` | Xem logs |
| `scripts/migrate_sqlite_to_postgres.py` | Migration DB |
| `scripts/verify_migration.py` | Kiểm tra migration |

### 9.2 Health Checks

```powershell
# Check all services
docker ps --format "table {{.Names}}\t{{.Status}}"

# Individual health checks
curl http://localhost:3000/health    # Open WebUI
curl http://localhost:4000/health    # LiteLLM
curl http://localhost:5000/health    # Middleware
docker exec openwebui-postgres pg_isready
```

### 9.3 Monitoring Metrics

**Middleware Logs:**
```
2026-02-05 10:30:15 INFO rid=mw_abc123 method=POST path=/v1/chat/completions latency_ms=1234 status=200
```

**Key Metrics:**
- Request latency (ms)
- Success/Error rate
- Token usage per user
- Cost per user
- Active streams

### 9.4 Troubleshooting

| Vấn Đề | Giải Pháp |
|--------|-----------|
| Container không start | `docker-compose logs [service]` |
| 401 Unauthorized | Kiểm tra subkey trong users.json |
| 429 Too Many Requests | Quota exceeded, cần reset |
| 500 Internal Error | Kiểm tra middleware logs |
| Streaming bị đứng | Kiểm tra network, restart middleware |

### 9.5 Dashboard & Analytics

#### 9.5.1 Open WebUI Admin Panel

Truy cập: **http://localhost:3000/admin**

| Tab | Chức Năng |
|-----|-----------|
| **Dashboard** | Tổng quan hệ thống |
| **Users** | Quản lý người dùng, active users |
| **Settings** | Cấu hình connections, models |
| **Documents** | RAG settings, file limits |
| **Models** | Model preferences, defaults |
| **Workspace** | Knowledge bases, tools |

#### 9.5.2 Middleware Usage API

```bash
# Xem usage tất cả users
curl -H "Authorization: Bearer $ADMIN_KEY" \
  http://localhost:5000/admin/usage
```

**Response:**
```json
[
  {
    "user_id": "admin",
    "used_tokens": 1217,
    "used_cost_usd": 0.0078825,
    "used_image_requests": 0,
    "quota": {...}
  }
]
```

#### 9.5.3 Database Views (Khi dùng PostgreSQL)

```sql
-- Xem tổng hợp usage per user
SELECT * FROM vw_user_usage_summary;

-- Xem requests trong 24h
SELECT * FROM vw_recent_requests LIMIT 20;

-- Xem trend 7 ngày
SELECT * FROM vw_weekly_usage;
```

#### 9.5.4 OpenTelemetry Integration (Tùy chọn)

Open WebUI hỗ trợ distributed tracing qua OpenTelemetry:

```yaml
environment:
  - OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
  - OTEL_SERVICE_NAME=openwebui
```

Integration với:
- Grafana LGTM (Loki, Grafana, Tempo, Mimir)
- Jaeger/Tempo cho tracing
- Prometheus cho metrics

---

## 📊 Tóm Tắt Tính Năng

### ✅ Đã Triển Khai
- [x] Chat UI đa phương thức
- [x] 21 models (OpenAI + Gemini)
- [x] User authentication (2 tầng)
- [x] Quota & cost tracking
- [x] RAG với PGVector
- [x] Image/TTS/STT/Video generation
- [x] Admin management APIs
- [x] Docker deployment
- [x] Playwright test suite (14 tests)

### 🔜 Có Thể Mở Rộng
- [ ] Multi-tenant với phân quyền
- [ ] Prometheus metrics
- [ ] OpenTelemetry tracing
- [ ] SSO integration
- [ ] Custom model fine-tuning
- [ ] Billing integration
