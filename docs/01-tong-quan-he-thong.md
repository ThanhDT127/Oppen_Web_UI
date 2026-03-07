# TÀI LIỆU TỔNG QUAN HỆ THỐNG OPPENWEBUI AI NỘI BỘ


## MỤC LỤC

1. Chỉ mục tài liệu
2. Tổng quan, Phạm vi và Mục đích
3. Yêu cầu nghiệp vụ
4. Yêu cầu phi chức năng
5. Mô tả chức năng và Sơ đồ tổng thể
6. Cấu trúc cấu phần hệ thống
7. Kiến trúc dữ liệu, Tích hợp và Luồng xử lý
8. Bảo mật và An toàn thông tin
9. Quy trình vận hành

---

## 1. CHỈ MỤC TÀI LIỆU

| STT | Mã     | Tên tài liệu          | Mô tả                                                     | Đối tượng       |
| --- | ------ | --------------------- | --------------------------------------------------------- | --------------- |
| 01  | DOC-01 | Tổng quan hệ thống    | Tài liệu này - phạm vi, yêu cầu, kiến trúc, bảo mật       | Tất cả          |
| 02  | DOC-02 | Tài liệu vận hành     | Hướng dẫn vận hành chuyên sâu, troubleshooting            | QTV hệ thống    |
| 03  | DOC-03 | Kiến trúc Middleware  | Chi tiết middleware proxy: routing, quota, cost tracking  | Đội kỹ thuật    |
| 04  | DOC-04 | Sơ đồ kiến trúc       | Diagrams: system context, component, data flow, ERD       | Đội kỹ thuật    |
| 05  | DOC-05 | Kiến trúc Database    | Schema 32+ tables, Open WebUI + Middleware databases      | Đội kỹ thuật    |
| 06  | DOC-06 | Kiến trúc RAG         | RAG pipeline: embedding, chunking, vector search, HNSW    | Đội kỹ thuật    |
| 07  | DOC-07 | API Reference         | REST API endpoints, request/response, error codes         | Đội phát triển  |
| 08  | DOC-08 | Dashboard Admin       | Dashboard UI, metrics, filters, charts, user CRUD         | QTV hệ thống    |
| 09  | DOC-09 | Quản lý người dùng    | User CRUD, RBAC, subkey management, audit trail           | QTV hệ thống    |
| 10  | DOC-10 | Hướng dẫn sử dụng     | Hướng dẫn end-user: chat, RAG, image gen, export          | Người dùng      |
| 11  | DOC-11 | Báo cáo tổng quan     | Báo cáo trình bày cho lãnh đạo, so sánh giải pháp         | Ban lãnh đạo    |
| 12  | DOC-12 | Checklist tính năng   | 103+ tính năng, trạng thái, kết quả test                  | QTV và Kỹ thuật |

Thứ tự đọc khuyến nghị: DOC-01 > DOC-11 > DOC-10 > DOC-02 > DOC-08 > DOC-03 > DOC-05

---

## 2. TỔNG QUAN, PHẠM VI VÀ MỤC ĐÍCH

### 2.1. Giới thiệu hệ thống

Hệ thống AI nội bộ (Open WebUI Stack) là nền tảng trợ lý AI tập trung cho toàn tổ chức. Hệ thống hoạt động như một "ChatGPT nội bộ" nhưng bổ sung các khả năng:

- Kiểm soát chi phí chủ động (quota / user / tháng)
- Bảo mật dữ liệu (embedding chạy local, tài liệu không rời server)
- Quản trị tập trung (dashboard real-time, audit trail)
- Đa nhà cung cấp (OpenAI + Google Gemini qua 1 gateway duy nhất)

### 2.2. Phạm vi

| Tiêu chí            | Chi tiết                                                              |
| ------------------- | --------------------------------------------------------------------- |
| Quy mô tổ chức      | Doanh nghiệp từ 200+ nhân viên, nhiều phòng ban                       |
| Phòng ban mục tiêu  | Tất cả: Kỹ thuật, Kinh doanh, Nhân sự, Tài chính, Marketing, R&D      |
| Địa lý              | Mạng nội bộ LAN/VPN - truy cập từ bất kỳ máy nào trong mạng           |
| Ngôn ngữ            | Hỗ trợ 50+ ngôn ngữ (tối ưu tiếng Việt và tiếng Anh)                  |
| Nền tảng            | Web-based - truy cập qua trình duyệt (Chrome, Firefox, Edge, Safari ) |
| Hạ tầng             | On-premise (Docker trên Windows Server hoặc Linux)                    |
| Mô hình triển khai  | Docker Compose - khởi động trong 2 phút                               |

### 2.3. Mục đích

#### A. Thay thế dịch vụ SaaS phân tán

| Trước                                               | Sau                                               |
| --------------------------------------------------- | ------------------------------------------------- |
| Mỗi nhân viên tự đăng ký ChatGPT/Gemini riêng lẻ    | Một cổng truy cập duy nhất cho tất cả dịch vụ AI  |
| Không kiểm soát chi phí - phát sinh ngoài kế hoạch  | Quota chặt chẽ theo user/phòng ban/tháng          |
| Rủi ro rò rỉ dữ liệu qua tài khoản cá nhân          | Tài liệu nội bộ xử lý 100% trên server riêng      |
| Không có audit trail - không biết ai dùng gì        | Log chi tiết mọi request: cost, model, user       |

#### B. Nền tảng tập trung và Quản trị chủ động

- Quản trị người dùng: CRUD users, phân quyền RBAC (Admin / Manager / User / Pending)
- Quản trị quota: Giới hạn chi phí, token, số ảnh theo user/nhóm/tháng
- Quản trị model: Chọn model nào hiển thị cho user nào, giới hạn model đắt
- Theo dõi real-time: Dashboard 7 KPIs + biểu đồ + SSE live stream
- Kiểm soát dữ liệu: Knowledge Base quản lý tập trung, phân quyền access

#### C. Tối ưu chi phí sử dụng AI

- Multi-provider routing: Tự động chọn provider rẻ nhất cho cùng chất lượng
- Bảng giá model: Cập nhật giá input/output token cho 20 models trong DB
- Quota enforcement: Vượt quota - tự động từ chối, không phát sinh chi phí ngoài kế hoạch
- Cost dashboard: Real-time tracking chi phí theo user, model, thời gian
- Ước tính: 10 users x 20 requests/ngày ~ $50-150/tháng (so với $300/tháng cho ChatGPT Enterprise)

### 2.4. Đối tượng sử dụng

| Vai trò               | Truy cập                | Chức năng chính                                   |
| --------------------- | ----------------------- | ------------------------------------------------- |
| Ban lãnh đạo          | Báo cáo tổng quan       | Xem chi phí, ROI, tình trạng hệ thống             |
| Quản trị viên (Admin) | Dashboard + Admin Panel | Quản lý user, quota, model, knowledge, monitoring |
| Trưởng bộ phận        | Open WebUI + Dashboard  | Quản lý knowledge phòng ban, xem chi phí nhóm     |
| Nhân viên (User)      | Open WebUI (port 3000)  | Chat AI, RAG, tạo ảnh, xuất file, TTS/STT         |
| Kỹ thuật viên         | Full stack access       | Vận hành, bảo trì, cập nhật hệ thống              |

---

## 3. YÊU CẦU NGHIỆP VỤ

### 3.1. Chat AI đa phương thức

| ID    | Yêu cầu          | Mô tả                                                        | Ưu tiên    |
| ----- | ----------------- | ------------------------------------------------------------| ---------- |
| BR-01 | Chat text         | Hỏi đáp, soạn thảo, phân tích, dịch thuật qua AI            | Cao        |
| BR-02 | Đa model          | Chọn từ 14 model chat (GPT-5, GPT-4o, Gemini 2.5, Gemini 3) | Cao        |
| BR-03 | Vision input      | Gửi ảnh/screenshot để AI phân tích (multimodal)             | Trung bình |
| BR-04 | Context 1M token  | Đọc hiểu tài liệu hàng trăm trang trong 1 session           | Trung bình |
| BR-05 | Lịch sử chat      | Lưu trữ và tìm kiếm lịch sử hội thoại                       | Cao        |

### 3.2. Tạo ảnh AI

| ID    | Yêu cầu                | Mô tả                                           | Ưu tiên    |
| ----- | ---------------------- | ----------------------------------------------- | ---------- |
| BR-06 | Text-to-Image          | Tạo ảnh từ mô tả text: banner, poster, mockup   | Trung bình |
| BR-07 | Đa provider            | DALL-E 3 (OpenAI) + Gemini Image (Google)       | Trung bình |
| BR-08 | Kiểm soát chi phí ảnh  | Quota riêng cho image requests                  | Trung bình |

### 3.3. RAG / Knowledge Base

| ID    | Yêu cầu               | Mô tả                                             | Ưu tiên |
| ----- | ----------------------| ------------------------------------------------- | ------- |
| BR-09 | Upload tài liệu       | PDF, Word, Excel, CSV, TXT, HTML - max 50MB/file  | Cao     |
| BR-10 | Tìm kiếm ngữ nghĩa    | Hybrid search (BM25 + vector cosine similarity)   | Cao     |
| BR-11 | Trích dẫn nguồn       | AI trả lời kèm citation (tên file, trang, đoạn)   | Cao     |
| BR-12 | Phân quyền Knowledge  | Chỉ user/nhóm được grant mới truy cập Knowledge   | Cao     |
| BR-13 | Embedding local       | Dữ liệu nội bộ KHÔNG gửi ra bên ngoài             | Cao     |

### 3.4. Quản lý chi phí và Quota

| ID    | Yêu cầu            | Mô tả                                                        | Ưu tiên    |
| ----- | ------------------ | -------------------------------------------------------------| ---------- |
| BR-14 | Quota per user     | Giới hạn cost_usd, tokens, image_requests/tháng              | Cao        |
| BR-15 | Auto-enforce       | Vượt quota - 403 tự động, không cần admin can thiệp          | Cao        |
| BR-16 | Dashboard chi phí  | Real-time: tổng cost, top users, top models, xu hướng        | Cao        |
| BR-17 | Audit trail        | Ghi lại EVERY request: user, model, tokens, cost, timestamp  | Cao        |
| BR-18 | Bảng giá model     | Mỗi model có giá input/output riêng, cập nhật trong DB       | Trung bình |

### 3.5. Xuất dữ liệu và Tools

| ID    | Yêu cầu       | Mô tả                                            | Ưu tiên    |
| ----- | ------------- | ------------------------------------------------ | ---------- |
| BR-19 | Export Excel  | Trích xuất bảng biểu - .xlsx có format, filter   | Trung bình |
| BR-20 | Export PDF    | Xuất hội thoại - PDF hỗ trợ tiếng Việt           | Trung bình |
| BR-21 | Export Word   | Xuất hội thoại - .docx                           | Trung bình |
| BR-22 | TTS/STT       | Text-to-Speech + Speech-to-Text                  | Thấp       |

### 3.6. Quản trị người dùng

| ID    | Yêu cầu            | Mô tả                                               | Ưu tiên |
| ----- | ------------------ | --------------------------------------------------- | ------- |
| BR-23 | User CRUD          | Tạo, sửa, xóa user từ Dashboard hoặc API            | Cao     |
| BR-24 | Subkey management  | Mã hóa HMAC-SHA256, rotate key, plaintext 1 lần     | Cao     |
| BR-25 | Role-based access  | Admin / Manager / User / Pending                    | Cao     |
| BR-26 | Active/Disable     | Toggle enable/disable per user - 403 khi disabled   | Cao     |

---

## 4. YÊU CẦU PHI CHỨC NĂNG

### 4.1. Hiệu năng (Performance)

| Chỉ số               | Yêu cầu                   | Ghi chú                          |
| -------------------- | ------------------------- | -------------------------------- |
| Latency P95          | < 2000ms (text chat)      | Không tính LLM generation time   |
| Throughput           | 50+ concurrent users      | Docker resource-dependent        |
| RAG indexing         | < 60s cho file 100 trang  | ~313 chunks x embedding          |
| Dashboard response   | < 500ms (summary API)     | 5s polling interval              |
| SSE stream           | Real-time < 100ms delay   | Server-Sent Events               |

### 4.2. Khả dụng (Availability)

| Chỉ số                 | Yêu cầu                                | Ghi chú                            |
| ---------------------- | -------------------------------------- | -----------------------------------|
| Uptime                 | 99.5% (giờ hành chính)                 | ~4h downtime/tháng cho bảo trì     |
| Auto-restart           | restart: unless-stopped                | Docker tự khởi động lại khi crash  |
| Health check           | Mỗi 10s (PostgreSQL), 5s (Dashboard)   | Tự động detect failure             |
| Graceful degradation   | LiteLLM down - lỗi nhưng MW vẫn OK     | Isolation giữa các service         |

### 4.3. Bảo mật (Security)
 
| Chỉ số           |  Yêu cầu                             | Ghi chú                          |
| ---------------- | ------------------------------------ | -------------------------------- |
| Authentication   | JWT + HMAC-SHA256 subkey             | Multi-layer auth                 |
| Session          | HttpOnly cookie, 4h expiry           | Chống XSS                        |
| Network          | Docker internal network              | Internal services không expose   |
| Data at rest     | PostgreSQL trong Docker volume       | Không cloud DB                   |
| Embedding        | 100% local (sentence-transformers)   | Tài liệu nội bộ KHÔNG ra ngoài   |

### 4.4. Khả năng mở rộng (Scalability)

| Chiều       | Phương pháp                     | Ghi chú                |
| ----------- | ------------------------------- | ---------------------- |
| Horizontal  | Docker replicas cho middleware  | Scale read throughput  |
| Vertical    | Tăng RAM/CPU container          | Cho embedding, DB      |
| Storage     | PostgreSQL + Docker volumes     | Expandable             |
| Models      | Thêm vào litellm_config.yaml   | Hot-plug models         |

### 4.5. Tương thích (Compatibility)

| Thành phần   | Yêu cầu                                          |
| ------------ | ------------------------------------------------ |
| Trình duyệt  | Chrome 90+, Firefox 88+, Edge 90+, Safari 14+    |
| Server OS    | Windows Server 2019+, Ubuntu 20.04+, CentOS 8+   |
| Docker       | Docker Engine 24.0+, Docker Compose v2.20+       |
| Database     | PostgreSQL 16 + PGVector 0.8.0                   |

---

## 5. MÔ TẢ CHỨC NĂNG VÀ SƠ ĐỒ TỔNG THỂ

### 5.1. Tổng quan chức năng

| Module                       | Số tính năng | Trạng thái | Mô tả                                         |
| ---------------------------- | ------------ | ---------- | --------------------------------------------- |
| Phân quyền và Quản lý user   | 12           | Hoạt động  | Đăng ký, phân quyền, RBAC, Admin Panel        |
| Chat AI                      | 18           | Hoạt động  | 14 models, streaming, markdown, code          |
| Knowledge Base và RAG        | 15           | Hoạt động  | Upload, embedding, hybrid search, citations   |
| Tạo ảnh (Image Gen)          | 6            | Hoạt động  | DALL-E 3, Gemini Image, cost tracking         |
| Giọng nói (TTS/STT)          | 4            | Hoạt động  | Text-to-Speech, Speech-to-Text                |
| Custom Tools                 | 3            | Hoạt động  | Export Excel/PDF/Word                         |
| Middleware Proxy             | 20           | Hoạt động  | Auth, quota, cost, routing, audit             |
| Dashboard Admin              | 15           | Hoạt động  | 7 KPIs, charts, filters, user CRUD            |
| Cấu hình và Tùy chỉnh        | 10           | Hoạt động  | Model settings, RAG config, UI themes         |
| TỔNG CỘNG                    | 103          |            |                                               |

### 5.2. Sơ đồ System Context

```
                         NGƯỜI DÙNG
                    (200+ nhân viên, Admin)
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

### 5.3. Sơ đồ Use Case

```
+-------------------------------------------------------------+
|                  HỆ THỐNG AI NỘI BỘ                         |
|-------------------------------------------------------------|
|                                                             |
|  [End User]  ---- Chat AI (text, vision, streaming)         |
|              ---- Hỏi đáp Knowledge Base (#KB)              |
|              ---- Upload tài liệu vào Knowledge             |
|              ---- Tạo ảnh (/image)                          |
|              ---- Xuất file (Excel, PDF, Word)              |
|              ---- Nhập giọng nói (STT) / Nghe (TTS)        |
|                                                             |
|  [Admin]     ---- Quản lý user (CRUD, quota, subkey)        |
|              ---- Xem Dashboard chi phí real-time           |
|              ---- Duyệt user pending                        |
|              ---- Cấu hình model, knowledge                 |
|              ---- Xem audit logs, access logs               |
|              ---- Backup database                           |
|                                                             |
|  [Sys Admin] ---- Vận hành Docker (start/stop/restart)      |
|              ---- Monitoring health check                   |
|              ---- Cập nhật code, thêm model                 |
|              ---- Troubleshooting và recovery               |
|                                                             |
+-------------------------------------------------------------+
```

---

## 6. CẤU TRÚC CẤU PHẦN HỆ THỐNG

### 6.1. Tổng quan 4 tầng (Tier Architecture)

| Tier    | Service    | Port | Công nghệ                 | Mục đích                                      |
| ------- | ---------- | ---- | ------------------------- | --------------------------------------------- |
| Tier 1  | Open WebUI | 3000 | Python + SvelteKit        | Giao diện người dùng, chat, RAG, knowledge    |
| Tier 2  | Middleware | 5000 | Python + FastAPI          | Auth, quota, cost tracking, dashboard, audit  |
| Tier 3a | LiteLLM    | 4000 | Python                    | LLM proxy: routing, retry, model mapping      |
| Tier 3b | PostgreSQL | 5432 | PostgreSQL 16 + PGVector  | Database + vector search                      |

### 6.2. Open WebUI (Tier 1) - Giao diện người dùng

Container: openwebui-app

| Module            | Chức năng                                          |
| ----------------- | -------------------------------------------------- |
| Chat Engine       | Đa model, streaming, markdown rendering            |
| Knowledge Manager | Upload file, tạo collections, phân quyền           |
| RAG Pipeline      | Text extraction > chunking > embedding > PGVector  |
| User Auth         | Email/password + JWT, role-based                   |
| Admin Panel       | Quản lý users, models, knowledge, settings         |
| Custom Tools      | Export Excel/PDF/Word qua Action buttons           |

### 6.3. Middleware (Tier 2) - Xác thực và Quản trị

Container: openwebui-middleware

| Module         | File               | Chức năng                                    |
| -------------- | ------------------ | -------------------------------------------- |
| API Gateway    | main.py            | FastAPI app, route registration, CORS        |
| Auth Core      | core/auth.py       | Subkey validation, user lookup, HMAC-SHA256  |
| Cost Engine    | core/cost.py       | Price lookup, cost calculation, quota check  |
| Database       | core/db.py         | PostgreSQL connection pool, schema, CRUD     |
| Alerting       | core/alerting.py   | Quota alerts, webhook notifications          |
| User Admin API | api/user_admin.py  | CRUD users, rotate key, delete               |
| Summary API    | api/summary.py     | Metrics aggregation, time-window filtering   |
| Stream API     | api/stream.py      | SSE real-time events                         |
| Access Logs    | api/access_logs.py | Paginated access log queries                 |
| Audit API      | api/audit_query.py | Admin audit trail query                      |
| Dashboard      | dashboard/         | HTML/CSS/JS SPA: charts, filters, user CRUD  |

### 6.4. LiteLLM (Tier 3a) - LLM Proxy

Container: openwebui-litellm

| Chức năng       | Mô tả                                                    |
| --------------- | ---------------------------------------------------------|
| Model Routing   | Map chat-gpt-5 > openai/gpt-5, chat-gemini > gemini/...  |
| Multi-provider  | OpenAI + Google Gemini qua 1 gateway                     |
| Retry/Fallback  | Tự động retry khi lỗi, fallback sang provider khác       |
| Streaming       | Forward SSE stream từ LLM > middleware > client          |
| Config          | litellm/litellm_config.yaml - 20 models định nghĩa sẵn   |

### 6.5. PostgreSQL + PGVector (Tier 3b)

Container: openwebui-postgres

| Database   | Số bảng | Mục đích                                              |
| ---------- | ------- | ----------------------------------------------------- |
| openwebui  | 26      | User, chat, file, knowledge, document_chunk (vector)  |
| middleware | 6       | mw_users, mw_prices, mw_config, mw_pending, mw_audit  |

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

## 7. KIẾN TRÚC DỮ LIỆU, TÍCH HỢP VÀ LUỒNG XỬ LÝ

### 7.1. Schema Database

#### Database openwebui - 26 bảng chính

| Nhóm      | Bảng                             | Mục đích                         |
| --------- | -------------------------------- | -------------------------------- |
| User      | user, auth                       | Thông tin user, credentials      |
| Chat      | chat, channel, message           | Hội thoại, kênh, tin nhắn        |
| Knowledge | knowledge, file, knowledge_file  | Collections, files, liên kết     |
| RAG       | document, document_chunk         | Text chunks + vector(1536) HNSW  |
| Admin     | config, feedback, tag            | Cấu hình, đánh giá, gắn thẻ      |
| Groups    | group                            | Nhóm người dùng, phân quyền      |

#### Database middleware - 6 bảng

| Bảng           | Columns chính                                       | Mục đích              |
| -------------- | --------------------------------------------------- | --------------------- |
| mw_users       | user_id, subkey_hash, role, active, allowed_models  | Quản lý user API      |
| mw_prices      | model, input_per_1m, output_per_1m, image_cost      | Bảng giá model        |
| mw_config      | key, value                                          | Cấu hình runtime      |
| mw_pending     | rid, user_id, model, created_at                     | Requests đang stream  |
| mw_audit_log   | ts, user_id, model, status, tokens, cost_usd        | Log tất cả requests   |
| mw_request_log | ts, method, path, status_code, latency_ms           | Log HTTP access       |

Lưu ý: Không có Foreign Key giữa 2 databases (by design - cross-database FK không khả thi trong PostgreSQL). user_id lưu dạng TEXT.

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

### 7.3. Tích hợp - API Providers

20 models được cấu hình trong litellm/litellm_config.yaml:
- 14 chat models (8 OpenAI + 6 Google)
- 3 image models (1 OpenAI + 2 Google)
- 1 TTS model (OpenAI)
- 2 STT models (OpenAI)

### 7.4. Luồng xử lý chính

#### Luồng Chat (BR-01)

```
1. User gõ prompt > Open WebUI
2. Open WebUI gọi POST /v1/chat/completions (Header: Bearer <subkey>)
3. Middleware nhận request:
   a. Validate subkey > tìm user trong mw_users
   b. Kiểm tra active = true
   c. Kiểm tra model trong allowed_models
   d. Kiểm tra quota (cost_usd < limit_cost_usd)
   e. Ghi audit_log (status: pending)
   f. Forward > LiteLLM (port 4000)
4. LiteLLM route > OpenAI hoặc Gemini API
5. Response stream về:
   a. Middleware tính cost = tokens x price_per_token
   b. Update mw_users: used_tokens += X, used_cost_usd += Y
   c. Ghi audit_log (status: ok, cost, tokens)
6. Open WebUI render response (markdown, code highlight)
```

#### Luồng RAG (BR-09 > BR-13)

```
INDEXING:
1. User upload file > Open WebUI
2. Extract text (PyPDF2, python-docx, openpyxl)
3. Split > chunks (1000 chars, 200 overlap)
4. Embedding (sentence-transformers/all-MiniLM-L6-v2) > vector(384)
5. Store > PostgreSQL document_chunk table (HNSW indexed)

RETRIEVAL:
1. User hỏi #KB "Chính sách nghỉ phép?"
2. Embed query > vector(384)
3. Hybrid search: BM25 (keyword) + cosine similarity (vector)
4. Top-K=4 chunks > inject vào system prompt
5. LLM trả lời kèm citations
```

#### Luồng Image Generation (BR-06)

```
1. User dùng /image hoặc Action button
2. POST /v1/images/generations > Middleware
3. Validate auth + quota + model allowed
4. Forward > LiteLLM > OpenAI DALL-E / Gemini Image
5. Response: image URL hoặc base64
6. Middleware tính cost (fixed per image)
7. Update quota, ghi audit log
```

---

## 8. BẢO MẬT VÀ AN TOÀN THÔNG TIN

### 8.1. Kiến trúc bảo mật đa tầng

```
+------------------------------------------------------------------+
| LAYER 1: NETWORK                                                 |
| Docker internal network - chỉ port 3000, 5000 expose ra ngoài    |
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
| Embedding chạy 100% local - tài liệu KHÔNG gửi ra ngoài         |
| Database trong Docker volume - không cloud DB                    |
| Subkey hashing: HMAC-SHA256 (one-way, không decrypt được)        |
| Audit trail: mọi request đều được ghi log                        |
+------------------------------------------------------------------+
```

### 8.2. Chi tiết Authentication

| Thành phần      | Phương thức            | Chi tiết                         |
| --------------- | ---------------------- | -------------------------------- |
| Open WebUI      | Email + Password       | Bcrypt hash, JWT token           |
| Middleware API  | Subkey (Bearer token)  | HMAC-SHA256 with MW_SECRET salt  |
| Dashboard       | Admin key              | JWT cookie, HttpOnly, 4h expiry  |
| LiteLLM         | Master key             | LITELLM_MASTER_KEY (env var)     |

### 8.3. Subkey Security

```
Quy trình tạo subkey:
1. Tạo plaintext: secrets.token_urlsafe(32) > "sk_abc123def456..."
2. Hash: HMAC-SHA256(plaintext, MW_SECRET) > "a1b2c3d4..."
3. Lưu DB: chỉ lưu hash (subkey_hash)
4. Hiển thị plaintext CHỈ 1 LẦN cho admin
5. User dùng plaintext làm Bearer token khi gọi API

Khi authenticate:
1. Request đến: Authorization: Bearer sk_abc123def456...
2. Middleware hash(sk_abc123...) > a1b2c3d4...
3. So sánh hash với mw_users.subkey_hash
4. Match > xác thực thành công
```

### 8.4. Network và Data Security

| Mối đe dọa           | Biện pháp                                           |
| -------------------- | --------------------------------------------------- |
| Truy cập trái phép   | Firewall chỉ mở port 3000, 5000                     |
| XSS                  | HttpOnly cookie, CSP headers                        |
| CSRF                 | SameSite=Lax cookie                                 |
| Man-in-the-middle    | Docker internal network (không expose LiteLLM, PG)  |
| Rò rỉ dữ liệu RAG    | Embedding chạy local, vector lưu on-premise         |
| Brute-force subkey   | HMAC-SHA256 + constant-time comparison              |
| Lạm dụng API         | Quota enforcement, rate limiting per user           |

### 8.5. Lưu ý quan trọng

- Nội dung chat ĐƯỢC GỬI tới OpenAI/Google qua API - đây là bản chất của dịch vụ LLM cloud.
- Tài liệu Knowledge (RAG) KHÔNG GỬI - embedding chạy 100% local trên server.
- Database lưu trên server riêng - không sử dụng cloud database.

---

## 9. QUY TRÌNH VẬN HÀNH

### 9.1. Khởi động / Dừng hệ thống

| Thao tác            | Lệnh                                | Ghi chú                 |
| ------------------- | ----------------------------------- | ------------------------|
| Start all           | docker compose up -d                | Khởi động 4 services    |
| Stop all            | docker compose down                 | Dừng, giữ data          |
| Restart             | docker compose restart              | Restart tất cả          |
| Restart 1 service   | docker compose restart middleware   | Chỉ restart middleware  |
| View logs           | docker compose logs -f middleware   | Follow logs real-time   |
| Check status        | docker compose ps                   | Xem trạng thái          |

### 9.2. Thao tác định kỳ

| Chu kỳ      | Thao tác                 | Chi tiết                                      |
| ----------- | ------------------------ | --------------------------------------------- |
| Hàng ngày   | Duyệt user pending       | Admin Panel > Users > Approve                 |
| Hàng ngày   | Kiểm tra chi phí         | Dashboard (http://<server>:5000/dashboard)    |
| Hàng tuần   | Review chi phí per user  | Dashboard > Filter by user, xem trends        |
| Hàng tuần   | Health check             | docker compose ps - tất cả container running  |
| Hàng tuần   | Backup database          | pg_dump command                               |
| Hàng tháng  | Review quota             | Điều chỉnh quota theo mức sử dụng thực tế     |
| Hàng tháng  | Update hệ thống          | docker compose pull && docker compose up -d   |

### 9.3. Backup và Recovery

```
# Backup database openwebui
docker exec openwebui-postgres pg_dump -U openwebui_user -d openwebui > backup_openwebui.sql

# Backup database middleware
docker exec openwebui-postgres pg_dump -U openwebui_user -d middleware > backup_middleware.sql

# Restore
docker exec -i openwebui-postgres psql -U openwebui_user -d openwebui < backup_openwebui.sql
```

### 9.4. Monitoring và Dashboard

Truy cập: http://<server>:5000/dashboard

7 Metrics Cards:

| Card         | Ý nghĩa                             | Ngưỡng cảnh báo         |
| ------------ | ----------------------------------- | ------------------------ |
| LLM Calls    | Tổng requests (chat/image/audio)    | -                        |
| Admin Ops    | Thao tác admin (reconcile, reset)   | -                        |
| Pending      | Requests đang xử lý                 | > 10: kiểm tra LiteLLM  |
| Error Rate   | % lỗi                               | > 5%: điều tra           |
| P95 Latency  | 95th percentile latency             | > 5000ms: kiểm tra      |
| Total Tokens | Tokens đã xử lý                     | -                        |
| Total Cost   | Chi phí USD                         | Theo budget              |

Tabs: Overview / Logs / Access / Users

---

## PHỤ LỤC

### A. Thông tin truy cập

| Dịch vụ       | URL                             | Đối tượng           |
| ------------- | ------------------------------- | ------------------- |
| Open WebUI    | http://<server>:3000            | Tất cả users        |
| Dashboard     | http://<server>:5000/dashboard  | Admin only          |
| API Endpoint  | http://<server>:5000/v1         | Tích hợp ứng dụng   |
| Health Check  | http://<server>:5000/health     | Monitoring          |

### B. File cấu hình

| File                        | Mục đích                   | Khi nào sửa               |
| --------------------------- | -------------------------- | --------------------------|
| docker-compose.yml          | Cấu hình toàn bộ stack     | Đổi port, tăng resource   |
| .env                        | API keys, mật khẩu         | Đổi API key, mật khẩu DB  |
| litellm/litellm_config.yaml | Danh sách 20 models        | Thêm/bớt model AI         |
| llm-mw/data/users.json      | User backup (source: DB)   | Không sửa trực tiếp       |
| llm-mw/data/prices.json     | Price backup (source: DB)  | Không sửa trực tiếp       |

### C. Thuật ngữ

| Thuật ngữ  | Giải thích                                                   |
| ---------- | ------------------------------------------------------------ |
| LLM        | Large Language Model - mô hình ngôn ngữ lớn                  |
| RAG        | Retrieval-Augmented Generation - sinh kết hợp truy xuất      |
| Embedding  | Chuyển text thành vector số để so sánh ngữ nghĩa             |
| PGVector   | Extension PostgreSQL cho vector similarity search            |
| HNSW       | Hierarchical Navigable Small World - thuật toán tìm vector   |
| Subkey     | Mã xác thực API cho middleware (dạng sk_...)                 |
| Quota      | Hạn mức sử dụng (tokens, USD, image requests)                |
| SSE        | Server-Sent Events - stream dữ liệu real-time                |
| JWT        | JSON Web Token - token xác thực phiên                        |
| RBAC       | Role-Based Access Control - phân quyền theo vai trò          |

---

Tài liệu được tạo ngày 06/03/2026. Phiên bản 1.0.
Liên hệ đội kỹ thuật AI để biết thêm chi tiết.
