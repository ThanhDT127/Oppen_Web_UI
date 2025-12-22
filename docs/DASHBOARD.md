# Dashboard Improvements - Metrics & Auth

## Overview

Cải tiến dashboard để hiển thị metrics rõ ràng hơn và enforce authentication đúng cách.

## ✅ Changes Implemented

### 1. **Enforce Auth cho Admin Endpoints** (BẮT BUỘC)

**Endpoints được bảo vệ:**
- `GET /v1/_mw/summary` - Aggregate usage statistics
- `GET /v1/_mw/stream` - SSE realtime audit stream

**Phương thức authentication cho phép:**
- ✅ **Cookie session** (`mw_admin_session`) - cho dashboard
- ✅ **X-Admin-Key header** - cho curl/ops
- ✅ **Authorization: Bearer** - backward compatibility

**Cách login dashboard:**
```bash
# 1. Call login endpoint (chỉ 1 lần)
POST /v1/_mw/dashboard/login
Body: {"admin_key": "YOUR_ADMIN_KEY"}

# 2. Cookie được set tự động (4 giờ expiry)
# 3. Tất cả requests sau dùng cookie, không cần key trong JS/URL
```

**Cách dùng curl/ops:**
```bash
# X-Admin-Key header (khuyến nghị)
curl http://localhost:5000/v1/_mw/summary?minutes=30 \
  -H "X-Admin-Key: YOUR_ADMIN_KEY"

# Hoặc Authorization Bearer (backward compat)
curl http://localhost:5000/v1/_mw/summary?minutes=30 \
  -H "Authorization: Bearer YOUR_ADMIN_KEY"
```

**Bảo mật:**
- ❌ KHÔNG cho phép `?key=` trong URL
- ✅ Cookie HttpOnly (prevent XSS)
- ✅ JWT_SECRET không dùng default (log warning nếu thiếu)
- ✅ Session expiry 4 giờ

---

### 2. **Sửa logic Summary - Tách loại request**

**Endpoint:** `GET /v1/_mw/summary?minutes=<N>`

**Response mới có thêm breakdown:**

```json
{
  "time_window_minutes": 30,
  
  // Overall counts
  "requests_total": 10,       // Tổng requests (ok + error + reconciled)
  "llm_calls_total": 8,       // Chỉ LLM endpoints (chat/image/audio/video)
  "admin_ops_total": 1,       // Admin operations (reconcile, etc)
  "pending_count": 2,         // Streaming chưa reconcile
  "error_count": 0,
  
  // LLM breakdown
  "chat_calls": 6,            // /v1/chat/completions
  "image_calls": 1,           // /v1/images/generations
  "audio_calls": 1,           // /v1/audio/transcriptions + speech
  "video_calls": 0,           // /v1/video/generations
  
  // Performance
  "error_rate_percent": 0.0,
  "p95_latency_ms": 1234.56,
  "tokens_total": 15000,      // Chỉ từ ok + reconciled
  "cost_total_usd": 0.0225,   // Chỉ từ ok + reconciled
  
  // Top lists
  "top_users": [...],
  "top_models": [...]
}
```

**Quy tắc tính toán:**

- **`llm_calls_total`**: Đếm endpoint thuộc:
  - `/v1/chat/completions`
  - `/v1/images/generations`
  - `/v1/audio/transcriptions`
  - `/v1/audio/speech`
  - `/v1/video/generations`
  - Chỉ status `ok`, `error`, `reconciled` (KHÔNG pending)

- **`admin_ops_total`**: Đếm:
  - `/admin/reconcile`
  - `/admin/usage`
  - `/admin/reset`

- **`pending_count`**: Đếm status `pending` (streaming chưa reconcile)

- **`tokens_total` & `cost_total_usd`**: 
  - ✅ Chỉ cộng từ status `ok` + `reconciled`
  - ❌ KHÔNG cộng từ `pending` (chưa biết tokens)
  - ❌ KHÔNG cộng từ `error` (cost = 0)

- **Breakdown chi tiết**:
  - `chat_calls` = đếm `/v1/chat/completions` (ok/error/reconciled only)
  - `image_calls` = đếm `/v1/images/generations`
  - `audio_calls` = đếm `/v1/audio/*`
  - `video_calls` = đếm `/v1/video/generations`

---

### 3. **Sửa Dashboard UI**

**URL dashboard:** http://localhost:5000/dashboard

**Metrics hiển thị (6 chỉ số chính):**

| Label | Nguồn | Ý nghĩa |
|-------|-------|---------|
| **LLM Calls** | `llm_calls_total` | Tổng calls đến LLM (chat/image/audio/video) |
| **Admin Ops** | `admin_ops_total` | Operations quản trị (reconcile, etc) |
| **Pending** | `pending_count` | Streaming chưa reconcile |
| **Error Rate** | `error_rate_percent` | % request lỗi |
| **P95 Latency** | `p95_latency_ms` | Latency phân vị 95 |
| **Tokens** | `tokens_total` | Tổng tokens (ok + reconciled) |
| **Cost** | `cost_total_usd` | Tổng cost USD |

**Breakdown LLM Calls:**
- Hiển thị: `Chat: X | Image: Y | Audio: Z`

**Polling:**
- Gọi `/v1/_mw/summary?minutes=15` mỗi 5 giây
- Hiển thị Top Users và Top Models

**SSE Stream:**
- Kết nối `/v1/_mw/stream` với cookie
- Hiển thị 50 events gần nhất

---

### 4. **Idempotent Reconcile** (ĐÃ CÓ TRƯỚC)

Đã implement từ trước:
- Reconcile cùng `rid` 2 lần → lần 2 trả "Already reconciled"
- Không double-charge quota
- Không ghi audit line thứ 2

---

## 📊 Ý nghĩa các chỉ số

### Phân biệt các loại request

**LLM Calls** (`llm_calls_total`):
- Là requests thực sự gọi đến LLM model
- Chat, Image, Audio, Video generation
- Đây là metrics chính để track usage

**Admin Ops** (`admin_ops_total`):
- Operations quản trị hệ thống
- Reconcile pending streams
- Get usage, reset quota
- KHÔNG phải LLM calls

**Pending** (`pending_count`):
- Streaming requests chưa được reconcile
- Chưa biết tokens/cost chính xác
- Cần reconcile để có data đầy đủ

**Total Requests** (`requests_total`):
- Tổng tất cả (LLM + Admin + ...)
- Có thể gây hiểu nhầm nên ẨN trong UI
- Chỉ hiện `llm_calls_total` để rõ ràng

---

## 🧪 Testing

### Run automated tests:

```bash
cd llm-mw
python -m pytest tests/test_dashboard_improvements.py -v
```

**Test coverage:**
- ✅ Auth enforcement (summary + stream require auth)
- ✅ Auth methods work (X-Admin-Key + cookie session)
- ✅ Summary breakdown fields exist
- ✅ LLM calls = sum of breakdown
- ✅ Dashboard HTML có labels mới

**Results:** 9/9 tests PASSED

### Manual testing:

#### 1. Test Auth Protection

```bash
# Should return 403
curl http://localhost:5000/v1/_mw/summary

# Should return 200
curl http://localhost:5000/v1/_mw/summary \
  -H "X-Admin-Key: YOUR_ADMIN_KEY"
```

#### 2. Test Summary Breakdown

```bash
curl http://localhost:5000/v1/_mw/summary?minutes=30 \
  -H "X-Admin-Key: YOUR_ADMIN_KEY" | jq
```

Verify response có:
- `llm_calls_total`
- `admin_ops_total`
- `pending_count`
- `chat_calls`, `image_calls`, `audio_calls`, `video_calls`

#### 3. Test Dashboard UI

1. Mở: http://localhost:5000/dashboard
2. Login với admin key: `YOUR_ADMIN_KEY`
3. Verify:
   - Có label "LLM Calls" (không phải "Total Requests")
   - Có label "Admin Ops"
   - Có label "Pending"
   - Breakdown hiển thị: Chat/Image/Audio
   - Metrics update mỗi 5s

---

## 🔧 Configuration

### Environment Variables

```bash
# Required
ADMIN_KEY=your-strong-admin-key-here        # Admin authentication
JWT_SECRET=your-strong-jwt-secret-here      # Session signing (32+ chars)

# Optional (có defaults)
AUDIT_LOG_FILE=../logs/audit.jsonl
```

⚠️ **Production notes:**
- Đặt `JWT_SECRET` mạnh (32+ ký tự random)
- Đổi `ADMIN_KEY` định kỳ
- Enable HTTPS và set `secure=True` cho cookies

---

## 📝 Summary of Changes

### Files Modified:

1. **`api/summary.py`** - Added breakdown logic
   - Added LLM_ENDPOINTS mapping
   - Added counters: `llm_calls_total`, `admin_ops_total`, breakdown
   - Modified aggregation logic to classify by endpoint
   - Added breakdown fields to response

2. **`dashboard/index.html`** - Updated UI labels
   - Changed "Total Requests" → "LLM Calls"
   - Added "Admin Ops" metric card
   - Added breakdown display (Chat/Image/Audio)
   - Updated metric IDs and display logic

### Files Created:

3. **`tests/test_dashboard_improvements.py`** - Comprehensive tests
   - TestAuth: 4 tests (auth enforcement + methods)
   - TestSummaryBreakdown: 3 tests (fields + math)
   - TestDashboardUI: 2 tests (HTML + labels)

### Files Already OK (No changes needed):

- ✅ `utils/auth_guard.py` - Auth already implemented
- ✅ `api/stream.py` - Auth already enforced
- ✅ `api/admin.py` - Idempotent reconcile already done
- ✅ `utils/jwt_auth.py` - JWT utilities already complete

---

## 🎯 Verification Checklist

- [x] Summary endpoint requires auth (403 without key)
- [x] Stream endpoint requires auth (403 without key)
- [x] X-Admin-Key header works
- [x] Cookie session works (dashboard login)
- [x] Summary returns breakdown fields
- [x] `llm_calls_total` = sum of breakdown
- [x] Pending không cộng vào llm_calls_total
- [x] Tokens/cost chỉ từ ok + reconciled
- [x] Dashboard shows "LLM Calls" label
- [x] Dashboard shows "Admin Ops" label
- [x] Dashboard shows breakdown (Chat/Image/Audio)
- [x] All tests pass (9/9)

---

## 🚀 Next Steps (Out of Scope)

Những gì KHÔNG làm trong bước này (theo yêu cầu):
- ❌ Prometheus/Grafana integration
- ❌ Create/rotate admin key API
- ❌ Multi-user với roles khác nhau
- ❌ Advanced alerting
- ❌ Database backend

Scope hiện tại: **Chỉ sửa metrics + auth + UI labels**

---

## 📚 API Reference

### GET /v1/_mw/summary

**Auth:** Required (X-Admin-Key or cookie)

**Query params:**
- `minutes` (optional, default=60): Time window

**Response:**
```json
{
  "time_window_minutes": 30,
  "cutoff_time": "2025-12-20T15:00:00+07:00",
  "requests_total": 10,
  "llm_calls_total": 8,
  "admin_ops_total": 1,
  "pending_count": 2,
  "error_count": 0,
  "error_rate_percent": 0.0,
  "chat_calls": 6,
  "image_calls": 1,
  "audio_calls": 1,
  "video_calls": 0,
  "p95_latency_ms": 1234.56,
  "tokens_total": 15000,
  "cost_total_usd": 0.0225,
  "top_users": [...],
  "top_models": [...]
}
```

### GET /v1/_mw/stream

**Auth:** Required (X-Admin-Key or cookie)

**Response:** SSE stream
```
event: audit
data: {"ts":"...","rid":"...","status":"ok",...}

event: audit
data: {"ts":"...","rid":"...","status":"pending",...}
```

### POST /v1/_mw/dashboard/login

**Auth:** None (public login endpoint)

**Body:**
```json
{"admin_key": "YOUR_ADMIN_KEY"}
```

**Response:**
```json
{"ok": true, "expires_in_hours": 4}
```

**Sets cookie:** `mw_admin_session` (HttpOnly, 4h expiry)

---

**Document Version:** 1.0  
**Last Updated:** 2025-12-20  
**Status:** ✅ Production Ready
