# 🔍 Exploration: Nâng cấp Open WebUI Stack → SaaS Platform 200 Users

> **Ngày**: 2026-04-11 | **Cập nhật**: 2026-04-13  
> **Chế độ**: Explore Mode (không implement, chỉ phân tích & đề xuất)  
> **Mục tiêu**: Phân tích gap giữa hiện trạng và nền tảng SaaS cấp ChatGPT/Gemini/Grok/Claude cho 200 người dùng doanh nghiệp

---

## 1. 📊 Hiện Trạng Hệ Thống (Snapshot)

### Kiến trúc đã triển khai

```
NAT: 51122 → 3000
       │
  Nginx :3000 (HTTPS TLS 1.2/1.3, HTTP/2)
       │
  ┌────┴──────────────┐
  │                   │
  Open WebUI :8080    Middleware :5000
  (6 workers, 10GB)   (4 workers, 2GB)
  │                   │
  SearXNG :8080       LiteLLM :4000
  Redis :6379         (4 workers, 4GB)
  Docling :5001       │
  │                   ├─→ OpenAI   (GPT-5, 5.2, 5.4)
  PostgreSQL :5432    ├─→ Gemini   (3.1 Pro, 3.1 FL, 2.5 Flash)
  (8GB, PGVector)     ├─→ xAI      (Grok 4.20, 4.1 Fast/Lite)
                      └─→ Anthropic (Claude Opus/Sonnet 4.6, Haiku 4.5)
```

### Điểm mạnh đã có ✅

| Lĩnh vực | Chi tiết | Trạng thái |
|-----------|----------|:----------:|
| **Hạ tầng** | 8 containers, Docker Compose, resource limits, health checks | ✅ Production |
| **Bảo mật** | HTTPS, internal-only ports, rate limiting, HMAC-SHA256 subkeys | ✅ Solid |
| **AI Models** | 12 chat + 6 image + 1 TTS + 2 STT + 1 embedding = **22 models** | ✅ Đa dạng |
| **RAG** | PGVector, Gemini Embedding 1536d, Hybrid Search (BM25+Vector), Docling OCR | ✅ Functional |
| **Quota** | Cost limit, token limit, image limit per user, period-based reset | ✅ Working |
| **Dashboard** | 4 tabs (Usage, Access, Users, Logs), charts, SSE streaming, notifications | ✅ Functional |
| **Tài liệu** | 17 docs + 116 features checklist + test suite | ✅ Comprehensive |
| **Scale plan** | Phase 1 (done), Phase 2-3 (planned) | ✅ Planned |

### Điểm yếu / Gap so với SaaS ⚠️

| Lĩnh vực | Gap | Mức ảnh hưởng |
|-----------|-----|:-------------:|
| **Performance** | `load_users()` O(N) per request — 4 full-table scans + 800 loop iterations cho 1 chat message (200 users) | 🔴 Critical |
| **RAG** | Dùng character splitter cơ bản, không có reranking, không có multi-modal RAG | 🔴 Critical |
| **Backup & Recovery** | Không có automated backup, không có disaster recovery | 🔴 Critical |
| **DB Coupling** | Dashboard muốn query Open WebUI DB nhưng kiến trúc hiện tại là decoupled — chưa có access strategy | 🟡 High |
| **Dashboard** | Dashboard SPA thuần HTML/JS, chỉ khai thác 2/7 tables MW DB | 🟡 High |
| **User Experience** | Không có onboarding, không có usage dashboard cho end-user | 🟡 High |
| **Monitoring** | Không có Prometheus/Grafana, không có uptime alerting | 🟡 High |
| **SSO/LDAP** | Chưa tích hợp AD nội bộ, cần thiết kế SSO↔MW subkey auth flow | 🟡 High |
| **Rate Limiting** | Chỉ rate limit ở Nginx level (per IP), chưa có per-user rate limit ở MW level | 🟡 Medium |
| **Phân nhóm** | Chưa dùng Group-based quota/permission (table `group` có sẵn) | 🟡 Medium |
| **Compliance** | Chưa có audit trail export, data retention policy | 🟡 Medium |
| **API Integration** | Chưa mở API cho external system (DMS, ERP) | 🟡 Medium |

---

## 2. 🔬 Phân Tích Chi Tiết Từng Nhóm Công Việc

### 2.0. 🚨 Nhóm 0: Performance Debt (PHẢI SỬA TRƯỚC KHI SCALE)

> [!CAUTION]
> **Bottleneck nghiêm trọng**: Mỗi chat request hiện tại gọi `load_users()` **4 lần**, mỗi lần query `SELECT * FROM mw_users` rồi loop toàn bộ O(N) để tìm 1 user. Với 200 users = **800 iterations + 4 DB full-table queries mỗi tin nhắn**.

#### Hiện trạng flow xử lý 1 chat request

```
┌───── 1 CHAT MESSAGE (hiện tại, 200 users) ─────────────┐
│                                                          │
│  1. require_user()           → SELECT * + loop 200 ❌   │
│  2. enforce_and_bump_quota() → SELECT * + loop 200 ❌   │
│  3. _finalize_streaming()    → SELECT * + loop 200 ❌   │
│  4. check_and_send_alerts()  → SELECT * + loop 200 ❌   │
│                                                          │
│  TỔNG: 4 × full-table scan + 4 × O(200) loop           │
│  = ~800 iterations mỗi message                          │
│                                                          │
│  Files ảnh hưởng:                                        │
│  • core/quota.py:82     (load_users → loop)             │
│  • api/chat.py:657      (load_users → loop → save)      │
│  • core/alerting.py:160 (load_users → loop)             │
│  • api/admin.py:23,43   (load_users → loop)             │
│  • user_admin.py        (10 lần load_users)             │
└──────────────────────────────────────────────────────────┘
```

#### Mục tiêu: O(1) per request

```
┌───── SAU KHI SỬA ──────────────────────────────────────┐
│                                                          │
│  1. require_user()    → get_user_by_id(uid) O(1) ✅     │
│  2. enforce_quota()   → UPDATE WHERE user_id=%s O(1) ✅ │
│  3. finalize_stream() → UPDATE WHERE user_id=%s O(1) ✅ │
│  4. check_alerts()    → get_user_by_id(uid) O(1) ✅     │
│                                                          │
│  TỔNG: 4 × indexed query, 0 loops                       │
│  Giảm ~200× overhead cho mỗi request                    │
└──────────────────────────────────────────────────────────┘
```

| # | Việc cần làm | Mô tả | Effort | Impact |
|:-:|-------------|-------|:------:|:------:|
| 1 | **`get_user_by_id()`** | Thay `load_users()` + loop → `SELECT ... WHERE user_id = %s` indexed query | 3-4 ngày | 🔴 Critical |
| 2 | **`update_user_quota()`** | Thay load-all → modify → save-all bằng `UPDATE ... WHERE user_id = %s` atomic query | 2-3 ngày | 🔴 Critical |
| 3 | **Per-user rate limit** | Thêm rate limiting ở MW level (dùng Redis counter per user_id) | 2 ngày | 🟡 High |
| 4 | **Benchmark suite** | Script đo response time với 50/100/200 simulated users | 1 ngày | 🟡 High |

---

### 2.1. 🏗️ Quyết Định Kiến Trúc: Open WebUI DB Access Strategy

> [!IMPORTANT]
> **50% các Dashboard improvements phụ thuộc vào quyết định này.** Middleware hiện tại là **decoupled** — nó KHÔNG có connection pool đến Open WebUI database (chỉ có 1 direct `psycopg2.connect()` trong `alerting.py:464` để lấy email). Cần quyết định trước khi làm Dashboard.

#### Kiến trúc hiện tại (decoupled by design)

```
┌────────────────────────────────────────────────────────────┐
│  Middleware container ──→ middleware DB (mw_*)              │
│    • ThreadedConnectionPool (min=5, max=30)                │
│    • 7 tables: mw_users, mw_audit_log, mw_prices, ...     │
│                                                             │
│  Open WebUI container ──→ openwebui DB                     │
│    • SQLAlchemy ORM + Alembic migrations                   │
│    • 26+ tables: user, chat, file, knowledge, group, ...   │
│                                                             │
│  ❌ KHÔNG CÓ cross-database connection (by design!)        │
│  ⚠️ Ngoại lệ duy nhất: alerting.py line 464               │
│     → psycopg2.connect() trực tiếp, KHÔNG dùng pool       │
└────────────────────────────────────────────────────────────┘
```

#### 3 options

| Option | Mô tả | Ưu | Nhược | Effort |
|--------|-------|-----|-------|:------:|
| **A: Read-only pool** | Thêm 1 connection pool riêng cho OW DB trong MW, chỉ SELECT | Nhanh, trực tiếp | Coupling: OW schema đổi khi upgrade → MW phải cập nhật | 2-3 ngày |
| **B: API Bridge** | OW expose internal REST API → MW gọi API thay vì truy cập DB | Loose coupling, safe | Cần fork/patch Open WebUI thêm endpoint, latency cao hơn | 5-7 ngày |
| **C: Materialized Views** | PostgreSQL materialized views join 2 databases trên cùng server | 1 PostgreSQL instance, query nhanh | Stale data (cần refresh), phức tạp hơn | 3-4 ngày |

> **Khuyến nghị**: **Option A** (read-only pool) cho MVP — nhanh nhất, OW schema ổn định ở các tables chính (`user`, `chat`, `feedback`, `group`). Thêm version check khi startup để cảnh báo nếu OW schema đổi.

---

### 2.2. 🤖 Nhóm 1: Hạ Tầng AI — Nâng Cấp RAG

#### Hiện trạng RAG

```
┌──────────────────────────────────────────────────────────┐
│                    HIỆN TẠI (Basic RAG)                    │
│                                                            │
│  Upload → Docling Extract → Character Split → Embed →      │
│  PGVector Store → Hybrid Search → Inject Prompt → LLM     │
│                                                            │
│  Config hiện tại (docker-compose.yml):                      │
│  • RAG_TEXT_SPLITTER=character  ← cơ bản nhất              │
│  • CHUNK_SIZE=1500                                          │
│  • CHUNK_OVERLAP=100                                        │
│  • ENABLE_RAG_HYBRID_SEARCH=true                           │
│                                                            │
│  ❌ Không Reranking                                        │
│  ❌ Không Query Rewriting                                  │
│  ❌ Không Multi-modal (chỉ text)                           │
│  ❌ Character splitter — chia cứng theo ký tự, không biết  │
│     ranh giới câu/đoạn/ý                                   │
│  ❌ Không Citation verification                             │
│  ❌ Không feedback loop (user vote → improve retrieval)     │
└──────────────────────────────────────────────────────────┘
```

#### Mục tiêu RAG (Advanced)

```
┌──────────────────────────────────────────────────────────────────┐
│                    MỤC TIÊU (Advanced RAG)                        │
│                                                                    │
│  ┌────────────┐   ┌──────────────┐   ┌───────────────┐           │
│  │ Intelligent │   │ Multi-modal  │   │ Semantic      │           │
│  │ Chunking    │   │ Processing   │   │ Chunking      │           │
│  └──────┬──────┘   └──────┬───────┘   └───────┬───────┘           │
│         │                 │                   │                    │
│         ▼                 ▼                   ▼                    │
│  ┌──────────────────────────────────────────────────┐             │
│  │           EMBEDDING (Gemini 1536d)                │             │
│  └──────────────────────┬───────────────────────────┘             │
│                         │                                          │
│                         ▼                                          │
│  ┌──────────────────────────────────────────────────┐             │
│  │           PGVector + Metadata Index               │             │
│  └──────────────────────┬───────────────────────────┘             │
│                         │                                          │
│         ┌───────────────┼───────────────┐                         │
│         ▼               ▼               ▼                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────────┐              │
│  │ Query      │  │ Hybrid     │  │ Multi-Query    │              │
│  │ Rewriting  │  │ Search     │  │ Retrieval      │              │
│  └──────┬─────┘  └─────┬──────┘  └───────┬────────┘              │
│         │              │                 │                         │
│         └──────────────┼─────────────────┘                         │
│                        ▼                                           │
│  ┌──────────────────────────────────────────────────┐             │
│  │           RERANKER (Cross-encoder / LLM-based)    │             │
│  └──────────────────────┬───────────────────────────┘             │
│                         ▼                                          │
│  ┌──────────────────────────────────────────────────┐             │
│  │           CONTEXT COMPRESSION + INJECTION         │             │
│  └──────────────────────────────────────────────────┘             │
└──────────────────────────────────────────────────────────────────┘
```

#### Chi tiết cải thiện RAG

| # | Cải thiện | Mô tả | Độ phức tạp | Impact |
|:-:|-----------|-------|:-----------:|:------:|
| 1a | **Recursive Splitter** (config change) | Đổi `RAG_TEXT_SPLITTER=character` → `recursive` — chia theo newline, period, spaces thay vì cắt cứng theo ký tự. **Chỉ cần đổi 1 dòng env**. Cải thiện nhưng vẫn rule-based. | ⭐ Low | 🟡 Medium |
| 1b | **True Semantic Chunking** (custom) | Viết Pipeline/Filter dùng embedding để detect ranh giới ý nghĩa. Chia chunk dựa trên cosine similarity giữa các câu liền kề. **Khác biệt hoàn toàn** so với recursive splitter. | ⭐⭐⭐ High | 🔴 High |
| 2 | **Reranking** | Thêm reranker sau hybrid search. Open WebUI KHÔNG có built-in reranking hook → Cần viết custom Pipeline hoặc dùng Open WebUI Pipelines API. Option: LLM-based reranking qua prompt (đắt nhưng nhanh deploy) hoặc cross-encoder model (rẻ nhưng cần host riêng) | ⭐⭐⭐ High | 🔴 High |
| 3 | **Query Rewriting** | LLM tự expand/rephrase query trước khi search (HyDE technique) | ⭐⭐ Med | 🟡 Med |
| 4 | **Multi-Query Retrieval** | Sinh 3-5 biến thể của query → search song song → merge results | ⭐⭐ Med | 🟡 Med |
| 5 | **Metadata Filtering** | Thêm metadata tags khi upload (department, doc_type, date) → filter khi search | ⭐⭐ Med | 🟡 Med |
| 6 | **Context Window Optimization** | Tự động compress chunks trước khi inject vào prompt (giảm token cost) | ⭐⭐⭐ High | 🟡 Med |
| 7 | **Citation Verification** | LLM verify citation accuracy, highlight passages lấy từ source | ⭐⭐ Med | 🟡 Med |
| 8 | **Feedback Loop** | User 👍/👎 response → ghi log → dùng để tune retrieval params | ⭐⭐ Med | 🟡 Med |
| 9 | **Scheduled Re-indexing** | Tự động re-embed documents khi model embedding thay đổi | ⭐⭐ Med | 🟢 Low |
| 10 | **Multi-modal RAG** | Index hình ảnh, bảng trong PDF bằng vision model | ⭐⭐⭐ High | 🟡 Med |

> [!IMPORTANT]
> **Khuyến nghị ưu tiên RAG**:
> - **Ngay** (5 phút): Đổi `character` → `recursive` trong docker-compose.yml (#1a)
> - **Giai đoạn 2** (1-2 tuần): Implement Reranking qua Pipeline (#2) — impact cao nhất
> - **Giai đoạn sau**: True semantic chunking (#1b) — cần nghiên cứu thêm

---

### 2.3. 🖥️ Nhóm 2: Dashboard & Khai Thác CSDL

#### Hiện trạng Dashboard

```
Dashboard hiện tại (SPA HTML/JS — 33KB HTML + 12 JS modules)
│
├── 📈 Usage Tab
│   ├── 8 metric cards (requests, cost, tokens, latency, errors, billable, missing, pending)
│   ├── Request Type donut chart
│   ├── Requests/Cost/Tokens over time line charts
│   ├── Top Users table + donut
│   └── Top Models table + donut
│
├── 🌐 Access Tab
│   ├── HTTP access summary
│   └── Access events stream
│
├── 👥 Users Tab
│   ├── User CRUD (create, edit, delete)
│   ├── Quota management
│   ├── Subkey rotation
│   └── Enable/disable user
│
└── 📋 Logs Tab
    ├── Audit log query with filters
    ├── Sort & pagination
    └── Export to Excel
```

#### Dữ liệu CSDL chưa khai thác

```
┌─────────────────────────────────────────────────────────┐
│  MIDDLEWARE DB (7 tables)                                │
│                                                          │
│  ✅ mw_audit_log    → Đã khai thác (charts, tables)     │
│  ✅ mw_users        → Đã khai thác (user CRUD, quota)   │
│  ⬜ mw_prices       → Chỉ read-only, chưa có UI edit   │
│  ⬜ mw_config       → Chưa có UI quản lý               │
│  ⬜ mw_request_log  → Chưa khai thác                    │
│  ⬜ mw_pending      → Hiển thị count, chưa detail       │
│  ⬜ mw_notifications→ Có panel, chưa quản lý nâng cao   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  OPENWEBUI DB (26 tables) — CẦN OW DB ACCESS STRATEGY  │
│  ⚠️ Phụ thuộc Section 2.1 (quyết định kiến trúc)       │
│                                                          │
│  ⬜ user / auth      → Sync status với mw_users        │
│  ⬜ chat / message    → Analytics: chat patterns        │
│  ⬜ knowledge / file  → Analytics: knowledge usage      │
│  ⬜ group             → Group-based analytics           │
│  ⬜ feedback          → User satisfaction metrics       │
│  ⬜ document_chunk    → RAG health monitoring           │
│  ⬜ tag               → Tag analytics                  │
│  ⬜ memory            → Memory usage stats             │
└─────────────────────────────────────────────────────────┘
```

#### Chi tiết cải thiện Dashboard

| # | Cải thiện | Dữ liệu nguồn | Phụ thuộc OW DB? | Effort | Impact |
|:-:|-----------|---------------|:----------------:|:------:|:------:|
| 1 | **Price Editor** | `mw_prices` | ❌ | 2-3 ngày | 🟡 Med |
| 2 | **System Config UI** | `mw_config` | ❌ | 2-3 ngày | 🟡 Med |
| 3 | **Cost Comparison page** | `mw_prices` | ❌ | 2 ngày | 🟡 Med |
| 4 | **Pending Detail View** | `mw_pending` | ❌ | 1-2 ngày | 🟢 Low |
| 5 | **User Sync Status** | `mw_users` + OW `user` | ✅ Option A/B/C | 3-5 ngày | 🟡 Med |
| 6 | **Chat Analytics** | OW `chat` + `message` | ✅ Option A/B/C | 5-7 ngày | 🔴 High |
| 7 | **Knowledge Analytics** | OW `knowledge` + `file` | ✅ Option A/B/C | 4-5 ngày | 🟡 Med |
| 8 | **RAG Health Monitor** | OW `document_chunk` | ✅ Option A/B/C | 3-4 ngày | 🟡 Med |
| 9 | **User Satisfaction** | OW `feedback` | ✅ Option A/B/C | 4-5 ngày | 🔴 High |
| 10 | **Group Analytics** | OW `group` + MW audit | ✅ Option A/B/C | 5-7 ngày | 🔴 High |
| 11 | **Export Reports** | All sources | ✅ (partial) | 5-7 ngày | 🟡 Med |
| 12 | **Real-time Active Users** | SSE + `mw_pending` | ❌ | 3-4 ngày | 🟡 Med |

> [!WARNING]
> Items #5-#11 (7/12 items — chiếm ~60%) **không thể triển khai** cho đến khi quyết định OW DB Access Strategy (Section 2.1). Items #1-#4, #12 có thể làm song song ngay.

---

## 3. 💡 Nhóm 3: ĐỀ XUẤT Nghiên Cứu Bổ Sung

### 3.1. 🔐 Bảo mật & Compliance

> [!WARNING]
> **SSO/LDAP cần thiết kế auth flow mới**: Open WebUI login tạo JWT riêng, nhưng MW dùng HMAC-SHA256 subkey. Khi user SSO vào OW, cần auto-provision MW subkey. Cần thiết kế flow:
> `AD login → OW JWT → Middleware auto-create user + generate subkey → inject vào OW settings`

| # | Tính năng | Mô tả | Effort thực tế |
|:-:|-----------|-------|:--------------:|
| 1 | **SSO/LDAP Integration** | Open WebUI hỗ trợ sẵn `OAUTH_*` env, nhưng cần thêm auto-provision MW user khi SSO login lần đầu | 3-5 ngày |
| 2 | **Audit Trail Export** | Xuất audit log dạng CSV/PDF cho compliance review (dashboard đã có Export Excel — mở rộng thêm PDF) | 1-2 ngày |
| 3 | **Data Retention Policy** | Tự động xóa audit logs sau N ngày, archive old chats | 2-3 ngày |
| 4 | **IP Whitelist per User** | Giới hạn IP truy cập ở MW level cho user nhạy cảm | 2 ngày |

### 3.2. 📊 Monitoring & Alerting Infrastructure

```
┌──────────────────────────────────────────────────────┐
│  ĐỀ XUẤT: Monitoring Stack                           │
│                                                       │
│  ┌─────────┐    ┌────────────┐    ┌─────────────┐    │
│  │Prometheus│───▶│  Grafana   │───▶│ AlertManager│    │
│  │ (scrape) │    │(visualize) │    │ (email/zalo)│    │
│  └────┬─────┘    └────────────┘    └─────────────┘    │
│       │                                               │
│  ┌────┴─────────────────────────────────┐             │
│  │ Metrics Sources:                      │             │
│  │  • Nginx (request rate, error rate)   │             │
│  │  • PostgreSQL (connections, queries)  │             │
│  │  • Middleware (custom /metrics)       │             │
│  │  • Docker (CPU, RAM, network)         │             │
│  │  • LiteLLM (provider latency, errors) │             │
│  └───────────────────────────────────────┘             │
└──────────────────────────────────────────────────────┘
```

| # | Tính năng | Mô tả | Effort |
|:-:|-----------|-------|:------:|
| 1 | **Prometheus + Grafana** | Pre-built Docker images, cộng thêm exporters (postgres, nginx) | 1-2 ngày |
| 2 | **Custom /metrics endpoint** | Expose middleware metrics dạng Prometheus format qua FastAPI | 1 ngày |
| 3 | **Uptime Alert** | Email/Zalo khi service down > 5 phút | 1 ngày |
| 4 | **Cost Spike Alert** | Cảnh báo khi chi phí bất thường (>2x daily average) | 1 ngày |
| 5 | **Slowness Alert** | Cảnh báo khi P95 latency > 30s liên tục 5 phút | 1 ngày |

### 3.3. 🔄 Backup & Disaster Recovery

| # | Tính năng | Mô tả | Effort |
|:-:|-----------|-------|:------:|
| 1 | **Automated Daily Backup** | Cron job pg_dump (cả 2 databases: openwebui + middleware), giữ 30 ngày | 1 ngày |
| 2 | **Backup to Network Share** | Copy backup ra NAS/shared drive (offsite) | 0.5 ngày |
| 3 | **Docker Volume Backup** | Backup `openwebui_data` volume (uploaded files) | 0.5 ngày |
| 4 | **Restore Test Procedure** | Document + script phục hồi. **Phải test trên staging trước production** | 1-2 ngày |
| 5 | **Config Version Control** | Git versioning cho tất cả config (docker-compose, nginx, litellm) | ✅ Đã có |

### 3.4. 👥 Quản Lý Người Dùng Nâng Cao

| # | Tính năng | Mô tả | Effort |
|:-:|-----------|-------|:------:|
| 1 | **Group/Department Management** | Phân nhóm theo phòng ban, quota theo group. Cần sửa quota system + MW + dashboard + integrate OW `group` table | 7-10 ngày |
| 2 | **Onboarding Flow** | Email welcome + hướng dẫn setup cho user mới | 2 ngày |
| 3 | **Self-service Quota View** | End-user xem quota còn lại — MW đã có endpoint `/v1/_mw/quota-status`, cần embed vào OW UI | 2-3 ngày |
| 4 | **Usage Reports per User** | User tự xem lịch sử dùng và chi phí cá nhân | 3-4 ngày |
| 5 | **Bulk User Import** | Import users từ CSV/Excel (hữu ích cho 200 users) | 1-2 ngày |

### 3.5. 🧰 Custom Tools & Automation

| # | Tính năng | Mô tả | Effort |
|:-:|-----------|-------|:------:|
| 1 | **Template Prompts Library** | Kho prompt templates theo phòng ban (HR, Marketing, R&D) | 2 ngày |
| 2 | **Workflow/Pipelines** | Open WebUI Pipelines cho automated tasks | 3-5 ngày |
| 3 | **Scheduled Reports** | Email báo cáo chi phí hàng tuần/tháng cho managers | 2-3 ngày |
| 4 | **Webhook Integration** | Gửi notification tới Zalo/Teams/Slack khi events quan trọng | 2 ngày |
| 5 | **API Gateway** | Expose middleware API cho hệ thống nội bộ khác (DMS, ERP) | 3-5 ngày |

### 3.6. 🚀 Performance & Scalability

| # | Tính năng | Mô tả | Effort |
|:-:|-----------|-------|:------:|
| 1 | **Redis Caching** | Cache user config, price data trong Redis (đã có Redis container cho WebSocket) | 2 ngày |
| 2 | **Request Queue** | Queue system cho heavy requests (image gen, large doc RAG) | 3-5 ngày |
| 3 | **Database Partitioning** | Partition mw_audit_log theo tháng (khi đạt vài triệu rows) | 2 ngày |

> **Lưu ý**: PgBouncer và CDN **không cần thiết** cho 200 users nội bộ. MW đã có `ThreadedConnectionPool(min=5, max=30)` — đủ cho workload này. Nginx đã serve static tốt cho internal tool.

### 3.7. 📱 User Experience (UX) Nâng Cao

| # | Tính năng | Mô tả | Effort |
|:-:|-----------|-------|:------:|
| 1 | **Welcome Tour** | Interactive tutorial cho user mới (first login) | 2-3 ngày |
| 2 | **Conversation Templates** | Templates cho use cases phổ biến (dịch, viết email, phân tích) | 1 ngày |
| 3 | **Admin Announcement** | Admin đăng thông báo hiện banner cho tất cả users (OW hỗ trợ sẵn `WEBUI_BANNERS`) | 0.5 ngày |

### 3.8. 🧪 Testing & Quality Assurance

| # | Tính năng | Mô tả | Effort |
|:-:|-----------|-------|:------:|
| 1 | **Load Testing** | k6/Locust scripts cho stress testing 200 concurrent users | 2 ngày |
| 2 | **Smoke Tests** | Script kiểm tra health tất cả services sau mỗi deploy | 1 ngày |
| 3 | **Automated E2E Tests** | Playwright tests cho critical flows (login, chat, upload, RAG) | 3-5 ngày |
| 4 | **API Contract Tests** | Đảm bảo middleware API không breaking changes | 2 ngày |

---

## 4. ⚠️ Đánh Giá Rủi Ro

| Rủi ro | Impact | Xác suất | Mitigation |
|--------|:------:|:--------:|------------|
| **Upgrade Open WebUI** bản mới breaking OW DB schema → Dashboard queries hỏng | 🔴 High | 🟡 Med | Freeze OW version trong dev cycle. Thêm schema version check khi MW startup |
| **SSO conflict với MW subkey auth** — user SSO không có subkey → MW reject | 🔴 High | 🔴 High | Thiết kế auto-provision flow TRƯỚC khi implement SSO |
| **Backup restore fail** trên production → mất data | 🔴 High | 🟡 Med | Test restore procedure trên staging trước. Document runbook |
| **load_users() bottleneck** gây timeout với 200 users concurrent | 🟡 Med | 🔴 High | Phase 0 — **sửa trước khi onboard 200 users** |
| **RAG Pipeline custom** xung đột với OW internal RAG | 🟡 Med | 🟡 Med | Dùng Open WebUI Pipelines API (official extension point), không fork |
| **SSE connections phân tán** across Uvicorn workers → dashboard mất events | 🟢 Low | 🟡 Med | Redis pub/sub cho SSE broadcast (tương tự websocket manager đã có) |

---

## 5. 🗺️ Lộ Trình Đề Xuất (Roadmap)

### Phase 0: Performance Debt & Foundations (2 tuần)
> *Ưu tiên P0: Sửa trước khi scale. Không phụ thuộc gì khác.*

| Ưu tiên | Nhóm | Việc cần làm | Effort |
|:-------:|------|-------------|:------:|
| **P0** | 🚨 Performance | Refactor `load_users()` → `get_user_by_id()` O(1) | 3-4 ngày |
| **P0** | 🚨 Performance | Refactor `save_users()` → atomic `UPDATE` per user | 2-3 ngày |
| **P0** | 🔄 Backup | Automated daily backup script (pg_dump cả 2 DB + volumes) | 1-2 ngày |
| **P0** | 🏗️ Architecture | Quyết định OW DB access strategy (A/B/C) | 1 ngày |
| **P0** | 🧪 Testing | Benchmark suite (50/100/200 users) | 1 ngày |
| P1 | 🤖 RAG | Đổi `character` → `recursive` splitter (config change) | 5 phút |

**Milestone**: Mỗi chat request < 200ms latency overhead ở MW level với 200 users. Backup tự động chạy hàng ngày.

---

### Phase 1: Core Platform (3 tuần)
> *Ưu tiên P1: Nền tảng cho 200 users*

| Ưu tiên | Nhóm | Việc cần làm | Effort |
|:-------:|------|-------------|:------:|
| P1 | 🔐 Bảo mật | SSO/LDAP + auto-provision MW user flow | 3-5 ngày |
| P1 | 👥 Users | Bulk user import (CSV → MW + OW) | 1-2 ngày |
| P1 | 👥 Users | Group/Department management | 7-10 ngày |
| P1 | 🚨 Performance | Per-user rate limiting (Redis counter) | 2 ngày |

**Milestone**: 200 users onboarded qua SSO/bulk import, phân nhóm theo phòng ban, rate limit per user.

---

### Phase 2: RAG & Dashboard (3-4 tuần)
> *Ưu tiên P1-P2: Khai thác dữ liệu + AI quality*

| Ưu tiên | Nhóm | Việc cần làm | Effort |
|:-------:|------|-------------|:------:|
| P1 | 🤖 RAG | Implement Reranking (Pipeline) | 5-7 ngày |
| P1 | 🖥️ Dashboard | Price Editor + Config UI (MW DB only — #1,#2,#3) | 4-5 ngày |
| P1 | 🖥️ Dashboard | Group/Dept Analytics (#10) | 5-7 ngày |
| P2 | 🖥️ Dashboard | Chat Analytics (#6) + User Satisfaction (#9) | 7-10 ngày |
| P2 | 🖥️ Dashboard | RAG Health Monitor (#8) | 3-4 ngày |

**Milestone**: RAG quality cải thiện rõ rệt. Admin thấy analytics theo phòng ban + feedback users.

---

### Phase 3: Monitoring & Automation (2-3 tuần)
> *Ưu tiên P2: Operations maturity*

| Ưu tiên | Nhóm | Việc cần làm | Effort |
|:-------:|------|-------------|:------:|
| P2 | 📊 Monitoring | Prometheus + Grafana + Custom /metrics | 2-3 ngày |
| P2 | 🧰 Automation | Scheduled weekly reports (email) | 2-3 ngày |
| P2 | 🧰 Automation | Webhook integration (Zalo/Teams) | 2 ngày |
| P2 | 🧪 Testing | Load testing scripts (200 users sim) | 2 ngày |
| P2 | 📱 UX | Self-service quota view cho end-user | 2-3 ngày |

**Milestone**: Full observability stack. Managers nhận báo cáo tự động. Load test confirm 200 users OK.

---

### Phase 4: Advanced Features (3-4 tuần, optional)
> *Ưu tiên P3: Nice-to-have, schedule nếu có thời gian*

| Ưu tiên | Nhóm | Việc cần làm | Effort |
|:-------:|------|-------------|:------:|
| P3 | 📱 UX | Welcome tour cho user mới | 2-3 ngày |
| P3 | 📱 UX | Template prompts library | 2 ngày |
| P3 | 🤖 RAG | Query Rewriting (HyDE) | 3-5 ngày |
| P3 | 🤖 RAG | Multi-modal RAG (image/table in PDF) | 7-10 ngày |
| P3 | 🧰 Automation | API Gateway cho external systems | 3-5 ngày |

**Milestone**: Polish layer hoàn thiện.

---

### Tổng timeline (1 dev, thực tế)

```
┌──────────┬──────────┬───────────┬──────────┬──────────┐
│ Phase 0  │ Phase 1  │ Phase 2   │ Phase 3  │ Phase 4  │
│ 2 tuần   │ 3 tuần   │ 3-4 tuần  │ 2-3 tuần │ 3-4 tuần │
│ Perf+BU  │ Core     │ RAG+Dash  │ Monitor  │ Advanced │
├──────────┼──────────┼───────────┼──────────┼──────────┤
│ Tuần 1-2 │ Tuần 3-5 │ Tuần 6-9  │ Tuần     │ Tuần     │
│          │          │           │ 10-12    │ 13-16    │
└──────────┴──────────┴───────────┴──────────┴──────────┘
            Tổng: ~14-16 tuần (3.5-4 tháng)
            Phase 0-3: ~10-12 tuần (core platform ready)
```

---

## 6. 📈 So Sánh với SaaS Platform Thương Mại

```
┌──────────────────────┬───────────┬───────────┬──────────────┐
│ Feature              │ ChatGPT   │ Hệ thống  │ Sau Roadmap  │
│                      │ / Gemini  │ Hiện tại  │ (P0-P3)      │
├──────────────────────┼───────────┼───────────┼──────────────┤
│ Multi-provider AI    │ ❌ 1 only │ ✅ 4      │ ✅ 4+        │
│ Cost control/quota   │ ❌ None   │ ✅ Full   │ ✅ Full++    │
│ RAG / Knowledge      │ ✅ Basic  │ ✅ Basic  │ ✅ Advanced  │
│ Admin Dashboard      │ ❌ None   │ ✅ Good   │ ✅ Enterprise│
│ SSO/LDAP             │ ✅ (Ent)  │ ❌ None   │ ✅ Yes       │
│ Group management     │ ✅ (Ent)  │ ❌ None   │ ✅ Yes       │
│ Audit/Compliance     │ ✅ (Ent)  │ ✅ Partial│ ✅ Full      │
│ Monitoring           │ N/A       │ ❌ None   │ ✅ Full      │
│ Backup automation    │ N/A       │ ❌ None   │ ✅ Daily     │
│ Web search           │ ✅ Built  │ ✅ SearXNG│ ✅ SearXNG   │
│ Image generation     │ ✅ 1 mod  │ ✅ 6 mod  │ ✅ 6+ mod    │
│ Voice I/O            │ ✅ Built  │ ✅ TTS/STT│ ✅ TTS/STT   │
│ Custom tools         │ ✅ GPTs   │ ✅ Basic  │ ✅ Advanced  │
│ Data sovereignty     │ ❌ Cloud  │ ✅ On-prem│ ✅ On-prem   │
│ Self-hosted          │ ❌ No     │ ✅ Yes    │ ✅ Yes       │
│ Cost/month (200 usr) │ ~$4,000+  │ API only  │ API only     │
└──────────────────────┴───────────┴───────────┴──────────────┘
```

> [!TIP]
> **Lợi thế cạnh tranh lớn nhất** so với ChatGPT Enterprise/Gemini Business:
> 1. **Multi-provider** — 4 providers, 22 models, user chọn tùy ý
> 2. **Data sovereignty** — Tất cả on-premise, tuân thủ PDPA
> 3. **Cost control** — Granular quota per user, real-time tracking
> 4. **Chi phí thấp hơn nhiều** — Chỉ trả per-API-call, không subscription $20/user/month

---

## 7. ❓ Câu Hỏi Cần Làm Rõ Trước Khi Lập Kế Hoạch

1. **AD/LDAP**: Rạng Đông có Active Directory không? Protocol nào (LDAP, OAUTH2, SAML)?
2. **Groups**: Muốn phân nhóm theo phòng ban cụ thể nào? (R&D, Marketing, HR, Kinh doanh...)
3. **OW DB Access**: Chọn Option A (read-only pool), B (API bridge), hay C (materialized views)?
4. **Backup destination**: Backup muốn lưu ở đâu? (local disk, NAS, cloud?)
5. **Timeline**: Muốn hoàn thành Phase 0-3 trong 12 tuần hay có deadline khác?
6. **Team size**: Bao nhiêu người phát triển? (1 dev → 14-16 tuần, 2 dev → 8-10 tuần)
7. **External API**: Có nhu cầu mở API cho hệ thống khác truy cập không?
8. **OW Version freeze**: Sẵn sàng freeze Open WebUI version trong thời gian phát triển? (khuyến nghị: ✅)

---

## 8. ✅ Definition of Done — Mỗi Phase

| Phase | Tiêu chí hoàn thành |
|-------|---------------------|
| **Phase 0** | ✅ `load_users()` refactored → O(1). ✅ Benchmark: <200ms MW overhead/request (200 users). ✅ Backup chạy tự động hàng ngày. ✅ OW DB strategy quyết định. |
| **Phase 1** | ✅ 200 users onboarded (SSO hoặc bulk). ✅ Group-based permissions. ✅ Per-user rate limit hoạt động. ✅ Zero regression trên existing features. |
| **Phase 2** | ✅ RAG reranking hoạt động, đo được improvement qua test queries. ✅ Dashboard có analytics mới (MW-only items #1-4 + cross-DB items). ✅ Docs cập nhật. |
| **Phase 3** | ✅ Grafana dashboard live. ✅ Alert email/webhook hoạt động. ✅ Load test pass 200 concurrent. ✅ Weekly report gửi tự động. |

---

> 💭 *Đây là phiên bản đã sửa chữa dựa trên critical review (2026-04-13). Khi bạn quyết định bắt đầu, hãy dùng `/opsx:propose` cho Phase 0 trước.*
