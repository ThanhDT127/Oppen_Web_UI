# 🏗️ ARCHITECTURE - OPPEN WEB UI

## 📐 System Overview

The Oppen Web UI system consists of **8 Docker containers** on the same network, providing AI chat with auth, quota, cost tracking, and web search.

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                            │
│   https://openwebui.rangdong.com.vn:51122/ (HTTPS qua Nginx)    │
└────────────────────────────────┬────────────────────────────────┘
                                 ▲
                                 │
                                 ▼
┌══ SERVER ══════════════════════════════════════════════════════════════════════════┐
│                                                                                    │
│  ┌── Docker Network: openwebui-network ─────────────────────────────────────────┐  │
│  │                                                                              │  │
│  │  ┌───────────────────────────────────────────────────────────────────────┐   │  │
│  │  │                     OPEN WEBUI (Port 8080, 6 workers)                 │   │  │
│  │  │  - Chat AI đa mô hình (text, image, audio)                            │   │  │
│  │  │  - Quản lý hồ sơ & xác thực người dùng                                │   │  │
│  │  │  - Lịch sử hội thoại & tìm kiếm RAG                                   │   │  │
│  │  │  - Web Search (gọi SearXNG khi LLM dùng Native Function Calling)      │   │  │
│  │  └──────────┬───────────────────────────────────────┬────────────────────┘   │  │
│  │             │ OpenAI API Format                     │ Web Search API         │  │
│  │             ▲                                       ▼                        │  │
│  │             │                          ┌────────────────────────┐            │  │
│  │             │                          │  SEARXNG (Port 8080)   │            │  │
│  │             │                          │  - Metasearch engine   │            │  │
│  │             │                          │  - Brave, DDG, Bing    │            │  │
│  │             │                          │  - JSON API (internal) │            │  │
│  │             │                          └────────────────────────┘            │  │
│  │             ▼                                                                │  │
│  │  ┌──────────────────────────────────────────────┐   ┌─────────────────────┐  │  │
│  │  │        LLM MIDDLEWARE (Port 5000, 4 workers) │   │ POSTGRESQL (5432)   │  │  │
│  │  │                                              │   │                     │  │  │
│  │  │  - Proxy AI: Chat, Image, Audio              │   │ Dữ liệu người dùng  │  │  │
│  │  │    (stream & non-stream)                     │   │  - Tài khoản/Subkey │  │  │
│  │  │                                              │   │  - Hạn mức (Quota)  │  │  │
│  │  │  - Admin Dashboard (qua Nginx /dashboard)    │   │                     │  │  │
│  │  │    Biểu đồ, thống kê, top users/models       │   │ Bảng giá model      │  │  │
│  │  │                                              │   │  - Cost/token input │  │  │
│  │  │  - Quản lý User & Quota                      │◄-►│  - Cost/token output│  │  │
│  │  │    Tạo/sửa/xóa user, cấp phát hạn mức        │   │                     │  │  │
│  │  │                                              │   │ Audit & Log         │  │  │
│  │  │  - Kiểm toán (Audit)                         │   │  - Lịch sử request  │  │  │
│  │  │    Ghi log kép (DB + file), realtime SSE     │   │  - Chi phí & tokens │  │  │
│  │  │                                              │   │  - Lỗi & latency    │  │  │
│  │  │  - Tính chi phí (Cost Tracking)              │   │                     │  │  │
│  │  │    Tự động tính $/token theo bảng giá        │   │ Cấu hình hệ thống   │  │  │
│  │  │                                              │   │  - Ngưỡng cảnh báo  │  │  │
│  │  │  - Xác thực & Bảo mật                        │   │  - Request đang chờ │  │  │
│  │  │    Subkey hashing, JWT dashboard, auth guard │   │                     │  │  │
│  │  └──────────────────────┬───────────────────────┘   └─────────────────────┘  │  │
│  │                          Forward to LiteLLM                                  │  │
│  │                         ▲                                                    │  │
│  │                         │                                                    │  │
│  │                         ▼                                                    │  │
│  │  ┌───────────────────────────────────────────────────────────────────────┐   │  │
│  │  │                   LITELLM PROXY (Port 4000, 4 workers)                │   │  │
│  │  │  - Đổi tên model: chat-gpt-5 -> openai/gpt-5 (16 models)              │   │  │
│  │  │  - Định tuyến đa nhà cung cấp (OpenAI, Gemini, Anthropic, XAI)        │   │  │
│  │  └──────────────────────┬────────────────────────────────────────────────┘   │  │
│  │                         │                                                    │  │
│  └─────────────────────────┼────────────────────────────────────────────────────┘  │
│                            │                                                       │
╚════════════════════════════╪═══════════════════════════════════════════════════════╝
                             │
              ┌──────────────┼────────────────────────────┐
              ▼              ▼              ▼              ▼    
         [OpenAI API]   [Gemini API]  [XAI API]  [Anthropic API]
```

### Biểu đồ luồng Web Search (Native Function Calling)

```
  User: "Giá vàng hôm nay?"
         │
         ▼
  ┌─── OPEN WEBUI ───────────────────────────────────────────────┐
  │  1. Gửi prompt + tool_definition(web_search) tới LLM        │
  │     POST /v1/chat/completions ──► Middleware ──► LiteLLM     │
  └──────────────────────────────────────────────────────────────┘
         │
         ▼
  ┌─── LLM (GPT-5 / Gemini) ────────────────────────────────────┐
  │  2. LLM phân tích: cần thông tin realtime                    │
  │     → Trả về tool_call: web_search(query="giá vàng hôm nay")│
  └──────────────────────────────────────────────────────────────┘
         │
         ▼
  ┌─── OPEN WEBUI ───────────────────────────────────────────────┐
  │  3. Nhận tool_call → gọi SearXNG                             │
  │     GET http://searxng:8080/search?q=giá+vàng&format=json    │
  └──────────────────────────────────────────────────────────────┘
         │
         ▼
  ┌─── SEARXNG (Port 8080) ──────────────────────────────────────┐
  │  4. Tìm kiếm song song:                                     │
  │     Google ──► kết quả                                       │
  │     Brave  ──► kết quả    ──► Tổng hợp JSON (5 results)      │
  │     DDG    ──► kết quả                                       │
  └──────────────────────────────────────────────────────────────┘
         │
         ▼
  ┌─── OPEN WEBUI ───────────────────────────────────────────────┐
  │  5. Inject kết quả search vào context                        │
  │     → Gọi LLM lần 2 với search results                      │
  └──────────────────────────────────────────────────────────────┘
         │
         ▼
  ┌─── LLM (Lần 2) ─────────────────────────────────────────────┐
  │  6. Sinh câu trả lời dựa trên dữ liệu search                │
  │     → Kèm citations (nguồn: giavang.org, baomoi.com)        │
  └──────────────────────────────────────────────────────────────┘
         │
         ▼
  ┌─── RESPONSE ─────────────────────────────────────────────────┐
  │  "Giá vàng hôm nay (11/03/2026):                             │
  │   - XAU: 5,217.46 USD/Ounce  [giavang.org]                  │
  │   - SJC: 184.2 - 187.2 triệu VNĐ/lượng  [baomoi.com]"      │
  │                                                              │
  │  Chi phí: $0 (search) + LLM tokens only (qua Middleware)     │
  │  📎 Retrieved 2 sources                                      │
  └──────────────────────────────────────────────────────────────┘
```

### Giải thích thuật ngữ trong biểu đồ

#### 🔲 Các khung viền (Boundary)

| Ký hiệu / Thuật ngữ      | Giải thích                                                                                      |
| ------------------------ | ----------------------------------------------------------------------------------------------- |
| `┌══ SERVER ══┐`         | Khung ngoài cùng — đại diện máy chủ vật lý hoặc VM chạy toàn bộ dịch vụ                         |
| `┌── Docker Network ──┐` | Khung bên trong — mạng nội bộ Docker `openwebui-network`, 5 container giao tiếp qua tên service |
| `┌── ... ──┐`            | Mỗi hộp nhỏ = 1 Docker container (dịch vụ chạy độc lập, có port riêng)                          |
| `┌── ├── ──┤ ──┘`        | Các viền bên trong Middleware = phân chia 3 tầng code: API → Core → Utilities                   |

#### 🔗 Mũi tên & kết nối

| Ký hiệu             | Giải thích                                                                                 |
| ------------------- | ------------------------------------------------------------------------------------------ |
| `│` và `↓`          | Luồng dữ liệu đi xuống, theo chiều request: User → WebUI → Middleware → LiteLLM → Provider |
| `◄──┼──►`           | Kết nối 2 chiều giữa Middleware ↔ PostgreSQL (đọc/ghi dữ liệu)                             |
| `OpenAI API Format` | Giao thức chuẩn OpenAI — Middleware nhận request theo format này từ Open WebUI             |
| `Bearer subkey`     | Phương thức xác thực — header `Authorization: Bearer <khóa_user>` gửi kèm mỗi request      |
| `Proxy to LiteLLM`  | Middleware chuyển tiếp request đến LiteLLM sau khi xác thực & kiểm tra quota               |

#### 🧱 6 Docker Containers (Dịch vụ chính)

| Container          | Port   | Giải thích chi tiết                                                                            |
| ------------------ | ------ | ---------------------------------------------------------------------------------------------- |
| **Open WebUI**     | `3000` | Giao diện web cho end-user — chat AI, quản lý hồ sơ, lịch sử hội thoại, RAG (tìm tài liệu)     |
| **LLM Middleware** | `5000` | Tầng trung gian do team phát triển (FastAPI/Python) — xác thực, quota, proxy, audit, dashboard |
| **PostgreSQL**     | `5432` | CSDL quan hệ — 2 database: `openwebui` (chat + PGVector) và `middleware` (6 bảng `mw_*`)       |
| **LiteLLM Proxy**  | `4000` | Proxy mã nguồn mở — aliasing tên model + route request đến đúng provider (OpenAI/Gemini/...)   |
| **SearXNG**        | `8080` | Web search engine tự host (internal only) — tổng hợp kết quả từ Google, Brave, DuckDuckGo   |
| **Apache Tika**    | `9998` | OCR/text extraction server — xử lý PDF scan, hình ảnh, và các file phức tạp                   |

#### 📦 Cấu trúc bên trong LLM Middleware

| Tầng           | Thư mục  | Giải thích                                                                                  |
| -------------- | -------- | ------------------------------------------------------------------------------------------- |
| **API Layer**  | `api/`   | Tầng HTTP — mỗi file `.py` xử lý 1 nhóm endpoint (chat, images, admin, dashboard, audit...) |
| **Core Logic** | `core/`  | Logic nghiệp vụ — xác thực subkey, tính cost, kiểm tra quota, quản lý kết nối DB            |
| **Utilities**  | `utils/` | Công cụ dùng chung — JWT token, bảo vệ route, ghi log kép (DB + file)                       |

#### 📊 Các bảng dữ liệu PostgreSQL (trong biểu đồ)

| Bảng             | Giải thích                                                                                       |
| ---------------- | ------------------------------------------------------------------------------------------------ |
| `mw_users`       | Tài khoản user: tên, subkey (hash), quota hiện tại, danh sách model được phép, trạng thái active |
| `mw_prices`      | Bảng giá: mỗi model có giá `input_per_token` và `output_per_token` (USD)                         |
| `mw_config`      | Cấu hình hệ thống: ngưỡng cảnh báo quota, cài đặt email alert                                    |
| `mw_pending`     | Request đang xử lý (tạm thời): tạo khi bắt đầu, xóa khi hoàn tất — dùng để reconcile             |
| `mw_audit_log`   | Log kiểm toán có cấu trúc: mỗi request AI = 1 dòng (user, model, status, cost, tokens, latency)  |
| `mw_request_log` | Log chi tiết HTTP: toàn bộ request/response headers, body, timing (dùng debug)                   |

#### 🔑 Thuật ngữ kỹ thuật

| Thuật ngữ                    | Giải thích                                                                                |
| ---------------------------- | ----------------------------------------------------------------------------------------- |
| **Subkey**                   | Khóa API riêng của từng user, hash SHA-256 rồi lưu DB để so khớp khi xác thực             |
| **JWT**                      | JSON Web Token — token đăng nhập dashboard admin, ký bằng `JWT_SECRET`, hết hạn sau 4 giờ |
| **Dual-write**               | Ghi dữ liệu đồng thời vào 2 nơi: PostgreSQL (chính) + file JSON/log (backup phụ)          |
| **Fallback**                 | Cơ chế dự phòng: nếu PostgreSQL lỗi → tự động đọc từ file JSON/log thay thế               |
| **SSE (Server-Sent Events)** | Kỹ thuật streaming — server đẩy dữ liệu realtime xuống browser, dùng cho chat + live log  |
| **Quota**                    | Hạn mức sử dụng — giới hạn tokens hoặc chi phí theo chu kỳ tuần/tháng, tự động reset      |
| **Model aliasing**           | Đổi tên model ngắn (vd: `chat-gpt-5`) → tên đầy đủ provider (`openai/gpt-5`)              |
| **PGVector**                 | Extension PostgreSQL cho vector search — dùng để RAG tìm tài liệu tương tự                |
| **RAG**                      | Retrieval-Augmented Generation — AI đọc tài liệu upload trước, kết hợp vào câu trả lời    |
| **Healthcheck**              | Kiểm tra sức khỏe container — Docker tự ping dịch vụ theo chu kỳ, restart nếu lỗi         |
| **Volume**                   | Ổ đĩa Docker — dữ liệu tồn tại khi container restart (vd: `postgres_data` lưu DB)         |
| **Bind mount**               | Gắn thư mục máy host vào container (vd: `./llm-mw:/app` để code đồng bộ live)             |

---

## � Mô tả Tính năng Hệ thống

> Hệ thống cung cấp **116+ tính năng** chia thành 12 nhóm chức năng chính.
> Chi tiết từng tính năng xem tại [checklist-tinh-nang.md](file:///c:/Code/openwebui_fetch/Oppen_Web_UI/docs/checklist-tinh-nang.md).

### 1. Phân quyền & Quản lý Người dùng

| Tính năng                   | Mô tả                                                                     |
| --------------------------- | ------------------------------------------------------------------------- |
| Đăng ký / Đăng nhập         | Email + password, JWT token. Hỗ trợ OAuth/SSO (AD/LDAP/Google) sẵn sàng   |
| 3 cấp phân quyền            | **Admin** (toàn quyền), **User** (chat + upload), **Pending** (chờ duyệt) |
| Quản lý user qua WebUI      | Admin thêm/xóa/sửa role/reset password trên giao diện web                 |
| Quản lý user qua Middleware | Dashboard :5000 — tạo user + subkey, cấu hình quota, bật/tắt tài khoản    |
| Access Control              | Giới hạn quyền truy cập theo user/group trên Knowledge và Model           |
| Audit log hoạt động         | Ghi lại mọi thao tác admin (tạo user, đổi quota, rotate key) vào DB       |

### 2. Chat AI đa mô hình (15 models)

| Nhà cung cấp       | Models                                                                              |
| ------------------ | ----------------------------------------------------------------------------------- |
| **OpenAI GPT-5**   | `chat-gpt-5` (flagship), `chat-gpt-5-mini`, `chat-gpt-5-nano`                       |
| **OpenAI GPT-4.1** | `chat-gpt-4.1` (1M context), `chat-gpt-4.1-mini`, `chat-gpt-4.1-nano`               |
| **OpenAI GPT-4o**  | `chat-gpt-4o` (multimodal), `chat-gpt-4o-mini`                                      |
| **Google Gemini**  | `chat-gemini-3-pro`, `chat-gemini-2.5-pro`, `chat-gemini-2.5-flash`,                |
|                    | `chat-gemini-2.5-flash-lite`, `chat-gemini-2.0-flash`, `chat-gemini-2.0-flash-lite` |

**Tính năng chat nổi bật:**

| Tính năng               | Mô tả                                                               |
| ----------------------- | ------------------------------------------------------------------- |
| Streaming response      | Hiển thị từng token realtime qua SSE                                |
| Multimodal input        | Gửi hình ảnh + text (GPT-4o, Gemini)                                |
| Lịch sử hội thoại       | Lưu toàn bộ trong PostgreSQL, tìm kiếm theo keyword                 |
| Pin / Archive / Share   | Ghim, lưu trữ, chia sẻ hội thoại qua link công khai                 |
| Folder + Tags           | Tổ chức hội thoại vào folder, gắn tag phân loại                     |
| Chuyển model giữa chừng | Đổi model trong cùng 1 hội thoại bất kỳ lúc nào                     |
| Memory                  | AI nhớ thông tin user giữa các hội thoại (lưu trong table `memory`) |

### 3. Web Search (SearXNG + Native Function Calling)

| Tính năng                  | Mô tả                                                                   |
| -------------------------- | ----------------------------------------------------------------------- |
| SearXNG self-hosted        | Web search engine nội bộ, $0 chi phí, tổng hợp Google + Brave + DDG     |
| Native Function Calling    | Model tự quyết định khi nào cần tìm kiếm web (không cần user bật thủ công) |
| Source Citations           | Response kèm trích dẫn nguồn (tên website + URL) dạng chip/tag          |
| Multi-engine aggregation   | SearXNG gọi nhiều search engine song song, tổng hợp kết quả chất lượng   |
| Cấu hình per-model         | Mỗi model bật/tắt web search riêng biệt (Capabilities + Default Features) |

### 4. Tạo ảnh AI (Image Generation)

| Model              | Engine   | Mô tả                                                      |
| ------------------ | -------- | ---------------------------------------------------------- |
| `img-gpt-dalle-3`  | DALL-E 3 | Tạo ảnh từ text — 1024x1024 — chuyển đổi B64 → URL tự động |
| `img-gemini-flash` | Gemini   | Tạo ảnh nhanh — phù hợp prototype, logo                    |
| `img-gemini-pro`   | Gemini   | Tạo ảnh chất lượng cao — lên đến 4K                        |

### 5. Giọng nói (Voice I/O)

| Model             | Loại | Mô tả                                                         |
| ----------------- | ---- | ------------------------------------------------------------- |
| `tts-gpt-4o-mini` | TTS  | Chuyển text → giọng nói tự nhiên (nhấn icon 🔊 trên response) |
| `stt-gpt-4o`      | STT  | Nhận dạng giọng nói → text (nhấn icon 🎤 trong chat)          |
| `stt-gpt-4o-mini` | STT  | Phiên bản nhẹ, nhanh hơn, chi phí thấp                        |

### 6. RAG — Knowledge Base (Cơ sở Tri thức)

| Tính năng                | Mô tả                                                                     |
| ------------------------ | ------------------------------------------------------------------------- |
| Tạo Knowledge Collection | Workspace → Knowledge → Create. Đặt tên, mô tả, phân quyền                |
| Upload đa định dạng      | PDF, DOCX, XLSX, TXT, CSV, MD, HTML — tối đa 50MB/file                    |
| Gọi trong chat bằng `#`  | Gõ `#ten-knowledge` trong chat để AI tham khảo tài liệu                   |
| Attach file trực tiếp    | Kéo thả file vào chat → AI đọc và trả lời ngay (xử lý tạm)                |
| Gán Knowledge vào Model  | Admin gán Knowledge mặc định cho model cụ thể                             |
| Hybrid Search            | BM25 (keyword) + Vector (semantic) kết hợp cho kết quả chính xác hơn      |
| HNSW Vector Index        | Approximate nearest neighbor — m=16, ef_construction=64                   |
| Citation (trích dẫn)     | AI trích dẫn tên file + số trang nguồn trong câu trả lời                  |
| Embedding qua middleware | `gemini-embedding-001` (1536-dim, giảm từ 3072 native) qua Middleware → LiteLLM → Gemini API |
| PGVector                 | Vector storage trong PostgreSQL — dữ liệu không rời hệ thống              |

### 7. Kiểm soát Chi phí & Quota (Middleware)

| Tính năng              | Mô tả                                                               |
| ---------------------- | ------------------------------------------------------------------- |
| Quota per user         | Giới hạn chi phí (USD) hoặc tokens theo chu kỳ tuần/tháng           |
| Tự động reset quota    | Hết chu kỳ → quota auto-reset, không cần can thiệp                  |
| Cảnh báo gần hết quota | Thông báo khi user sử dụng gần hết hạn mức                          |
| Chặn khi hết quota     | HTTP 429 — từ chối request khi vượt hạn mức                         |
| Sub-key per user       | Mỗi user có API key riêng, hash SHA-256, lưu an toàn trong DB       |
| Cost tracking tự động  | Tính chi phí mỗi request theo bảng giá model (input + output token) |
| Bảng giá tùy chỉnh     | Admin cấu hình giá riêng cho từng model trong `mw_prices`           |
| Email alert            | Cấu hình ngưỡng cảnh báo + email thông báo khi vượt ngưỡng          |

### 8. Admin Dashboard (Middleware :5000)

| Thành phần            | Mô tả                                                                   |
| --------------------- | ----------------------------------------------------------------------- |
| **Tab Usage**         | Tổng quan: 6 biểu đồ (Cost/Tokens/Requests over time, Request types,    |
|                       | Cost by User, Cost by Model) + 13 metrics cards                         |
| **Tab Users**         | Quản lý user: tạo/sửa/xóa, cấp quota, bật/tắt, rotate subkey            |
| **Tab Logs**          | Log explorer: tìm kiếm audit log với bộ lọc (user, model, status, date) |
| **Tab Access**        | HTTP access monitoring: top paths, status codes, latency                |
| **Insight banners**   | Tự động tạo tóm tắt: top spender, model phổ biến nhất, tổng chi phí     |
| **Time range filter** | Lọc: 1h, 6h, 24h, 7d, 30d, hoặc custom date range                       |
| **Top-N + Sort**      | Top 5/10/20/50/All, sort by Cost/Requests/Tokens/Latency/Errors         |
| **SSE Realtime**      | Live stream audit events — cập nhật dashboard không cần refresh         |
| **JWT Auth**          | Đăng nhập admin bằng `ADMIN_KEY` → JWT cookie (4h), auto-logout         |

### 9. Quản lý User qua Dashboard

| Tính năng               | Mô tả                                                 |
| ----------------------- | ----------------------------------------------------- |
| Tạo user + subkey       | Tạo tài khoản → tự động sinh API subkey               |
| Sửa thông tin user      | Đổi tên, quota, danh sách model được phép             |
| Rotate subkey           | Thu hồi key cũ, sinh key mới (bảo mật khi key bị lộ)  |
| Bật / Tắt user          | Disable tạm / enable lại tài khoản                    |
| Xem quota status        | Hiển thị: used / limit / remaining / % sử dụng        |
| Allowed models per user | Giới hạn user chỉ dùng được danh sách model nhất định |

### 10. Công cụ Mở rộng (Custom Tools)

| Tool                 | Mô tả                                                                           |
| -------------------- | ------------------------------------------------------------------------------- |
| **Xuất Excel**       | Chat → bảng → file .xlsx — auto-detect số, ngày, tiền tệ (VNĐ/$), freeze header |
| **Xuất PDF**         | Xuất nội dung hội thoại → PDF có format                                         |
| **Xuất DOCX**        | Xuất nội dung hội thoại → Word có format                                        |
| **Wizard UI**        | Modal progress 3 bước: chuẩn hóa → tạo file → tải xuống                         |
| **Custom Functions** | Framework cho admin thêm Python functions tùy chỉnh                             |
| **Custom Tools**     | Framework cho AI gọi function (function calling)                                |

### 11. Bảo mật & Xác thực

| Tính năng                | Mô tả                                                              |
| ------------------------ | ------------------------------------------------------------------ |
| Subkey hashing SHA-256   | Key user không lưu plaintext — chỉ lưu hash trong DB               |
| JWT với HTTP-only cookie | Token đăng nhập dashboard — hết hạn 4h, không truy cập được từ JS  |
| Auth guard decorator     | Tự động bảo vệ endpoints admin — kiểm tra JWT trước khi xử lý      |
| Secrets trong `.env`     | `ADMIN_KEY`, `JWT_SECRET`, `MW_SECRET` — không commit vào git      |
| Docker internal network  | Các container giao tiếp nội bộ — không expose port không cần thiết |
| Dual-write audit         | Mọi request AI đều ghi vào DB + file backup — không thể xóa vết    |

### 12. Hạ tầng & Vận hành

| Tính năng                | Mô tả                                                                    |
| ------------------------ | ------------------------------------------------------------------------ |
| 4 Docker containers      | PostgreSQL + LiteLLM + Middleware + Open WebUI — 1 lệnh `docker compose` |
| Auto-restart             | Container tự restart khi lỗi hoặc server reboot                          |
| Health checks            | Docker kiểm tra sức khỏe: `pg_isready` (5s), `GET /health` (30s)         |
| Persistent volumes       | `postgres_data` giữ dữ liệu khi container restart/rebuild                |
| Bind mounts              | Source code live-sync: `./llm-mw:/app` — thay đổi code phản ánh ngay     |
| DB-first + File fallback | Đọc từ PostgreSQL trước, nếu lỗi → tự động fallback đọc từ JSON/log      |
| Dual-write logging       | Ghi log vào DB (primary) + file (backup) đồng thời                       |
| 3 kênh log               | System log, detail log (JSON), audit log (JSONL) — rotation tự động      |
| Backup thủ công          | `pg_dump` toàn bộ database qua `docker exec`                             |

### Kế hoạch Phát triển (Roadmap)

| Tính năng dự kiến        | Mô tả                                                                 |
| ------------------------ | --------------------------------------------------------------------- |
| Nhóm người dùng (Groups) | Phân quyền và quota theo phòng ban — framework có sẵn (table `group`) |
| Backup tự động           | Cron job chạy `pg_dump` hàng ngày                                     |
| Monitoring (Prometheus)  | Uptime monitoring + alerting với Grafana                              |
| SSO / LDAP               | Đăng nhập Active Directory nội bộ — Open WebUI hỗ trợ sẵn             |
| Báo cáo tự động          | Email/Zalo báo cáo chi phí hàng tuần                                  |
| On-premise LLM           | Chạy Llama/Mistral local — không phụ thuộc API ngoài (cần GPU)        |
| Tích hợp DMS/ERP         | Kết nối hệ thống nội bộ qua Middleware API                            |
| Web crawling             | Tự động fetch và index dữ liệu web — Open WebUI hỗ trợ sẵn URL import |

> **Tổng kết:** 110+ tính năng đã hoạt động | 8 tính năng trong roadmap phát triển.

---

## �🔐 Kiến trúc Bảo mật

### Luồng Xác thực

```
1. User Login
   ├─→ POST /dashboard/login {username, password}
   ├─→ Middleware validates ADMIN_KEY
   └─→ Returns JWT token (4-hour expiry) in HTTP-only cookie

2. Authenticated Requests
   ├─→ Browser sends JWT cookie automatically
   ├─→ auth_guard.py validates token signature & expiry
   └─→ Request proceeds or returns 403 Forbidden

3. API Key Management
   ├─→ Subkeys: User-specific tokens with quotas
   ├─→ Admin Key: Full access to admin endpoints
   └─→ LiteLLM Key: Backend proxy authentication
```

### Quản lý Secrets (Khóa bí mật)

| Secret            | Mục đích                                 | Vị trí               | Nạp bởi        |
| ----------------- | ---------------------------------------- | -------------------- | -------------- |
| `JWT_SECRET`      | Ký JWT token cho phiên dashboard         | `.env`               | `config.py`    |
| `MW_SECRET`       | Mã hóa nội bộ middleware                 | `.env`               | `config.py`    |
| `ADMIN_KEY`       | Xác thực admin endpoints                 | `.env`               | `config.py`    |
| `LITELLM_KEY`     | Xác thực proxy LiteLLM                   | `.env`               | `config.py`    |
| `DATABASE_URL`    | Chuỗi kết nối PostgreSQL (middleware DB) | `docker-compose.yml` | `config.py`    |
| Provider API Keys | Khóa API của OpenAI, Gemini, v.v.        | `.env`               | LiteLLM config |

**Nguyên tắc bảo mật:**
- Tất cả secrets lưu trong `.env` (không bao giờ commit lên git)
- `.env.example` cung cấp mẫu không chứa giá trị thật
- `config.py` cảnh báo nếu phát hiện giá trị mặc định
- JWT token hết hạn sau 4 giờ
- Audit logs ghi lại toàn bộ thao tác admin

---

## 📊 Luồng Dữ liệu

### Yêu cầu Chat Completion

```
User sends message in OpenWebUI
    ↓
POST /v1/chat/completions
    ├─ Headers: Authorization: Bearer <subkey>
    ├─ Body: {model, messages, stream: true/false}
    ↓
Middleware (chat.py)
    ├─ Extracts subkey from Authorization header
    ├─ Validates user & quota (core/auth.py + core/quota.py)
    ├─ Checks period-based limits (tokens/cost)
    ├─ Records pending request to data/pending.csv
    ├─ Proxies to LiteLLM → POST http://localhost:4000/v1/chat/completions
    ├─ Receives response (stream or non-stream)
    ├─ Calculates cost (core/cost.py, prices from mw_prices DB)
    ├─ Updates user quota in mw_users DB (+ users.json backup)
    └─ Returns to OpenWebUI
    ↓
LiteLLM Proxy
    ├─ Routes to appropriate provider (OpenAI, Gemini, etc.)
    ├─ Handles retries & fallbacks
    └─ Returns formatted response
```

### Yêu cầu Dashboard Admin

```
User accesses http://localhost:5000/dashboard
    ↓
GET /dashboard
    ├─ main.py serves dashboard/index.html
    └─ Returns HTML page
    ↓
JavaScript loads
    ↓
GET /v1/_mw/summary
    ├─ Includes JWT cookie
    ├─ utils/auth_guard.py validates JWT
    ├─ api/summary_v2.py queries mw_audit_log DB table (fallback: audit.jsonl)
    └─ Returns JSON: {totals, breakdown_by_user, breakdown_by_model, timeseries}
    ↓
Dashboard displays metrics
```

---

## 💾 Tầng Lưu trữ Dữ liệu

### PostgreSQL (Chính — database `middleware`)

Dữ liệu middleware được lưu trong database `middleware` riêng biệt trên PostgreSQL dùng chung. Tất cả chức năng đều dùng DB làm nguồn chính, tự động fallback sang file JSON/log nếu DB không khả dụng.

**6 bảng:**

| Bảng             | Mục đích                                         | Nguồn gốc                            |
| ---------------- | ------------------------------------------------ | ------------------------------------ |
| `mw_users`       | Tài khoản user, subkeys, quota                   | Migrate từ `users.json`              |
| `mw_prices`      | Bảng giá model (cost/token)                      | Migrate từ `prices.json`             |
| `mw_config`      | Cấu hình alert, system settings                  | Migrate từ `alert_config.json`       |
| `mw_pending`     | Theo dõi request đang xử lý                      | Migrate từ `pending.csv`             |
| `mw_audit_log`   | Audit log có cấu trúc (chat, image, audio, v.v.) | Migrate từ `audit.jsonl`             |
| `mw_request_log` | HTTP request logs (chi tiết request/response)    | Migrate từ `middleware.requests.log` |

**Kiến trúc đọc/ghi:**
- **DB-first:** Tất cả API đọc từ PostgreSQL trước
- **Dual-write:** Ghi đồng thời vào DB + file backup
- **Fallback:** Nếu DB lỗi, tự động đọc từ file JSON/log
- **Auto-migration:** Lần chạy đầu tiên, tự import dữ liệu từ JSON/CSV vào DB

**Kết nối:** `DATABASE_URL=postgresql://openwebui_user:<password>@postgres:5432/middleware`

### File Backup (Phụ)

Các file JSON/log được giữ lại làm backup:

| File                           | Mục đích              | Còn ghi? |
| ------------------------------ | --------------------- | -------- |
| `data/users.json`              | Backup dữ liệu user   | ✅ Có    |
| `prices.json`                  | Backup bảng giá       | ✅ Có    |
| `data/alert_config.json`       | Backup cấu hình alert | ✅ Có    |
| `logs/audit.jsonl`             | Backup audit log      | ✅ Có    |
| `logs/middleware.requests.log` | Backup request log    | ✅ Có    |

**Thao tác chính:**
- Đọc user: `core/auth.py` → `load_users()` (DB → fallback file)
- Ghi user: `core/auth.py` → `save_users()` (DB + file đồng thời)
- Kiểm tra quota: `core/quota.py` → `maybe_reset_quota()`
- Ghi audit: `utils/logging.py` → `write_audit_line()` (DB + file đồng thời)

---

## 🔄 Vòng đời Request

### Streaming Chat (95% lưu lượng)

```
1. Request Validation (10ms)
   ├─ Extract Authorization header
   ├─ Hash subkey and lookup user in mw_users DB (fallback: users.json)
   ├─ Check user.active status
   └─ Enforce period-based quota limits

2. Record Pending (5ms)
   ├─ Write to mw_pending DB + data/pending.csv (dual-write)
   └─ Used for reconciling streaming requests

3. Proxy to LiteLLM (50-200ms first token)
   ├─ Forward request to http://localhost:4000/v1/chat/completions
   ├─ Set stream=true in request body
   └─ Receive Server-Sent Events (SSE) stream

3. Stream Processing (duration varies)
   ├─ Read SSE chunks line by line
   ├─ Parse data: {delta: {content: "..."}}
   ├─ Forward to client immediately
   └─ Track [DONE] signal

4. Quota Update (5ms)
   ├─ Decrement pending_count
   ├─ Increment llm_calls
   └─ Trigger autosave
```

### Non-Streaming Chat

```
1. Validation (10ms)
2. Proxy Request (2-10 seconds)
   ├─ Wait for complete response
   └─ Parse JSON body
3. Quota Update (5ms)
4. Return full response
```

---

## 🧩 Trách nhiệm từng Module

### Tầng API (`api/`)

| Module               | Endpoints                                          | Mục đích                               |
| -------------------- | -------------------------------------------------- | -------------------------------------- |
| `chat.py`            | `/v1/chat/completions`                             | Proxy chat chính, kiểm tra quota       |
| `admin.py`           | `/admin/usage`, `/admin/reset`, `/admin/reconcile` | Thống kê & quản lý quota               |
| `models.py`          | `/v1/models`                                       | Danh sách model từ LiteLLM             |
| `dashboard_login.py` | `/v1/_mw/dashboard/login`, `/logout`               | Đăng nhập/đăng xuất JWT                |
| `summary_v2.py`      | `/v1/_mw/summary`                                  | Dữ liệu dashboard từ `mw_audit_log`    |
| `audit_query.py`     | `/v1/_mw/audit/query`                              | Truy vấn audit log có bộ lọc           |
| `access_logs.py`     | `/v1/_mw/access_summary`, `/access_stream`         | Giám sát HTTP access (DB)              |
| `stream.py`          | `/v1/_mw/stream`                                   | SSE realtime audit events (polling DB) |
| `user_admin.py`      | `/v1/_mw/admin/users`, `/admin/audit`              | Quản lý user CRUD                      |
| `health.py`          | `/health`                                          | Kiểm tra sức khỏe hệ thống             |
| `images.py`          | `/v1/images/generations`                           | Proxy tạo ảnh (DALL-E, gpt-image-1)    |
| `audio.py`           | `/v1/audio/transcriptions`                         | Proxy phiên dịch audio (Whisper)       |
| `media.py`           | `/v1/_mw/media/*`                                  | Phục vụ file media tĩnh                |
| `quota_status.py`    | `/v1/_mw/quota-status`, `/admin/alerts/*`          | Trạng thái quota & cấu hình alert      |
| `embeddings.py`      | `/v1/embeddings`                                   | Proxy embedding (Gemini), inject dims  |

### Logic Nghiệp vụ (`core/`)

| Module           | Mục đích                                                            |
| ---------------- | ------------------------------------------------------------------- |
| `db.py`          | Connection pool PostgreSQL, tạo schema, auto-migration dữ liệu cũ   |
| `auth.py`        | Xác thực user, hash subkey SHA-256 (DB chính, fallback file)        |
| `quota.py`       | Theo dõi quota theo chu kỳ (tuần/tháng), tự động reset              |
| `cost.py`        | Tính chi phí token (đọc giá từ `mw_prices`, fallback `prices.json`) |
| `alerting.py`    | Quản lý cấu hình alert quota (DB chính, fallback file)              |
| `audit_state.py` | Quản lý trạng thái request đang xử lý để ghi audit log              |

### Công cụ Hỗ trợ (`utils/`)

| Module          | Mục đích                                                  |
| --------------- | --------------------------------------------------------- |
| `auth_guard.py` | Decorator bảo vệ endpoint — kiểm tra JWT token hợp lệ     |
| `jwt_auth.py`   | Tạo JWT token, quản lý cookie (set/clear)                 |
| `logging.py`    | Ghi log kép vào file + PostgreSQL (detail_log, audit_log) |
| `helpers.py`    | Hàm tiện ích (parse request, format data)                 |
| `media.py`      | Xử lý file media (upload, lưu trữ)                        |

### Dịch vụ (`services/`)

| Module       | Mục đích                                                                 |
| ------------ | ------------------------------------------------------------------------ |
| `litellm.py` | Client giao tiếp HTTP với LiteLLM proxy (forward request, nhận response) |

---

## 🔌 Hạ tầng Docker & Phụ thuộc Dịch vụ

### Kiến trúc Container

| Container              | Image                     | Ports  | Volumes                                | Restart  |
| ---------------------- | ------------------------- | ------ | -------------------------------------- | -------- |
| `openwebui-postgres`   | `pgvector/pgvector:pg16`  | `5432` | `pgdata:/var/lib/postgresql/data`      | `always` |
| `openwebui-litellm`    | `ghcr.io/berriai/litellm` | `4000` | `./litellm/litellm_config.yaml`        | `always` |
| `openwebui-middleware` | custom build (Python)     | `5000` | `./llm-mw:/app`, `./logs:/app/../logs` | `always` |
| `open-webui`           | `ghcr.io/open-webui`      | `3000` | `open-webui:/app/backend/data`         | `always` |

### Thứ tự Khởi động & Phụ thuộc

```
1. PostgreSQL (port 5432)  — base, healthcheck: pg_isready
2. LiteLLM (port 4000)     — depends_on: postgres[healthy]
3. Middleware (port 5000)  — depends_on: postgres[healthy], litellm[started]
4. OpenWebUI (port 3000)   — depends_on: middleware[started]
```

### Kiểm tra Sức khỏe (Health Checks)

| Dịch vụ    | Endpoint      | Response khi OK                                   | Chu kỳ |
| ---------- | ------------- | ------------------------------------------------- | ------ |
| PostgreSQL | `pg_isready`  | exit 0                                            | 5s     |
| LiteLLM    | `GET /health` | `{"status":"ok"}`                                 | 30s    |
| Middleware | `GET /health` | `{"status":"ok","uptime_s":...,"db":{"ok":true}}` | 30s    |
| OpenWebUI  | `GET /`       | HTML 200                                          | 30s    |

---

## 🌐 Danh sách API đầy đủ (28 endpoints)

### Endpoints AI Proxy (Dành cho End-user)

| Method | Endpoint                   | Xác thực          | Mô tả                                                                          |
| ------ | -------------------------- | ----------------- | ------------------------------------------------------------------------------ |
| `POST` | `/v1/chat/completions`     | `Bearer <subkey>` | Chat completion — stream/non-stream. Quota check → proxy LiteLLM → audit log   |
| `POST` | `/v1/embeddings`           | `Bearer <subkey>` | Embedding proxy — inject dimensions=1536, cost tracking, audit. Gemini via LiteLLM |
| `POST` | `/v1/images/generations`   | `Bearer <subkey>` | Image generation (DALL-E, etc.). Hỗ trợ `gpt-image-1` với B64 → URL conversion |
| `POST` | `/v1/audio/transcriptions` | `Bearer <subkey>` | Audio transcription (Whisper). Multipart form upload                           |
| `GET`  | `/v1/models`               | `Bearer <subkey>` | Danh sách models từ LiteLLM, lọc theo `allowed_models` của user                |

### Dashboard Auth

| Method | Endpoint                   | Auth               | Description                              |
| ------ | -------------------------- | ------------------ | ---------------------------------------- |
| `POST` | `/v1/_mw/dashboard/login`  | `{admin_key}` body | Admin login → trả JWT cookie (4h expiry) |
| `POST` | `/v1/_mw/dashboard/logout` | JWT cookie         | Xóa JWT cookie                           |
| `GET`  | `/v1/_mw/auth_check`       | JWT cookie         | Kiểm tra phiên đăng nhập hiện tại        |

### Dashboard Data APIs

| Method | Endpoint                 | Auth              | Description                                                         |
| ------ | ------------------------ | ----------------- | ------------------------------------------------------------------- |
| `GET`  | `/v1/_mw/summary`        | JWT/Admin         | Dữ liệu dashboard chính — totals, by_user, by_model, timeseries     |
| `GET`  | `/v1/_mw/stream`         | JWT/Admin         | SSE stream — real-time audit events (DB polling mỗi 2s)             |
| `GET`  | `/v1/_mw/audit/query`    | JWT/Admin         | Log explorer — truy vấn audit có bộ lọc (user, model, status, date) |
| `GET`  | `/v1/_mw/access_summary` | JWT/Admin         | HTTP access log — top paths, status codes, latency                  |
| `GET`  | `/v1/_mw/access_stream`  | JWT/Admin         | SSE stream cho HTTP access events                                   |
| `GET`  | `/v1/_mw/quota-status`   | `Bearer <subkey>` | Trạng thái quota user (used/limit/remaining)                        |
| `GET`  | `/v1/_mw/media/{name}`   | Public            | Phục vụ file media tĩnh (images)                                    |

### User Management (Admin)

| Method  | Endpoint                                   | Auth      | Description                           |
| ------- | ------------------------------------------ | --------- | ------------------------------------- |
| `GET`   | `/v1/_mw/admin/users`                      | JWT/Admin | Danh sách users với quota/status      |
| `POST`  | `/v1/_mw/admin/users`                      | JWT/Admin | Tạo user mới (tự sinh subkey)         |
| `PATCH` | `/v1/_mw/admin/users/{user_id}`            | JWT/Admin | Cập nhật user (quota, models, active) |
| `POST`  | `/v1/_mw/admin/users/{user_id}/rotate_key` | JWT/Admin | Sinh lại subkey cho user              |
| `POST`  | `/v1/_mw/admin/users/{user_id}/disable`    | JWT/Admin | Tắt tài khoản user                    |
| `POST`  | `/v1/_mw/admin/users/{user_id}/enable`     | JWT/Admin | Bật lại tài khoản user                |
| `GET`   | `/v1/_mw/admin/audit`                      | JWT/Admin | Lịch sử thao tác admin (audit trail)  |

### Alert Configuration (Admin)

| Method | Endpoint                          | Auth      | Description                          |
| ------ | --------------------------------- | --------- | ------------------------------------ |
| `GET`  | `/v1/_mw/admin/alerts/config`     | JWT/Admin | Lấy cấu hình ngưỡng cảnh báo & email |
| `PUT`  | `/v1/_mw/admin/alerts/config`     | JWT/Admin | Cập nhật cấu hình alert              |
| `POST` | `/v1/_mw/admin/alerts/test-email` | JWT/Admin | Gửi email cảnh báo test              |

### Legacy Admin

| Method | Endpoint           | Auth          | Description                             |
| ------ | ------------------ | ------------- | --------------------------------------- |
| `GET`  | `/admin/usage`     | `X-Admin-Key` | Thống kê sử dụng cơ bản (legacy format) |
| `POST` | `/admin/reset`     | `X-Admin-Key` | Reset quota counter cho user            |
| `POST` | `/admin/reconcile` | `X-Admin-Key` | Đối chiếu request đang pending          |
| `GET`  | `/health`          | Public        | Sức khỏe hệ thống + DB status + uptime  |

---

## 📱 Tài liệu Giao diện Dashboard

### Tabs

| Tab        | Description                       | Data Source              |
| ---------- | --------------------------------- | ------------------------ |
| **Usage**  | Metrics, charts, top users/models | `/v1/_mw/summary`        |
| **Users**  | User management, quota gauges     | `/v1/_mw/admin/users`    |
| **Logs**   | Searchable audit log explorer     | `/v1/_mw/audit/query`    |
| **Access** | HTTP access monitoring            | `/v1/_mw/access_summary` |

### Charts (6 total)

| Chart              | Type     | Data                                  | Answers                               |
| ------------------ | -------- | ------------------------------------- | ------------------------------------- |
| Cost Over Time     | Line     | `timeseries[].cost_usd`               | Chi phí có xu hướng tăng hay giảm?    |
| Tokens Over Time   | Line     | `timeseries[].tokens_total`           | Lượng tokens tiêu thụ theo thời gian? |
| Requests Over Time | Line     | `timeseries[].requests_total`         | Tần suất sử dụng hệ thống?            |
| Request Types      | Doughnut | `totals.chat/image/audio/video_calls` | Dùng Chat, Image hay Audio nhiều?     |
| Cost by User       | Doughnut | `breakdown_by_user[].cost_usd`        | Ai chiếm phần lớn chi phí?            |
| Cost by Model      | Doughnut | `breakdown_by_model[].cost_usd`       | Model nào tốn kém nhất?               |

### Interactive Controls

| Control            | Function                                        |
| ------------------ | ----------------------------------------------- |
| Time range buttons | Filter: Last 1h, 6h, 24h, 7d, 30d               |
| Custom date range  | Start/end datetime pickers                      |
| Top-N selector     | Show Top 5, 10, 20, 50, or All                  |
| Sort-by dropdown   | Sort by Cost, Requests, Tokens, Latency, Errors |

### Insight Banners (Vietnamese)

Each section includes a `💡 insight banner` with dynamic auto-generated text:
- **Overview**: tổng requests, chi phí, cost/request, tokens — cập nhật theo time range
- **Top Users**: 🏆 top spender (tên, cost, % share) + số users active
- **Top Models**: 💰 model tốn nhất + 🔥 model phổ biến nhất + số models

---

## 📊 Chỉ số & Đo lường

### Dashboard Metrics (Usage Tab)

| Metric             | Source                                | Formula                                 |
| ------------------ | ------------------------------------- | --------------------------------------- |
| **Total Requests** | `totals.requests_total`               | COUNT(*) trong khoảng time range        |
| **Chat Calls**     | `totals.chat_calls`                   | COUNT WHERE purpose='chat'              |
| **Image Calls**    | `totals.image_calls`                  | COUNT WHERE purpose='image'             |
| **Audio Calls**    | `totals.audio_calls`                  | COUNT WHERE purpose='audio'             |
| **Video Calls**    | `totals.video_calls`                  | COUNT WHERE purpose='video'             |
| **Total Cost**     | `totals.cost_total_usd`               | SUM(cost_usd)                           |
| **Total Tokens**   | `totals.tokens_total`                 | SUM(tokens_total)                       |
| **P95 Latency**    | `totals.p95_latency_ms`               | PERCENTILE_CONT(0.95) trên latency_ms   |
| **Error Rate**     | `totals.error_count / requests_total` | % requests có status='error'            |
| **Billable Calls** | `totals.billable_calls`               | Requests có cost > 0                    |
| **Usage Missing**  | `totals.usage_missing_calls`          | Requests OK nhưng thiếu token/cost data |
| **Pending**        | `totals.pending_open_count`           | Requests đang chờ response              |

### Per-User Breakdown

| Field                | Description               |
| -------------------- | ------------------------- |
| `requests_total`     | Tổng số requests của user |
| `tokens_total`       | Tổng tokens sử dụng       |
| `cost_usd`           | Tổng chi phí              |
| `p95_latency_ms`     | Trung bình P95 latency    |
| `error_rate_percent` | % requests lỗi            |

### Per-Model Breakdown

Cùng fields như per-user, thêm:
- **Avg $/req** = `cost_usd / requests_total`
- **Expense tag**: 💲 expensive (>$0.01/req) hoặc 💚 cheap (<$0.001/req)

---

## 📝 Kiến trúc Logging

### 3 kênh ghi Log

| Logger          | File                                  | Định dạng | Rotation | Mục đích                                  |
| --------------- | ------------------------------------- | --------- | -------- | ----------------------------------------- |
| `llm_mw`        | `logs/middleware.log`                 | Text      | 5MB × 5  | Sự kiện hệ thống, lỗi, khởi động          |
| `llm_mw_detail` | `logs/backup/middleware.requests.log` | JSON      | 20MB × 5 | Chi tiết request/response đầy đủ          |
| `llm_mw_audit`  | `logs/backup/audit.jsonl`             | JSONL     | 50MB × 5 | Audit log có cấu trúc (dual-write vào DB) |

### Dual-Write Pattern

```
Request completes → audit_from_request()
    ├── INSERT INTO mw_audit_log (...)  ← Primary (PostgreSQL)
    └── audit_logger.info(json.dumps(..))  ← Backup (audit.jsonl)
```

### Audit Log Fields

```json
{
  "ts": "2026-03-03T10:30:00+00:00",
  "rid": "req_abc123",
  "user_id": "adminrd",
  "endpoint": "/v1/chat/completions",
  "model": "chat-gpt-4o-mini",
  "purpose": "chat",
  "status": "ok",
  "status_code": 200,
  "latency_ms": 1234.5,
  "tokens_in": 500,
  "tokens_out": 1200,
  "tokens_total": 1700,
  "cost_usd": 0.0045
}
```

---

## 🔧 Hướng dẫn Vận hành

### Thao tác Thường dùng

| Thao tác              | Lệnh                                                                                    |
| --------------------- | --------------------------------------------------------------------------------------- |
| Khởi động toàn bộ     | `docker compose up -d`                                                                  |
| Build lại middleware  | `docker compose up -d --build middleware`                                               |
| Xem log middleware    | `docker logs -f openwebui-middleware`                                                   |
| Vào shell DB          | `docker exec -it openwebui-postgres psql -U openwebui_user -d middleware`               |
| Đếm audit log         | `SELECT COUNT(*) FROM mw_audit_log;`                                                    |
| Top chi phí (30 ngày) | `SELECT user_id, SUM(cost_usd) FROM mw_audit_log WHERE ts > now()-'30d' ... ORDER BY 2` |
| Reset quota user      | `POST /admin/reset` với header `X-Admin-Key`                                            |
| Backup database       | `docker exec openwebui-postgres pg_dump -U openwebui_user middleware > backup.sql`      |

### Xử lý Sự cố

| Triệu chứng              | Nguyên nhân                            | Cách khắc phục                                    |
| ------------------------ | -------------------------------------- | ------------------------------------------------- |
| Dashboard hiện "No data" | Sai khoảng thời gian / chưa có dữ liệu | Chọn "Last 30d" hoặc kiểm tra `mw_audit_log`      |
| Đăng nhập thất bại       | Sai admin key hoặc JWT hết hạn         | Kiểm tra `ADMIN_KEY` trong `.env`                 |
| "Usage missing" > 0      | Request xong nhưng thiếu token data    | LiteLLM không trả `usage` → kiểm tra model config |
| Streaming bị đứt         | EventSource timeout                    | Dashboard tự retry (backoff 1s→15s)               |
| Quota không reset        | Chu kỳ chưa hết                        | Quota auto-reset khi hết period (tuần/tháng)      |
| Cost = 0 cho model mới   | Chưa có bảng giá                       | Thêm model vào `mw_prices` hoặc `prices.json`     |
| DB connection refused    | PostgreSQL chưa sẵn sàng               | `docker logs openwebui-postgres` để kiểm tra      |

### Tham chiếu Biến Môi trường

| Biến           | Bắt buộc | Mặc định                                                   | Mô tả                                   |
| -------------- | -------- | ---------------------------------------------------------- | --------------------------------------- |
| `DATABASE_URL` | ✅       | `postgresql://openwebui_user:...@postgres:5432/middleware` | Chuỗi kết nối PostgreSQL                |
| `ADMIN_KEY`    | ✅       | _(trống)_                                                  | Khóa xác thực admin                     |
| `JWT_SECRET`   | ✅       | `default-jwt-secret-CHANGE-IN-PRODUCTION`                  | Ký JWT token — **phải đổi khi deploy**  |
| `MW_SECRET`    | ✅       | `default-secret-CHANGE-IN-PRODUCTION`                      | Mã hóa nội bộ — **phải đổi khi deploy** |
| `LITELLM_BASE` | ✅       | `http://127.0.0.1:4000/v1`                                 | URL proxy LiteLLM                       |
| `LITELLM_KEY`  | ⚠️       | _(trống)_                                                  | API key xác thực với LiteLLM            |

---

## 🧪 Chiến lược Kiểm thử

### Unit Tests (`tests/`)
- `test_subkey_manager.py`: Quota logic, concurrency
- `test_auth_guard.py`: JWT validation, expiry
- `test_stream_processor.py`: SSE parsing edge cases

### Integration Tests
- `test_fixes.py`: End-to-end chat completion (13 tests)
- `test_dashboard_improvements.py`: Dashboard API & auth (9 tests)

---

## 🚀 Triển khai & Mở rộng

### Checklist Triển khai Production

- [ ] Generate secure random values for `JWT_SECRET` and `MW_SECRET`
- [ ] Set strong `ADMIN_KEY` (min 20 characters)
- [ ] Restrict `.env` file permissions (`chmod 600`)
- [ ] Enable HTTPS (Nginx reverse proxy)
- [ ] Configure firewall (only expose port 3000)
- [ ] Set up PostgreSQL backup schedule (`pg_dump` cron)
- [ ] Monitor `mw_audit_log` growth

### Mở rộng Quy mô

| Hướng mở rộng  | Cách thực hiện              | Ghi chú                               |
| -------------- | --------------------------- | ------------------------------------- |
| **Vertical**   | Thêm uvicorn workers        | `uvicorn main:app --workers 4`        |
| **Horizontal** | Nhiều Middleware containers | Shared PostgreSQL, stateless design   |
| **DB**         | Tăng `max_connections`      | Hoặc dùng PgBouncer connection pooler |

---

## 📚 Tài liệu Bổ sung

- [Architecture Diagrams](ARCHITECTURE-DIAGRAMS.md) — System Context, Component, DFD, ERD, Use Case, Sequence, Deployment
- [RAG Architecture](rag-architecture.md) — RAG pipeline documentation
- [System Overview Report](system-overview-report.md) — Detailed system analysis

---

**Cập nhật lần cuối:** 4 tháng 3, 2026  
**Phiên bản:** 5.0 (Việt hóa + thuật ngữ + căn chỉnh bảng)
