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

| STT | Mã     | Tên tài liệu         | Mô tả                                                     | Đối tượng       |
| --- | ------ | -------------------- | --------------------------------------------------------- | --------------- |
| 01  | DOC-01 | Tổng quan hệ thống   | Tài liệu này - phạm vi, yêu cầu, kiến trúc, bảo mật       | Tất cả          |
| 02  | DOC-02 | Tài liệu vận hành    | Hướng dẫn vận hành chuyên sâu, troubleshooting            | QTV hệ thống    |
| 03  | DOC-03 | Kiến trúc Middleware | Chi tiết middleware proxy: routing, quota, cost tracking  | Đội kỹ thuật    |
| 04  | DOC-04 | Sơ đồ kiến trúc      | Diagrams: system context, component, data flow, ERD       | Đội kỹ thuật    |
| 05  | DOC-05 | Kiến trúc Database   | Schema 32+ tables, Open WebUI + Middleware databases      | Đội kỹ thuật    |
| 06  | DOC-06 | Kiến trúc RAG        | RAG pipeline: embedding, chunking, vector search, HNSW    | Đội kỹ thuật    |
| 07  | DOC-07 | API Reference        | REST API endpoints, request/response, error codes         | Đội phát triển  |
| 08  | DOC-08 | Dashboard Admin      | Dashboard UI, metrics, filters, charts, user CRUD         | QTV hệ thống    |
| 09  | DOC-09 | Quản lý người dùng   | User CRUD, RBAC, subkey management, audit trail           | QTV hệ thống    |
| 10  | DOC-10 | Hướng dẫn sử dụng    | Hướng dẫn end-user: chat, RAG, image gen, export          | Người dùng      |
| 11  | DOC-11 | Báo cáo tổng quan    | Báo cáo trình bày cho lãnh đạo, so sánh giải pháp         | Ban lãnh đạo    |
| 12  | DOC-12 | Checklist tính năng  | 103+ tính năng, trạng thái, kết quả test                  | QTV và Kỹ thuật |
| 13  | DOC-13 | Cảnh báo Quota       | Hệ thống cảnh báo quota, email notification, SSE          | QTV hệ thống    |
| 14  | DOC-14 | Kế hoạch mở rộng     | Phase 1-3: tối ưu server, scale ngang, multi-server       | Đội kỹ thuật    |
| 15  | DOC-15 | Nginx HTTPS          | Reverse proxy, SSL, routing, rate limiting, vận hành      | QTV hệ thống    |
| 16  | DOC-16 | Web Search           | SearXNG, Redis cache, filter function, thời gian/địa điểm | Đội kỹ thuật    |
| 17  | DOC-17 | Cân bằng tải         | Phân bổ tài nguyên, rate limit, LiteLLM routing, RPM      | Đội kỹ thuật    |

Thứ tự đọc khuyến nghị: DOC-01 > DOC-11 > DOC-10 > DOC-02 > DOC-08 > DOC-03 > DOC-05

---

## 2. TỔNG QUAN, PHẠM VI VÀ MỤC ĐÍCH

### 2.1. Giới thiệu hệ thống

Hệ thống AI nội bộ (Open WebUI Stack) là nền tảng trợ lý AI tập trung cho toàn tổ chức. Hệ thống hoạt động như một "ChatGPT nội bộ" nhưng bổ sung các khả năng:

- Kiểm soát chi phí chủ động (quota / user / tháng)
- Bảo mật dữ liệu (vectors lưu on-premise, embedding qua Gemini API)
- Quản trị tập trung (dashboard real-time, audit trail)
- Đa nhà cung cấp (OpenAI + Gemini + xAI + Anthropic qua 1 gateway duy nhất)

### 2.2. Phạm vi

| STT | Tiêu chí           | Chi tiết                                                              |
| --- | ------------------ | --------------------------------------------------------------------- |
| 01  | Quy mô tổ chức     | Doanh nghiệp từ 200+ nhân viên, nhiều phòng ban                       |
| 02  | Phòng ban mục tiêu | Tất cả: Kỹ thuật, Kinh doanh, Nhân sự, Tài chính, Marketing, R&D      |
| 03  | Địa lý             | HTTPS qua domain nội bộ + NAT firewall (truy cập LAN và WAN)          |
| 04  | Ngôn ngữ           | Hỗ trợ 50+ ngôn ngữ (tối ưu tiếng Việt và tiếng Anh)                  |
| 05  | Nền tảng           | Web-based - truy cập qua trình duyệt (Chrome, Firefox, Edge, Safari ) |
| 06  | Hạ tầng            | On-premise (Docker trên Windows Server, 20 CPU / 32GB RAM)            |
| 07  | Mô hình triển khai | Docker Compose 9 services + Nginx HTTPS reverse proxy                 |

### 2.3. Mục đích

#### A. Thay thế dịch vụ SaaS phân tán

| STT | Trước                                              | Sau                                              |
| --- | -------------------------------------------------- | ------------------------------------------------ |
| 01  | Mỗi nhân viên tự đăng ký ChatGPT/Gemini riêng lẻ   | Một cổng truy cập duy nhất cho tất cả dịch vụ AI |
| 02  | Không kiểm soát chi phí - phát sinh ngoài kế hoạch | Quota chặt chẽ theo user/phòng ban/tháng         |
| 03  | Rủi ro rò rỉ dữ liệu qua tài khoản cá nhân         | Tài liệu nội bộ xử lý 100% trên server riêng     |
| 04  | Không có audit trail - không biết ai dùng gì       | Log chi tiết mọi request: cost, model, user      |

#### B. Nền tảng tập trung và Quản trị chủ động

- Quản trị người dùng: CRUD users, phân quyền RBAC (Admin / Manager / User / Pending)
- Quản trị quota: Giới hạn chi phí, token, số ảnh theo user/nhóm/tháng
- Quản trị model: Chọn model nào hiển thị cho user nào, giới hạn model đắt
- Theo dõi real-time: Dashboard 7 KPIs + biểu đồ + SSE live stream
- Kiểm soát dữ liệu: Knowledge Base quản lý tập trung, phân quyền access

#### C. Tối ưu chi phí sử dụng AI

- Multi-provider routing: Tự động chọn provider rẻ nhất cho cùng chất lượng
- Bảng giá model: Cập nhật giá input/output token cho 19 models trong DB
- Quota enforcement: Vượt quota - tự động từ chối, không phát sinh chi phí ngoài kế hoạch
- Cost dashboard: Real-time tracking chi phí theo user, model, thời gian
- Ước tính: 10 users x 20 requests/ngày ~ $50-150/tháng (so với $300/tháng cho ChatGPT Enterprise)

### 2.4. Đối tượng sử dụng

| STT | Vai trò               | Truy cập                                   | Chức năng chính                                   |
| --- | --------------------- | ------------------------------------------ | ------------------------------------------------- |
| 01  | Ban lãnh đạo          | Báo cáo tổng quan                          | Xem chi phí, ROI, tình trạng hệ thống             |
| 02  | Quản trị viên (Admin) | `https://domain:51122/dashboard`           | Quản lý user, quota, model, knowledge, monitoring |
| 03  | Trưởng bộ phận        | `https://domain:51122/`                    | Quản lý knowledge phòng ban, xem chi phí nhóm     |
| 04  | Nhân viên (User)      | `https://openwebui.rangdong.com.vn:51122/` | Chat AI, RAG, tạo ảnh, xuất file, TTS/STT         |
| 05  | Kỹ thuật viên         | SSH + Docker CLI                           | Vận hành, bảo trì, cập nhật hệ thống              |

---

## 3. YÊU CẦU NGHIỆP VỤ

### 3.1. Chat AI đa phương thức

| STT | ID    | Yêu cầu          | Mô tả                                                       | Ưu tiên    |
| --- | ----- | ---------------- | ----------------------------------------------------------- | ---------- |
| 01  | BR-01 | Chat text        | Hỏi đáp, soạn thảo, phân tích, dịch thuật qua AI            | Cao        |
| 02  | BR-02 | Đa model         | Chọn từ 14 model chat (GPT-5, GPT-4o, Gemini 2.5, Gemini 3) | Cao        |
| 03  | BR-03 | Vision input     | Gửi ảnh/screenshot để AI phân tích (multimodal)             | Trung bình |
| 04  | BR-04 | Context 1M token | Đọc hiểu tài liệu hàng trăm trang trong 1 session           | Trung bình |
| 05  | BR-05 | Lịch sử chat     | Lưu trữ và tìm kiếm lịch sử hội thoại                       | Cao        |

### 3.2. Tạo ảnh AI

| STT | ID    | Yêu cầu               | Mô tả                                         | Ưu tiên    |
| --- | ----- | --------------------- | --------------------------------------------- | ---------- |
| 01  | BR-06 | Text-to-Image         | Tạo ảnh từ mô tả text: banner, poster, mockup | Trung bình |
| 02  | BR-07 | Đa provider           | DALL-E 3 (OpenAI) + Gemini Image (Google)     | Trung bình |
| 03  | BR-08 | Kiểm soát chi phí ảnh | Quota riêng cho image requests                | Trung bình |

### 3.3. RAG / Knowledge Base

| STT | ID    | Yêu cầu              | Mô tả                                                  | Ưu tiên |
| --- | ----- | -------------------- | ------------------------------------------------------ | ------- |
| 01  | BR-09 | Upload tài liệu      | PDF, Word, Excel, CSV, TXT, HTML - max 50MB/file       | Cao     |
| 02  | BR-10 | Tìm kiếm ngữ nghĩa   | Hybrid search (BM25 + vector cosine similarity)        | Cao     |
| 03  | BR-11 | Trích dẫn nguồn      | AI trả lời kèm citation (tên file, trang, đoạn)        | Cao     |
| 04  | BR-12 | Phân quyền Knowledge | Chỉ user/nhóm được grant mới truy cập Knowledge        | Cao     |
| 05  | BR-13 | Embedding qua API    | Text chunks gửi tới Gemini API, vectors lưu on-premise | Cao     |

### 3.4. Quản lý chi phí và Quota

| STT | ID    | Yêu cầu           | Mô tả                                                       | Ưu tiên    |
| --- | ----- | ----------------- | ----------------------------------------------------------- | ---------- |
| 01  | BR-14 | Quota per user    | Giới hạn cost_usd, tokens, image_requests/tháng             | Cao        |
| 02  | BR-15 | Auto-enforce      | Vượt quota - 403 tự động, không cần admin can thiệp         | Cao        |
| 03  | BR-16 | Dashboard chi phí | Real-time: tổng cost, top users, top models, xu hướng       | Cao        |
| 04  | BR-17 | Audit trail       | Ghi lại EVERY request: user, model, tokens, cost, timestamp | Cao        |
| 05  | BR-18 | Bảng giá model    | Mỗi model có giá input/output riêng, cập nhật trong DB      | Trung bình |

### 3.5. Xuất dữ liệu và Tools

| STT | ID    | Yêu cầu      | Mô tả                                          | Ưu tiên    |
| --- | ----- | ------------ | ---------------------------------------------- | ---------- |
| 01  | BR-19 | Export Excel | Trích xuất bảng biểu - .xlsx có format, filter | Trung bình |
| 02  | BR-20 | Export PDF   | Xuất hội thoại - PDF hỗ trợ tiếng Việt         | Trung bình |
| 03  | BR-21 | Export Word  | Xuất hội thoại - .docx                         | Trung bình |
| 04  | BR-22 | TTS/STT      | Text-to-Speech + Speech-to-Text                | Thấp       |

### 3.6. Quản trị người dùng

| STT | ID    | Yêu cầu           | Mô tả                                             | Ưu tiên |
| --- | ----- | ----------------- | ------------------------------------------------- | ------- |
| 01  | BR-23 | User CRUD         | Tạo, sửa, xóa user từ Dashboard hoặc API          | Cao     |
| 02  | BR-24 | Subkey management | Mã hóa HMAC-SHA256, rotate key, plaintext 1 lần   | Cao     |
| 03  | BR-25 | Role-based access | Admin / Manager / User / Pending                  | Cao     |
| 04  | BR-26 | Active/Disable    | Toggle enable/disable per user - 403 khi disabled | Cao     |

---

## 4. YÊU CẦU PHI CHỨC NĂNG

### 4.1. Hiệu năng (Performance)

| STT | Chỉ số             | Yêu cầu                  | Ghi chú                        |
| --- | ------------------ | ------------------------ | ------------------------------ |
| 01  | Latency P95        | < 2000ms (text chat)     | Không tính LLM generation time |
| 02  | Throughput         | 50+ concurrent users     | Docker resource-dependent      |
| 03  | RAG indexing       | < 60s cho file 100 trang | ~313 chunks x embedding        |
| 04  | Dashboard response | < 500ms (summary API)    | 5s polling interval            |
| 05  | SSE stream         | Real-time < 100ms delay  | Server-Sent Events             |

### 4.2. Khả dụng (Availability)

| STT | Chỉ số               | Yêu cầu                              | Ghi chú                           |
| --- | -------------------- | ------------------------------------ | --------------------------------- |
| 01  | Uptime               | 99.5% (giờ hành chính)               | ~4h downtime/tháng cho bảo trì    |
| 02  | Auto-restart         | restart: unless-stopped              | Docker tự khởi động lại khi crash |
| 03  | Health check         | Mỗi 10s (PostgreSQL), 5s (Dashboard) | Tự động detect failure            |
| 04  | Graceful degradation | LiteLLM down - lỗi nhưng MW vẫn OK   | Isolation giữa các service        |

### 4.3. Bảo mật (Security)
 
| STT | Chỉ số         | Yêu cầu                        | Ghi chú                                    |
| --- | -------------- | ------------------------------ | ------------------------------------------ |
| 01  | Authentication | JWT + HMAC-SHA256 subkey       | Multi-layer auth                           |
| 02  | Session        | HttpOnly cookie, 4h expiry     | Chống XSS                                  |
| 03  | Network        | Docker internal network        | Internal services không expose             |
| 04  | Data at rest   | PostgreSQL trong Docker volume | Không cloud DB                             |
| 05  | Embedding      | Gemini API (qua Middleware)    | Text chunks gửi Google, vectors on-premise |

### 4.4. Khả năng mở rộng (Scalability)

| STT | Chiều      | Phương pháp                    | Ghi chú               |
| --- | ---------- | ------------------------------ | --------------------- |
| 01  | Horizontal | Docker replicas cho middleware | Scale read throughput |
| 02  | Vertical   | Tăng RAM/CPU container         | Cho embedding, DB     |
| 03  | Storage    | PostgreSQL + Docker volumes    | Expandable            |
| 04  | Models     | Thêm vào litellm_config.yaml   | Hot-plug models       |

### 4.5. Tương thích (Compatibility)

| STT | Thành phần  | Yêu cầu                                        |
| --- | ----------- | ---------------------------------------------- |
| 01  | Trình duyệt | Chrome 90+, Firefox 88+, Edge 90+, Safari 14+  |
| 02  | Server OS   | Windows Server 2019+, Ubuntu 20.04+, CentOS 8+ |
| 03  | Docker      | Docker Engine 24.0+, Docker Compose v2.20+     |
| 04  | Database    | PostgreSQL 16 + PGVector 0.8.0                 |

---

## 5. MÔ TẢ CHỨC NĂNG VÀ SƠ ĐỒ TỔNG THỂ

### 5.1. Tổng quan chức năng

| STT | Module                     | Số tính năng | Trạng thái    | Mô tả                                        |
| --- | -------------------------- | ------------ | ------------- | -------------------------------------------- |
| 01  | Phân quyền và Quản lý user | 12           | Hoạt động     | Đăng ký, phân quyền, RBAC, Admin Panel       |
| 02  | Chat AI                    | 18           | Hoạt động     | 14 models, streaming, markdown, code         |
| 03  | Knowledge Base và RAG      | 15           | Hoạt động     | Upload, embedding, hybrid search, citations  |
| 04  | **Web Search (SearXNG)**   | **6**        | **Hoạt động** | **SearXNG tự host, Native FC, multi-engine** |
| 05  | Tạo ảnh (Image Gen)        | 6            | Hoạt động     | DALL-E 3, Gemini Image, cost tracking        |
| 06  | Giọng nói (TTS/STT)        | 4            | Hoạt động     | Text-to-Speech, Speech-to-Text               |
| 07  | Custom Tools               | 3            | Hoạt động     | Export Excel/PDF/Word                        |
| 08  | Middleware Proxy           | 20           | Hoạt động     | Auth, quota, cost, routing, audit            |
| 09  | Dashboard Admin            | 15           | Hoạt động     | 7 KPIs, charts, filters, user CRUD           |
| 10  | Cấu hình và Tùy chỉnh      | 10           | Hoạt động     | Model settings, RAG config, UI themes        |
| 11  | TỔNG CỘNG                  | 109          |               |                                              |

### 5.2. Sơ đồ System Context

```
    ┌────────────────────────────────────────────────────────────────┐
    │                     NGƯỜI DÙNG (200+ nhân viên)                │
    │   https://openwebui.rangdong.com.vn:51122/                     │
    │   https://openwebui.rangdong.com.vn:51122/dashboard            │
    └───────────────────────────┬────────────────────────────────────┘
                                │
                    Firewall NAT: 51122 → 3000
                                │
    ╔═══════════════════════════╪════════════════════════════════════╗
    ║  Windows Server (20 CPU / 32GB RAM)                            ║
    ║  Docker Compose · 9 containers · openwebui-network             ║
    ║                               │                                ║
    ║  ┌────────────────────────────▼────────────────────────────┐   ║
    ║  │       NGINX (openwebui-nginx) :3000 HTTPS               │   ║
    ║  │       ← DUY NHẤT PORT MỞ RA NGOÀI →                     │   ║
    ║  │  SSL: wildcard *.rangdong.com.vn (TLS 1.2/1.3)          │   ║
    ║  │  Rate limit: 10 req/s (chat), 5 req/phút (login)        │   ║
    ║  │  Gzip: CSS, JS, JSON, SVG | Upload: max 100MB           │   ║
    ║  │                                                         │   ║
    ║  │  Routing (nginx.conf):                                  │   ║
    ║  │  /                → open-webui:8080  (chat UI)          │   ║
    ║  │  /_app/, /static/ → open-webui:8080  (JS/CSS assets)    │   ║
    ║  │  /ws/             → open-webui:8080  (WebSocket)        │   ║
    ║  │  /api/v1/auths/   → open-webui:8080  (login, 5req/m)    │   ║
    ║  │  /v1/             → middleware:5000  (LLM API proxy)    │   ║
    ║  │  /v1/_mw/         → middleware:5000  (admin API + SSE)  │   ║
    ║  │  /dashboard       → middleware:5000  (admin SPA)        │   ║
    ║  └──────┬─────────────────────────────────────┬────────────┘   ║
    ║         │                                     │                ║
    ║         ▼                                     ▼                ║
    ║  ┌──────────────────┐              ┌───────────────────────┐   ║
    ║  │  OPEN WEBUI      │              │  MIDDLEWARE           │   ║
    ║  │  :8080 (6 wrk)   │              │  :5000 (4 workers)    │   ║
    ║  │  CPU: 6 | 10GB   │              │  CPU: 4 | 2GB         │   ║
    ║  │                  │────────────▶ │                       │   ║
    ║  │  Chat, RAG, KBs  │ LLM requests │  Auth (subkey HMAC)   │   ║
    ║  │  File upload     │ qua MW proxy │  Quota enforcement    │   ║
    ║  │  Admin Panel     │              │  Cost tracking        │   ║
    ║  │  User Auth (JWT) │              │  Dashboard SPA        │   ║
    ║  │                  │              │  Audit trail (SSE)    │   ║
    ║  └──┬─────────┬─────┘              └──────┬────────────────┘   ║
    ║     │         │                           │                    ║
    ║     │ DB      │ Web Search                │ Forward LLM        ║
    ║     │         │                           │                    ║
    ║     │         ▼                           ▼                    ║
    ║     │  ┌──────────────┐          ┌─────────────────────┐       ║
    ║     │  │  SEARXNG     │          │  LITELLM            │       ║
    ║     │  │  :8080       │          │  :4000 (4 workers)  │       ║
    ║     │  │  CPU: 1 | 1GB│          │  CPU: 4 | 4GB       │       ║
    ║     │  │              │          │                     │       ║
    ║     │  │  DuckDuckGo  │          │  Model routing      │       ║
    ║     │  │  Brave       │          │  Retry / Fallback   │       ║
    ║     │  │  Bing        │          │  SSE streaming      │       ║
    ║     │  │  Google (tắt)│          │  19 models config   │       ║
    ║     │  └───────┬──────┘          └──────────┬──────────┘       ║
    ║     │          │ cache                      │                  ║
    ║     │          ▼                            │                  ║
    ║     │  ┌──────────────┐                     │                  ║
    ║     │  │  REDIS       │                     │                  ║
    ║     │  │  :6379       │                     │                  ║
    ║     │  │  CPU:0.5|256M│                     │                  ║
    ║     │  │  Search cache│                     │                  ║
    ║     │  └──────────────┘                     │                  ║
    ║     │                                       │                  ║
    ║     ▼                                       │                  ║
    ║  ┌──────────────────────┐                   │                  ║
    ║  │  POSTGRESQL          │                   │                  ║
    ║  │  :5432               │                   │                  ║
    ║  │  CPU: 2 | 8GB        │                   │                  ║
    ║  │  + PGVector 0.8.0    │                   │                  ║
    ║  │                      │                   │                  ║
    ║  │  DB: openwebui (26T) │                   │                  ║
    ║  │  DB: middleware (6T) │◄── MW ghi audit───┘                  ║
    ║  │                      │                                      ║
    ║  │  Tuning: shared=4GB  │                                      ║
    ║  │  max_conn=300        │                                      ║
    ║  └──────────────────────┘                                      ║
    ║                                                                ║
    ║  DOCLING (:5001) — OCR/Document extraction (PDF, DOCX, scan)    ║
    ║                                                                ║
    ║  Port mở: CHỈ Nginx :3000/tcp                                  ║
    ║  Port ĐÓNG: 8080, 5000, 5001, 4000, 5432, 6379                  ║
    ╚══════════════════════════════════════════════╪═════════════════╝
                                                   │
                                    LiteLLM gọi API ra ngoài
                                                   │
                           ┌───────────────┬───────────────┤──────────┐
                           │               │               │          │
                           ▼               ▼               ▼          ▼
                    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
                    │ OpenAI   │    │ Google   │    │ xAI      │    │ Anthropic│
                    │ GPT-5    │    │ Gemini   │    │ Grok-4   │    │ Claude4.6│
                    │ image    │    │ 2.5/3    │    │          │    │          │
                    │          │    │ Image    │    │          │    │          │
                    └──────────┘    └──────────┘    └──────────┘    └──────────┘
```

### 5.3. Sơ đồ Use Case

```
+-------------------------------------------------------------+
| STT | HỆ THỐNG AI NỘI BỘ                                    |
| --- | ----------------------------------------------------- |
| 01  |                                                       |
| 02  | [End User]  ---- Chat AI (text, vision, streaming)    |
| 03  | ---- Hỏi đáp Knowledge Base (#KB)                     |
| 04  | ---- Upload tài liệu vào Knowledge                    |
| 05  | ---- Tạo ảnh (/image)                                 |
| 06  | ---- Xuất file (Excel, PDF, Word)                     |
| 07  | ---- Nhập giọng nói (STT) / Nghe (TTS)                |
| 08  |                                                       |
| 09  | [Admin]     ---- Quản lý user (CRUD, quota, subkey)   |
| 10  | ---- Xem Dashboard chi phí real-time                  |
| 11  | ---- Duyệt user pending                               |
| 12  | ---- Cấu hình model, knowledge                        |
| 13  | ---- Xem audit logs, access logs                      |
| 14  | ---- Backup database                                  |
| 15  |                                                       |
| 16  | [Sys Admin] ---- Vận hành Docker (start/stop/restart) |
| 17  | ---- Monitoring health check                          |
| 18  | ---- Cập nhật code, thêm model                        |
| 19  | ---- Troubleshooting và recovery                      |
| 20  |                                                       |
+-------------------------------------------------------------+
```

---

## 6. CẤU TRÚC CẤU PHẦN HỆ THỐNG

### 6.1. Tổng quan 7 tầng (Tier Architecture)

| STT | Tier     | Service    | Port (nội bộ)                  | Workers | CPU      | RAM        | Mục đích                                     |
| --- | -------- | ---------- | ------------------------------ | ------- | -------- | ---------- | -------------------------------------------- |
| 01  | Tier 0   | **Nginx**  | **3000** (HTTPS, cửa duy nhất) | auto    | 1        | 512MB      | Reverse proxy, SSL, rate limiting, gzip      |
| 02  | Tier 1   | Open WebUI | 8080                           | 6       | 6        | 10GB       | Giao diện người dùng, chat, RAG, knowledge   |
| 03  | Tier 2   | Middleware | 5000                           | 4       | 4        | 2GB        | Auth, quota, cost tracking, dashboard, audit |
| 04  | Tier 3a  | LiteLLM    | 4000                           | 4       | 4        | 4GB        | LLM proxy: routing, retry, model mapping     |
| 05  | Tier 3b  | PostgreSQL | 5432                           | —       | 2        | 8GB        | Database + vector search, tuning 32GB RAM    |
| 06  | Tier 4a  | SearXNG    | 8080                           | —       | 1        | 1GB        | Web search: DuckDuckGo, Brave, Bing          |
| 07  | Tier 4b  | Redis      | 6379                           | —       | 0.5      | 256MB      | Cache search results + SearXNG rate limiter  |
| 08  | **Tổng** |            |                                | **14**  | **18.5** | **25.8GB** | Còn dư 1.5 CPU + 6GB cho OS                  |

### 6.2. Open WebUI (Tier 1) - Giao diện người dùng

Container: openwebui-app

| STT | Module            | Chức năng                                         |
| --- | ----------------- | ------------------------------------------------- |
| 01  | Chat Engine       | Đa model, streaming, markdown rendering           |
| 02  | Knowledge Manager | Upload file, tạo collections, phân quyền          |
| 03  | RAG Pipeline      | Text extraction > chunking > embedding > PGVector |
| 04  | User Auth         | Email/password + JWT, role-based                  |
| 05  | Admin Panel       | Quản lý users, models, knowledge, settings        |
| 06  | Custom Tools      | Export Excel/PDF/Word qua Action buttons          |

### 6.3. Middleware (Tier 2) - Xác thực và Quản trị

Container: openwebui-middleware

| STT | Module         | File               | Chức năng                                   |
| --- | -------------- | ------------------ | ------------------------------------------- |
| 01  | API Gateway    | main.py            | FastAPI app, route registration, CORS       |
| 02  | Auth Core      | core/auth.py       | Subkey validation, user lookup, HMAC-SHA256 |
| 03  | Cost Engine    | core/cost.py       | Price lookup, cost calculation, quota check |
| 04  | Database       | core/db.py         | PostgreSQL connection pool, schema, CRUD    |
| 05  | Alerting       | core/alerting.py   | Quota alerts, webhook notifications         |
| 06  | User Admin API | api/user_admin.py  | CRUD users, rotate key, delete              |
| 07  | Summary API    | api/summary.py     | Metrics aggregation, time-window filtering  |
| 08  | Stream API     | api/stream.py      | SSE real-time events                        |
| 09  | Access Logs    | api/access_logs.py | Paginated access log queries                |
| 10  | Audit API      | api/audit_query.py | Admin audit trail query                     |
| 11  | Dashboard      | dashboard/         | HTML/CSS/JS SPA: charts, filters, user CRUD |

### 6.4. LiteLLM (Tier 3a) - LLM Proxy

Container: openwebui-litellm

| STT | Chức năng      | Mô tả                                                   |
| --- | -------------- | ------------------------------------------------------- |
| 01  | Model Routing  | Map chat-gpt-5 > openai/gpt-5, chat-gemini > gemini/... |
| 02  | Multi-provider | OpenAI + Gemini + xAI + Anthropic qua 1 gateway         |
| 03  | Retry/Fallback | Tự động retry khi lỗi, fallback sang provider khác      |
| 04  | Streaming      | Forward SSE stream từ LLM > middleware > client         |
| 05  | Config         | litellm/litellm_config.yaml - 19 models định nghĩa sẵn  |

### 6.5. PostgreSQL + PGVector (Tier 3b)

Container: openwebui-postgres

| STT | Database   | Số bảng | Mục đích                                             |
| --- | ---------- | ------- | ---------------------------------------------------- |
| 01  | openwebui  | 26      | User, chat, file, knowledge, document_chunk (vector) |
| 02  | middleware | 6       | mw_users, mw_prices, mw_config, mw_pending, mw_audit |

### 6.6. Docker Infrastructure

```
docker-compose.yml:

  services:                                              Port     CPU   RAM
    nginx           # nginx:alpine                       3000     1     512MB  ← CỬA DUY NHẤT
    postgres        # pgvector/pgvector:0.8.0-pg16       —        2     8GB
    redis           # redis:7-alpine                     —        0.5   256MB
    litellm         # ghcr.io/berriai/litellm             —        4     4GB
    middleware      # Custom build (./llm-mw/Dockerfile)  —        4     2GB
    open-webui      # Custom build (Dockerfile.openwebui) —        6     10GB
    searxng          # searxng/searxng:latest              —        1     1GB

  volumes:
    postgres_data       # Database persistent storage
    litellm_logs        # LiteLLM log files
    openwebui_data      # Open WebUI uploads, files
    searxng_data        # SearXNG config & cache

  nginx config files:
    nginx/nginx.conf    # Reverse proxy config (routing, SSL, rate limit)
    nginx/ssl/          # SSL certificate (fullchain.pem + privkey.pem)

  networks:
    openwebui-network   # Internal bridge network (tất cả container)
```

---

## 7. KIẾN TRÚC DỮ LIỆU, TÍCH HỢP VÀ LUỒNG XỬ LÝ

### 7.1. Schema Database

#### Database openwebui - 26 bảng chính

| STT | Nhóm      | Bảng                            | Mục đích                        |
| --- | --------- | ------------------------------- | ------------------------------- |
| 01  | User      | user, auth                      | Thông tin user, credentials     |
| 02  | Chat      | chat, channel, message          | Hội thoại, kênh, tin nhắn       |
| 03  | Knowledge | knowledge, file, knowledge_file | Collections, files, liên kết    |
| 04  | RAG       | document, document_chunk        | Text chunks + vector(1536) HNSW |
| 05  | Admin     | config, feedback, tag           | Cấu hình, đánh giá, gắn thẻ     |
| 06  | Groups    | group                           | Nhóm người dùng, phân quyền     |

#### Database middleware - 6 bảng

| STT | Bảng           | Columns chính                                      | Mục đích             |
| --- | -------------- | -------------------------------------------------- | -------------------- |
| 01  | mw_users       | user_id, subkey_hash, role, active, allowed_models | Quản lý user API     |
| 02  | mw_prices      | model, input_per_1m, output_per_1m, image_cost     | Bảng giá model       |
| 03  | mw_config      | key, value                                         | Cấu hình runtime     |
| 04  | mw_pending     | rid, user_id, model, created_at                    | Requests đang stream |
| 05  | mw_audit_log   | ts, user_id, model, status, tokens, cost_usd       | Log tất cả requests  |
| 06  | mw_request_log | ts, method, path, status_code, latency_ms          | Log HTTP access      |

Lưu ý: Không có Foreign Key giữa 2 databases (by design - cross-database FK không khả thi trong PostgreSQL). user_id lưu dạng TEXT.

### 7.2. ERD - Database middleware

```
+----------------+     +--------------------+     +----------------+
| STT | mw_users     |  | mw_audit_log    |  | mw_pending |
| --- | ------------ |  | --------------- |  | ---------- |
| 01  | user_id (PK) |  | id (PK, SERIAL) |  | rid (PK)   |
| 02  | subkey_hash  |  | ts              |  | user_id    |
| 03  | role         |  | user_id (TEXT)  |  | model      |
| 04  | active       |  | model           |  | created_at |
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
| STT | ts          |  | mw_config     |
| --- | ----------- |  | ------------- |
| 01  | path        |  | key (PK)      |
| 02  | status_code |  | value (JSONB) |
| 03  | latency_ms  |  | updated_at    |
                       | payload (JSONB)    |     +----------------+
                       +--------------------+
```

### 7.3. Tích hợp - API Providers

19 models được cấu hình trong litellm/litellm_config.yaml:
- 12 chat models (3 OpenAI + 3 Google + 3 xAI + 3 Anthropic)
- 6 image models (2 OpenAI + 2 Google + 2 xAI)
- 1 embedding model (Google Gemini)

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
3. Split > chunks (1500 chars, 100 overlap)
4. Embedding (gemini-embedding-001 qua Middleware→LiteLLM→Google API) > vector(1536)
5. Store > PostgreSQL document_chunk table (HNSW indexed)

RETRIEVAL:
1. User hỏi #KB "Chính sách nghỉ phép?"
2. Embed query > vector(1536)
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

#### Luồng Web Search (Native Function Calling)

```
1. User hỏi câu cần thông tin realtime (VD: "Giá vàng hôm nay?")
2. Open WebUI gửi prompt + tool definition (web_search) > Middleware > LiteLLM > LLM
3. LLM quyết định gọi tool web_search (Native Function Calling)
4. Open WebUI nhận tool_call > gọi SearXNG: GET http://searxng:8080/search?q=<query>&format=json
5. SearXNG tìm kiếm trên Google, Brave, DuckDuckGo > trả kết quả JSON
6. Open WebUI inject kết quả vào context > gọi LLM lần 2 để sinh câu trả lời
7. LLM trả lời kèm trích dẫn nguồn (citations)
8. Chi phí: $0 cho search (SearXNG tự host), chỉ tính LLM tokens qua Middleware
```

Điều kiện để Web Search hoạt động:
- Admin Panel > Settings > Web Search: engine = searxng, URL = http://searxng:8080/search?q=<query>&format=json
- Model config: Capabilities > Web Search ✅, Default Features > Web Search ✅
- Advanced Params > Function Calling = **Native** (cho model hỗ trợ: GPT-5, GPT-4o, Gemini 2.5+/3)

---

## 8. BẢO MẬT VÀ AN TOÀN THÔNG TIN

### 8.1. Kiến trúc bảo mật đa tầng

```
+------------------------------------------------------------------+
| LAYER 0: NGINX (Reverse Proxy)                                   |
| HTTPS TLS 1.2/1.3 — wildcard cert *.rangdong.com.vn              |
| Rate limiting: 10 req/s (chat), 5 req/phút (login)               |
| Chỉ 1 port mở: 3000 (NAT 51122 từ ngoài)                        |
+------------------------------------------------------------------+
| LAYER 1: NETWORK                                                 |
| Docker internal network — TẤT CẢ port internal ĐÓNG              |
| PostgreSQL, LiteLLM, Middleware, WebUI: KHÔNG expose port         |
+------------------------------------------------------------------+
| LAYER 2: AUTHENTICATION                                          |
| Open WebUI: Email/Password + JWT token                           |
| Middleware: Subkey HMAC-SHA256 (Bearer token)                    |
| Dashboard: Admin key + JWT cookie (HttpOnly, secure=True, 4h)    |
+------------------------------------------------------------------+
| LAYER 3: AUTHORIZATION (RBAC)                                    |
| Roles: Admin > Manager > User > Pending                         |
| Model restriction per user (allowed_models)                      |
| Knowledge access control (per collection)                        |
+------------------------------------------------------------------+
| LAYER 4: DATA SECURITY                                           |
| Text chunks gửi tới Gemini API để embedding - vectors lưu on-premise  |
| Database trong Docker volume - không cloud DB                    |
| Subkey hashing: HMAC-SHA256 (one-way, không decrypt được)        |
| Audit trail: mọi request đều được ghi log                        |
+------------------------------------------------------------------+
```

### 8.2. Chi tiết Authentication

| STT | Thành phần     | Phương thức           | Chi tiết                        |
| --- | -------------- | --------------------- | ------------------------------- |
| 01  | Open WebUI     | Email + Password      | Bcrypt hash, JWT token          |
| 02  | Middleware API | Subkey (Bearer token) | HMAC-SHA256 with MW_SECRET salt |
| 03  | Dashboard      | Admin key             | JWT cookie, HttpOnly, 4h expiry |
| 04  | LiteLLM        | Master key            | LITELLM_MASTER_KEY (env var)    |

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

| STT | Mối đe dọa         | Biện pháp                                          |
| --- | ------------------ | -------------------------------------------------- |
| 01  | Truy cập trái phép | Nginx: chỉ 1 port mở (3000 HTTPS)                  |
| 02  | XSS                | HttpOnly cookie, CSP headers                       |
| 03  | CSRF               | SameSite=Lax cookie, secure=True                   |
| 04  | Man-in-the-middle  | HTTPS TLS 1.2/1.3 + Docker internal network        |
| 05  | Rò rỉ dữ liệu RAG  | Text chunks gửi Gemini API, vectors lưu on-premise |
| 06  | Brute-force login  | Nginx rate limit 5 req/phút cho /api/v1/auths/     |
| 07  | Brute-force subkey | HMAC-SHA256 + constant-time comparison             |
| 08  | DDoS / Spam        | Nginx rate limit 10 req/s + burst=50 per IP        |
| 09  | Lạm dụng API       | Quota enforcement + Nginx rate limiting            |

### 8.5. Lưu ý quan trọng

- Nội dung chat ĐƯỢC GỬI tới OpenAI/Google/xAI/Anthropic qua API - đây là bản chất của dịch vụ LLM cloud.
- Text chunks từ tài liệu Knowledge (RAG) ĐƯỢC GỬI tới Google Gemini API để tạo embedding vectors.
- Vectors embedding và tài liệu gốc lưu on-premise trong PGVector - không cloud DB.

---

## 9. QUY TRÌNH VẬN HÀNH

### 9.1. Khởi động / Dừng hệ thống

| STT | Thao tác          | Lệnh                                          | Ghi chú                      |
| --- | ----------------- | --------------------------------------------- | ---------------------------- |
| 01  | Start all         | `docker compose up -d`                        | Khởi động 9 services         |
| 02  | Stop all          | `docker compose down`                         | Dừng, giữ data               |
| 03  | Restart           | `docker compose restart`                      | Restart tất cả               |
| 04  | Restart 1 service | `docker compose restart middleware`           | Chỉ restart middleware       |
| 05  | Nginx reload      | `docker exec openwebui-nginx nginx -s reload` | Reload config, 0 downtime    |
| 06  | View logs         | `docker compose logs -f middleware`           | Follow logs real-time        |
| 07  | Check status      | `docker compose ps`                           | Xem trạng thái               |
| 08  | Nginx test config | `docker exec openwebui-nginx nginx -t`        | Validate config trước reload |

### 9.2. Thao tác định kỳ

| STT | Chu kỳ     | Thao tác                | Chi tiết                                            |
| --- | ---------- | ----------------------- | --------------------------------------------------- |
| 01  | Hàng ngày  | Duyệt user pending      | Admin Panel > Users > Approve                       |
| 02  | Hàng ngày  | Kiểm tra chi phí        | `https://openwebui.rangdong.com.vn:51122/dashboard` |
| 03  | Hàng tuần  | Review chi phí per user | Dashboard > Filter by user, xem trends              |
| 04  | Hàng tuần  | Health check            | `docker compose ps` - tất cả 8 container running    |
| 05  | Hàng tuần  | Backup database         | pg_dump command                                     |
| 06  | Hàng tháng | Review quota            | Điều chỉnh quota theo mức sử dụng thực tế           |
| 07  | Hàng tháng | Update hệ thống         | `docker compose pull; docker compose up -d`         |
| 08  | Hàng năm   | Gia hạn SSL cert        | Copy cert mới vào nginx/ssl/ → nginx reload         |

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

Truy cập: `https://openwebui.rangdong.com.vn:51122/dashboard`

7 Metrics Cards:

| STT | Card         | Ý nghĩa                           | Ngưỡng cảnh báo        |
| --- | ------------ | --------------------------------- | ---------------------- |
| 01  | LLM Calls    | Tổng requests (chat/image/audio)  | -                      |
| 02  | Admin Ops    | Thao tác admin (reconcile, reset) | -                      |
| 03  | Pending      | Requests đang xử lý               | > 10: kiểm tra LiteLLM |
| 04  | Error Rate   | % lỗi                             | > 5%: điều tra         |
| 05  | P95 Latency  | 95th percentile latency           | > 5000ms: kiểm tra     |
| 06  | Total Tokens | Tokens đã xử lý                   | -                      |
| 07  | Total Cost   | Chi phí USD                       | Theo budget            |

Tabs: Overview / Logs / Access / Users

---

## PHỤ LỤC

### A. Thông tin truy cập

| STT | Dịch vụ      | URL                                                 | Đối tượng         |
| --- | ------------ | --------------------------------------------------- | ----------------- |
| 01  | Open WebUI   | `https://openwebui.rangdong.com.vn:51122/`          | Tất cả users      |
| 02  | Dashboard    | `https://openwebui.rangdong.com.vn:51122/dashboard` | Admin only        |
| 03  | API Endpoint | `https://openwebui.rangdong.com.vn:51122/v1/`       | Tích hợp ứng dụng |
| 04  | Nội bộ (LAN) | `https://192.168.20.66:3000/`                       | Truy cập nội bộ   |

### B. File cấu hình

| STT | File                        | Mục đích                   | Khi nào sửa                |
| --- | --------------------------- | -------------------------- | -------------------------- |
| 01  | docker-compose.yml          | Cấu hình 9 services        | Đổi port, tăng resource    |
| 02  | .env                        | API keys, mật khẩu         | Đổi API key, mật khẩu DB   |
| 03  | nginx/nginx.conf            | Reverse proxy + SSL config | Thêm route, đổi rate limit |
| 04  | nginx/ssl/fullchain.pem     | SSL certificate            | Gia hạn cert hàng năm      |
| 05  | nginx/ssl/privkey.pem       | SSL private key            | Gia hạn cert hàng năm      |
| 06  | litellm/litellm_config.yaml | Danh sách 19 models        | Thêm/bớt model AI          |
| 07  | searxng/settings.yml        | Cấu hình SearXNG search    | Thêm/bớt search engine     |
| 08  | llm-mw/data/users.json      | User backup (source: DB)   | Không sửa trực tiếp        |
| 09  | llm-mw/data/prices.json     | Price backup (source: DB)  | Không sửa trực tiếp        |

### C. Thuật ngữ

| STT | Thuật ngữ | Giải thích                                                  |
| --- | --------- | ----------------------------------------------------------- |
| 01  | LLM       | Large Language Model - mô hình ngôn ngữ lớn                 |
| 02  | RAG       | Retrieval-Augmented Generation - sinh kết hợp truy xuất     |
| 03  | Embedding | Chuyển text thành vector số để so sánh ngữ nghĩa            |
| 04  | PGVector  | Extension PostgreSQL cho vector similarity search           |
| 05  | HNSW      | Hierarchical Navigable Small World - thuật toán tìm vector  |
| 06  | Subkey    | Mã xác thực API cho middleware (dạng sk_...)                |
| 07  | Quota     | Hạn mức sử dụng (tokens, USD, image requests)               |
| 08  | SSE       | Server-Sent Events - stream dữ liệu real-time               |
| 09  | JWT       | JSON Web Token - token xác thực phiên                       |
| 10  | RBAC      | Role-Based Access Control - phân quyền theo vai trò         |
| 11  | SearXNG   | Metasearch engine tự host - tổng hợp kết quả từ nhiều nguồn |
| 12  | Native FC | Native Function Calling - model tự quyết định gọi tool      |

---

Tài liệu được tạo ngày 06/03/2026. Cập nhật lần cuối: 27/03/2026 (Phiên bản 2.0 — thêm Nginx HTTPS, Redis, resource limits, đóng ports).
Liên hệ đội kỹ thuật AI để biết thêm chi tiết.
