# Database Architecture - Chi tiết kỹ thuật

> **Database**: PostgreSQL 16 + PGVector 0.8.0  
> **Cập nhật**: 2026-03-03  
> **Docker Image**: `pgvector/pgvector:0.8.0-pg16`

---

## 1. Tổng quan

Hệ thống sử dụng PostgreSQL 16 làm database chính, tích hợp PGVector extension cho vector storage (phục vụ RAG).

**2 databases:**
- `openwebui` — Lưu toàn bộ data của Open WebUI (users, chats, knowledge, embeddings, settings) — 32 tables
- `middleware` — Lưu data của LLM Middleware (users, prices, audit logs, request logs) — 6 tables

### 1.1. Kết nối

```
Connection String: postgresql://openwebui_user:<password>@postgres:5432/openwebui
Port exposed:     5432 (localhost)
Docker container: openwebui-postgres
Volume:           postgres_data (persistent)
```

### 1.2. Extensions

| Extension           | Version | Mục đích                         |
| ------------------- | ------- | -------------------------------- |
| `vector` (PGVector) | 0.8.0   | Vector similarity search cho RAG |
| `plpgsql`           | 1.0     | Procedural language (built-in)   |

---

## 2. Database `openwebui` — Open WebUI Schema (32 tables)

### 2.1. Sơ đồ quan hệ tổng quát

```
┌─────────┐     ┌──────────┐     ┌────────────┐
│  user   │────▶│   chat   │────▶│  chat_file  │
│         │     │          │     │  (chat_id,  │
│         │     │          │     │   file_id)  │
│         │     └────┬─────┘     └──────┬──────┘
│         │          │                   │
│         │          ▼                   ▼
│         │     ┌──────────┐      ┌──────────┐
│         │     │ chatidtag│      │   file   │
│         │     │ (chat_id,│      │          │◀──────┐
│         │     │  tag_id) │      └──────────┘       │
│         │     └──────────┘                         │
│         │                                          │
│         │     ┌──────────┐     ┌────────────────┐  │
│         │────▶│knowledge │────▶│ knowledge_file │──┘
│         │     │          │     │ (knowledge_id, │
│         │     │          │     │  file_id)      │
│         │     └──────────┘     └────────────────┘
│         │
│         │     ┌──────────┐     ┌────────────────┐
│         │────▶│ channel  │────▶│ channel_member │
│         │     │          │     │ channel_file   │
│         │     │          │     │ channel_webhook│
│         │     └──────────┘     └────────────────┘
│         │
│         │     ┌──────────┐     ┌────────────────┐
│         │────▶│  group   │────▶│ group_member   │
│         │     └──────────┘     └────────────────┘
│         │
│         │     ┌──────────┐
│         │────▶│  memory  │  (user personal memory)
│         │     └──────────┘
│         │
│         │     ┌──────────┐
│         │────▶│  folder  │  (chat organization)
│         │     └──────────┘
└─────────┘

Standalone tables:
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  model   │  │   tool   │  │ function │  │  prompt  │
└──────────┘  └──────────┘  └──────────┘  └──────────┘

┌──────────┐  ┌──────────────┐  ┌──────────────┐
│  config  │  │   document   │  │document_chunk│
└──────────┘  └──────────────┘  │  (VECTORS)   │
                                └──────────────┘

┌──────────────┐  ┌──────────────┐  ┌─────────────────┐
│   message    │  │message_react │  │  oauth_session  │
└──────────────┘  └──────────────┘  └─────────────────┘

┌──────────────┐  ┌──────────────┐  ┌──────────┐
│   api_key    │  │    auth      │  │   note   │
└──────────────┘  └──────────────┘  └──────────┘

┌──────────────┐  ┌──────────────┐
│   feedback   │  │alembic_version│ (migration tracking)
└──────────────┘  └──────────────┘

┌──────────────┐
│   tag        │
└──────────────┘
```

---

## 3. Chi tiết các Table quan trọng

### 3.1. `user` - Người dùng

```sql
Table "public.user"
     Column       |          Type          | Nullable
------------------+------------------------+----------
 id               | character varying(255) | NOT NULL  -- UUID
 name             | character varying(255) | NOT NULL  -- Display name
 email            | character varying(255) | NOT NULL  -- Email unique
 role             | character varying(50)  |           -- "admin", "user", "pending"
 profile_image_url| character varying(255) |           -- Avatar URL
 last_active_at   | bigint                 | NOT NULL  -- Unix timestamp
 created_at       | bigint                 | NOT NULL
 updated_at       | bigint                 | NOT NULL
 api_key          | character varying(255) |           -- Personal API key
 settings         | text                   |           -- JSON: UI preferences, default model
 info             | text                   |           -- JSON: additional info
 oauth_sub        | character varying(255) |           -- OAuth subject ID

Primary Key: pk_user_id (id)
Referenced by: chat, file, knowledge, memory, message, group_member, oauth_session, ...
```

### 3.2. `auth` - Xác thực

```sql
Table "public.auth"
  Column   |  Type  | Nullable
-----------+--------+----------
 id        | text   | NOT NULL  -- Same as user_id
 email     | text   | NOT NULL
 password  | text   | NOT NULL  -- Hashed password (bcrypt)
 active    | boolean| NOT NULL  -- Account active?

Primary Key: btree (id)
```

### 3.3. `chat` - Hội thoại

```sql
Table "public.chat"
   Column   |          Type          | Nullable
------------+------------------------+----------
 id         | character varying(255) | NOT NULL  -- UUID
 user_id    | character varying(255) | NOT NULL  -- FK → user
 title      | text                   |           -- Chat title
 chat       | text                   |           -- JSON: TOÀN BỘ messages, model info
 created_at | bigint                 | NOT NULL
 updated_at | bigint                 |
 share_id   | character varying(255) |           -- Shared chat ID (public link)
 archived   | boolean                |           -- Đã archive?
 pinned     | boolean                |           -- Đã pin?
 meta       | text                   |           -- JSON: tags, metadata
 folder_id  | text                   |           -- FK → folder

Indexes:
  PRIMARY KEY: btree (id)
  user_id_archived_idx: btree (user_id) WHERE archived = true
  user_id_pinned_idx: btree (user_id) WHERE pinned = true

Referenced by: chat_file, chatidtag
```

> **Lưu ý**: Column `chat` lưu TOÀN BỘ messages dạng JSON. Đây là thiết kế "document-style" trong relational DB. Mỗi lần user gửi message, toàn bộ JSON được update.

### 3.4. `document_chunk` - Vector Embeddings ⭐

```sql
Table "public.document_chunk"
     Column      |     Type     | Nullable
-----------------+--------------+----------
 id              | text         | NOT NULL  -- UUID
 vector          | vector(1536) |           -- Embedding vector
 collection_name | text         | NOT NULL  -- Thuộc collection nào
 text            | text         |           -- Nội dung text gốc
 vmetadata       | jsonb        |           -- Metadata (source, page, chunk_index)

Indexes:
  PRIMARY KEY: btree (id)
  idx_document_chunk_collection_name: btree (collection_name)
  idx_document_chunk_vector: hnsw (vector vector_cosine_ops)
    WITH (m='16', ef_construction='64')
```

**Đây là table quan trọng nhất cho RAG.** Mỗi row = 1 text chunk + vector embedding.

> ℹ️ **Embedding model**: `gemini-embedding-001` (native 3072-dim, giảm xuống 1536 qua middleware `dimensions` param). PGVector HNSW hỗ trợ tối đa 2000 dims.

#### vmetadata example:
```json
{
  "source": "HR_Policy.pdf",
  "page": 5,
  "chunk_index": 12,
  "collection_name": "knowledge-bases",
  "total_chunks": 50
}
```

#### Vector search query:
```sql
-- Tìm 4 chunks tương tự nhất với query embedding
SELECT id, text, vmetadata,
       1 - (vector <=> '[0.1, 0.2, ..., 0.5]'::vector) AS similarity
FROM document_chunk
WHERE collection_name = 'my-knowledge'
ORDER BY vector <=> '[0.1, 0.2, ..., 0.5]'::vector
LIMIT 4;
```

### 3.5. `knowledge` - Knowledge Collections

```sql
Table "public.knowledge"
     Column     |  Type  | Nullable
----------------+--------+----------
 id             | text   | NOT NULL  -- UUID
 user_id        | text   | NOT NULL  -- Owner
 name           | text   | NOT NULL  -- "Tài liệu nội bộ"
 description    | text   |           -- Mô tả
 meta           | json   |           -- Additional metadata
 created_at     | bigint | NOT NULL
 updated_at     | bigint |
 access_control | json   |           -- Who can access
 data           | json   |           -- Configuration data

Referenced by: knowledge_file (ON DELETE CASCADE)
```

### 3.6. `knowledge_file` - Liên kết Knowledge ↔ File

```sql
Table "public.knowledge_file"
    Column    |  Type  | Nullable
--------------+--------+----------
 id           | text   | NOT NULL
 user_id      | text   | NOT NULL
 knowledge_id | text   | NOT NULL  -- FK → knowledge (CASCADE DELETE)
 file_id      | text   | NOT NULL  -- FK → file (CASCADE DELETE)
 created_at   | bigint | NOT NULL
 updated_at   | bigint | NOT NULL

Unique: (knowledge_id, file_id)  -- 1 file chỉ thuộc 1 knowledge 1 lần
```

### 3.7. `file` - File uploads

```sql
Table "public.file"
    Column     |  Type  | Nullable
---------------+--------+----------
 id            | text   | NOT NULL  -- UUID
 user_id       | text   | NOT NULL
 filename      | text   |           -- Original filename
 meta          | json   |           -- Size, mime type, etc.
 created_at    | bigint | NOT NULL
 updated_at    | bigint |
 hash          | text   |           -- File content hash (dedup)
 path          | text   |           -- Storage path
 access_control| json   |

Referenced by: chat_file, knowledge_file, channel_file
```

### 3.8. `document` - Document metadata

```sql
Table "public.document"
     Column      |          Type          | Nullable
-----------------+------------------------+----------
 id              | integer (SERIAL)       | NOT NULL
 collection_name | varchar(255)           | NOT NULL  -- UNIQUE
 name            | varchar(255)           | NOT NULL  -- UNIQUE
 title           | text                   | NOT NULL
 filename        | text                   | NOT NULL
 content         | text                   |           -- Extracted text (full)
 user_id         | varchar(255)           | NOT NULL
 timestamp       | bigint                 | NOT NULL
```

### 3.9. `chat_file` - Files trong Chat

```sql
Table "public.chat_file"
   Column   |  Type  | Nullable
------------+--------+----------
 id         | text   | NOT NULL
 user_id    | text   | NOT NULL
 chat_id    | text   | NOT NULL  -- FK → chat (CASCADE)
 file_id    | text   | NOT NULL  -- FK → file (CASCADE)
 message_id | text   |           -- Thuộc message nào
 created_at | bigint | NOT NULL
 updated_at | bigint | NOT NULL

Unique: (chat_id, file_id)
```

### 3.10. `memory` - User Memory

```sql
Table "public.memory"
   Column   |          Type          | Nullable
------------+------------------------+----------
 id         | varchar(255)           | NOT NULL
 user_id    | varchar(255)           | NOT NULL
 content    | text                   | NOT NULL  -- Memory content
 updated_at | bigint                 | NOT NULL
 created_at | bigint                 | NOT NULL
```

Open WebUI lưu "memory" - thông tin mà LLM cần nhớ về user (VD: user thích code Python, user là developer, etc.)

### 3.11. `model` - Model Configuration

```sql
Table "public.model"
     Column     |  Type   | Nullable | Default
----------------+---------+----------+---------
 id             | text    | NOT NULL |         -- Model ID
 user_id        | text    | NOT NULL |         -- Creator
 base_model_id  | text    |          |         -- Base model
 name           | text    | NOT NULL |         -- Display name
 meta           | text    | NOT NULL |         -- JSON: capabilities, tags
 params         | text    | NOT NULL |         -- JSON: temperature, top_p, etc.
 created_at     | bigint  | NOT NULL |
 updated_at     | bigint  | NOT NULL |
 access_control | json    |          |         -- Who can use
 is_active      | boolean | NOT NULL | true    -- Enabled?
```

### 3.12. `message` - Channel Messages

```sql
Table "public.message"
   Column    |  Type   | Nullable | Default
-------------+---------+----------+---------
 id          | text    | NOT NULL |         -- UUID
 user_id     | text    |          |
 channel_id  | text    |          |         -- Thuộc channel nào
 content     | text    |          |         -- Message content
 data        | json    |          |         -- Attachments, media
 meta        | json    |          |         -- Metadata
 created_at  | bigint  |          |
 updated_at  | bigint  |          |
 parent_id   | text    |          |         -- Thread parent
 reply_to_id | text    |          |         -- Reply to message
 is_pinned   | boolean | NOT NULL | false
 pinned_at   | bigint  |          |
 pinned_by   | text    |          |

Referenced by: channel_file
```

### 3.13. Các table phụ trợ

| Table                                                             | Mục đích                      |
| ----------------------------------------------------------------- | ----------------------------- |
| `api_key`                                                         | API keys cho external access  |
| `config`                                                          | System configuration (JSON)   |
| `feedback`                                                        | User feedback trên responses  |
| `folder`                                                          | Chat folder organization      |
| `function`                                                        | Custom Python functions       |
| `group` + `group_member`                                          | User groups                   |
| `channel` + `channel_member` + `channel_webhook` + `channel_file` | Channels (team chat)          |
| `chatidtag` + `tag`                                               | Chat tagging system           |
| `message_reaction`                                                | Reactions trên messages       |
| `note`                                                            | User notes                    |
| `oauth_session`                                                   | OAuth login sessions          |
| `prompt`                                                          | Saved prompt templates        |
| `tool`                                                            | Custom tools                  |
| `alembic_version`                                                 | DB migration version tracking |
| `migratehistory`                                                  | Migration history             |

---

## 3b. Database `middleware` — Middleware Schema (6 tables)

Middleware sử dụng database riêng `middleware` trên cùng PostgreSQL instance.

**Connection:** `postgresql://openwebui_user:<password>@postgres:5432/middleware`

### `mw_users` — Middleware users (quota, subkeys)

```sql
Table "public.mw_users"
    Column    |  Type  | Nullable
--------------+--------+----------
 user_id       | text   | NOT NULL  -- PRIMARY KEY
 data          | jsonb  | NOT NULL  -- Full user JSON (subkey, quota, allowed_models, etc.)
 updated_at    | timestamptz | DEFAULT now()
```

### `mw_prices` — Model pricing

```sql
Table "public.mw_prices"
    Column    |  Type  | Nullable
--------------+--------+----------
 model         | text   | NOT NULL  -- PRIMARY KEY (model ID)
 data          | jsonb  | NOT NULL  -- Price JSON (input/output per token)
 updated_at    | timestamptz | DEFAULT now()
```

### `mw_config` — Configuration (alerts, system alerts)

```sql
Table "public.mw_config"
    Column    |  Type  | Nullable
--------------+--------+----------
 key           | text   | NOT NULL  -- PRIMARY KEY ('alert_config', 'system_alerts')
 value         | jsonb  | NOT NULL  -- Config JSON
 updated_at    | timestamptz | DEFAULT now()
```

### `mw_pending` — In-flight request tracking

```sql
Table "public.mw_pending"
    Column    |  Type  | Nullable
--------------+--------+----------
 rid           | text   | NOT NULL  -- PRIMARY KEY (request ID)
 data          | jsonb  | NOT NULL  -- Request metadata
 created_at    | timestamptz | DEFAULT now()
```

### `mw_audit_log` — Structured audit events ⭐

```sql
Table "public.mw_audit_log"
      Column      |     Type        | Nullable
------------------+-----------------+----------
 id                | SERIAL          | NOT NULL  -- PRIMARY KEY (auto-increment)
 ts                | timestamptz     |           -- Event timestamp
 rid               | text            |           -- Request ID
 user_id           | text            |           -- User who made the request
 endpoint          | text            |           -- API endpoint
 model             | text            |           -- Model used
 purpose           | text            |           -- Request purpose
 status            | text            |           -- ok, error, pending, reconciled
 status_code       | integer         |           -- HTTP status code
 latency_ms        | real            |           -- Response time
 tokens_in         | integer         |           -- Input tokens
 tokens_out        | integer         |           -- Output tokens
 tokens_total      | integer         |           -- Total tokens
 cost_usd          | numeric(12,8)   |           -- Cost in USD
 image_count       | integer         |
 tts_chars         | integer         |
 stt_seconds       | real            |
 video_count       | integer         |
 error_type        | text            |
 error_message     | text            |

Indexes:
  idx_mw_audit_ts: btree (ts)
  idx_mw_audit_user: btree (user_id)
  idx_mw_audit_rid: btree (rid)
```

Đây là table quan trọng nhất của middleware — lưu toàn bộ lịch sử sử dụng AI (chat, image, audio, video). Dashboard query trực tiếp table này.

### `mw_request_log` — HTTP request logs

```sql
Table "public.mw_request_log"
    Column    |     Type        | Nullable
--------------+-----------------+----------
 id            | SERIAL          | NOT NULL  -- PRIMARY KEY
 ts            | timestamptz     |           -- Request timestamp
 payload       | jsonb           |           -- Full request/response metadata

Indexes:
  idx_mw_reqlog_ts: btree (ts)
```

### Kiến trúc dual-write

```
Middleware Code
    │
    ├─── Write to PostgreSQL (primary)
    │       mw_users, mw_prices, mw_config,
    │       mw_audit_log, mw_request_log
    │
    └─── Write to Files (backup)
            users.json, prices.json,
            audit.jsonl, middleware.requests.log

API Queries
    │
    ├─── Try PostgreSQL first
    │
    └─── Fallback to files if DB unavailable
```

---

## 4. Indexes (65 indexes)

### 4.1. Primary Keys & Unique Indexes

Mỗi table đều có Primary Key (btree). Các unique indexes quan trọng:
- `document_collection_name` UNIQUE on `document(collection_name)`
- `document_name` UNIQUE on `document(name)`
- `uq_knowledge_file_knowledge_file` UNIQUE on `(knowledge_id, file_id)`
- `uq_chat_file_chat_file` UNIQUE on `(chat_id, file_id)`

### 4.2. Performance Indexes

```sql
-- Chat queries nhanh theo user
user_id_archived_idx: btree (user_id) WHERE archived = true
user_id_pinned_idx: btree (user_id) WHERE pinned = true

-- Vector similarity search (HNSW)
idx_document_chunk_vector: hnsw (vector vector_cosine_ops)
  WITH (m='16', ef_construction='64')

-- Collection lookup
idx_document_chunk_collection_name: btree (collection_name)

-- Foreign key lookups
ix_knowledge_file_knowledge_id, ix_knowledge_file_file_id
ix_chat_file_chat_id, ix_chat_file_file_id
```

---

## 5. Data Size & Statistics (Hiện tại)

| Metric                      | Giá trị                                 |
| --------------------------- | --------------------------------------- |
| Tổng tables (openwebui DB)  | 32                                      |
| Tổng tables (middleware DB) | 6                                       |
| Tổng indexes                | 65+                                     |
| DB Extensions               | vector (pgvector 0.8.0)                 |
| Document chunks             | 1 chunk (collection: "knowledge-bases") |
| document_chunk table size   | ~80 KB                                  |
| Index method                | HNSW (cosine similarity)                |

---

## 6. Scaling & Performance

### 6.1. PGVector Performance Benchmarks

| Số vectors | HNSW Index Build | Search Latency | RAM Usage |
| ---------- | ---------------- | -------------- | --------- |
| 1,000      | < 1 giây         | < 1ms          | ~6 MB     |
| 10,000     | ~5 giây          | < 5ms          | ~60 MB    |
| 100,000    | ~1 phút          | < 10ms         | ~600 MB   |
| 1,000,000  | ~10 phút         | < 50ms         | ~6 GB     |
| 10,000,000 | ~2 giờ           | < 100ms        | ~60 GB    |

> Với vector(1536) (Gemini embedding-001, giảm từ 3072 native): mỗi vector = 1536 × 4 bytes = 6.14 KB raw data

### 6.2. Tối ưu hóa

```sql
-- Tăng ef_search cho recall tốt hơn (default: 40)
SET hnsw.ef_search = 100;

-- Tăng work_mem chồ sơrts lớn
SET work_mem = '256MB';

-- Parallel queries
SET max_parallel_workers_per_gather = 4;
```

### 6.3. Giới hạn

| Giới hạn              | Giá trị                     |
| --------------------- | --------------------------- |
| Max vector dimensions | 16,000 (PGVector limit)     |
| Max rows/table        | ~2 tỷ (PostgreSQL limit)    |
| Max database size     | Unlimited (disk-limited)    |
| Max connections       | 100 (default, configurable) |
| Docker volume         | Unlimited (disk-limited)    |

---

## 7. Backup & Recovery

### 7.1. Backup

```bash
# Full database dump
docker exec openwebui-postgres pg_dump -U openwebui_user -d openwebui > backup.sql

# Custom format (parallel restore support)
docker exec openwebui-postgres pg_dump -U openwebui_user -d openwebui -Fc > backup.dump

# Only specific tables
docker exec openwebui-postgres pg_dump -U openwebui_user -d openwebui \
  -t document_chunk -t knowledge -t knowledge_file > rag_backup.sql
```

### 7.2. Restore

```bash
# Full restore
cat backup.sql | docker exec -i openwebui-postgres psql -U openwebui_user -d openwebui

# Custom format
docker exec -i openwebui-postgres pg_restore -U openwebui_user -d openwebui < backup.dump
```

### 7.3. Volume Backup

```bash
# Stop containers first
docker compose down

# Backup postgres volume
docker run --rm -v oppen_web_ui_postgres_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres_volume.tar.gz /data

# Backup openwebui data volume
docker run --rm -v oppen_web_ui_openwebui_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/openwebui_data.tar.gz /data
```

---

## 8. Hiện trạng & Kế hoạch

### 8.1. Đang có (Hiện tại)

| Feature                        | Status    |
| ------------------------------ | --------- |
| PostgreSQL 16 + PGVector 0.8.0 | ✅ Active |
| HNSW vector index              | ✅ Active |
| Knowledge Collections          | ✅ Active |
| File uploads (PDF, DOCX, TXT)  | ✅ Active |
| Hybrid Search (BM25 + Vector)  | ✅ Active |
| User authentication            | ✅ Active |
| Chat history persistence       | ✅ Active |
| User memory                    | ✅ Active |
| Channels (team chat)           | ✅ Active |
| Persistent Docker volumes      | ✅ Active |

### 8.2. Đã cấu hình nhưng chưa tận dụng

| Feature                  | Status       | Ghi chú                         |
| ------------------------ | ------------ | ------------------------------- |
| Groups & Access Control  | ⚠️ Chưa dùng | Tables có nhưng chưa tạo groups |
| Custom Functions & Tools | ⚠️ Chưa dùng | Infrastructure sẵn sàng         |
| Prompt Templates         | ⚠️ Chưa dùng | Table `prompt` trống            |
| Notes                    | ⚠️ Chưa dùng | Table `note` trống              |
| Feedback system          | ⚠️ Chưa dùng | Table `feedback` trống          |

### 8.3. Có thể nâng cấp (Kế hoạch tương lai)

| Feature                     | Cách làm                                                                    |
| --------------------------- | --------------------------------------------------------------------------- |
| Better Vietnamese support   | Đổi embedding model sang multilingual                                       |
| Larger file uploads         | Tăng `RAG_FILE_MAX_SIZE`                                                    |
| More users                  | Tạo sub-keys và groups                                                      |
| External embedding (OpenAI) | Set `RAG_EMBEDDING_ENGINE=openai`                                           |
| Full-text search (FTS)      | `CREATE INDEX ON document_chunk USING GIN(to_tsvector('vietnamese', text))` |
| Document version control    | Custom tool hoặc function                                                   |
| Scheduled backup            | Cron job + pg_dump                                                          |
| Read replicas               | PostgreSQL streaming replication                                            |
| Connection pooling          | PgBouncer container                                                         |

---

## 9. Docker Volume Layout

```
Docker Volumes:
├── postgres_data          → /var/lib/postgresql/data (PostgreSQL data files)
│   ├── base/              → Database files
│   ├── global/            → Shared catalogs
│   ├── pg_wal/            → Write-ahead logs
│   └── pg_stat/           → Statistics
│
├── openwebui_data         → /app/backend/data (Open WebUI)
│   ├── uploads/           → User uploaded files
│   ├── cache/             → Model cache (embeddings)
│   └── config.json        → Runtime config
│
└── litellm_logs           → /app/logs (LiteLLM)
    └── litellm.log        → API request logs
```

---

## 10. Kết nối giữa các thành phần

```
User Browser (localhost:3000)
        │
        ▼
┌──────────────────────────────────────────────┐
│          Open WebUI (port 8080)              │
│                                              │
│  ┌────────────┐  ┌──────────────────────┐    │
│  │ RAG Engine │  │ Chat Engine           │    │
│  │            │  │                      │    │
│  │ - Extract  │  │ - Messages → JSON    │    │
│  │ - Chunk    │  │ - History in `chat`  │    │
│  │ - Embed    │  │   table              │    │
│  │ - Search   │  │ - Files → `chat_file`│    │
│  └─────┬──────┘  └─────────┬────────────┘    │
│        │                   │                 │
│        ▼                   ▼                 │
│  ┌─────────────────────────────────────┐     │
│  │      PostgreSQL + PGVector          │     │
│  │                                     │     │
│  │  document_chunk ←→ knowledge        │     │
│  │  file ←→ knowledge_file             │     │
│  │  user ←→ chat ←→ chat_file          │     │
│  │  auth, model, config, memory        │     │
│  └─────────────────────────────────────┘     │
│                                              │
│        ▼ (LLM calls)                        │
│  ┌──────────────────────┐                    │
│  │ Middleware (port 5000)│                   │
│  │ - Auth & Quota        │                   │
│  │ - Cost tracking       │                   │
│  └──────────┬───────────┘                    │
│             ▼                                │
│  ┌──────────────────────┐                    │
│  │ LiteLLM (port 4000)  │                   │
│  │ - Model routing       │                   │
│  │ - API key management  │                   │
│  └──────────────────────┘                    │
└──────────────────────────────────────────────┘
```
