## 1. Enhanced Authentication Error Handling

- [x] 1.1 Refactor `require_user()` trong `llm-mw/core/auth.py` để phân biệt 3 loại lỗi: missing key (401), invalid key (401), inactive user (403) — mỗi loại có error message và logging riêng
- [x] 1.2 Thêm logging WARNING cho mỗi authentication failure: log hashed subkey (8 chars), request path, client IP
- [x] 1.3 Cập nhật `api/models.py` sử dụng error codes mới từ `require_user()`

## 2. CORS Configuration Fix

- [x] 2.1 Cập nhật CORS middleware trong `llm-mw/main.py` để chấp nhận Open WebUI public URL origin cho browser preflight requests
- [x] 2.2 Đảm bảo server-to-server requests (không có Origin header) không bị CORS block

## 3. Auth Diagnostic Endpoint

- [x] 3.1 Tạo file `llm-mw/api/auth_test.py` với endpoint `GET /v1/_mw/auth-test` — xác thực Bearer token và trả về user info (user_id, active, allowed_models, quota status)
- [x] 3.2 Đăng ký route mới trong `llm-mw/main.py`

## 4. Testing & Verification

- [x] 4.1 Test auth-test endpoint với subkey hợp lệ (expect 200 + user info)
- [x] 4.2 Test auth-test endpoint với subkey không hợp lệ (expect 401)
- [x] 4.3 Test models endpoint với subkey hợp lệ (expect 200 + model list)
- [x] 4.4 Test từ Open WebUI Settings → Connections với subkey user — verify models load thành công
- [x] 4.5 Kiểm tra middleware logs để xác nhận logging chi tiết hoạt động
