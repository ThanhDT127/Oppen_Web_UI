## 1. Core Functions (core/auth.py + core/db.py)

- [x] 1.1 Thêm `_get_user_by_id_db(user_id)` trong `core/db.py` — `SELECT ... WHERE user_id = %s` trả Dict hoặc None
- [x] 1.2 Thêm `get_user_by_id(user_id)` trong `core/auth.py` — DB-first, file fallback (giống pattern `load_users()`)
- [x] 1.3 Thêm `_update_user_quota_db(user_id, add_tokens, add_cost_usd, add_image_requests, add_stt_requests)` trong `core/db.py` — atomic `UPDATE ... SET field = field + %s WHERE user_id = %s`
- [x] 1.4 Thêm `update_user_quota(user_id, ...)` trong `core/auth.py` — DB update + JSON file backup cho 1 user
- [x] 1.5 Thêm `update_user_alerts(user_id, alerts_sent)` trong `core/auth.py` — update alerts_sent cho 1 user
- [x] 1.6 Thêm helper `_update_user_in_file(user_id, updates)` — đọc JSON file → sửa 1 entry → ghi lại


## 2. Refactor Hot Path — quota.py

- [x] 2.1 Refactor `enforce_and_bump_quota()` — thay `load_users()` + loop bằng `get_user_by_id()`
- [x] 2.2 Refactor `enforce_and_bump_quota()` — thay `save_users(users)` bằng `update_user_quota()`
- [x] 2.3 Verify: `maybe_reset_quota()` vẫn hoạt động đúng với single-user dict

## 3. Refactor Hot Path — api/chat.py

- [x] 3.1 Refactor `_finalize_streaming()` (line ~656-667) — thay load-all → modify → save-all bằng `update_user_quota()`
- [x] 3.2 Verify: Quota warning text vẫn inject đúng sau streaming

## 4. Refactor Hot Path — api/embeddings.py

- [x] 4.1 Refactor phần quota bump (line ~129-135) — thay load-all → modify → save-all bằng `update_user_quota()`

## 5. Refactor Hot Path — core/alerting.py

- [x] 5.1 Refactor `check_and_send_alerts()` (line ~160) — thay `load_users()` + loop bằng `get_user_by_id()`
- [x] 5.2 Refactor `check_and_send_alerts()` (line ~257) — thay `save_users(users)` bằng `update_user_alerts()`
- [x] 5.3 Refactor `get_user_quota_status()` (line ~526) — thay `load_users()` + loop bằng `get_user_by_id()`

## 6. Refactor Admin Path — api/user_admin.py

- [x] 6.1 Refactor các endpoint tìm 1 user (7 chỗ load_users) — dùng `get_user_by_id()` cho single-user lookup
- [x] 6.2 Giữ `load_users()` cho endpoint list all users

## 7. Refactor Admin Path — còn lại

- [x] 7.1 Refactor `api/admin.py` — dùng `get_user_by_id()` ở chỗ tìm 1 user (2 chỗ), giữ `load_users()` cho list
- [x] 7.2 Refactor `api/health.py` (line ~53) — dùng `load_users()` count hoặc dedicated count query
- [x] 7.3 Refactor `core/notification.py` (line ~201) — dùng `get_user_by_id()` thay load-all

## 8. Tests & Verification

- [x] 8.1 Update `test_alerting.py` — sửa tests dùng `load_users()` cho phù hợp với API mới
- [x] 8.2 Viết unit test cho `get_user_by_id()` (3 scenarios: exists, not exists, fallback)
- [x] 8.3 Viết unit test cho `update_user_quota()` (3 scenarios: increment, multi-field, not found)
- [x] 8.4 Test end-to-end: gửi chat request → verify quota bumped đúng, audit log ghi đúng
- [x] 8.5 Benchmark: so sánh latency trước/sau refactor với simulated 200 users
