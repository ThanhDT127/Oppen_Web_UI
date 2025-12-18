# Tài liệu giải thích dự án (chi tiết)

Tài liệu này mô tả **bài toán tổng thể**, **kiến trúc hệ thống**, và giải thích **vai trò từng thành phần/từng file** trong repo `Oppen_Web_UI` (đang đặt tại `D:\ktlt\Works\oppenwebui2`).

> Mục tiêu của tài liệu: bạn có thể đọc để hiểu nhanh hệ thống hoạt động thế nào, các endpoint nào tồn tại, quota/cost được tính ra sao, và sửa/ mở rộng ở đâu.

---

## 1) Bài toán tổng thể

Bạn đang xây một hệ thống chat LLM “3 tầng” để:

1. **Cung cấp UI chat** cho người dùng (OpenWebUI).
2. **Xác thực** người dùng theo “subkey” và **giới hạn quota** (token/cost, và cả quota theo loại tác vụ: image/tts/stt/video) bằng một lớp middleware tự viết.
3. **Proxy thống nhất** đến nhiều nhà cung cấp LLM (OpenAI/Gemini/…): LiteLLM.

Điểm quan trọng:
- **User không cần biết** key nhà cung cấp (OPENAI_API_KEY/GEMINI_API_KEY). User chỉ dùng **subkey**.
- Middleware là “điểm kiểm soát”: auth + quota + log request-id + fallback tính cost.
- LiteLLM đảm nhiệm “chuyển đổi API”: cung cấp endpoint **OpenAI-compatible** để middleware/UI gọi giống OpenAI.

---

## 2) Kiến trúc & luồng request

### 2.1 Kiến trúc 3 service

```
OpenWebUI (port 3000)
   |
   |  HTTP POST /v1/chat/completions
   |  Header: Authorization: Bearer <SUBKEY>
   v
Middleware (FastAPI, port 5000)
   |
   |  HTTP POST /chat/completions (qua LiteLLM base)
   |  Header: Authorization: Bearer <LITELLM_KEY>
   |  Header: X-Request-ID: mw_<uuid>
   v
LiteLLM (port 4000)
   |
   |  gọi provider tương ứng (OpenAI/Gemini)
   v
Provider (OpenAI / Gemini)
```

### 2.2 Phân tách “các loại key”

- `SUBKEY` (end-user):
  - Người dùng nhập vào OpenWebUI (Settings → Connections → API Key).
  - Middleware kiểm tra subkey này trong `llm-mw/users.json`.

- `LITELLM_KEY` (master key của LiteLLM):
  - Middleware dùng để gọi LiteLLM.
  - Không đưa cho end-user.

- `OPENAI_API_KEY`, `GEMINI_API_KEY`:
  - LiteLLM dùng để gọi provider.
  - Không đưa cho end-user.

- `ADMIN_KEY`:
  - Key quản trị để gọi các endpoint `/admin/*` (xem usage/reset/reconcile).

---

## 3) Tổng quan cấu trúc repo

Các thành phần trong repo (mức quan trọng cao → thấp):

- `litellm/`
  - `litellm_config.yaml`: khai báo model list & master key & log.

- `llm-mw/`
  - `main.py`: **middleware FastAPI** (trái tim của hệ thống).
  - `users.json`: “DB user” (subkey, allowed_models, quota,…).
  - `users.example.json`: mẫu cấu trúc users.
  - `prices.json`: bảng giá fallback khi LiteLLM không trả cost header.
  - `pending.csv`: runtime artifact (tự sinh) để track request stream đang pending.
  - `smoke_test_endpoints.py`: script test nhanh các endpoint chính.

- `scripts/`
  - `start_stack.ps1`: chạy 3 service + redirect logs.
  - `run_litellm_with_env.ps1`: load `.env` rồi chạy LiteLLM.
  - `stop_stack.ps1`: dừng 3 service theo port.

- `.env` (local, không commit)
  - chứa cấu hình runtime (base URLs, keys, DATA_DIR,…).

- `.webui_secret_key`
  - secret key của OpenWebUI (được tự tạo/đọc khi chạy OpenWebUI).

- `openwebui_data/` (runtime data)
  - nơi OpenWebUI lưu DB & dữ liệu (ví dụ `webui.db`, `vector_db/`…).

- `logs/` (runtime logs)
  - logs cho LiteLLM/middleware/openwebui.

---

## 4) Giải thích từng file/thư mục

### 4.0 Các file top-level khác

- `README.md`
  - Là hướng dẫn vận hành chi tiết (rất dài) gồm: cách chạy 3 service, cấu hình Connections trong OpenWebUI, mô tả endpoint middleware, ghi chú backup/restore, v.v.
  - Tài liệu bạn đang đọc (`PROJECT_EXPLAINED_VI.md`) thiên về **giải thích code/kiến trúc** và “ý nghĩa từng phần”.

- `requirements.txt`
  - Danh sách Python packages tối thiểu để chạy stack.
  - Thực tế cài đặt thường dùng `pip install -r requirements.txt` trong venv.

- `.gitignore`
  - Chặn commit các file nhạy cảm và runtime artifacts như: `.env`, `llm-mw/users.json`, `openwebui_data/`, `logs/`, `*.db`, v.v.
  - Lý do: keys/secrets + DB local không nên lên git.

- `logs/`
  - Thư mục log runtime được `scripts/start_stack.ps1` tạo và ghi vào.
  - Thường có: `litellm.*.log`, `middleware.*.log`, `openwebui.*.log`.

### 4.1 `litellm/litellm_config.yaml`

**Vai trò:** cấu hình LiteLLM chạy ở port 4000, expose API OpenAI-compatible.

Các phần chính:
- `model_list`: danh sách model mà LiteLLM sẽ expose.
  - Ví dụ: `gpt-4o`, `gpt-4o-mini`, `gemini-2.5-flash`,…
  - Mỗi entry map về provider-specific model:
    - OpenAI: `model: openai/<model>`
    - Gemini: `model: gemini/<model>`
- `general_settings.master_key: os.environ/LITELLM_KEY`:
  - LiteLLM yêu cầu bearer token khi gọi.
  - Middleware sẽ gửi `Authorization: Bearer <LITELLM_KEY>`.
- `logging.file: "litellm/litellm.log"`:
  - log file để middleware có thể “reconcile” usage theo request-id.

### 4.2 `llm-mw/users.json`

**Vai trò:** “database” đơn giản dạng JSON chứa danh sách user.

Mỗi user có:
- `user_id`: định danh.
- `subkey`: token mà end-user dùng.
- `allowed_models`: `[*]` hoặc list model cụ thể.
- `quota`:
  - `period`: `weekly|monthly`
  - `timezone`: `Asia/Bangkok`…
  - `limit_tokens`, `limit_cost_usd` (0 = unlimited)
  - các counter `used_*`

> Middleware sẽ đọc/ghi file này trực tiếp để update counters sau mỗi request.

### 4.3 `llm-mw/prices.json`

**Vai trò:** bảng giá fallback.

Middleware ưu tiên lấy cost từ LiteLLM thông qua header:
- `x-litellm-response-cost` hoặc `x-litellm-cost`

Nếu không có header cost, middleware sẽ tự tính fallback bằng `prices.json`.

Bảng giá có thể gồm:
- Text/chat tokens: `input_per_1m`, `output_per_1m` (USD / 1,000,000 tokens)
- Image: `per_image_usd` (có thể theo quality/size)
- TTS: `tts_usd_per_1m_chars`
- Video: `video_usd_per_second` hoặc `video_usd_per_second_by_size`

### 4.4 `llm-mw/smoke_test_endpoints.py`

**Vai trò:** test nhanh các endpoint middleware với một `SUBKEY`.

Script gọi lần lượt:
- `/v1/chat/completions`
- `/v1/images/generations`
- `/v1/audio/speech` (stream)
- `/v1/audio/transcriptions` (multipart)
- `/v1/video/generations`

và so sánh chênh lệch quota counter trong `users.json`.

### 4.5 `scripts/start_stack.ps1`

**Vai trò:** chạy cả stack (LiteLLM + Middleware + OpenWebUI) và ghi log.

Tính năng chính:
- Auto activate venv (nếu có `$env:VIRTUAL_ENV` hoặc `.venv`/`..\..\venv`).
- Start từng service nếu port chưa “Listen”.
- Chạy OpenWebUI với UTF-8 env để tránh UnicodeEncodeError khi redirect stdout.
- Set `DATA_DIR` cho OpenWebUI để DB nằm trong `openwebui_data/` của project.

### 4.6 `scripts/run_litellm_with_env.ps1`

**Vai trò:** load `.env` (đặt env var vào `Process`) rồi chạy lệnh `litellm --config ...`.

Điểm quan trọng:
- Nếu `OPENAI_API_KEY` và `GEMINI_API_KEY` đều thiếu → script hard-fail (để tránh chạy “rỗng”).
- Dọn `DATABASE_URL` khỏi env nếu bị set từ trước (để tránh LiteLLM init Prisma ngoài ý muốn).

### 4.7 `openwebui_data/`

**Vai trò:** nơi OpenWebUI lưu dữ liệu runtime.

Thường gồm:
- `webui.db` (SQLite): users/chats/messages/settings…
- `vector_db/`: embeddings (ChromaDB) nếu dùng RAG.

---

## 5) Cấu hình runtime (`.env`) – ý nghĩa từng biến

> Không nên đưa file `.env` lên git. Chỉ mô tả cấu trúc & ý nghĩa.

Ví dụ tối thiểu (dùng placeholder):

```env
# Middleware -> LiteLLM
LITELLM_BASE=http://127.0.0.1:4000/v1
LITELLM_KEY=<LITELLM_MASTER_KEY>

# Admin endpoints của middleware
ADMIN_KEY=<MW_ADMIN_KEY>

# Provider keys cho LiteLLM
OPENAI_API_KEY=<OPENAI_API_KEY>
GEMINI_API_KEY=<GEMINI_API_KEY>

# OpenWebUI data dir (để DB nằm trong project)
DATA_DIR=D:/ktlt/Works/oppenwebui2/openwebui_data
```

---

## 6) Giải thích chi tiết `llm-mw/main.py`

File này là **FastAPI middleware**. Có thể chia thành các “khối code” chính như sau:

### Khối A — Khởi tạo app, CORS, load env, cấu hình paths/log

Mục tiêu:
- tạo FastAPI app
- load `.env`
- set đường dẫn tới:
  - `USERS_FILE`, `PRICES_FILE`, `PENDING_CSV`, `LITELLM_LOG_FILE`
- set logger `middleware.log`

Ý nghĩa chính:
- Tất cả quota/usage được ghi trong `llm-mw/users.json`.
- Log reconcile đọc từ `litellm/litellm.log`.

### Khối B — Lifecycle: tạo HTTP client dùng lại

- `@app.on_event("startup")`: tạo `httpx.AsyncClient` dùng chung, giới hạn connection.
- `@app.on_event("shutdown")`: đóng client.

Ý nghĩa:
- tránh tạo client mới mỗi request → giảm overhead.

### Khối C — Middleware log request

`@app.middleware("http")`:
- đo latency
- log `rid` (request-id) + method/path/status

`rid` lấy từ:
- `request.state.mw_request_id` (do middleware set), hoặc
- `X-Request-ID` header client gửi.

### Khối D — Auth & permission

1) `_require_user(request)`
- Đọc header `Authorization: Bearer <subkey>`
- Tìm user bằng `_find_user(subkey)`
- Nếu không có user/ user inactive → 401/403

2) `_assert_model_allowed(user, model)`
- Nếu `allowed_models == ["*"]` → cho tất cả
- Nếu không, chỉ cho phép model nằm trong list

### Khối E — Quota & cost helpers

1) `_load_users()` / `_save_users()`
- đọc/ghi JSON list từ `users.json`

2) `_load_prices()`
- đọc `prices.json` để fallback tính cost

3) `_period_anchor_ms(period, tz)`
- tính mốc đầu kỳ (đầu tuần hoặc đầu tháng) theo timezone

4) `_maybe_reset_quota(user)`
- nếu sang kỳ mới → reset tất cả `used_*` counters

5) `_enforce_and_bump_task_quota(...)`
- khóa `_lock` để tránh race-condition khi nhiều request đồng thời
- enforce quota trước khi gọi provider (apply=False) hoặc sau khi gọi provider (apply=True)
- tăng các bộ đếm:
  - token/cost
  - image requests
  - tts requests/chars
  - stt requests
  - video requests/seconds

6) `_get_litellm_cost_from_headers(headers)`
- đọc cost từ header LiteLLM

7) `_calc_cost_usd(...)`, `_calc_image_cost_usd(...)`, `_calc_tts_cost_usd(...)`, `_calc_video_cost_usd(...)`
- fallback cost calculator khi LiteLLM không trả cost

### Khối F — Pending stream & reconcile

1) `_append_pending(request_id, user_id)` / `_remove_pending(request_id)`
- ghi/xóa request streaming đang chạy vào file `pending.csv`

2) `_find_usage_in_litellm_log(request_id)`
- đọc cuối file `litellm/litellm.log` (tối đa ~5MB)
- regex parse model/tokens/cost theo request_id

Ý nghĩa:
- Streaming đôi khi không có `usage` ngay ở response.
- Admin có thể gọi `/admin/reconcile` để “bù” usage dựa trên log.

---

## 7) Danh sách endpoint trong middleware (đầy đủ)

### 7.1 `GET /health`
- Trả `{ok: true, time: <unix>}`
- Dùng để kiểm tra middleware sống.

### 7.2 `GET /v1/models`
- Proxy sang `GET {LITELLM_BASE}/models`
- Trả list model mà LiteLLM expose.
- Nếu LiteLLM down → trả `{data: []}`.

### 7.3 `POST /v1/chat/completions`

**Vai trò:** endpoint chính cho chat (OpenAI-compatible).

Luồng xử lý:
1. Auth user bằng `_require_user`.
2. Validate `model` + check allowed.
3. Reset quota nếu sang kỳ.
4. “Gỡ” vấn đề `gpt-5*`:
   - Nếu client gửi `max_tokens` → đổi sang `max_completion_tokens`.
   - Set floor cho `gpt-5*` để tránh output rỗng.
   - Clamp token budget tối đa 512.
5. Tạo `request_id = mw_<uuid>`; gắn vào:
   - `X-Request-ID` header khi gọi LiteLLM
   - `body.metadata.mw_request_id`
6. Nếu `stream=true`:
   - `_append_pending`
   - mở upstream stream bằng `httpx.AsyncClient(...).send(stream=True)`
   - trả `StreamingResponse(text/event-stream)`
   - cuối stream: `_remove_pending` + close stream/client
7. Nếu non-stream:
   - POST sang LiteLLM
   - lấy `usage` (prompt_tokens/completion_tokens)
   - tính `cost_usd` từ header hoặc fallback
   - enforce quota (`limit_tokens`, `limit_cost_usd`)
   - `_enforce_and_bump_task_quota(add_tokens, add_cost_usd)`
   - thêm debug fields vào response:
     - `_mw_user`, `_mw_request_id`, `_mw_added_tokens`, `_mw_added_cost_usd`

### 7.4 `POST /v1/images/generations`

**Vai trò:** tạo ảnh (OpenAI-compatible images endpoint).

Luồng:
- default model: `gemini-2.5-flash-image`.
- enforce quota image requests trước call.
- drop một số param không phù hợp:
  - `gpt-image-1*`: bỏ `response_format`
  - `gemini-*`: bỏ `user` và `metadata`
- call LiteLLM `/images/generations`
- tăng counters (image_requests + cost)

### 7.5 `POST /v1/audio/speech`

**Vai trò:** TTS (text-to-speech), trả về stream binary.

Luồng:
- enforce quota trước call: tts_requests + tts_chars
- mở upstream stream và trả `StreamingResponse` với `content-type` từ LiteLLM
- sau khi call thành công: bump request/chars + cost

### 7.6 `POST /v1/audio/transcriptions`

**Vai trò:** STT (speech-to-text), nhận multipart `file`.

Luồng:
- parse `await request.form()`
- đọc file bytes + build multipart sang LiteLLM
- enforce stt_requests trước call
- call LiteLLM `/audio/transcriptions`
- cost: chỉ charge nếu LiteLLM trả cost header (fallback STT theo phút không tính ở đây)

### 7.7 `POST /v1/video/generations`

**Vai trò:** tạo video (proxy sang LiteLLM `/videos`).

Luồng:
- parse duration (`seconds|duration_seconds|duration`) → normalize về `seconds`
- enforce video_requests + video_seconds trước call
- call LiteLLM `/videos`
- cost header hoặc fallback theo `prices.json`

### 7.8 `GET /admin/usage`
- Header phải là `Authorization: Bearer <ADMIN_KEY>`
- Trả toàn bộ list users từ `users.json`.

### 7.9 `POST /admin/reset`
- `Authorization` admin
- Body có thể có `user_id` (nếu không có: reset tất cả)
- reset quota theo kỳ bằng `_maybe_reset_quota` và ghi file.

### 7.10 `POST /admin/reconcile`
- `Authorization` admin
- Body: `{request_id, user_id, model?}`
- đọc usage từ `litellm.log` theo request_id
- tính lại token + cost
- cộng dồn vào `users.json` (dùng lock)
- `_remove_pending(request_id)`

---

## 8) Ghi chú vận hành quan trọng

- OpenWebUI lần đầu có thể tải model embeddings (HuggingFace) → khởi động chậm.
- Với Keras 3, Transformers yêu cầu `tf-keras` → nếu thiếu sẽ báo lỗi khi OpenWebUI update models.
- Streaming requests: usage/cost có thể cần reconcile nếu client ngắt giữa chừng.

---

## 9) Checklist khi muốn mở rộng

- Thêm model mới:
  1) thêm vào `litellm/litellm_config.yaml`
  2) (tuỳ) cập nhật `llm-mw/prices.json` để fallback cost
  3) cập nhật `llm-mw/users.json` (allowed_models) nếu bạn không dùng `[*]`

- Thêm loại quota mới:
  - mở rộng schema `quota` trong `users.json` + cập nhật `_enforce_and_bump_task_quota`.

---

## 10) Tóm tắt “ai làm gì” (1 trang)

- OpenWebUI (3000): UI chat + lưu lịch sử vào SQLite trong `openwebui_data/`.
- Middleware (5000): auth subkey + enforce quota + log request-id + proxy đến LiteLLM.
- LiteLLM (4000): unify API & route đến OpenAI/Gemini.

Hết.
