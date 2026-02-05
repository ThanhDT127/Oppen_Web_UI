# 📋 KẾ HOẠCH TỔNG THỂ - TRIỂN KHAI AI AGENT OPPEN WEB UI

> **Phiên bản:** 1.0  
> **Ngày cập nhật:** 03/02/2026  
> **Trạng thái:** Production-Ready  
> **Mục tiêu:** Xây dựng hệ thống AI Chatbot/Agent hỗ trợ Nhóm Contact Center

---

## 📖 MỤC LỤC

1. [Tổng Quan Hệ Thống](#1-tổng-quan-hệ-thống)
2. [Kiến Trúc Kỹ Thuật](#2-kiến-trúc-kỹ-thuật)
3. [Kế Hoạch Triển Khai Chi Tiết](#3-kế-hoạch-triển-khai-chi-tiết)
4. [Chi Tiết Các Giai Đoạn](#4-chi-tiết-các-giai-đoạn)
5. [Thông Tin Kỹ Thuật](#5-thông-tin-kỹ-thuật)
6. [Phân Công Công Việc](#6-phân-công-công-việc)
7. [Tài Liệu Liên Quan](#7-tài-liệu-liên-quan)

---

## 1. Tổng Quan Hệ Thống

### 1.1 Mục Tiêu Dự Án

Xây dựng hệ thống AI Chatbot/Agent với các mục tiêu:

| STT | Mục Tiêu | Trạng Thái |
|-----|----------|------------|
| 1 | Cung cấp UI chat thân thiện cho người dùng (OpenWebUI) | ✅ Hoàn thành |
| 2 | Xác thực & phân quyền người dùng theo "subkey" | ✅ Hoàn thành |
| 3 | Quản lý quota (tokens/cost) và giới hạn theo user/period | ✅ Hoàn thành |
| 4 | Proxy thống nhất đến nhiều LLM providers (OpenAI/Gemini) | ✅ Hoàn thành |
| 5 | Tracking chi tiết usage & cost cho mỗi request | ✅ Hoàn thành |

### 1.2 Tính Năng Hiện Tại

✅ **Đã hoàn thành:**
- Chat Completions (streaming & non-streaming)
- Image Generation với quota tracking
- Quota Management (tokens + cost)
- Multi-User Authentication với RBAC
- Usage Logging & Monitoring
- Admin Dashboard realtime
- File Upload và Multimodal support

🚧 **Đang phát triển:**
- Video Generation qua OpenWebUI Tool/Pipe
- Audio TTS/STT qua OpenWebUI Tool/Pipe
- Tích hợp API Webhook Zalo

---

## 2. Kiến Trúc Kỹ Thuật

### 2.1 Kiến Trúc 3 Tầng

```
┌──────────────────────────────────────────────────────────┐
│                     USER BROWSER                         │
│                  http://localhost:3000                   │
└────────────────────────┬─────────────────────────────────┘
                         │ HTTP/HTTPS
                         ▼
┌──────────────────────────────────────────────────────────┐
│                   OpenWebUI (Port 3000)                  │
│  - Web-based chat interface                              │
│  - User authentication & session management              │
│  - Chat history storage (SQLite)                         │
│  - Model selection UI                                    │
└────────────────────────┬─────────────────────────────────┘
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
                         │ POST /chat/completions
                         │ Authorization: Bearer <LITELLM_KEY>
                         ▼
┌──────────────────────────────────────────────────────────┐
│                LiteLLM Proxy (Port 4000)                 │
│  - Multi-provider routing (OpenAI, Gemini, Anthropic)    │
│  - Load balancing & fallback                             │
│  - Rate limiting & cost tracking                         │
│  - Model aliasing & transformation                       │
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

### 2.2 Cấu Trúc Thư Mục Dự Án

```
C:\Code\Openwebui\
├── .env                          # ⚠️ Environment variables (GIT IGNORED)
├── .env.example                  # Template cho environment setup
├── README.md                     # Tài liệu tổng quan dự án
├── requirements.txt              # Python dependencies
│
├── docs/                         # 📚 Tài liệu
│   ├── ARCHITECTURE.md           # Kiến trúc hệ thống
│   ├── API_REFERENCE.md          # Tài liệu API endpoints
│   ├── DASHBOARD.md              # Hướng dẫn Admin Dashboard
│   ├── DATABASE_CONFIG.md        # Cấu hình database
│   ├── QUICKSTART.md             # Hướng dẫn khởi động nhanh
│   ├── PROJECT_EXPLAINED_VI.md   # Giải thích chi tiết (tiếng Việt)
│   ├── USER_MANAGEMENT.md        # Quản lý user & RBAC
│   └── MASTER_PLAN.md            # File kế hoạch tổng này
│
├── scripts/                      # 🔧 Scripts khởi động
│   ├── start.ps1                 # Start all services (PowerShell)
│   ├── start.bat                 # Start all services (Batch)
│   └── stop.ps1                  # Stop all services
│
├── llm-mw/                       # 🧠 Middleware (FastAPI)
│   ├── main.py                   # Entry point
│   ├── config.py                 # Configuration
│   ├── api/                      # API endpoints (11 modules)
│   ├── core/                     # Business logic (auth, quota, cost)
│   ├── utils/                    # Helpers (jwt, logging, guards)
│   ├── services/                 # External clients (litellm)
│   ├── dashboard/                # Admin UI (HTML/CSS/JS)
│   ├── data/                     # Runtime data
│   │   ├── users.json            # User database
│   │   ├── prices.json           # Model pricing
│   │   └── pending.csv           # Pending tracking
│   └── models/                   # Data models
│
├── litellm/                      # 🔀 LiteLLM Proxy
│   └── litellm_config.yaml       # Model definitions & settings
│
├── logs/                         # 📝 Application logs
│   ├── middleware.log            # Main log
│   ├── middleware.requests.log   # Request log
│   ├── audit.jsonl               # Audit trail
│   └── mw_media/                 # Uploaded media files
│
└── openwebui_data/               # 💾 OpenWebUI database & files
    └── webui.db                  # SQLite database
```

### 2.3 Phân Loại API Keys

| Key Type | Scope | Stored Where | Used By |
|----------|-------|--------------|---------|
| `SUBKEY` | End-user | `llm-mw/data/users.json` | OpenWebUI → Middleware |
| `LITELLM_KEY` | Master | `.env` (LITELLM_KEY) | Middleware → LiteLLM |
| `OPENAI_API_KEY` | Provider | `.env` | LiteLLM → OpenAI |
| `GEMINI_API_KEY` | Provider | `.env` | LiteLLM → Gemini |
| `ADMIN_KEY` | Admin | `.env` (ADMIN_KEY) | Admin tools → Middleware |
| `JWT_SECRET` | Session | `.env` | Dashboard authentication |

---

## 3. Kế Hoạch Triển Khai Chi Tiết

### 3.1 Timeline Tổng Quan

```
     Tháng 5/2025          Tháng 6/2025         Quý 3/2025           Quý 4/2025
    ┌────────────┐        ┌────────────┐       ┌────────────┐       ┌────────────┐
    │   Tuần 1-4 │        │   Tuần 1-4 │       │   Tuần 1-4 │       │   Tuần 1-4 │
    └────────────┘        └────────────┘       └────────────┘       └────────────┘
         │                      │                    │                    │
         ▼                      ▼                    ▼                    ▼
    ┌─────────┐           ┌─────────┐          ┌─────────┐          ┌─────────┐
    │ GĐ 1-2  │           │  GĐ 3   │          │ GĐ 4-5  │          │ GĐ 6-7  │
    │ Setup   │           │ Dữ liệu │          │ Thiết kế │          │ Triển   │
    │         │           │         │          │ & Test   │          │ khai    │
    └─────────┘           └─────────┘          └─────────┘          └─────────┘
```

### 3.2 Chi Tiết Các Giai Đoạn

| STT | Giai đoạn | Trụ cột | Mục tiêu | Sản phẩm/Kết quả đạt được | Chủ trì | Phối hợp | Chuyên gia | Mốc hoàn thành |
|-----|-----------|---------|----------|---------------------------|---------|----------|------------|----------------|
| 1 | Xác định mục tiêu & phạm vi | Quản lý dự án | Xác định phạm vi, mục tiêu, đội ngũ triển khai | - Khảo sát hiện trạng và điểm nghẽn<br>- Phạm vi: Nhóm Contact Center | A. Dương | - TTDL&ĐHS: Hiếu, Trang, Quy<br>- Nhóm Contact Center | | 31/5 |
| 2 | Thiết lập hạ tầng | Hạ tầng | Chuẩn bị nền tảng để vận hành Agent và dữ liệu KMS | - Chọn nền tảng (on-prem/cloud): Cài đặt máy ảo<br>- Cài đặt các service khác để selfhost n8n<br>- Cài đặt Vector DB: Phương pháp đề xuất cho model text-embedding<br>- Thiết lập API: Cài đặt AI model hoặc sử dụng API trả phí (API custom node text-embedding model, kiểm tra việc xử lý ngôn ngữ tiếng Việt của model) | TTDL&ĐHS: Huy | TTDL&ĐHS: Hiếu, Dũng, Thảo | Thầy Cường & Các thầy TTS, Thầy Phong | |
| 3 | Chuẩn bị dữ liệu | Dữ liệu | Làm sạch & chuẩn hóa dữ liệu cho AI Agent | - Xây dựng khung check list dữ liệu cần training<br>- Tập hợp tài liệu nội bộ PDF, Word, Notion…<br>- Làm sạch, thêm metadata, tạo chỉ mục | TTDL&ĐHS: Quy | - P.TT: Chị Yến, Ngọc<br>- TMĐT: A. Trường<br>- NCTT: Trường<br>- C4LED: Diễn, Hiền<br>- Nhóm Contact Center<br>- TTDL&ĐHS: Hiếu, Thảo, Thuý, Nhung | Thầy Cường & Các thầy TTS, Thầy Phong | |
| 4 | Thiết kế luồng AI | Agent design | Xây dựng luồng work-flow logic Agent, truy vấn, hồi đáp | - Mapping câu hỏi – nguồn Dữ liệu<br>- Thiết kế prompt chain / RAG flow<br>- API Webhook trả lời tự động: Chatbot tương tác được trên nền tảng Zalo | TTDL&ĐHS: Hiếu | TTDL&ĐHS: Quy, Huy, Thảo | Thầy Cường & Các thầy TTS, Thầy Phong | |
| 5 | Triển khai thử nghiệm & cải tiến | Chất lượng | Kiểm thử tính chính xác, logic phản hồi, tốc độ | - Test nội bộ theo checklist<br>- Chatbot hoạt động ổn định 24/7<br>- Fix bug và ghi nhận ý kiến người dùng | TTDL&ĐHS: Quy | - Nhóm Contact Center<br>- TTDL&ĐHS: Trang, Hiếu, Huy | | |
| 6 | Đào tạo người dùng | Triển khai | Hướng dẫn nhân sự sử dụng Agent hiệu quả | - Tài liệu hướng dẫn vận hành<br>- Đào tạo đội ngũ vận hành cập nhật | TTDL&ĐHS: Quy | | | |
| 7 | Vận hành chính thức | Vận hành | Triển khai rộng rãi, tracking log sử dụng, bảo trì định kỳ | - Theo dõi log<br>- Cập nhật cơ sở dữ liệu định kỳ<br>- Đánh giá hiệu quả | | | | Liên tục |

---

## 4. Chi Tiết Các Giai Đoạn

### 4.1 Giai Đoạn 1: Xác Định Mục Tiêu & Phạm Vi

**Trạng thái:** ✅ Đã hoàn thành cơ bản

**Công việc đã thực hiện:**
- [x] Khảo sát hiện trạng hệ thống Chat AI
- [x] Xác định phạm vi: Nhóm Contact Center
- [x] Thiết lập kiến trúc 3 tầng (OpenWebUI + Middleware + LiteLLM)
- [x] Cài đặt và cấu hình ban đầu

**Sản phẩm:**
- Tài liệu kiến trúc hệ thống ([ARCHITECTURE.md](./ARCHITECTURE.md))
- Tài liệu giải thích dự án ([PROJECT_EXPLAINED_VI.md](./PROJECT_EXPLAINED_VI.md))

---

### 4.2 Giai Đoạn 2: Thiết Lập Hạ Tầng

**Trạng thái:** ✅ Đã hoàn thành

**Công việc đã thực hiện:**

#### A. Nền tảng On-Premise:
- [x] Cài đặt Python 3.10+ virtual environment
- [x] Thiết lập 3 services:
  - OpenWebUI (Port 3000)
  - Middleware FastAPI (Port 5000)
  - LiteLLM Proxy (Port 4000)
- [x] Cấu hình firewall rules

#### B. Vector DB & Text Embedding:
- [x] LiteLLM hỗ trợ routing đến multiple providers
- [ ] (Planned) Cài đặt Vector DB riêng cho RAG

#### C. API Setup:
- [x] Tích hợp OpenAI API (gpt-4o, gpt-4o-mini, gpt-5)
- [x] Tích hợp Gemini API (gemini-2.0-flash, gemini-2.5-pro, gemini-2.5-flash)
- [x] Image Generation (gpt-image-1, gemini-2.5-flash-image)

**Sản phẩm:**
- Scripts khởi động tự động ([scripts/start.ps1](../scripts/start.ps1))
- Hướng dẫn cấu hình ([QUICKSTART.md](./QUICKSTART.md), [DATABASE_CONFIG.md](./DATABASE_CONFIG.md))

---

### 4.3 Giai Đoạn 3: Chuẩn Bị Dữ Liệu

**Trạng thái:** 🚧 Đang thực hiện

**Công việc cần làm:**
- [ ] Xây dựng khung checklist dữ liệu cần training
- [ ] Thu thập tài liệu nội bộ (PDF, Word, Notion)
- [ ] Làm sạch và chuẩn hóa dữ liệu
- [ ] Thêm metadata cho documents
- [ ] Tạo chỉ mục (indexing) cho tìm kiếm

**Nguồn dữ liệu:**
- P.TT: Tài liệu quy trình
- TMĐT: Catalog sản phẩm
- NCTT: Báo cáo nghiên cứu
- C4LED: Tài liệu kỹ thuật
- Contact Center: FAQ, scripts trả lời

---

### 4.4 Giai Đoạn 4: Thiết Kế Luồng AI

**Trạng thái:** 🚧 Đang thiết kế

**Công việc cần làm:**

#### A. Mapping Câu hỏi - Nguồn Dữ liệu:
- [ ] Phân loại câu hỏi theo chủ đề
- [ ] Mapping nguồn dữ liệu tương ứng
- [ ] Thiết kế intent recognition

#### B. Prompt Chain / RAG Flow:
- [ ] Thiết kế system prompts
- [ ] Xây dựng retrieval pipeline
- [ ] Tối ưu context window

#### C. API Webhook Zalo:
- [ ] Nghiên cứu Zalo OA API
- [ ] Thiết kế integration flow
- [ ] Implement webhook endpoint

**Luồng xử lý file hiện tại:**
> Xem chi tiết: [FILE_UPLOAD_FLOW.md](./FILE_UPLOAD_FLOW.md)

```
User Upload → OpenWebUI (base64) → Middleware (materialize) → LiteLLM → Provider
```

---

### 4.5 Giai Đoạn 5: Triển Khai Thử Nghiệm

**Trạng thái:** 🚧 Đang thực hiện

**Công việc cần làm:**
- [ ] Xây dựng test cases
- [ ] Test nội bộ theo checklist
- [ ] Đảm bảo hoạt động ổn định 24/7
- [ ] Thu thập feedback và fix bugs

**Checklist kiểm thử:**
- [ ] Chat completion hoạt động
- [ ] Streaming response ổn định
- [ ] Image generation thành công
- [ ] Quota enforcement đúng
- [ ] Authentication/Authorization đúng
- [ ] Dashboard metrics chính xác
- [ ] Logs đầy đủ và dễ đọc

---

### 4.6 Giai Đoạn 6: Đào Tạo Người Dùng

**Trạng thái:** ⏳ Chưa bắt đầu

**Công việc cần làm:**
- [ ] Viết tài liệu hướng dẫn sử dụng
- [ ] Tạo video tutorial
- [ ] Tổ chức training sessions
- [ ] Đào tạo đội ngũ vận hành

**Tài liệu cần chuẩn bị:**
- Hướng dẫn sử dụng OpenWebUI
- Hướng dẫn Admin Dashboard ([DASHBOARD.md](./DASHBOARD.md))
- FAQ troubleshooting
- Quy trình báo lỗi

---

### 4.7 Giai Đoạn 7: Vận Hành Chính Thức

**Trạng thái:** ⏳ Chưa bắt đầu

**Công việc liên tục:**
- [ ] Theo dõi logs và metrics
- [ ] Cập nhật cơ sở dữ liệu định kỳ
- [ ] Đánh giá hiệu quả hàng tháng
- [ ] Bảo trì và nâng cấp hệ thống

**Monitoring Tools:**
- Admin Dashboard: `http://localhost:5000/dashboard`
- Audit logs: `logs/audit.jsonl`
- Request logs: `logs/middleware.requests.log`

---

## 5. Thông Tin Kỹ Thuật

### 5.1 API Endpoints Chính

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/health` | GET | Health check | No |
| `/v1/models` | GET | List available models | Subkey |
| `/v1/chat/completions` | POST | Chat completion | Subkey |
| `/v1/images/generations` | POST | Image generation | Subkey |
| `/v1/audio/transcriptions` | POST | Audio transcription | Subkey |
| `/dashboard/login` | POST | Admin login | Admin Key |
| `/v1/_mw/summary` | GET | Dashboard metrics | JWT Cookie |
| `/admin/usage` | GET | User usage stats | Admin Key |
| `/admin/reset` | POST | Reset quota | Admin Key |

> Xem chi tiết: [API_REFERENCE.md](./API_REFERENCE.md)

### 5.2 User Management & RBAC

**User Schema:**
```json
{
  "user_id": "admin",
  "role": "admin",  // admin | manager | user
  "subkey_hash": "...",
  "active": true,
  "allowed_models": ["*"],
  "quota": {
    "period": "monthly",
    "timezone": "Asia/Bangkok",
    "limit_tokens": 0,
    "limit_cost_usd": 0,
    "limit_image_requests": 0,
    "used_tokens": 0,
    "used_cost_usd": 0.0,
    "used_image_requests": 0
  }
}
```

> Xem chi tiết: [USER_MANAGEMENT.md](./USER_MANAGEMENT.md)

### 5.3 Models Hỗ Trợ

| Model | Provider | Vision | Image Gen | Notes |
|-------|----------|--------|-----------|-------|
| gpt-4o | OpenAI | ✅ | ❌ | Best vision model |
| gpt-4o-mini | OpenAI | ✅ | ❌ | Cost-effective |
| gpt-5 | OpenAI | ✅ | ❌ | Reasoning + vision |
| gpt-image-1 | OpenAI | ❌ | ✅ | DALL-E 3 |
| gemini-2.0-flash | Google | ✅ | ❌ | Fast, good vision |
| gemini-2.5-pro | Google | ✅ | ❌ | Most powerful |
| gemini-2.5-flash | Google | ✅ | ❌ | Balanced |
| gemini-2.5-flash-image | Google | ❌ | ✅ | Image generation |

### 5.4 Security Checklist

- [x] Subkeys stored as HMAC-SHA256 hashes
- [x] JWT tokens expire after 4 hours
- [x] HttpOnly cookies (chống XSS)
- [x] API keys in `.env` (never committed)
- [x] Audit logs for all admin operations
- [ ] HTTPS (cần reverse proxy)
- [ ] Rate limiting per user

---

## 6. Phân Công Công Việc

### 6.1 Nhân Sự Chính

| Vai trò | Người phụ trách | Trách nhiệm |
|---------|-----------------|-------------|
| Project Lead | A. Dương | Quản lý tổng thể, phạm vi dự án |
| Infrastructure Lead | Huy (TTDL&ĐHS) | Cài đặt hạ tầng, Vector DB, API |
| Data Lead | Quy (TTDL&ĐHS) | Thu thập, làm sạch dữ liệu |
| AI Design Lead | Hiếu (TTDL&ĐHS) | Thiết kế luồng Agent, prompts |
| Testing Lead | Quy (TTDL&ĐHS) | Kiểm thử, QA |
| Training Lead | Quy (TTDL&ĐHS) | Đào tạo người dùng |

### 6.2 Đội Ngũ Hỗ Trợ

- **TTDL&ĐHS:** Hiếu, Trang, Thảo, Dũng, Thuý, Nhung
- **P.TT:** Chị Yến, Ngọc
- **TMĐT:** A. Trường
- **NCTT:** Trường
- **C4LED:** Diễn, Hiền
- **Contact Center:** Nhóm vận hành

### 6.3 Chuyên Gia Tư Vấn

- Thầy Cường & Các thầy TTS
- Thầy Phong

---

## 7. Tài Liệu Liên Quan

### 7.1 Tài Liệu Kỹ Thuật

| Tài liệu | Mô tả | Link |
|----------|-------|------|
| ARCHITECTURE.md | Kiến trúc hệ thống chi tiết | [Xem](./ARCHITECTURE.md) |
| API_REFERENCE.md | Tài liệu API endpoints | [Xem](./API_REFERENCE.md) |
| DASHBOARD.md | Hướng dẫn Admin Dashboard | [Xem](./DASHBOARD.md) |
| DATABASE_CONFIG.md | Cấu hình database | [Xem](./DATABASE_CONFIG.md) |
| QUICKSTART.md | Hướng dẫn khởi động nhanh | [Xem](./QUICKSTART.md) |
| PROJECT_EXPLAINED_VI.md | Giải thích chi tiết (tiếng Việt) | [Xem](./PROJECT_EXPLAINED_VI.md) |
| USER_MANAGEMENT.md | Quản lý user & RBAC | [Xem](./USER_MANAGEMENT.md) |
| FILE_UPLOAD_FLOW.md | Luồng xử lý file upload | [Xem](./FILE_UPLOAD_FLOW.md) |
| IMAGE_GENERATION.md | Hướng dẫn tạo ảnh | [Xem](./IMAGE_GENERATION.md) |

### 7.2 Quick Start Commands

```powershell
# Khởi động tất cả services
.\scripts\start.ps1

# Dừng tất cả services
.\scripts\stop.ps1

# Access URLs
# OpenWebUI (Chat):     http://localhost:3000
# Admin Dashboard:      http://localhost:5000/dashboard
# Middleware Health:    http://localhost:5000/health
# LiteLLM Health:       http://localhost:4000/health
```

### 7.3 Troubleshooting

**Services không khởi động:**
```powershell
Get-Process | Where-Object {$_.ProcessName -like "*python*"} | Stop-Process -Force
.\scripts\start.ps1
```

**Dashboard login thất bại:**
- Kiểm tra `ADMIN_KEY` trong `.env`
- Kiểm tra `JWT_SECRET` trong `.env`
- Xem logs: `logs/middleware.log`

**Không kết nối được từ máy khác:**
```powershell
# Mở firewall ports
New-NetFirewallRule -DisplayName "OpenWebUI-3000" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 3000
New-NetFirewallRule -DisplayName "Middleware-5000" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5000
New-NetFirewallRule -DisplayName "LiteLLM-4000" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 4000
```

---

## 📝 Ghi Chú Cập Nhật

| Ngày | Version | Thay đổi |
|------|---------|----------|
| 03/02/2026 | 1.0 | Tạo kế hoạch tổng thể ban đầu |

---

**Người tạo:** AI Assistant  
**Người phê duyệt:** _[Chờ phê duyệt]_  
**Ngày cập nhật cuối:** 03/02/2026
