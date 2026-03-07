# TAI LIEU TONG QUAN HE THONG AI NOI BO

**Ma tai lieu:** DOC-01  
**Phien ban:** 1.0  
**Ngay lap:** 06/03/2026  
**Doi tuong:** Ban lanh dao, Quan tri vien, Truong bo phan, Doi ky thuat  
**Phan loai:** NOI BO - HAN CHE

---

## MUC LUC

1. Chi muc tai lieu
2. Tong quan, Pham vi va Muc dich
3. Yeu cau nghiep vu
4. Yeu cau phi chức năng
5. Mo ta chức năng va So do tong the
6. Cau truc cau phan hệ thống
7. Kiến trúc dữ liệu, Tich hop va Luong xu ly
8. Bảo mật va An toan thong tin
9. Quy trinh vận hành

---

## 1. CHI MUC TAI LIEU

| STT | Ma     | Ten tai lieu         | Mo ta                                                    | Doi tuong       |
| --- | ------ | -------------------- | -------------------------------------------------------- | --------------- |
| 01  | DOC-01 | Tong quan hệ thống   | Tai lieu nay - pham vi, yeu cau, kiến trúc, bảo mật      | Tat ca          |
| 02  | DOC-02 | Tai lieu vận hành    | Hướng dẫn vận hành chuyen sau, troubleshooting           | QTV hệ thống    |
| 03  | DOC-03 | Kiến trúc Middleware | Chi tiet middleware proxy: routing, quota, cost tracking | Doi ky thuat    |
| 04  | DOC-04 | So do kiến trúc      | Diagrams: system context, component, data flow, ERD      | Doi ky thuat    |
| 05  | DOC-05 | Kiến trúc Database   | Schema 32+ tables, Open WebUI + Middleware databases     | Doi ky thuat    |
| 06  | DOC-06 | Kiến trúc RAG        | RAG pipeline: embedding, chunking, vector search, HNSW   | Doi ky thuat    |
| 07  | DOC-07 | API Reference        | REST API endpoints, request/response, error codes        | Doi phat trien  |
| 08  | DOC-08 | Dashboard Admin      | Dashboard UI, metrics, filters, charts, user CRUD        | QTV hệ thống    |
| 09  | DOC-09 | Quản lý người dùng   | User CRUD, RBAC, subkey management, audit trail          | QTV hệ thống    |
| 10  | DOC-10 | Hướng dẫn sử dụng    | Hướng dẫn end-user: chat, RAG, image gen, export         | Người dùng      |
| 11  | DOC-11 | Bao cao tong quan    | Bao cao trinh bay cho lanh dao, so sanh giai phap        | Ban lanh dao    |
| 12  | DOC-12 | Checklist tính năng  | 103+ tính năng, trang thai, ket qua test                 | QTV va Ky thuat |

Thu tu doc khuyen nghi: DOC-01 > DOC-11 > DOC-10 > DOC-02 > DOC-08 > DOC-03 > DOC-05

---

## 2. TONG QUAN, PHAM VI VA MUC DICH

### 2.1. Gioi thieu hệ thống

Hệ thống AI nội bộ (Open WebUI Stack) la nen tang tro ly AI tap trung cho toan to chuc. Hệ thống hoat dong nhu mot "ChatGPT nội bộ" nhung bo sung cac kha nang:

- Kiem soat chi phí chu dong (quota / user / thang)
- Bảo mật dữ liệu (embedding chay local, tai lieu khong roi server)
- Quan tri tap trung (dashboard real-time, audit trail)
- Da nhà cung cấp (OpenAI + Google Gemini qua 1 gateway duy nhat)

### 2.2. Pham vi

| Tieu chi           | Chi tiet                                                             |
| ------------------ | -------------------------------------------------------------------- |
| Quy mo to chuc     | Doanh nghiep tu 200+ nhan vien, nhieu phong ban                      |
| Phong ban muc tieu | Tat ca: Ky thuat, Kinh doanh, Nhan su, Tai chinh, Marketing, R&D     |
| Dia ly             | Mang nội bộ LAN/VPN - truy cap tu bat ky may nao trong mang          |
| Ngon ngu           | Ho tro 50+ ngon ngu (toi uu tieng Viet va tieng Anh)                 |
| Nen tang           | Web-based - truy cap qua trinh duyet (Chrome, Firefox, Edge, Safari) |
| Ha tang            | On-premise (Docker tren Windows Server hoac Linux)                   |
| Mô hình triển khai | Docker Compose - khởi động trong 2 phut                              |

### 2.3. Muc dich

#### A. Thay the dịch vụ SaaS phan tan

| Truoc                                              | Sau                                              |
| -------------------------------------------------- | ------------------------------------------------ |
| Moi nhan vien tu dang ky ChatGPT/Gemini rieng le   | Mot cong truy cap duy nhat cho tat ca dịch vụ AI |
| Khong kiem soat chi phí - phat sinh ngoai ke hoach | Quota chat che theo user/phong ban/thang         |
| Rui ro ro ri dữ liệu qua tài khoản ca nhan         | Tai lieu nội bộ xu ly 100% tren server rieng     |
| Khong co audit trail - khong biet ai dung gi       | Log chi tiet moi request: cost, model, user      |

#### B. Nen tang tap trung va Quan tri chu dong

- Quan tri người dùng: CRUD users, phân quyền RBAC (Admin / Manager / User / Pending)
- Quan tri quota: Gioi han chi phí, token, so anh theo user/nhom/thang
- Quan tri model: Chon model nao hien thi cho user nao, gioi han model dat
- Theo doi real-time: Dashboard 7 KPIs + biểu đồ + SSE live stream
- Kiem soat dữ liệu: Knowledge Base quản lý tap trung, phân quyền access

#### C. Toi uu chi phí sử dụng AI

- Multi-provider routing: Tự động chon provider re nhat cho cung chat luong
- Bảng giá model: Cập nhật gia input/output token cho 20 models trong DB
- Quota enforcement: Vuot quota - tự động tu choi, khong phat sinh chi phí ngoai ke hoach
- Cost dashboard: Real-time tracking chi phí theo user, model, thoi gian
- Uoc tinh: 10 users x 20 requests/ngay ~ $50-150/thang (so voi $300/thang cho ChatGPT Enterprise)

### 2.4. Doi tuong sử dụng

| Vai tro               | Truy cap                | Chức năng chinh                                   |
| --------------------- | ----------------------- | ------------------------------------------------- |
| Ban lanh dao          | Bao cao tong quan       | Xem chi phí, ROI, tinh trang hệ thống             |
| Quan tri vien (Admin) | Dashboard + Admin Panel | Quản lý user, quota, model, knowledge, monitoring |
| Truong bo phan        | Open WebUI + Dashboard  | Quản lý knowledge phong ban, xem chi phí nhom     |
| Nhan vien (User)      | Open WebUI (port 3000)  | Chat AI, RAG, tao anh, xuat file, TTS/STT         |
| Ky thuat vien         | Full stack access       | Vận hành, bao tri, cập nhật hệ thống              |

---

## 3. YEU CAU NGHIEP VU

### 3.1. Chat AI da phương thức

| ID    | Yeu cau          | Mo ta                                                       | Uu tien    |
| ----- | ---------------- | ----------------------------------------------------------- | ---------- |
| BR-01 | Chat text        | Hoi dap, soan thao, phan tich, dich thuat qua AI            | Cao        |
| BR-02 | Da model         | Chon tu 14 model chat (GPT-5, GPT-4o, Gemini 2.5, Gemini 3) | Cao        |
| BR-03 | Vision input     | Gui anh/screenshot de AI phan tich (multimodal)             | Trung binh |
| BR-04 | Context 1M token | Doc hieu tai lieu hang tram trang trong 1 session           | Trung binh |
| BR-05 | Lịch sử chat     | Luu tru va tìm kiếm lịch sử hội thoại                       | Cao        |

### 3.2. Tao anh AI

| ID    | Yeu cau               | Mo ta                                         | Uu tien    |
| ----- | --------------------- | --------------------------------------------- | ---------- |
| BR-06 | Text-to-Image         | Tao anh tu mo ta text: banner, poster, mockup | Trung binh |
| BR-07 | Da provider           | DALL-E 3 (OpenAI) + Gemini Image (Google)     | Trung binh |
| BR-08 | Kiem soat chi phí anh | Quota rieng cho image requests                | Trung binh |

### 3.3. RAG / Knowledge Base

| ID    | Yeu cau              | Mo ta                                            | Uu tien |
| ----- | -------------------- | ------------------------------------------------ | ------- |
| BR-09 | Upload tai lieu      | PDF, Word, Excel, CSV, TXT, HTML - max 50MB/file | Cao     |
| BR-10 | Tìm kiếm ngu nghia   | Hybrid search (BM25 + vector cosine similarity)  | Cao     |
| BR-11 | Trich dan nguon      | AI tra loi kem citation (ten file, trang, doan)  | Cao     |
| BR-12 | Phân quyền Knowledge | Chi user/nhom duoc grant moi truy cap Knowledge  | Cao     |
| BR-13 | Embedding local      | Dữ liệu nội bộ KHONG gui ra ben ngoai            | Cao     |

### 3.4. Quản lý chi phí va Quota

| ID    | Yeu cau           | Mo ta                                                       | Uu tien    |
| ----- | ----------------- | ----------------------------------------------------------- | ---------- |
| BR-14 | Quota per user    | Gioi han cost_usd, tokens, image_requests/thang             | Cao        |
| BR-15 | Auto-enforce      | Vuot quota - 403 tự động, khong can admin can thiep         | Cao        |
| BR-16 | Dashboard chi phí | Real-time: tong cost, top users, top models, xu huong       | Cao        |
| BR-17 | Audit trail       | Ghi lai EVERY request: user, model, tokens, cost, timestamp | Cao        |
| BR-18 | Bảng giá model    | Moi model co gia input/output rieng, cập nhật trong DB      | Trung binh |

### 3.5. Xuat dữ liệu va Tools

| ID    | Yeu cau      | Mo ta                                          | Uu tien    |
| ----- | ------------ | ---------------------------------------------- | ---------- |
| BR-19 | Export Excel | Trich xuat bang bieu - .xlsx co format, filter | Trung binh |
| BR-20 | Export PDF   | Xuat hội thoại - PDF ho tro tieng Viet         | Trung binh |
| BR-21 | Export Word  | Xuat hội thoại - .docx                         | Trung binh |
| BR-22 | TTS/STT      | Text-to-Speech + Speech-to-Text                | Thap       |

### 3.6. Quan tri người dùng

| ID    | Yeu cau           | Mo ta                                             | Uu tien |
| ----- | ----------------- | ------------------------------------------------- | ------- |
| BR-23 | User CRUD         | Tao, sua, xoa user tu Dashboard hoac API          | Cao     |
| BR-24 | Subkey management | Mã hóa HMAC-SHA256, rotate key, plaintext 1 lan   | Cao     |
| BR-25 | Role-based access | Admin / Manager / User / Pending                  | Cao     |
| BR-26 | Active/Disable    | Toggle enable/disable per user - 403 khi disabled | Cao     |

---

## 4. YEU CAU PHI CHUC NANG

### 4.1. Hieu nang (Performance)

| Chi so             | Yeu cau                  | Ghi chu                        |
| ------------------ | ------------------------ | ------------------------------ |
| Latency P95        | < 2000ms (text chat)     | Khong tinh LLM generation time |
| Throughput         | 50+ concurrent users     | Docker resource-dependent      |
| RAG indexing       | < 60s cho file 100 trang | ~313 chunks x embedding        |
| Dashboard response | < 500ms (summary API)    | 5s polling interval            |
| SSE stream         | Real-time < 100ms delay  | Server-Sent Events             |

### 4.2. Kha dung (Availability)

| Chi so               | Yeu cau                              | Ghi chu                           |
| -------------------- | ------------------------------------ | --------------------------------- |
| Uptime               | 99.5% (gio hanh chinh)               | ~4h downtime/thang cho bao tri    |
| Auto-restart         | restart: unless-stopped              | Docker tu khởi động lai khi crash |
| Health check         | Moi 10s (PostgreSQL), 5s (Dashboard) | Tự động detect failure            |
| Graceful degradation | LiteLLM down - loi nhung MW van OK   | Isolation giua cac service        |

### 4.3. Bảo mật (Security)

| Chi so         | Yeu cau                            | Ghi chu                        |
| -------------- | ---------------------------------- | ------------------------------ |
| Authentication | JWT + HMAC-SHA256 subkey           | Multi-layer auth               |
| Session        | HttpOnly cookie, 4h expiry         | Chong XSS                      |
| Network        | Docker internal network            | Internal services khong expose |
| Data at rest   | PostgreSQL trong Docker volume     | Khong cloud DB                 |
| Embedding      | 100% local (sentence-transformers) | Tai lieu nội bộ KHONG ra ngoai |

### 4.4. Kha nang mo rong (Scalability)

| Chieu      | Phuong phap                    | Ghi chu               |
| ---------- | ------------------------------ | --------------------- |
| Horizontal | Docker replicas cho middleware | Scale read throughput |
| Vertical   | Tang RAM/CPU container         | Cho embedding, DB     |
| Storage    | PostgreSQL + Docker volumes    | Expandable            |
| Models     | Them vao litellm_config.yaml   | Hot-plug models       |

### 4.5. Tuong thich (Compatibility)

| Thanh phan  | Yeu cau                                        |
| ----------- | ---------------------------------------------- |
| Trinh duyet | Chrome 90+, Firefox 88+, Edge 90+, Safari 14+  |
| Server OS   | Windows Server 2019+, Ubuntu 20.04+, CentOS 8+ |
| Docker      | Docker Engine 24.0+, Docker Compose v2.20+     |
| Database    | PostgreSQL 16 + PGVector 0.8.0                 |

---

## 5. MO TA CHUC NANG VA SO DO TONG THE

### 5.1. Tong quan chức năng

| Module                     | So tính năng | Trang thai | Mo ta                                       |
| -------------------------- | ------------ | ---------- | ------------------------------------------- |
| Phân quyền va Quản lý user | 12           | Hoat dong  | Dang ky, phân quyền, RBAC, Admin Panel      |
| Chat AI                    | 18           | Hoat dong  | 14 models, streaming, markdown, code        |
| Knowledge Base va RAG      | 15           | Hoat dong  | Upload, embedding, hybrid search, citations |
| Tao anh (Image Gen)        | 6            | Hoat dong  | DALL-E 3, Gemini Image, cost tracking       |
| Giong noi (TTS/STT)        | 4            | Hoat dong  | Text-to-Speech, Speech-to-Text              |
| Custom Tools               | 3            | Hoat dong  | Export Excel/PDF/Word                       |
| Middleware Proxy           | 20           | Hoat dong  | Auth, quota, cost, routing, audit           |
| Dashboard Admin            | 15           | Hoat dong  | 7 KPIs, charts, filters, user CRUD          |
| Cấu hình va Tuy chinh      | 10           | Hoat dong  | Model settings, RAG config, UI themes       |
| TONG CONG                  | 103          |            |                                             |

### 5.2. So do System Context

```
                         NGƯỜI DÙNG
                    (200+ nhan vien, Admin)
                              |
                              v
                    +-------------------------+
                    |   Open WebUI (3000)     |
                    |   Giao diện web / Chat  |
                    |   RAG / Knowledge       |
                    +------------+------------+
                                 |
                                 v
                    +-------------------------+
                    |   Middleware (5000)      |
                    |   Auth / Quota / Cost   |
                    |   Dashboard / User CRUD |
                    +------------+------------+
                                 |
              +------------------+------------------+
              |                  |                  |
              v                  v                  v
     +--------------+   +--------------+   +-----------------+
     | LiteLLM      |   | PostgreSQL   |   | Sentence-       |
     | Proxy (4000) |   | + PGVector   |   | Transformers    |
     |              |   | (5432)       |   | (local embed)   |
     +------+-------+   +--------------+   +-----------------+
            |
     +------+------+
     |             |
     v             v
  +--------+  +--------+
  | OpenAI |  | Google |
  |  API   |  | Gemini |
  +--------+  +--------+
```

### 5.3. So do Use Case

```
+-------------------------------------------------------------+
|                  HE THONG AI NOI BO                         |
|-------------------------------------------------------------|
|                                                             |
|  [End User]  ---- Chat AI (text, vision, streaming)         |
|              ---- Hoi dap Knowledge Base (#KB)              |
|              ---- Upload tai lieu vao Knowledge             |
|              ---- Tao anh (/image)                          |
|              ---- Xuat file (Excel, PDF, Word)              |
|              ---- Nhap giong noi (STT) / Nghe (TTS)        |
|                                                             |
|  [Admin]     ---- Quản lý user (CRUD, quota, subkey)        |
|              ---- Xem Dashboard chi phí real-time           |
|              ---- Duyet user pending                        |
|              ---- Cấu hình model, knowledge                 |
|              ---- Xem audit logs, access logs               |
|              ---- Backup database                           |
|                                                             |
|  [Sys Admin] ---- Vận hành Docker (start/stop/restart)      |
|              ---- Monitoring health check                   |
|              ---- Cập nhật code, them model                 |
|              ---- Troubleshooting va recovery               |
|                                                             |
+-------------------------------------------------------------+
```

---

## 6. CAU TRUC CAU PHAN HE THONG

### 6.1. Tong quan 4 tang (Tier Architecture)

| Tier    | Service    | Port | Cong nghe                | Muc dich                                     |
| ------- | ---------- | ---- | ------------------------ | -------------------------------------------- |
| Tier 1  | Open WebUI | 3000 | Python + SvelteKit       | Giao diện người dùng, chat, RAG, knowledge   |
| Tier 2  | Middleware | 5000 | Python + FastAPI         | Auth, quota, cost tracking, dashboard, audit |
| Tier 3a | LiteLLM    | 4000 | Python                   | LLM proxy: routing, retry, model mapping     |
| Tier 3b | PostgreSQL | 5432 | PostgreSQL 16 + PGVector | Database + vector search                     |

### 6.2. Open WebUI (Tier 1) - Giao diện người dùng

Container: openwebui-app

| Module            | Chức năng                                         |
| ----------------- | ------------------------------------------------- |
| Chat Engine       | Da model, streaming, markdown rendering           |
| Knowledge Manager | Upload file, tao collections, phân quyền          |
| RAG Pipeline      | Text extraction > chunking > embedding > PGVector |
| User Auth         | Email/password + JWT, role-based                  |
| Admin Panel       | Quản lý users, models, knowledge, settings        |
| Custom Tools      | Export Excel/PDF/Word qua Action buttons          |

### 6.3. Middleware (Tier 2) - Xác thực va Quan tri

Container: openwebui-middleware

| Module         | File               | Chức năng                                   |
| -------------- | ------------------ | ------------------------------------------- |
| API Gateway    | main.py            | FastAPI app, route registration, CORS       |
| Auth Core      | core/auth.py       | Subkey validation, user lookup, HMAC-SHA256 |
| Cost Engine    | core/cost.py       | Price lookup, cost calculation, quota check |
| Database       | core/db.py         | PostgreSQL connection pool, schema, CRUD    |
| Alerting       | core/alerting.py   | Quota alerts, webhook notifications         |
| User Admin API | api/user_admin.py  | CRUD users, rotate key, delete              |
| Summary API    | api/summary.py     | Metrics aggregation, time-window filtering  |
| Stream API     | api/stream.py      | SSE real-time events                        |
| Access Logs    | api/access_logs.py | Paginated access log queries                |
| Audit API      | api/audit_query.py | Admin audit trail query                     |
| Dashboard      | dashboard/         | HTML/CSS/JS SPA: charts, filters, user CRUD |

### 6.4. LiteLLM (Tier 3a) - LLM Proxy

Container: openwebui-litellm

| Chức năng      | Mo ta                                                   |
| -------------- | ------------------------------------------------------- |
| Model Routing  | Map chat-gpt-5 > openai/gpt-5, chat-gemini > gemini/... |
| Multi-provider | OpenAI + Google Gemini qua 1 gateway                    |
| Retry/Fallback | Tự động retry khi loi, fallback sang provider khac      |
| Streaming      | Forward SSE stream tu LLM > middleware > client         |
| Config         | litellm/litellm_config.yaml - 20 models dinh nghia san  |

### 6.5. PostgreSQL + PGVector (Tier 3b)

Container: openwebui-postgres

| Database   | So bang | Muc dich                                             |
| ---------- | ------- | ---------------------------------------------------- |
| openwebui  | 26      | User, chat, file, knowledge, document_chunk (vector) |
| middleware | 6       | mw_users, mw_prices, mw_config, mw_pending, mw_audit |

### 6.6. Docker Infrastructure

```
docker-compose.yml:

  services:
    postgres        # pgvector/pgvector:0.8.0-pg16
    litellm         # ghcr.io/berriai/litellm:main-latest
    middleware      # Custom build (./llm-mw/Dockerfile)
    open-webui      # ghcr.io/open-webui/open-webui:main

  volumes:
    postgres_data       # Database persistent storage
    litellm_logs        # LiteLLM log files
    openwebui_data      # Open WebUI uploads, files

  networks:
    openwebui-network   # Internal bridge network
```

---

## 7. KIEN TRUC DU LIEU, TICH HOP VA LUONG XU LY

### 7.1. Schema Database

#### Database openwebui - 26 bang chinh

| Nhom      | Bang                            | Muc dich                        |
| --------- | ------------------------------- | ------------------------------- |
| User      | user, auth                      | Thong tin user, credentials     |
| Chat      | chat, channel, message          | Hội thoại, kenh, tin nhan       |
| Knowledge | knowledge, file, knowledge_file | Collections, files, lien ket    |
| RAG       | document, document_chunk        | Text chunks + vector(1536) HNSW |
| Admin     | config, feedback, tag           | Cấu hình, danh gia, gan the     |
| Groups    | group                           | Nhom người dùng, phân quyền     |

#### Database middleware - 6 bang

| Bang           | Columns chinh                                      | Muc dich             |
| -------------- | -------------------------------------------------- | -------------------- |
| mw_users       | user_id, subkey_hash, role, active, allowed_models | Quản lý user API     |
| mw_prices      | model, input_per_1m, output_per_1m, image_cost     | Bảng giá model       |
| mw_config      | key, value                                         | Cấu hình runtime     |
| mw_pending     | rid, user_id, model, created_at                    | Requests dang stream |
| mw_audit_log   | ts, user_id, model, status, tokens, cost_usd       | Log tat ca requests  |
| mw_request_log | ts, method, path, status_code, latency_ms          | Log HTTP access      |

Luu y: Khong co Foreign Key giua 2 databases (by design - cross-database FK khong kha thi trong PostgreSQL). user_id luu dang TEXT.

### 7.2. ERD - Database middleware

```
+----------------+     +--------------------+     +----------------+
|  mw_users      |     |  mw_audit_log      |     |  mw_pending    |
|----------------|     |--------------------|     |----------------|
| user_id (PK)   |     | id (PK, SERIAL)    |     | rid (PK)       |
| subkey_hash    |     | ts                 |     | user_id        |
| role           |     | user_id (TEXT)     |     | model          |
| active         |     | model              |     | created_at     |
| allowed_models |     | endpoint           |     +----------------+
| quota (JSONB)  |     | status             |
| used_tokens    |     | tokens_total       |     +----------------+
| used_cost_usd  |     | cost_usd           |     |  mw_prices     |
+----------------+     | latency_ms         |     |----------------|
                       | payload (JSONB)    |     | model (PK)     |
                       +--------------------+     | input_per_1m   |
                                                  | output_per_1m  |
                       +--------------------+     | image_cost     |
                       |  mw_request_log    |     +----------------+
                       |--------------------|
                       | id (PK, SERIAL)    |     +----------------+
                       | ts                 |     |  mw_config     |
                       | method             |     |----------------|
                       | path               |     | key (PK)       |
                       | status_code        |     | value (JSONB)  |
                       | latency_ms         |     | updated_at     |
                       | payload (JSONB)    |     +----------------+
                       +--------------------+
```

### 7.3. Tich hop - API Providers

20 models duoc cấu hình trong litellm/litellm_config.yaml:
- 14 chat models (8 OpenAI + 6 Google)
- 3 image models (1 OpenAI + 2 Google)
- 1 TTS model (OpenAI)
- 2 STT models (OpenAI)

### 7.4. Luong xu ly chinh

#### Luong Chat (BR-01)

```
1. User go prompt > Open WebUI
2. Open WebUI goi POST /v1/chat/completions (Header: Bearer <subkey>)
3. Middleware nhan request:
   a. Validate subkey > tim user trong mw_users
   b. Kiểm tra active = true
   c. Kiểm tra model trong allowed_models
   d. Kiểm tra quota (cost_usd < limit_cost_usd)
   e. Ghi audit_log (status: pending)
   f. Forward > LiteLLM (port 4000)
4. LiteLLM route > OpenAI hoac Gemini API
5. Response stream ve:
   a. Middleware tinh cost = tokens x price_per_token
   b. Update mw_users: used_tokens += X, used_cost_usd += Y
   c. Ghi audit_log (status: ok, cost, tokens)
6. Open WebUI render response (markdown, code highlight)
```

#### Luong RAG (BR-09 > BR-13)

```
INDEXING:
1. User upload file > Open WebUI
2. Extract text (PyPDF2, python-docx, openpyxl)
3. Split > chunks (1000 chars, 200 overlap)
4. Embedding (sentence-transformers/all-MiniLM-L6-v2) > vector(384)
5. Store > PostgreSQL document_chunk table (HNSW indexed)

RETRIEVAL:
1. User hoi #KB "Chinh sach nghi phep?"
2. Embed query > vector(384)
3. Hybrid search: BM25 (keyword) + cosine similarity (vector)
4. Top-K=4 chunks > inject vao system prompt
5. LLM tra loi kem citations
```

#### Luong Image Generation (BR-06)

```
1. User dung /image hoac Action button
2. POST /v1/images/generations > Middleware
3. Validate auth + quota + model allowed
4. Forward > LiteLLM > OpenAI DALL-E / Gemini Image
5. Response: image URL hoac base64
6. Middleware tinh cost (fixed per image)
7. Update quota, ghi audit log
```

---

## 8. BAO MAT VA AN TOAN THONG TIN

### 8.1. Kiến trúc bảo mật da tang

```
+------------------------------------------------------------------+
| LAYER 1: NETWORK                                                 |
| Docker internal network - chi port 3000, 5000 expose ra ngoai    |
| Firewall rules cho port 3000 (WebUI), 5000 (API/Dashboard)       |
+------------------------------------------------------------------+
| LAYER 2: AUTHENTICATION                                          |
| Open WebUI: Email/Password + JWT token                           |
| Middleware: Subkey HMAC-SHA256 (Bearer token)                    |
| Dashboard: Admin key + JWT cookie (HttpOnly, 4h expiry)          |
+------------------------------------------------------------------+
| LAYER 3: AUTHORIZATION (RBAC)                                    |
| Roles: Admin > Manager > User > Pending                         |
| Model restriction per user (allowed_models)                      |
| Knowledge access control (per collection)                        |
+------------------------------------------------------------------+
| LAYER 4: DATA SECURITY                                           |
| Embedding chay 100% local - tai lieu KHONG gui ra ngoai          |
| Database trong Docker volume - khong cloud DB                    |
| Subkey hashing: HMAC-SHA256 (one-way, khong decrypt duoc)        |
| Audit trail: moi request deu duoc ghi log                        |
+------------------------------------------------------------------+
```

### 8.2. Chi tiet Authentication

| Thanh phan     | Phương thức           | Chi tiet                        |
| -------------- | --------------------- | ------------------------------- |
| Open WebUI     | Email + Password      | Bcrypt hash, JWT token          |
| Middleware API | Subkey (Bearer token) | HMAC-SHA256 with MW_SECRET salt |
| Dashboard      | Admin key             | JWT cookie, HttpOnly, 4h expiry |
| LiteLLM        | Master key            | LITELLM_MASTER_KEY (env var)    |

### 8.3. Subkey Security

```
Quy trinh tao subkey:
1. Tao plaintext: secrets.token_urlsafe(32) > "sk_abc123def456..."
2. Hash: HMAC-SHA256(plaintext, MW_SECRET) > "a1b2c3d4..."
3. Luu DB: chi luu hash (subkey_hash)
4. Hien thi plaintext CHI 1 LAN cho admin
5. User dung plaintext lam Bearer token khi goi API

Khi authenticate:
1. Request den: Authorization: Bearer sk_abc123def456...
2. Middleware hash(sk_abc123...) > a1b2c3d4...
3. So sanh hash voi mw_users.subkey_hash
4. Match > xác thực thanh cong
```

### 8.4. Network va Data Security

| Moi de doa         | Bien phap                                          |
| ------------------ | -------------------------------------------------- |
| Truy cap trai phep | Firewall chi mo port 3000, 5000                    |
| XSS                | HttpOnly cookie, CSP headers                       |
| CSRF               | SameSite=Lax cookie                                |
| Man-in-the-middle  | Docker internal network (khong expose LiteLLM, PG) |
| Ro ri dữ liệu RAG  | Embedding chay local, vector luu on-premise        |
| Brute-force subkey | HMAC-SHA256 + constant-time comparison             |
| Lam dung API       | Quota enforcement, rate limiting per user          |

### 8.5. Luu y quan trong

- Noi dung chat DUOC GUI toi OpenAI/Google qua API - day la ban chat cua dịch vụ LLM cloud.
- Tai lieu Knowledge (RAG) KHONG GUI - embedding chay 100% local tren server.
- Database luu tren server rieng - khong sử dụng cloud database.

---

## 9. QUY TRINH VAN HANH

### 9.1. Khởi động / Dung hệ thống

| Thao tac          | Lenh                              | Ghi chu                |
| ----------------- | --------------------------------- | ---------------------- |
| Start all         | docker compose up -d              | Khởi động 4 services   |
| Stop all          | docker compose down               | Dung, giu data         |
| Restart           | docker compose restart            | Restart tat ca         |
| Restart 1 service | docker compose restart middleware | Chi restart middleware |
| View logs         | docker compose logs -f middleware | Follow logs real-time  |
| Check status      | docker compose ps                 | Xem trang thai         |

### 9.2. Thao tac dinh ky

| Chu ky     | Thao tac                | Chi tiet                                     |
| ---------- | ----------------------- | -------------------------------------------- |
| Hang ngay  | Duyet user pending      | Admin Panel > Users > Approve                |
| Hang ngay  | Kiểm tra chi phí        | Dashboard (http://<server>:5000/dashboard)   |
| Hang tuan  | Review chi phí per user | Dashboard > Filter by user, xem trends       |
| Hang tuan  | Health check            | docker compose ps - tat ca container running |
| Hang tuan  | Backup database         | pg_dump command                              |
| Hang thang | Review quota            | Dieu chinh quota theo muc sử dụng thuc te    |
| Hang thang | Update hệ thống         | docker compose pull && docker compose up -d  |

### 9.3. Backup va Recovery

```
# Backup database openwebui
docker exec openwebui-postgres pg_dump -U openwebui_user -d openwebui > backup_openwebui.sql

# Backup database middleware
docker exec openwebui-postgres pg_dump -U openwebui_user -d middleware > backup_middleware.sql

# Restore
docker exec -i openwebui-postgres psql -U openwebui_user -d openwebui < backup_openwebui.sql
```

### 9.4. Monitoring va Dashboard

Truy cap: http://<server>:5000/dashboard

7 Metrics Cards:

| Card         | Y nghia                           | Ngưỡng cảnh báo        |
| ------------ | --------------------------------- | ---------------------- |
| LLM Calls    | Tong requests (chat/image/audio)  | -                      |
| Admin Ops    | Thao tac admin (reconcile, reset) | -                      |
| Pending      | Requests dang xu ly               | > 10: kiểm tra LiteLLM |
| Error Rate   | % loi                             | > 5%: dieu tra         |
| P95 Latency  | 95th percentile latency           | > 5000ms: kiểm tra     |
| Total Tokens | Tokens da xu ly                   | -                      |
| Total Cost   | Chi phí USD                       | Theo budget            |

Tabs: Overview / Logs / Access / Users

---

## PHU LUC

### A. Thong tin truy cap

| Dịch vụ      | URL                            | Doi tuong         |
| ------------ | ------------------------------ | ----------------- |
| Open WebUI   | http://<server>:3000           | Tat ca users      |
| Dashboard    | http://<server>:5000/dashboard | Admin only        |
| API Endpoint | http://<server>:5000/v1        | Tich hop ứng dụng |
| Health Check | http://<server>:5000/health    | Monitoring        |

### B. File cấu hình

| File                        | Muc dich                  | Khi nao sua              |
| --------------------------- | ------------------------- | ------------------------ |
| docker-compose.yml          | Cấu hình toan bo stack    | Doi port, tang resource  |
| .env                        | API keys, mật khẩu        | Doi API key, mật khẩu DB |
| litellm/litellm_config.yaml | Danh sach 20 models       | Them/bot model AI        |
| llm-mw/data/users.json      | User backup (source: DB)  | Khong sua truc tiep      |
| llm-mw/data/prices.json     | Price backup (source: DB) | Khong sua truc tiep      |

### C. Thuat ngu

| Thuat ngu | Giai thich                                                 |
| --------- | ---------------------------------------------------------- |
| LLM       | Large Language Model - mô hình ngon ngu lon                |
| RAG       | Retrieval-Augmented Generation - sinh ket hop truy xuat    |
| Embedding | Chuyen text thanh vector so de so sanh ngu nghia           |
| PGVector  | Extension PostgreSQL cho vector similarity search          |
| HNSW      | Hierarchical Navigable Small World - thuat toan tim vector |
| Subkey    | Ma xác thực API cho middleware (dang sk_...)               |
| Quota     | Hạn mức sử dụng (tokens, USD, image requests)              |
| SSE       | Server-Sent Events - stream dữ liệu real-time              |
| JWT       | JSON Web Token - token xác thực phien                      |
| RBAC      | Role-Based Access Control - phân quyền theo vai tro        |

---

Tai lieu duoc tao ngay 06/03/2026. Phien ban 1.0.
Lien he doi ky thuat AI de biet them chi tiet.
