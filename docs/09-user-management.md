# Hướng dẫn Quản lý Người dùng

## Tổng quan

LLM Middleware bao gồm hệ thống quản lý người dùng toàn diện với RBAC (Role-Based Access Control), quản lý vòng đời khóa API, và audit trail cho các thao tác quản trị.

## Schema Người dùng

Mỗi user trong bảng `mw_users` (PostgreSQL) có cấu trúc sau:

```json
{
  "user_id": "admin",
  "role": "admin",  // admin | manager | user
  "subkey_hash": "...",  // Chỉ lưu hash, plaintext không bao giờ lưu lâu dài
  "active": true,
  "allowed_models": ["*"],
  "quota": {
    "period": "monthly",
    "timezone": "Asia/Ho_Chi_Minh",
    "limit_tokens": 0,
    "limit_cost_usd": 0,
    "limit_image_requests": 0,
    "used_tokens": 0,
    "used_cost_usd": 0.0,
    "used_image_requests": 0
  }
}
```

### Vai trò (Roles)

- **admin**: Toàn quyền truy cập các endpoint quản trị (quản lý user)
- **manager**: (Dự kiến) Quyền admin chỉ đọc
- **user**: Người dùng API tiêu chuẩn với giới hạn quota

## Migration

Để thêm RBAC cho users.json hiện có:

```bash
python scripts/migrate_users_rbac.py
```

Script này sẽ:
1. Sao lưu users.json hiện tại
2. Thêm trường 'role' (user đầu tiên nhận 'admin', còn lại nhận 'user')
3. Xác thực và lưu

## Các Endpoint Quản trị

Tất cả endpoint yêu cầu xác thực admin (cookie session hoặc header X-Admin-Key).

### Danh sách Người dùng

```bash
GET /v1/_mw/admin/users
```

**Phản hồi:**
```json
{
  "users": [
    {
      "user_id": "admin",
      "role": "admin",
      "active": true,
      "allowed_models": ["*"],
      "quota": {...}
    }
  ],
  "total": 2
}
```

**Lưu ý:** Các khóa và hash được ẩn khỏi phản hồi.

---

### Tạo Người dùng

```bash
POST /v1/_mw/admin/users
Content-Type: application/json

{
  "user_id": "new_user",
  "role": "user",
  "allowed_models": ["chat-gemini-2.5-flash", "chat-gpt-5"],
  "limit_tokens": 100000,
  "limit_cost_usd": 5.0,
  "limit_image_requests": 50,
  "period": "monthly",
  "timezone": "Asia/Ho_Chi_Minh"
}
```

**Phản hồi:**
```json
{
  "message": "User created successfully",
  "user": {...},
  "subkey": "sk_abc123...",  // Chỉ hiển thị 1 LẦN DUY NHẤT!
  "warning": "Save this subkey securely. It will not be shown again."
}
```

**QUAN TRỌNG:** Sao chép subkey ngay lập tức. Không thể khôi phục sau này.

---

### Cập nhật Người dùng

```bash
PATCH /v1/_mw/admin/users/{user_id}
Content-Type: application/json

{
  "role": "manager",
  "active": true,
  "allowed_models": ["*"],
  "limit_cost_usd": 10.0
}
```

**Phản hồi:**
```json
{
  "message": "User updated successfully",
  "user": {...},
  "changes": {
    "role": "manager",
    "limit_cost_usd": 10.0
  }
}
```

**Các trường:** Tất cả đều tùy chọn. Chỉ các trường được cung cấp mới được cập nhật.

---

### Xoay vòng Khóa (Rotate Key)

```bash
POST /v1/_mw/admin/users/{user_id}/rotate_key
```

**Phản hồi:**
```json
{
  "message": "Key rotated successfully",
  "user_id": "user1",
  "subkey": "sk_new_key_xyz...",  // Chỉ hiển thị 1 LẦN DUY NHẤT!
  "warning": "Save this subkey securely. The old key is now invalid."
}
```

**QUAN TRỌNG:** Khóa cũ bị vô hiệu hóa ngay lập tức.

---

### Xóa Người dùng

```bash
DELETE /v1/_mw/admin/users/{user_id}
```

**Phản hồi:**
```json
{
  "message": "User alice deleted",
  "user_id": "alice"
}
```

**QUAN TRỌNG:**
- Xóa là vĩnh viễn - xóa khỏi cả DB và bản sao lưu JSON
- Không cho phép tự xóa (admin không thể xóa chính mình)
- Yêu cầu xác nhận 2 lần trên giao diện Dashboard

---

### Tắt Tài khoản (Disable)

```bash
POST /v1/_mw/admin/users/{user_id}/disable
```

**Phản hồi:**
```json
{
  "message": "User user1 disabled successfully",
  "user": {...}
}
```

Người dùng bị tắt không thể xác thực (trả về 403 Forbidden).

---

### Bật lại Tài khoản (Enable)

```bash
POST /v1/_mw/admin/users/{user_id}/enable
```

**Phản hồi:**
```json
{
  "message": "User user1 enabled successfully",
  "user": {...}
}
```

---

## Giao diện Quản lý trên Dashboard

Quản lý người dùng đầy đủ có sẵn tại Dashboard Admin `https://openwebui.example.com:51122/dashboard` > tab **Users**.

### Các Thao tác

| STT | Thao tác      | Nút        | Mô tả                                   |
| --- | ------------- | ---------- | --------------------------------------- |
| 01  | **Thêm user** | Add User   | Tạo user mới với subkey tự sinh         |
| 02  | **Sửa user**  | Edit       | Sửa quota, models, role, period, active |
| 03  | **Xóa user**  | Delete     | Xóa user (xác nhận 2 lần)               |
| 04  | **Xoay khóa** | Rotate Key | Vô hiệu khóa cũ, tạo khóa mới           |
| 05  | **Bật/Tắt**   | Toggle     | Bật/tắt tài khoản (403 khi bị tắt)      |

### Hiển thị Subkey

- Sau khi **Tạo** hoặc **Xoay khóa**, popup hiển thị subkey dạng plaintext
- Admin phải sao chép ngay lập tức - sẽ **KHÔNG** hiển thị lại
- Bảng Dashboard chỉ hiển thị hash đã ẩn (`abc...xyz`)
- Subkeys được hash bằng HMAC-SHA256 sử dụng `MW_SECRET`

---

### Nhật ký Kiểm toán Quản trị (Admin Audit Trail)

```bash
GET /v1/_mw/admin/audit?minutes=1440
```

**Phản hồi:**
```json
{
  "audit_trail": [
    {
      "ts": "2026-01-07T16:19:45.123456+00:00",
      "actor": "admin_session",
      "action": "create_user",
      "target_user": "new_user",
      "changes": {"role": "user", "allowed_models": ["*"]},
      "status": "ok",
      "ip": "127.0.0.1",
      "user_agent": "curl/7.68.0"
    }
  ],
  "total": 10
}
```

**Tham số truy vấn:**
- `minutes`: Khoảng thời gian (mặc định: 1440 = 24 giờ)
- `start` / `end`: Chuỗi ISO datetime cho khoảng tùy chỉnh

## File Nhật ký Kiểm toán

Các thao tác quản trị được ghi vào `logs/admin_audit.jsonl` (rotating, tối đa 20MB, 5 bản sao lưu).

Mỗi bản ghi bao gồm:
- `ts`: Thời gian (ISO UTC)
- `actor`: Định danh phiên admin
- `action`: Thao tác thực hiện (create_user, update_user, rotate_key, disable_user, enable_user)
- `target_user`: User ID bị ảnh hưởng
- `changes`: Tóm tắt các thay đổi
- `status`: ok | error
- `ip`: Địa chỉ IP client
- `user_agent`: User agent client

## Thực hành Bảo mật Tốt nhất

1. **Lưu trữ Khóa:**
   - Không bao giờ ghi log hoặc hiển thị subkey ngoại trừ khi tạo/xoay
   - Chỉ lưu hash (HMAC-SHA256) trong database
   - Sử dụng biến môi trường `MW_SECRET` làm salt hash

2. **Xoay vòng Khóa:**
   - Xoay khóa định kỳ (ví dụ: mỗi 90 ngày)
   - Xoay ngay lập tức nếu khóa bị lộ
   - Khóa cũ bị vô hiệu hóa tức thì

3. **RBAC:**
   - Cấp vai trò 'admin' hạn chế
   - Dùng vai trò 'user' cho người dùng API
   - Tương lai: vai trò 'manager' cho quyền admin chỉ đọc

4. **Nhật ký Kiểm toán:**
   - Rà soát admin_audit.jsonl định kỳ
   - Giám sát các thao tác admin trái phép
   - Đối chiếu với địa chỉ IP để điều tra

## Ví dụ

### Tạo User qua curl

```bash
curl -X POST http://localhost:5000/v1/_mw/admin/users \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "role": "user",
    "allowed_models": ["chat-gemini-2.5-flash"],
    "limit_cost_usd": 5.0,
    "period": "monthly"
  }'
```

### Xoay Khóa qua curl

```bash
curl -X POST http://localhost:5000/v1/_mw/admin/users/alice/rotate_key \
  -H "X-Admin-Key: $ADMIN_KEY"
```

### Tắt User qua curl

```bash
curl -X POST http://localhost:5000/v1/_mw/admin/users/alice/disable \
  -H "X-Admin-Key: $ADMIN_KEY"
```

## Xử lý Sự cố

### Lỗi: "Invalid admin key or session"

**Giải pháp:**
- Với curl: Dùng `-H "X-Admin-Key: $ADMIN_KEY"`
- Với dashboard: Đăng nhập bằng admin key để lấy session cookie

### Lỗi: "User already exists"

**Giải pháp:** User ID phải là duy nhất. Chọn user_id khác hoặc cập nhật user hiện có.

### Mất khóa, không xác thực được

**Giải pháp:** Admin phải xoay khóa và cung cấp khóa mới. Khóa cũ không thể khôi phục.

### Không tìm thấy nhật ký kiểm toán

**Giải pháp:** Nhật ký kiểm toán admin được tạo khi có thao tác admin đầu tiên. Đường dẫn file: `logs/admin_audit.jsonl`
