## 1. File 07-api-reference.md
- [x] 1.1 Thêm cột STT vào tất cả Markdown Tables.
- [x] 1.2 Căn lề thẳng hàng toàn bộ bảng.
- [x] 1.3 Cập nhật response schema `/v1/_mw/summary`: đảm bảo có `pending_open_count`, `embedding_calls`, `video_calls`, `billable_calls`.
- [x] 1.4 Thay model names cũ (`gpt-4-turbo`) → tên thực tế (`chat-gpt-5.4`) trong tất cả ví dụ.
- [x] 1.5 Kiểm tra tất cả routes khớp với `llm-mw/main.py` — phát hiện và sửa route `/v1/_mw/admin/access-logs` → `/v1/_mw/access_summary`.

## 2. File 15-nginx-https.md
- [x] 2.1 Thêm cột STT vào tất cả Markdown Tables.
- [x] 2.2 Căn lề thẳng hàng toàn bộ bảng.
- [x] 2.3 Kiểm tra vs `nginx/nginx.conf` — phát hiện và sửa 5 sai lệch:
  - Sửa login rate limit: 5/phút → **10/phút** (burst 5)
  - Thêm zone `api` (30r/s, burst 60) bị thiếu
  - Thêm `http2 on` vào bảng cấu hình chung
  - Sửa timeout `/ws/`: thêm **86400s (24h)** riêng cho WebSocket/Socket.IO
  - Routing table: thêm `/api/*` và `/v1/_mw/media/*`, bổ sung burst values chính xác

## 3. File 16-web-search.md
- [x] 3.1 Thêm cột STT vào tất cả Markdown Tables.
- [x] 3.2 Căn lề thẳng hàng toàn bộ bảng.
- [x] 3.3 Kiểm tra vs `searxng/settings.yml` — **Khớp hoàn toàn** (engines, Redis URL, port, limiter off).

## 4. File api-features-context-caching.md
- [x] 4.1 Thêm cột STT vào tất cả Markdown Tables.
- [x] 4.2 Căn lề thẳng hàng toàn bộ bảng.
- [x] 4.3 Kiểm tra vs `litellm/litellm_config.yaml` — thêm cột **Alias** vào Compatibility Matrix để phân biệt alias name (dùng khi gọi API) vs provider model name. Alias names đã được đồng bộ chính xác với config.
