## Context

Open WebUI stack sử dụng kiến trúc 4-tier: Open WebUI (port 8080) → Middleware (port 5000) → LiteLLM (port 4000) → PostgreSQL. Tất cả chạy trong Docker network, truy cập qua Nginx reverse proxy (port 3000, NAT tới 51122).

Hiện tại, khi user trong Open WebUI cấu hình "Direct Connection" tới middleware:
- Open WebUI **gửi request từ backend** (server-side) tới `http://middleware:5000/v1` — đúng network, header Authorization được forward
- Middleware nhận Bearer token, gọi `require_user()` để xác thực subkey
- Nếu subkey không khớp hash trong DB → trả 401/403 → Open WebUI hiển thị "OpenAI: Network Problem"

Root cause phát hiện:
1. **CORS misconfiguration**: `allow_origins` chỉ chấp nhận `https://openwebui.rangdong.com.vn:51122` — browser preflight requests bị block khi user mở Settings → Connections và giao diện gọi trực tiếp tới middleware
2. **Subkey validation**: `_find_user_db()` sử dụng `hash_subkey()` với `MW_SECRET` — nếu user nhập sai subkey hoặc subkey chưa được hash đúng trong DB, nhận 403 generic
3. **No debug info**: Error messages không phân biệt "missing key" vs "invalid key" vs "inactive user" → admin không debug được

## Goals / Non-Goals

**Goals:**
- Sửa CORS để browser requests từ Open WebUI Settings hoạt động chính xác
- Trả error messages rõ ràng, phân biệt từng loại lỗi xác thực
- Thêm diagnostic endpoint giúp admin kiểm tra subkey nhanh chóng
- Thêm logging chi tiết giúp trace lỗi xác thực trong production

**Non-Goals:**
- Không thay đổi cơ chế hash subkey (HMAC-SHA256)
- Không thay đổi flow xác thực cơ bản
- Không thêm UI mới vào dashboard
- Không sửa Open WebUI frontend code

## Decisions

### D1: Fix CORS để chấp nhận internal Docker origins

**Decision**: Thêm wildcard internal origins cho Docker network communication.

**Rationale**: Open WebUI gửi request từ server-side nên không cần CORS, nhưng khi user mở Settings → Connections, browser gọi middleware API (verify connection) qua Nginx → cần CORS headers đúng. Giải pháp là thêm internal origins vào allow_origins.

**Alternative considered**: Disable CORS hoàn toàn → rejected vì giảm bảo mật.

### D2: Error messages chi tiết trong auth flow

**Decision**: Sửa `require_user()` và endpoint responses để phân biệt:
- 401: Missing Bearer token
- 401: Subkey not found in database
- 403: User account is deactivated
- 200 + empty data: User authenticated but no models available

**Rationale**: Generic errors làm admin mất thời gian debug. Error detail chỉ visible trong server logs (không expose qua API cho security).

### D3: Auth diagnostic endpoint

**Decision**: Tạo `GET /v1/_mw/auth-test` yêu cầu Bearer token, trả về:
```json
{
  "status": "ok",
  "user_id": "user1",
  "active": true,
  "allowed_models": ["*"],
  "quota_remaining": {...}
}
```

**Rationale**: Admin có thể test subkey ngay từ curl hoặc browser mà không cần gọi models endpoint.

## Risks / Trade-offs

- **[Expose user info qua auth-test]** → Mitigation: Endpoint chỉ trả thông tin cơ bản (user_id, active status), không bao gồm subkey/hash. Response chỉ trả về cho chính user đang auth.
- **[CORS mở rộng]** → Mitigation: Chỉ thêm cùng public URL đã có, không thêm wildcard `*`.
- **[Detailed error messages có thể giúp attacker]** → Mitigation: Chi tiết lỗi chỉ trong server logs, API responses vẫn generic nhưng có error code riêng.
