## Why

Khi user (non-admin) trong Open WebUI cấu hình "Direct Connection" tới middleware (`http://middleware:5000/v1`) với Bearer token (subkey), hệ thống không load được danh sách models và hiển thị lỗi "OpenAI: Network Problem". Vấn đề cốt lõi là:

1. **CORS blocking**: Middleware chỉ cho phép origin `https://openwebui.example.com:51122` nhưng khi Open WebUI server-side forward request, nó sử dụng internal Docker hostname (`http://middleware:5000`) — không match CORS.
2. **Subkey mismatch giữa DB và fallback**: Subkeys trong `users.json` (plaintext) không tương ứng với subkey_hash trong DB vì `MW_SECRET` khác nhau giữa file `.env` local và Docker container.
3. **Thiếu error messaging rõ ràng**: Khi xác thực thất bại, middleware trả về `401/403` generic mà không có thông tin debug giúp user/admin xác định nguyên nhân.

## What Changes

- Thêm cấu hình CORS linh hoạt hơn để hỗ trợ internal Docker network origins (Open WebUI server-to-middleware communication)
- Cải thiện error response từ endpoint `/v1/models` để trả về thông tin lỗi chi tiết hơn (phân biệt "missing key" vs "invalid key" vs "inactive user")
- Thêm diagnostic endpoint `/v1/_mw/auth-test` cho admin để kiểm tra xác thực subkey mà không cần gọi models
- Thêm logging chi tiết hơn trong `require_user()` để trace lỗi xác thực
- Fix CORS middleware để chấp nhận requests từ Open WebUI container (internal network)

## Capabilities

### New Capabilities
- `auth-diagnostics`: Endpoint `/v1/_mw/auth-test` cho phép admin test subkey validity, trả về user_id + status + allowed_models. Giúp debug lỗi kết nối nhanh chóng.

### Modified Capabilities
_(Không có specs tồn tại để modify)_

## Impact

- **Code affected**: `llm-mw/core/auth.py` (improved error messages + logging), `llm-mw/main.py` (CORS + new route), `llm-mw/api/models.py` (better error response)
- **APIs**: New endpoint `GET /v1/_mw/auth-test` (requires Bearer token). Modified response format for `GET /v1/models` error cases.
- **Dependencies**: Không thêm dependency mới
- **Systems**: Middleware container cần rebuild sau khi thay đổi
