## 1. Chat Flow Documentation

- [x] 1.1 Tạo sequence diagram chi tiết cho streaming chat flow (Browser → Nginx → Open WebUI → Middleware → LiteLLM → Provider → response ngược lại)
- [x] 1.2 Tạo sequence diagram cho non-streaming chat flow
- [x] 1.3 Tạo sequence diagram cho image generation flow (Gemini, GPT Image, xAI Grok Imagine)
- [x] 1.4 Tạo bảng provider parameter compatibility matrix (max_tokens, size, stream_options, response format) cho tất cả 12 chat + 6 image models
- [x] 1.5 Tài liệu hóa error paths và recovery behavior cho từng provider (HTTP status codes, retry behavior, user-facing errors)

## 2. Fix Cross-Model Chat Errors

- [x] 2.1 Tạo `_normalize_provider_params(model, body)` function trong `chat.py` để tự động normalize parameters dựa trên provider type
- [x] 2.2 Mở rộng GPT-5 `max_tokens` → `max_completion_tokens` handling cho tất cả models cần nó
- [x] 2.3 Audit và fix xAI Grok parameter handling (không gửi `size` param, xử lý `aspect_ratio`)
- [ ] 2.4 Test cross-model switching: gửi request lần lượt đến mỗi provider và verify response format consistency

## 3. Fix HTTPS Image Serving

- [x] 3.1 Thêm Nginx location block riêng cho `/v1/_mw/media/` với: proxy_cache, Cache-Control headers (immutable, max-age=86400), CORS headers (Access-Control-Allow-Origin: *)
- [x] 3.2 Thêm Content-Type detection dựa trên file extension trong Nginx location
- [x] 3.3 Verify `MW_PUBLIC_URL` trong docker-compose.yml trả về đúng HTTPS URL
- [ ] 3.4 Test image accessibility: tạo ảnh trên 1 máy, truy cập từ máy khác qua HTTPS URL, verify hiển thị đúng

## 4. httpx Connection Pooling

- [x] 4.1 Tạo shared `httpx.AsyncClient` với connection pool trên `app.state` trong `main.py` (max_connections=100, max_keepalive_connections=50)
- [x] 4.2 Refactor `_handle_streaming()` trong `chat.py` để sử dụng `request.app.state.http_client` thay vì tạo client mới (line 816)
- [x] 4.3 Thêm graceful shutdown handler để close shared client khi app stops
- [x] 4.4 Verify connection reuse qua logging: log connection pool stats trước/sau request

## 5. Scalability Analysis & Documentation

- [x] 5.1 Tính toán bandwidth requirements: streaming chat (5-50 KB/s × 200 users), image generation (200-500 KB per image × concurrent requests)
- [x] 5.2 Phân tích users.json file lock contention: estimated lock wait time với 200 concurrent quota updates, throughput degradation
- [x] 5.3 Phân tích latency budget breakdown: Nginx (~1-5ms) + Middleware auth (~5-20ms) + LiteLLM routing (~10-30ms) + Provider TTFB (500ms-5s)
- [x] 5.4 Đánh giá Docker resource limits cho 200 users: middleware (2G/4CPU), LiteLLM (4G/4CPU, 4 workers), Open WebUI (10G/6CPU, 6 workers)
- [x] 5.5 Tạo stress test plan với locust: 200 concurrent chat users, 50 concurrent image users, measure P95 latency và error rate

## 6. Concurrent Session (Same Account) Analysis

- [x] 6.1 Phân tích quota race condition: sequence diagram cho concurrent quota check → bump flow, worst-case cost overshoot
- [x] 6.2 Tài liệu hóa JWT session token behavior: mỗi login tạo token riêng, chat history shared, WebSocket channel isolation
- [x] 6.3 Phân tích message interleaving risk khi 2 users chat cùng conversation đồng thời
- [x] 6.4 Đưa ra recommendations: có nên limit concurrent sessions per account? Nêu pros/cons

## 7. Verification & Testing

- [ ] 7.1 Test thủ công: Chat với mỗi provider (OpenAI, Gemini, Grok, Claude) và verify response format
- [ ] 7.2 Test thủ công: Tạo ảnh với Gemini, GPT Image, Grok Imagine → truy cập ảnh từ máy khác
- [ ] 7.3 Review Nginx config changes: verify cache hit/miss qua `X-Cache-Status` header
- [x] 7.4 Tổng hợp tất cả findings vào tài liệu kỹ thuật cuối cùng
