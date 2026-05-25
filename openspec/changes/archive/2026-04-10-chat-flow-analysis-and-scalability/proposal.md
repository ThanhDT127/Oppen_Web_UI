## Why

Hệ thống Open WebUI đang gặp các vấn đề nghiêm trọng ảnh hưởng đến trải nghiệm người dùng và khả năng mở rộng:

1. **Lỗi chat giữa các mô hình** — Khi chuyển đổi giữa Grok, ChatGPT, Gemini, Claude, các request bị lỗi do khác biệt về API format, parameter handling (vd: `max_tokens` vs `max_completion_tokens` cho GPT-5), và streaming behavior giữa các provider.

2. **Ảnh không hiển thị trên máy khác** — Ảnh sinh ra (từ DALL-E, Gemini, Grok Imagine) được lưu trên middleware container và serve qua HTTP URL. Khi truy cập từ máy khác, URL trỏ đến `MW_PUBLIC_URL` (hiện tại: `https://openwebui.example.com:51122`) nhưng routing qua Nginx chưa tối ưu, thiếu CORS headers, và thiếu caching cho media files.

3. **Scalability khi 200 người dùng đồng thời** — Hệ thống chưa được stress test cho quy mô lớn. Các điểm yếu tiềm ẩn: single httpx.AsyncClient per stream request, file-based users.json với file lock, single-upstream middleware trong Nginx, và thiếu connection pooling.

## What Changes

### Phân tích & Tài liệu hóa
- Tạo **tài liệu luồng chat chi tiết** (sequence diagram) từ browser → Nginx → Open WebUI → Middleware → LiteLLM → Provider và ngược lại
- **Audit lỗi cross-model**: phân tích log và code path cho từng provider (OpenAI, Gemini, xAI, Anthropic)
- **Root-cause analysis** cho image HTTPS serving issue

### Sửa lỗi & Cải thiện
- **Fix image serving over HTTPS**: Thêm Nginx location block cho media files với proper cache headers, CORS, và content-type detection
- **Fix cross-model chat errors**: Normalize response format, handle provider-specific parameters consistently
- **Thêm connection pooling** cho httpx client thay vì tạo mới mỗi streaming request

### Tối ưu hiệu suất
- **Benchmark & stress test plan** cho 200 concurrent users
- **Identify bottlenecks**: users.json file I/O, single middleware instance, streaming timeout handling
- **Concurrent session handling**: phân tích rủi ro khi nhiều người dùng cùng 1 tài khoản
- **Bandwidth optimization**: image caching, response compression, CDN-ready architecture

## Capabilities

### New Capabilities
- `chat-flow-documentation`: Tài liệu hóa chi tiết luồng chat end-to-end với sequence diagrams, error paths, và data flow cho tất cả providers
- `https-media-serving`: Fix và tối ưu serving media files (ảnh sinh ra) qua HTTPS cho truy cập từ mọi thiết bị, bao gồm CORS, caching, và CDN-ready
- `scalability-analysis`: Phân tích điểm yếu scalability cho 200+ concurrent users, bao gồm benchmark plan, bottleneck identification, và recommendations

### Modified Capabilities

## Impact

### Affected Code
- `llm-mw/api/chat.py` — Normalize cross-model parameters, fix httpx client pooling
- `llm-mw/api/images.py` — Image response handling consistency
- `llm-mw/utils/media.py` — Media URL generation và serving
- `nginx/nginx.conf` — Thêm media caching location, CORS headers, rate limiting tuning
- `docker-compose.yml` — Resource limits review, potential middleware scaling
- `llm-mw/config.py` — Connection pool settings

### Infrastructure
- Nginx reverse proxy configuration
- Docker resource allocation
- File I/O patterns (users.json)
- WebSocket/SSE connection management

### Dependencies
- httpx (async HTTP client) — connection pooling configuration
- LiteLLM — provider-specific parameter handling
- PostgreSQL — connection pool sizing for 200+ users
