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

**Mô tả:** Lấy danh sách các mô hình LLM từ LiteLLM proxy.

**Phản hồi:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "gpt-4-turbo",
      "object": "model",
      "created": 1234567890,
      "owned_by": "openai"
    },
    {
      "id": "gemini-pro",
      "object": "model",
      "created": 1234567890,
      "owned_by": "google"
    }
  ]
}
```

**Mã trạng thái:**
- `200 OK` - Lấy danh sách thành công
- `502 Bad Gateway` - LiteLLM proxy không khả dụng

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
  "model": "gpt-4-turbo",
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
  "model": "gpt-4-turbo",
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
  "model": "gpt-4-turbo",
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
data: {"id":"chatcmpl-xyz","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4-turbo","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}

data: {"id":"chatcmpl-xyz","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4-turbo","choices":[{"index":0,"delta":{"content":"Once"},"finish_reason":null}]}

data: {"id":"chatcmpl-xyz","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4-turbo","choices":[{"index":0,"delta":{"content":" upon"},"finish_reason":null}]}

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

## Endpoints Quản trị (Cần Admin Key)

Tất cả endpoints admin yêu cầu ADMIN_KEY trong header `Authorization`:

```
Authorization: Bearer YOUR_ADMIN_KEY
```

### Đăng nhập Dashboard

```http
POST /dashboard/login
Content-Type: application/json
```

**Nội dung Request:**
```json
{
  "username": "admin",
  "password": "YOUR_ADMIN_KEY"
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
POST /dashboard/logout
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
    "chat_calls": 40,
    "image_calls": 2,
    "audio_calls": 3
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
  "model": "gpt-4-turbo",
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

| Tham số              | Kiểu        | Bắt buộc | Mặc định | Mô tả                                 |
| -------------------- | ----------- | -------- | -------- | --------------------------------------|
| `model`              | string      | Co       | -        | ID model (vd: "gpt-4-turbo")          |
| `messages`           | array       | Co       | -        | Lịch sử hội thoại                     |
| `temperature`        | float       | Không    | 0.7      | Nhiệt độ lấy mẫu (0-2)                |
| `max_tokens`         | integer     | Không    | -        | Độ dài phản hồi tối đa                |
| `stream`             | boolean     | Không    | false    | Bật phản hồi streaming                |
| `top_p`              | float       | Không    | 1.0      | Ngưỡng lấy mẫu nucleus                |
| `frequency_penalty`  | float       | Không    | 0.0      | Phạt lặp lại (-2 đến 2)               |
| `presence_penalty`   | float       | Không    | 0.0      | Phạt đa dạng chủ đề (-2 đến 2)        |
| `stop`               | string/array| Không    | null     | Chuỗi dừng                            |
| `user`               | string      | Không    | -        | Định danh người dùng cuối để theo dõi |

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

| HTTP Status | Loại lỗi                 | Mô tả                        |
| ----------- | ------------------------ | ---------------------------- |
| 400         | `invalid_request_error`  | Request body không hợp lệ    |
| 401         | `authentication_error`   | Thiếu hoặc sai API key       |
| 403         | `quota_exceeded_error`   | Đã đạt giới hạn quota user   |
| 404         | `not_found_error`        | Tài nguyên không tồn tại     |
| 429         | `rate_limit_error`       | Quá nhiều request            |
| 500         | `internal_error`         | Lỗi phía server              |
| 502         | `gateway_error`          | LiteLLM proxy không khả dụng |

---

## Giới hạn Tốc độ

**Triển khai hiện tại:** Không có giới hạn tốc độ toàn cục (kiểm soát bởi LiteLLM proxy).

**Giới hạn Per-User:** Thực thi qua quota subkey:
- Mỗi subkey có `quota` (số request đồng thời tối đa)
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
    "model": "gpt-4-turbo",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": false
  }'
```

**Tạo Subkey:**
```bash
curl -X POST http://localhost:5000/v1/_mw/subkey \
  -H "Authorization: Bearer YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"quota": 100, "note": "Test user"}'
```

**Đăng nhập Dashboard:**
```bash
curl -X POST http://localhost:5000/dashboard/login \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"username": "admin", "password": "YOUR_ADMIN_KEY"}'
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

**Cập nhật lần cuối:** 7 tháng 3, 2026  
**Phiên bản API:** 2.0 (DB-backed, tương thích OpenAI)
