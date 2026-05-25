## Why

Middleware hiện tại sử dụng pattern `load_users()` → loop toàn bộ O(N) → `save_users()` ghi lại toàn bộ list mỗi khi cần truy vấn hay cập nhật 1 user. Mỗi chat request đi qua 4 lần gọi pattern này (`require_user`, `enforce_and_bump_quota`, `_finalize_streaming`, `check_and_send_alerts`), tạo ra **4 full-table scans + ~800 loop iterations + 3 full-table writes** cho mỗi tin nhắn khi có 200 users. Đây là P0 performance debt phải sửa trước khi scale lên 200 người dùng.

## What Changes

- Thêm hàm `get_user_by_id(user_id)` — indexed `SELECT ... WHERE user_id = %s` trả về 1 user, thay thế `load_users()` + loop ở hot path
- Thêm hàm `update_user_quota(user_id, ...)` — atomic `UPDATE ... SET ... WHERE user_id = %s` thay thế load-all → modify → save-all
- Refactor 4 hot-path files (`quota.py`, `chat.py`, `embeddings.py`, `alerting.py`) sử dụng hàm mới
- Refactor 4 admin-path files (`user_admin.py`, `admin.py`, `health.py`, `notification.py`) sử dụng hàm mới
- Giữ lại `load_users()` cho use cases cần danh sách đầy đủ (dashboard list all, bulk export)
- Cập nhật `test_alerting.py` cho API mới
- **BREAKING**: Các callers import `load_users` để tìm 1 user sẽ phải đổi sang `get_user_by_id`

## Capabilities

### New Capabilities
- `single-user-query`: Truy vấn và cập nhật 1 user với O(1) thay vì O(N), bao gồm `get_user_by_id()`, `update_user_quota()`, và refactor toàn bộ callers

### Modified Capabilities
_(Không có specs hiện tại bị ảnh hưởng)_

## Impact

- **Core files**: `core/auth.py` (thêm hàm mới), `core/db.py` (có thể thêm indexed query helpers)
- **Hot-path files** (mỗi request đều đi qua): `core/quota.py`, `api/chat.py`, `api/embeddings.py`, `core/alerting.py`
- **Admin-path files** (ít traffic): `api/user_admin.py`, `api/admin.py`, `api/health.py`, `core/notification.py`
- **Tests**: `test_alerting.py`
- **API contract**: Internal functions thay đổi, nhưng HTTP API không đổi (backward compatible)
- **Database**: Không đổi schema, chỉ đổi query patterns (SELECT * → SELECT WHERE, UPSERT all → UPDATE WHERE)
- **Expected impact**: Giảm ~200× DB/CPU overhead per request khi có 200 users
