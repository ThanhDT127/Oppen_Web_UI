# 13. Hệ thống Cảnh báo & Quản lý Quota

## Mục lục

1. [Tổng quan](#tổng-quan)
2. [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
3. [Hai loại cảnh báo](#hai-loại-cảnh-báo)
4. [User Quota — Cảnh báo theo tài khoản](#user-quota--cảnh-báo-theo-tài-khoản)
5. [API Budget — Cảnh báo theo nhà cung cấp](#api-budget--cảnh-báo-theo-nhà-cung-cấp)
6. [4 Kênh thông báo](#4-kênh-thông-báo)
7. [Cơ chế tính chi phí](#cơ-chế-tính-chi-phí)
8. [Cấu hình (Config)](#cấu-hình-config)
9. [Lưu trữ dữ liệu (DB + JSON)](#lưu-trữ-dữ-liệu-db--json)
10. [SMTP & Email](#smtp--email)
11. [Dashboard Notification](#dashboard-notification)
12. [Files liên quan](#files-liên-quan)
13. [Hướng dẫn vận hành](#hướng-dẫn-vận-hành)

---

## 1. Tổng quan

Hệ thống cảnh báo quota có 2 mục tiêu chính:

| Mục tiêu | Đối tượng | Ý nghĩa |
|----------|:---------:|---------|
| Cảnh báo quota user | **User** | Mỗi user dùng subkey riêng, có hạn mức riêng |
| Cảnh báo budget API | **Admin** | Tất cả user dùng chung API key, admin cần biết chi phí |

Hệ thống tách biệt hoàn toàn 2 loại cảnh báo này vì bản chất khác nhau:
- **User quota**: Hết → chỉ user đó bị chặn (403), các user khác vẫn hoạt động bình thường
- **API budget**: Hết → ảnh hưởng TẤT CẢ user, nên chỉ cảnh báo admin để quyết định

---

## 2. Kiến trúc hệ thống

```
User A ──[subkey_A]──┐                    ┌── OPENAI_API_KEY ($100/tháng)
User B ──[subkey_B]──┤── Middleware ──┬───┤   (tất cả user dùng chung)
User C ──[subkey_C]──┘     │         │   └── GEMINI_API_KEY ($50/tháng)
                           │         │       (tất cả user dùng chung)
                           │    LiteLLM Proxy
                           │
                    check_and_send_alerts()
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
   User Quota Alert   Provider Budget   Chat Inline
   (per-account)      (per-key)         Warning
          │                │                │
          ▼                ▼                ▼
   📧 User email     📧 Admin email    💬 Chat message
   🔔 Admin dash     🔔 Admin dash     (filter Open WebUI)
          │                │
          └───────┬────────┘
                  ▼
           ⏰ 8:00 AM Daily Digest
           (email admin tổng hợp)
```

---

## 3. Hai loại cảnh báo

### So sánh chi tiết

```
┌──────────────────────────────────┐  ┌──────────────────────────────────┐
│    USER QUOTA (Per-Account)      │  │   API BUDGET (Per-Provider)      │
├──────────────────────────────────┤  ├──────────────────────────────────┤
│                                  │  │                                  │
│  User A ──[subkey_A]──→ $10     │  │  OPENAI_API_KEY ──→ $100/tháng  │
│  User B ──[subkey_B]──→ $20     │  │  (tất cả user dùng chung)       │
│  User C ──[subkey_C]──→ $5      │  │                                  │
│                                  │  │  GEMINI_API_KEY ──→ $50/tháng   │
│  Mỗi user CÓ subkey RIÊNG      │  │  (tất cả user dùng chung)       │
│  Mỗi user CÓ hạn mức RIÊNG     │  │                                  │
│  Quota reset theo period         │  │  Budget = tiền THẬT admin nạp    │
│  (monthly/daily)                 │  │  Hết = tất cả user DỪNG         │
│                                  │  │                                  │
│  CẢNH BÁO → cho USER đó         │  │  CẢNH BÁO → cho ADMIN           │
│  (email của user)                │  │  (email admin)                   │
└──────────────────────────────────┘  └──────────────────────────────────┘
```

| Tiêu chí | User Quota | API Budget |
|----------|:----------:|:----------:|
| **Đối tượng** | 1 user cụ thể | Tất cả users chung |
| **Key sử dụng** | Subkey riêng | API key chung (OPENAI/GEMINI) |
| **Hạn mức** | Admin set per user ($10, $20...) | Admin set per provider ($100, $50) |
| **Nguồn data** | `mw_users.quota.used_cost_usd` | `SUM(mw_audit_log.cost_usd)` by model |
| **Reset** | Monthly/daily (tự động) | Monthly (tự động) |
| **Khi hết** | User đó bị chặn (403) | **KHÔNG tự chặn**, chỉ cảnh báo |
| **Cảnh báo cho** | **USER** (email) + admin (dashboard) | **ADMIN** (email + dashboard) |

---

## 4. User Quota — Cảnh báo theo tài khoản

### Luồng xử lý

```
User A gửi chat (dùng subkey_A)
         │
         ▼
   Middleware xác thực subkey_A → user_id = "user_a"
         │
         ▼
   LiteLLM proxy → OpenAI API (dùng OPENAI_API_KEY chung)
         │
         ◄── Response (cost = $0.05)
         │
         ▼
   mw_users: user_a.quota.used_cost_usd += $0.05
             user_a.quota.limit_cost_usd = $10.00
         │
         ▼
   Check: used / limit = ?% → so sánh với thresholds [80, 95, 100]
         │
         ├── 80% → 📧 Email USER: "Nhắc nhở quota đạt 80%"
         │         🔔 Dashboard notification (info)
         │
         ├── 95% → 📧 Email USER: "Cảnh báo quota đạt 95%"
         │         🔔 Dashboard notification (warning)
         │
         └── 100% → 📧 Email USER: "Quota hết, tài khoản bị chặn"
                    📧 Email ADMIN: "User A đã bị chặn"
                    🔔 Dashboard notification (critical)
                    ❌ Request tiếp theo → 403 Forbidden
```

### Ngưỡng cảnh báo

| Ngưỡng | Level | Email User | Email Admin | Dashboard | Hành động |
|:------:|:-----:|:----------:|:-----------:|:---------:|-----------|
| 80% | info | ✅ | ❌ | ✅ | Nhắc nhở user |
| 95% | warning | ✅ | ❌ | ✅ | Cảnh báo khẩn |
| 100% | critical | ✅ | ✅ | ✅ | **CHẶN user** |

### Email user nhận được

```
Subject: ⚠️ Cảnh báo quota — user_a đạt 95%

Xin chào user_a,

Tài khoản của bạn đã sử dụng 95% hạn mức chi phí.

  • Đã dùng: $9.5000
  • Hạn mức:  $10.00
  • Còn lại:  $0.5000

Vui lòng sử dụng tiết kiệm để tránh bị chặn.
```

### Email user lấy từ đâu?

1. Nếu `user_id` chứa `@` → dùng luôn làm email
2. Query từ Open WebUI database (bảng `user`) theo `name` hoặc `email`

---

## 5. API Budget — Cảnh báo theo nhà cung cấp

### Luồng xử lý

```
Tất cả user gửi request
         │
         ▼
   Tất cả đi qua OPENAI_API_KEY hoặc GEMINI_API_KEY (chung)
         │
         ▼
   mw_audit_log ghi: model="chat-gpt-4o", cost=$0.05
   mw_audit_log ghi: model="chat-gemini-2.5-pro", cost=$0.03
         │
         ▼
   Mỗi request → _check_provider_budget_alerts():
         │
         ▼
   SQL: SUM(cost_usd) FROM mw_audit_log
        WHERE ts >= đầu tháng
        GROUP BY provider (dựa trên model prefix)
         │
         ├── openai (chat-gpt*, img-gpt*, tts-gpt*, stt-gpt*) → $75/$100
         └── gemini (chat-gemini*, img-gemini*)                → $20/$50
         │
         ▼
   So sánh với thresholds [70, 90, 100]
         │
         ├── 70% → 🔔 Dashboard only
         ├── 90% → 🔔 Dashboard only
         └── 100% → 📧 Email ADMIN + 🔔 Dashboard
```

### Model prefix mapping

```json
{
    "openai": {
        "budget_usd": 100.00,
        "model_prefixes": ["chat-gpt", "img-gpt"]
    },
    "gemini": {
        "budget_usd": 50.00,
        "model_prefixes": ["chat-gemini", "img-gemini"]
    },
    "xai": {
        "budget_usd": 80.00,
        "model_prefixes": ["chat-grok", "img-grok"]
    },
    "anthropic": {
        "budget_usd": 100.00,
        "model_prefixes": ["chat-claude"]
    }
}
```

### Ngưỡng cảnh báo (per-provider)

| Provider | Ngưỡng | Email Admin | Dashboard | Hành động |
|----------|:------:|:-----------:|:---------:|-----------|
| OpenAI | 70% | ❌ | ✅ | Thông tin |
| OpenAI | 90% | ❌ | ✅ | Cảnh báo |
| OpenAI | 100% | ✅ | ✅ | **Cảnh báo khẩn** |
| Gemini | 80% | ❌ | ✅ | Thông tin |
| Gemini | 100% | ✅ | ✅ | **Cảnh báo khẩn** |

> **Lưu ý:** API Budget KHÔNG tự chặn vì chặn = tất cả user dừng. Admin phải quyết định: nạp thêm tiền hoặc tăng budget trong config.

---

## 6. 4 Kênh thông báo

### Kênh 1: Email User (per-user quota)

- **Trigger:** `user.quota.used_cost_usd / limit >= threshold`
- **Gửi qua:** SMTP (1 tài khoản sender → nhiều recipients)
- **Content:** Tên user, % đã dùng, số tiền còn lại

### Kênh 2: Email Admin (per-provider budget + critical)

- **Trigger:** `SUM(audit_log cost) / provider_budget >= threshold`
- **Chỉ gửi khi:** threshold = 100% (đạt ngưỡng tối đa)
- **Content:** Provider nào, chi phí bao nhiêu, còn lại bao nhiêu

### Kênh 3: Dashboard 🔔 Bell Icon

- **Trigger:** Mọi alert đều lưu vào `mw_notifications`
- **Hiển thị:** Bell icon trên status bar, click để xem dropdown
- **Polling:** JS poll `/notifications/unread` mỗi 30 giây
- **Chức năng:** Xem danh sách, đánh dấu đã đọc, đánh dấu tất cả

### Kênh 4: Daily Digest 📊

- **Trigger:** APScheduler cron 8:00 AM Vietnam (Asia/Ho_Chi_Minh)
- **Gửi cho:** Admin email
- **Nội dung:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 LLM Gateway — Daily Digest
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Thời gian: 2026-03-12 08:00
Tổng cảnh báo 24h: 5 (1 critical, 2 warning, 2 info)

🚨 CRITICAL ALERTS:
  • [23:30] quota_blocked: User_A đạt 100% quota

⚠️ WARNINGS:
  • [14:20] quota_warning: User_B đạt 95% quota

📊 QUOTA SUMMARY (toàn bộ users):
  • user_a: $10.00/$10.00 (100%)
  • user_b: $9.50/$20.00 (47%)
  • user_c: $1.20/$5.00 (24%)

💳 CHI PHÍ THEO PROVIDER (tháng này):
  • OPENAI: $18.50/$100.00 (18%)
  • GEMINI: $2.20/$50.00 (4%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Dashboard: /dashboard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 7. Cơ chế tính chi phí

### Luồng tính cost

```
Request → LiteLLM → API Provider
                ↓
    ┌───────────┴───────────┐
    ▼                       ▼
Non-streaming           Streaming
    │                       │
    ▼                       ▼
Response header:         LiteLLM log file:
x-litellm-response-     response_cost = X.XX
cost = X.XX
    │                       │
    └───────────┬───────────┘
                ▼
         litellm_cost > 0?
         ┌──YES──┤──NO──┐
         ▼              ▼
    Dùng LiteLLM    Tự tính:
    cost (ưu tiên)  tokens × mw_prices (DB)
```

**Ưu tiên:** LiteLLM cost (chính xác, cập nhật tự động) → nếu = 0 → tự tính bằng `mw_prices` (backup).

### 2 Nguồn dữ liệu cho cảnh báo

| Nguồn | Table | Dùng cho |
|-------|-------|---------|
| Cost per user (period) | `mw_users.quota.used_cost_usd` | **User quota alert** |
| Cost per request (có model) | `mw_audit_log.cost_usd` | **Per-provider budget** |

---

## 8. Cấu hình (Config)

File: `data/alert_config.json` (seed) → lưu trong `mw_config` table (DB primary)

```json
{
    "smtp": {
        "enabled": true,
        "host": "smtp.gmail.com",
        "port": 587,
        "username": "anthanh8573@gmail.com",
        "password_env": "SMTP_PASSWORD",
        "from_email": "anthanh8573@gmail.com",
        "use_tls": true
    },
    "admin_alerts": {
        "emails": ["anthanh8573@gmail.com"],
        "api_budgets": {
            "openai": {
                "enabled": true,
                "budget_usd": 100.00,
                "thresholds": [70, 90, 100],
                "model_prefixes": ["chat-gpt", "img-gpt", "tts-gpt", "stt-gpt"]
            },
            "gemini": {
                "enabled": true,
                "budget_usd": 50.00,
                "thresholds": [80, 100],
                "model_prefixes": ["chat-gemini", "img-gemini"]
            }
        },
        "per_user_quota": {
            "enabled": true,
            "thresholds": [80, 95, 100]
        }
    },
    "user_alerts": {
        "enabled": true,
        "send_email": true,
        "thresholds": [80, 95, 100],
        "email_source": "openwebui_db"
    }
}
```

### Thay đổi SMTP sang Outlook

Chỉ cần đổi:
```json
"smtp": {
    "host": "smtp.office365.com",
    "port": 587,
    "username": "your@outlook.com",
    "from_email": "your@outlook.com"
}
```

### Thêm provider mới (Claude, Grok)

```json
"api_budgets": {
    "claude": {
        "enabled": true,
        "budget_usd": 80.00,
        "thresholds": [70, 90, 100],
        "model_prefixes": ["chat-claude"]
    }
}
```

---

## 9. Lưu trữ dữ liệu (DB + JSON)

### Tất cả JSON đều đã có trong DB

| File JSON | Table DB | Code dùng gì? |
|-----------|----------|--------------|
| `users.json` | `mw_users` | DB first, JSON = backup |
| `prices.json` | `mw_prices` | DB first, JSON = backup |
| `alert_config.json` | `mw_config` (key='alert_config') | DB first, JSON = seed + backup |
| `system_alerts.json` | `mw_config` (key='system_alerts') | DB first, JSON = backup |

### Cơ chế đồng bộ

```
Startup (1 lần):     JSON ──── import ────→ DB
                                            ▲
Runtime READ:                   DB ← code   │
                                            │
Runtime SAVE:        code → DB + JSON ──────┘
                     (ghi song song cả 2)

Khi DB lỗi:         JSON → code (fallback)
```

### Database tables

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  mw_users   │     │  mw_audit_log   │     │ mw_notifications │
├─────────────┤     ├─────────────────┤     ├──────────────────┤
│ user_id     │     │ ts              │     │ id (PK, serial)  │
│ used_cost   │     │ user_id         │     │ ts (timestamptz) │
│ quota {     │     │ model           │     │ user_id          │
│   limit     │     │ cost_usd        │     │ type (varchar)   │
│   used      │     │ tokens_in/out   │     │ level (varchar)  │
│   period    │     │ duration_ms     │     │ title            │
│ }           │     │ status          │     │ message          │
│ alerts_sent │     │                 │     │ read (bool)      │
└──────┬──────┘     └───────┬─────────┘     │ emailed (bool)   │
       │                    │               │ metadata (jsonb) │
       │  Per-user quota    │  Per-provider └──────────────────┘
       │  alert check       │  budget check         ▲
       └────────┬───────────┘                       │
                │                                   │
                └── check_and_send_alerts() ────────┘
```

---

## 10. SMTP & Email

### Chỉ cần 1 tài khoản SMTP

```
                    1 tài khoản SMTP
                    (anthanh8573@gmail.com)
                           │
               ┌───────────┼───────────┐
               ▼           ▼           ▼
          user_a@...   user_b@...   admin@...
```

- **Người gửi (FROM):** `anthanh8573@gmail.com` — cố định
- **Người nhận (TO):** bất kỳ email nào (Gmail, Outlook, email công ty)
- **Mật khẩu:** chỉ cần App Password của tài khoản GỬI

### Yêu cầu

| Yêu cầu | Chi tiết |
|---------|---------|
| Gmail App Password | Tạo tại myaccount.google.com → Security → App passwords |
| Biến môi trường | `SMTP_PASSWORD` trong `.env` |
| User email | Tự động lấy từ Open WebUI DB (user đăng ký bằng email) |

---

## 11. Dashboard Notification

### Giao diện

- **Bell icon 🔔** trên status bar (góc phải)
- **Badge đỏ** hiện số unread
- **Dropdown panel** khi click: danh sách notification
- **Mark as read** khi click vào từng item
- **Mark all** nút "✓ Tất cả"

### API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/v1/_mw/admin/notifications` | Danh sách (limit, offset) |
| GET | `/v1/_mw/admin/notifications/unread` | Số unread |
| POST | `/v1/_mw/admin/notifications/{id}/read` | Đánh dấu đã đọc |
| POST | `/v1/_mw/admin/notifications/read-all` | Đánh dấu tất cả |

### Màu sắc theo level

| Level | Màu viền trái | Nền |
|-------|:-------------:|-----|
| info | `#667eea` (xanh) | Nhạt |
| warning | `#f59e0b` (vàng) | Vàng nhạt |
| critical | `#ef4444` (đỏ) | Đỏ nhạt |

---

## 12. Files liên quan

### Backend

| File | Chức năng |
|------|----------|
| `core/alerting.py` | Logic kiểm tra ngưỡng, routing alert |
| `core/notification.py` | Fan-out service (DB + email + digest) |
| `core/quota.py` | Enforce & bump quota per user |
| `core/cost.py` | Tính chi phí (LiteLLM → prices backup) |
| `api/notifications.py` | REST API cho dashboard |
| `main.py` | APScheduler + routes |

### Frontend

| File | Chức năng |
|------|----------|
| `dashboard/index.html` | Bell icon + dropdown panel |
| `dashboard/js/notifications.js` | Poll, render, mark read |
| `dashboard/css/dashboard.css` | Notification styles |

### Config & Data

| File | Chức năng |
|------|----------|
| `data/alert_config.json` | Cấu hình SMTP + thresholds (seed) |
| `data/system_alerts.json` | Tracking đã gửi threshold nào (backup) |

---

## 13. Hướng dẫn vận hành

### Deploy lần đầu

```bash
# 1. Đảm bảo SMTP_PASSWORD trong .env
echo "SMTP_PASSWORD=your_app_password" >> .env

# 2. Build & restart
docker compose build middleware
docker compose up -d

# 3. Verify
docker logs openwebui-middleware | grep "mw_notifications"
docker logs openwebui-middleware | grep "daily_digest"
```

### Thay đổi budget

Qua Dashboard API:
```bash
curl -X PUT http://192.168.20.66:5000/v1/_mw/admin/alerts/config \
  -H "Authorization: Bearer ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{ "admin_alerts": { "api_budgets": { "openai": { "budget_usd": 200 } } } }'
```

### Test cảnh báo

```bash
# Test email gửi được
curl -X POST http://192.168.20.66:5000/v1/_mw/admin/alerts/test-email \
  -H "Authorization: Bearer ADMIN_KEY"

# Xem notifications
curl http://192.168.20.66:5000/v1/_mw/admin/notifications \
  -H "Authorization: Bearer ADMIN_KEY"

# Xem unread count
curl http://192.168.20.66:5000/v1/_mw/admin/notifications/unread \
  -H "Authorization: Bearer ADMIN_KEY"
```

### Xem chi phí per-provider (SQL)

```sql
SELECT
    CASE
        WHEN model LIKE 'chat-gpt%' OR model LIKE 'img-gpt%'
            THEN 'openai'
        WHEN model LIKE 'chat-gemini%' OR model LIKE 'img-gemini%'
            THEN 'gemini'
        WHEN model LIKE 'chat-grok%' OR model LIKE 'img-grok%'
            THEN 'xai'
        WHEN model LIKE 'chat-claude%'
            THEN 'anthropic'
        ELSE 'other'
    END AS provider,
    COUNT(*) AS requests,
    SUM(cost_usd) AS total_cost
FROM mw_audit_log
WHERE ts >= date_trunc('month', now())
GROUP BY provider;
```

### Thêm provider mới

1. Thêm model vào `litellm_config.yaml`
2. Thêm pricing vào `prices.json`
3. Thêm provider budget vào `alert_config.json`:
   ```json
   "claude": {
       "enabled": true,
       "budget_usd": 80.00,
       "thresholds": [70, 90, 100],
       "model_prefixes": ["chat-claude"]
   }
   ```
4. Restart: `docker compose restart middleware`

### Reset alert tracking (đầu tháng tự động)

- **User quota:** Tự động reset khi `period_start` < anchor tháng mới
- **Provider budget:** Tự động vì tính từ `mw_audit_log WHERE ts >= đầu tháng`
- **System alerts:** Xóa thủ công nếu cần:
  ```bash
  curl -X PUT http://IP:5000/v1/_mw/admin/alerts/config \
    -H "Authorization: Bearer ADMIN_KEY" \
    -d '{}' # Reset system_alerts
  ```
