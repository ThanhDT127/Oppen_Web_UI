## 1. File 02-tai-lieu-van-hanh.md
- [x] 1.1 Thêm cột STT + căn lề toàn bộ bảng.
- [x] 1.2 Sửa route access logs: `/v1/_mw/admin/access-logs` → `/v1/_mw/access_summary`.
- [x] 1.3 Verify vs docker-compose.yml — container names, ports, resources khớp.

## 2. File 08-dashboard.md
- [x] 2.1 Thêm cột STT + căn lề toàn bộ bảng.
- [x] 2.2 Verify API endpoints vs main.py — đã khớp.

## 3. File 09-user-management.md
- [x] 3.1 Thêm cột STT + căn lề toàn bộ bảng.
- [x] 3.2 Sửa dashboard URL: `http://<server>:5000/dashboard` → `https://openwebui.example.com:51122/dashboard`.
- [x] 3.3 Sửa timezone trong schema: `Asia/Bangkok` → `Asia/Ho_Chi_Minh` (theo docker-compose.yml TZ).
- [x] 3.4 Sửa model names trong examples: `gemini-2.5-flash`, `gpt-4o-mini` → `chat-gemini-2.5-flash`, `chat-gpt-5` (aliases thực tế).

## 4. File 13-canh-bao-quota.md
- [x] 4.1 Thêm cột STT + căn lề toàn bộ bảng.
- [x] 4.2 Thêm xAI và Anthropic vào bảng ngưỡng cảnh báo per-provider (thiếu trước đó).
- [x] 4.3 Sửa curl examples: `http://10.0.0.1:5000` → `http://localhost:5000`, `Authorization: Bearer` → `X-Admin-Key: $ADMIN_KEY`.

## 5. File 14-ke-hoach-mo-rong.md
- [x] 5.1 Thêm cột STT + căn lề toàn bộ bảng.
- [x] 5.2 Verify resource specs vs docker-compose.yml.

## 6. File 17-can-bang-tai.md
- [x] 6.1 Thêm cột STT + căn lề toàn bộ bảng.
- [x] 6.2 Verify worker counts, rate limits vs nginx.conf + docker-compose.yml.
