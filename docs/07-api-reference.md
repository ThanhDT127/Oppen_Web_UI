# Tài liệu API - LLM Middleware

Tài liệu đầy đủ cho tất cả API endpoints trong LLM Middleware (Port 5000).

---

## URL Gốc

```
http://localhost:5000
```

Tất cả endpoints sử dụng định dạng tương thích OpenAI trừ khi có ghi chú khác.

---

## Endpoints Công khai (Không cần Xác thực)

### Kiểm tra Sức khỏe

```http
GET /health
```

**Mô tả:** Kiểm tra middleware có đang chạy không.

**Phản hồi:**
```json
{
  "ok": true,
  "time": 1772446338,
  "uptime_seconds": 233,
  "litellm": "healthy",
  "disk_free_gb": 53.35,
  "active_users": 4
}
```

**Mã trạng thái:**
- `200 OK` - Dịch vụ hoạt động bình thường

---

### Danh sách Model

```http
GET /v1/models
```

**Mô tả:** Lấy danh sách các mô hình LLM từ LiteLLM proxy. Bao gồm cả các **virtual auto-routing models** (inject bởi middleware).

**Phản hồi:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "openai-auto",
      "object": "model",
      "created": 1234567890,
      "owned_by": "smart-routing",
      "name": "ChatGPT (Auto)"
    },
    {
      "id": "chat-gpt-5.4",
      "object": "model",
      "created": 1234567890,
      "owned_by": "openai"
    }
  ]
}
```

> Auto models (`*-auto`) chỉ hiện nếu user có quyền dùng ít nhất 1 model trong tier.

**Mã trạng thái:**
- `200 OK` - Lấy danh sách thành công
- `502 Bad Gateway` - LiteLLM proxy không khả dụng

---

### Trạng thái Quota

```http
GET /v1/_mw/quota-status?user_id=<user_id>
```

Hoặc xác thực qua Header thay vì `user_id`:
```http
GET /v1/_mw/quota-status
Authorization: Bearer <subkey>
```

**Mô tả:** Truy vấn thông tin quota hiện tại của người dùng. Trả về dưới dạng phần trăm (không chứa chi tiết nhạy cảm), rất phù hợp sử dụng cho UI (Frontend) hoặc Open WebUI Filter để thông báo/chặn gửi tin nếu đã hết quota.

**Phản hồi:**
```json
{
  "active": true,
  "quota_used_pct": 85.5,
  "quota_remaining_pct": 14.5
}
```

**Mã trạng thái:**
- `200 OK` - Lấy trạng thái thành công
- `400 Bad Request` - Cần truyền tham số user_id hoặc Header Authorization

---

## Endpoints Yêu cầu Xác thực (Cần Subkey)

Tất cả endpoints chat yêu cầu subkey hợp lệ trong header `Authorization`:

```
Authorization: Bearer sk_user_abc123def456
```

### Chat Completion (Không Streaming)

```http
POST /v1/chat/completions
Content-Type: application/json
Authorization: Bearer <subkey>
```

**Nội dung Request:**
```json
{
  "model": "chat-gpt-5.4",
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

**Phản hồi:**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "chat-gpt-5.4",
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

**Mã trạng thái:**
- `200 OK` - Hoàn thành thành công
- `401 Unauthorized` - Subkey không hợp lệ hoặc thiếu
- `403 Forbidden` - Vượt quá quota
- `502 Bad Gateway` - Lỗi LiteLLM proxy

---

### Chat Completion (Streaming)

```http
POST /v1/chat/completions
Content-Type: application/json
Authorization: Bearer <subkey>
```

**Nội dung Request:**
```json
{
  "model": "chat-gpt-5.4",
  "messages": [
    {
      "role": "user",
      "content": "Tell me a short story."
    }
  ],
  "stream": true
}
```

**Phản hồi:** Server-Sent Events (SSE) stream

```
data: {"id":"chatcmpl-xyz","object":"chat.completion.chunk","created":1234567890,"model":"chat-gpt-5.4","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}

data: {"id":"chatcmpl-xyz","object":"chat.completion.chunk","created":1234567890,"model":"chat-gpt-5.4","choices":[{"index":0,"delta":{"content":"Once"},"finish_reason":null}]}

data: {"id":"chatcmpl-xyz","object":"chat.completion.chunk","created":1234567890,"model":"chat-gpt-5.4","choices":[{"index":0,"delta":{"content":" upon"},"finish_reason":null}]}

...

data: [DONE]
```

**Mã trạng thái:**
- `200 OK` - Stream bắt đầu thành công
- `401 Unauthorized` - Subkey không hợp lệ
- `403 Forbidden` - Vượt quá quota

---

### Chuyển đổi Giọng nói thành Văn bản

```http
POST /v1/audio/transcriptions
Content-Type: multipart/form-data
Authorization: Bearer <subkey>
```

**Nội dung Request:**
```
--boundary
Content-Disposition: form-data; name="file"; filename="audio.mp3"
Content-Type: audio/mpeg

<dữ liệu âm thanh nhị phân>
--boundary
Content-Disposition: form-data; name="model"

whisper-1
--boundary--
```

**Phản hồi:**
```json
{
  "text": "This is the transcribed text from the audio file."
}
```

**Định dạng hỗ trợ:** MP3, MP4, WAV, M4A, WEBM

**Mã trạng thái:**
- `200 OK` - Chuyển đổi thành công
- `400 Bad Request` - Định dạng file không hợp lệ
- `401 Unauthorized` - Subkey không hợp lệ

---

### Tạo Embedding Vector

```http
POST /v1/embeddings
Content-Type: application/json
Authorization: Bearer <subkey>
```

**Nội dung Request:**
```json
{
  "model": "gemini-embedding-001",
  "input": "This is a text to embed for vector search."
}
```

**Phản hồi:**
```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "embedding": [ 0.1, -0.05, 0.3, 0.8 ],
      "index": 0
    }
  ],
  "model": "gemini-embedding-001",
  "usage": {
    "prompt_tokens": 10,
    "total_tokens": 10
  }
}
```

**Mã trạng thái:**
- `200 OK` - Hoàn thành thành công
- `401 Unauthorized` - Subkey không hợp lệ
- `403 Forbidden` - Vượt quá quota

---

## Endpoints Quản trị (Cần Admin Key)

Tất cả endpoints admin yêu cầu ADMIN_KEY trong header `Authorization`:

```
Authorization: Bearer admin_master_key_456
```

### Đăng nhập Dashboard

```http
POST /v1/_mw/dashboard/login
Content-Type: application/json
```

**Nội dung Request:**
```json
{
  "username": "admin",
  "password": "admin_master_key_456"
}
```

**Phản hồi:**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Thiết lập Cookie:**
```
mw_dashboard_token=<jwt_token>; Path=/; HttpOnly; Max-Age=14400
```

**Mã trạng thái:**
- `200 OK` - Đăng nhập thành công (đã thiết lập JWT cookie)
- `401 Unauthorized` - Thông tin đăng nhập không hợp lệ

---

### Đăng xuất Dashboard

```http
POST /v1/_mw/dashboard/logout
```

**Phản hồi:**
```json
{
  "success": true
}
```

**Xóa Cookie:** `mw_dashboard_token`

**Mã trạng thái:**
- `200 OK` - Đăng xuất thành công

---

### Tổng hợp Dashboard (Xác thực JWT)

```http
GET /v1/_mw/summary
Cookie: mw_dashboard_token=<jwt_token>
```

**Mô tả:** Lấy dữ liệu metrics tổng hợp để hiển thị dashboard.

**Phản hồi:**
```json
{
  "time_range": {
    "start": "2026-03-02T01:20:17Z",
    "end": "2026-03-03T01:20:17Z",
    "bucket_size": "hour"
  },
  "totals": {
    "requests_total": 45,
    "requests_ok": 42,
    "error_count": 3,
    "error_rate_percent": 6.67,
    "tokens_total": 15000,
    "cost_total_usd": 0.025,
    "p95_latency_ms": 1250.5,
    "pending_open_count": 0,
    "chat_calls": 40,
    "embedding_calls": 2,
    "image_calls": 2,
    "audio_calls": 1,
    "video_calls": 0,
    "billable_calls": 43,
    "nonbillable_calls": 2,
    "usage_missing_calls": 0
  },
  "breakdown_by_user": [...],
  "breakdown_by_model": [...],
  "timeseries": [...]
}
```

**Tham số truy vấn:**
- `minutes` (int) - Khoảng thời gian (mặc định: 60)
- `start` / `end` (ISO datetime) - Khoảng thời gian tùy chỉnh
- `bucket` (string) - Độ chi tiết timeseries: "auto", "minute", "hour", "day"

**Nguồn dữ liệu:** Bảng PostgreSQL `mw_audit_log` (dự phòng: `audit.jsonl`)

**Mã trạng thái:**
- `200 OK` - Lấy tổng hợp thành công
- `403 Forbidden` - JWT token không hợp lệ hoặc hết hạn

---

### Truy vấn Audit Log (Xác thực JWT hoặc Admin)

```http
GET /v1/_mw/audit/query?limit=50&offset=0
Cookie: mw_dashboard_token=<jwt_token>
```

**Mô tả:** Tìm kiếm và lọc lịch sử request/audit log (phân trang).

**Tham số truy vấn:**
- `limit` (int) - Số lượng kết quả (1-500, mặc định: 50)
- `offset` (int) - Vị trí bắt đầu
- `user_id` / `model` / `status` / `endpoint` (string) - Bộ lọc tìm kiếm
- `min_cost` / `max_cost` (float) - Lọc theo chi phí lệnh gọi
- `start` / `end` (ISO datetime) - Khoảng thời gian
- `sort_by` (string) - "timestamp", "cost", "tokens", "duration"
- `sort_order` (string) - "asc", "desc"

**Phản hồi:**
```json
{
  "total": 125,
  "limit": 50,
  "offset": 0,
  "results": [
    {
      "ts": "2026-03-03T10:40:15+07:00",
      "user_id": "user1",
      "model": "chat-gpt-5.4",
      "status": "ok",
      "cost_usd": 0.002
    }
  ],
  "source": "database"
}
```

---

### Quản lý Thông báo Admin (Notifications)

```http
GET /v1/_mw/admin/notifications
Cookie: mw_dashboard_token=<jwt_token>
```

**Mô tả:** Lấy danh sách thông báo quản trị viên (ví dụ cảnh báo có người dùng sắp hết quota, alert hệ thống). 
Các API liên quan (Yêu cầu JWT hoặc Admin Key):
- `GET /v1/_mw/admin/notifications` - Danh sách thông báo
- `GET /v1/_mw/admin/notifications/unread` - Đếm thông báo chưa đọc
- `POST /v1/_mw/admin/notifications/{id}/read` - Đánh dấu thông báo đã đọc
- `POST /v1/_mw/admin/notifications/read-all` - Đánh dấu đọc tất cả

---

### Cấu hình Cảnh báo & Alert (Alert Config)

```http
GET /v1/_mw/admin/alerts/config
Authorization: Bearer <admin_key>
```

**Mô tả:** Đọc và cập nhật cấu hình thông báo (ví dụ cấu hình SMTP server, ngưỡng bật cảnh báo 80% quota, email nhận cảnh báo).
Các API liên quan (Chỉ dành cho Admin Key):
- `GET /v1/_mw/admin/alerts/config` - Lấy cấu hình
- `PUT /v1/_mw/admin/alerts/config` - Lưu cấu hình mới
- `POST /v1/_mw/admin/alerts/test-email` - Gửi email test xem SMTP hoạt động tốt không

---

### Thống kê Sử dụng

```http
GET /admin/usage
X-Admin-Key: <admin_key>
```

**Mô tả:** Xem thống kê sử dụng của tất cả user (subkey đã ẩn vì bảo mật).

**Phản hồi:**
```json
[
  {
    "user_id": "admin",
    "active": true,
    "allowed_models": ["*"],
    "used_tokens": 45000,
    "used_cost_usd": 0.125,
    "quota": {
      "period": "monthly",
      "timezone": "Asia/Bangkok",
      "limit_tokens": 0,
      "limit_cost_usd": 0,
      "period_start": 1735027200000,
      "used_tokens": 12000,
      "used_cost_usd": 0.035
    }
  }
]
```

**Mã trạng thái:**
- `200 OK` - Lấy thống kê thành công
- `403 Forbidden` - Admin key không hợp lệ

---

### Reset Quota

```http
POST /admin/reset
Content-Type: application/json
X-Admin-Key: <admin_key>
```

**Mô tả:** Reset quota theo chu kỳ cho user cụ thể hoặc tất cả users.

**Nội dung Request:**
```json
{
  "user_id": "user1"
}
```

**Bỏ `user_id` để reset tất cả user:**
```json
{}
```

**Phản hồi:**
```json
{
  "ok": true
}
```

**Mã trạng thái:**
- `200 OK` - Reset quota thành công
- `403 Forbidden` - Admin key không hợp lệ

---

### Đối chiếu Dữ liệu Sử dụng (Reconcile)

```http
POST /admin/reconcile
Content-Type: application/json
X-Admin-Key: <admin_key>
```

**Mô tả:** Đối chiếu thủ công dữ liệu sử dụng streaming request từ log LiteLLM.

**Nội dung Request:**
```json
{
  "request_id": "mw_abc123def456",
  "user_id": "user1"
}
```

**Phản hồi:**
```json
{
  "ok": true,
  "request_id": "mw_abc123def456",
  "user_id": "user1",
  "model": "chat-gpt-5.4",
  "prompt_tokens": 250,
  "completion_tokens": 180,
  "total_tokens": 430,
  "cost_usd": 0.00215
}
```

**Mã trạng thái:**
- `200 OK` - Đối chiếu thành công
- `403 Forbidden` - Admin key không hợp lệ
- `404 Not Found` - Không tìm thấy request ID hoặc user

---

### Stream Sự kiện Quản trị (SSE)

```http
GET /v1/_mw/stream
Cookie: mw_dashboard_token=<jwt_token>
```

**Mô tả:** Stream real-time các sự kiện quản trị để giám sát dashboard.

**Phản hồi:** Server-Sent Events

```
event: subkey_created
data: {"subkey":"sk_user_new123","quota":100,"timestamp":"2025-12-22T10:35:00Z"}

event: quota_exceeded
data: {"subkey":"sk_user_abc123","attempted":101,"quota":100,"timestamp":"2025-12-22T10:36:00Z"}

event: subkey_deleted
data: {"subkey":"sk_user_old456","timestamp":"2025-12-22T10:37:00Z"}
```

**Các loại sự kiện:**
- `subkey_created` - Subkey mới được tạo
- `subkey_updated` - Quota hoặc trạng thái active thay đổi
- `subkey_deleted` - Subkey bị xóa
- `quota_exceeded` - User đạt giới hạn quota
- `chat_completion` - Chat request đã xử lý

**Mã trạng thái:**
- `200 OK` - Stream bắt đầu
- `403 Forbidden` - JWT token không hợp lệ

---

## Tham số Chung

### Tham số Chat Completion

| STT | Tham số             | Kiểu         | Bắt buộc | Mặc định | Mô tả                                 |
| --- | ------------------- | ------------ | -------- | -------- | ------------------------------------- |
| 01  | `model`             | string       | Co       | -        | ID model (vd: "chat-gpt-5.4")          |
| 02  | `messages`          | array        | Co       | -        | Lịch sử hội thoại                     |
| 03  | `temperature`       | float        | Không    | 0.7      | Nhiệt độ lấy mẫu (0-2)                |
| 04  | `max_tokens`        | integer      | Không    | -        | Độ dài phản hồi tối đa                |
| 05  | `stream`            | boolean      | Không    | false    | Bật phản hồi streaming                |
| 06  | `top_p`             | float        | Không    | 1.0      | Ngưỡng lấy mẫu nucleus                |
| 07  | `frequency_penalty` | float        | Không    | 0.0      | Phạt lặp lại (-2 đến 2)               |
| 08  | `presence_penalty`  | float        | Không    | 0.0      | Phạt đa dạng chủ đề (-2 đến 2)        |
| 09  | `stop`              | string/array | Không    | null     | Chuỗi dừng                            |
| 10  | `user`              | string       | Không    | -        | Định danh người dùng cuối để theo dõi |

### Đối tượng Message

```json
{
  "role": "user|assistant|system",
  "content": "Nội dung text hoặc mảng cho multimodal"
}
```

**Message Multimodal (kèm hình ảnh):**
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

## Phản hồi Lỗi

Tất cả lỗi theo định dạng OpenAI:

```json
{
  "error": {
    "message": "Invalid subkey or quota exceeded",
    "type": "invalid_request_error",
    "code": "quota_exceeded"
  }
}
```

### Mã Lỗi

| STT | HTTP Status | Loại lỗi                | Mô tả                        |
| --- | ----------- | ----------------------- | ---------------------------- |
| 01  | 400         | `invalid_request_error` | Request body không hợp lệ    |
| 02  | 401         | `authentication_error`  | Thiếu hoặc sai API key       |
| 03  | 403         | `quota_exceeded_error`  | Đã đạt giới hạn quota user   |
| 04  | 404         | `not_found_error`       | Tài nguyên không tồn tại     |
| 05  | 429         | `rate_limit_error`      | Quá nhiều request            |
| 06  | 500         | `internal_error`        | Lỗi phía server              |
| 07  | 502         | `gateway_error`         | LiteLLM proxy không khả dụng |

---

## Giới hạn Tốc độ

**Triển khai hiện tại:** Không có giới hạn tốc độ toàn cục (kiểm soát bởi LiteLLM proxy).

**Giới hạn Per-User:** Thực thi qua quota subkey:
- Mỗi subkey có `quota` (hạn mức chi phí tính bằng USD hoặc theo Tokens cho từng chu kỳ tuần/tháng. API hiện không giới hạn số lượng request per minute để tránh ảnh hưởng luồng hoạt động song song).
- Vượt quota trả về `403 Forbidden`
- Quota tự động reset khi request hoàn thành

**Nâng cấp tương lai:** Giới hạn tốc độ dựa trên token (requests mỗi phút).

---

## Theo dõi Sử dụng

Tất cả request được theo dõi trong PostgreSQL (bảng `mw_audit_log`) với bản sao lưu file `logs/audit.jsonl`:

**Ví dụ truy vấn database:**
```sql
SELECT ts, user_id, model, tokens_total, cost_usd, status
FROM mw_audit_log
WHERE ts >= NOW() - INTERVAL '24 hours'
ORDER BY ts DESC;
```

**Định dạng bản sao lưu file (audit.jsonl):**
```jsonl
{"ts":"2026-03-03T10:40:15+07:00","rid":"mw_abc123","user_id":"user1","model":"chat-gpt-4o-mini","status":"ok","tokens_total":1234,"cost_usd":0.001}
```

---

## Ví dụ Kiểm thử

### Ví dụ cURL

**Chat Completion:**
```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Authorization: Bearer sk_user_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "chat-gpt-5.4",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": false
  }'
```

**Tạo Subkey:**
```bash
curl -X POST http://localhost:5000/v1/_mw/subkey \
  -H "Authorization: Bearer admin_master_key_456" \
  -H "Content-Type: application/json" \
  -d '{"quota": 100, "note": "Test user"}'
```

**Đăng nhập Dashboard:**
```bash
curl -X POST http://localhost:5000/v1/_mw/dashboard/login \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"username": "admin", "password": "admin_master_key_456"}'
```

**Lấy Tổng hợp (dùng cookie):**
```bash
curl http://localhost:5000/v1/_mw/summary -b cookies.txt
```

---

## Tài liệu Liên quan

- [Kiến trúc hệ thống](03-architecture.md) - Thiết kế hệ thống và luồng dữ liệu
- [Dashboard Admin](08-dashboard.md) - Hướng dẫn sử dụng giao diện admin
- [Quản lý người dùng](09-user-management.md) - CRUD user và quản lý quota

---

**Cập nhật lần cuối:** 11 tháng 05, 2026  
**Phiên bản API:** 2.2 (Thêm Smart Routing — Auto Models)
