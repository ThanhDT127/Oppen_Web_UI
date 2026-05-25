## ADDED Requirements

### Requirement: Concurrent User Bottleneck Analysis
Hệ thống SHALL được đánh giá và tài liệu hóa khả năng chịu tải cho 200 concurrent users, xác định rõ các bottleneck.

#### Scenario: Connection pool bottleneck identification
- **WHEN** 200 users đồng thời gửi chat requests
- **THEN** tài liệu MUST xác định bottleneck tại mỗi layer: (1) httpx connections từ Middleware→LiteLLM (hiện tại: 1 client/request), (2) LiteLLM max_parallel_requests (hiện: 50), (3) PostgreSQL max_connections (hiện: 300), (4) Nginx worker_connections (hiện: 2048)

#### Scenario: File I/O bottleneck analysis
- **WHEN** 200 users đồng thời trigger quota check/update
- **THEN** tài liệu MUST phân tích contention trên users.json file lock: estimated lock wait time, throughput degradation, và recommend migration plan

### Requirement: Bandwidth and Latency Assessment
Tài liệu SHALL đánh giá bandwidth requirements và latency budget cho 200 concurrent users.

#### Scenario: Streaming bandwidth calculation
- **WHEN** 200 users đồng thời chat (streaming mode)
- **THEN** tài liệu MUST tính toán: (1) estimated bandwidth per stream (~5-50 KB/s per user), (2) total bandwidth requirement (1-10 MB/s), (3) so sánh với server network capacity

#### Scenario: Image generation bandwidth
- **WHEN** 50 users đồng thời generate images (worst case)
- **THEN** tài liệu MUST tính toán: (1) average image size per provider (Gemini ~200KB, DALL-E ~500KB, Grok ~300KB), (2) peak bandwidth khi serve cached images, (3) middleware disk I/O impact

#### Scenario: Latency budget documentation
- **WHEN** admin cần optimize response time
- **THEN** tài liệu MUST breakdown latency: (1) Nginx proxy overhead (~1-5ms), (2) Middleware auth+quota check (~5-20ms), (3) LiteLLM routing (~10-30ms), (4) Provider API TTFB (500ms-5s), (5) total end-to-end P95 target

### Requirement: Concurrent Session Same Account Analysis
Tài liệu SHALL phân tích behavior và risks khi nhiều users chia sẻ cùng 1 tài khoản.

#### Scenario: Quota race condition analysis
- **WHEN** 5 users sử dụng cùng 1 subkey đồng thời
- **THEN** tài liệu MUST phân tích: (1) file lock serialization behavior, (2) potential for over-spend giữa check và bump, (3) worst-case cost overshoot amount

#### Scenario: Session token sharing behavior
- **WHEN** multiple users đăng nhập cùng 1 Open WebUI account
- **THEN** tài liệu MUST mô tả: (1) JWT token independence (mỗi session có token riêng), (2) chat history visibility (shared), (3) WebSocket channel isolation behavior

#### Scenario: Concurrent chat interference
- **WHEN** 2 users cùng tài khoản chat đồng thời trong cùng 1 conversation
- **THEN** tài liệu MUST phân tích: (1) message interleaving risk, (2) streaming response isolation, (3) chat history consistency

### Requirement: Resource Utilization Recommendations
Tài liệu SHALL đưa ra recommendations cụ thể cho resource allocation dựa trên analysis.

#### Scenario: Docker resource limits review
- **WHEN** admin cần configure hệ thống cho 200 users
- **THEN** tài liệu MUST recommend: (1) middleware memory/CPU limits (hiện: 2G/4CPU), (2) LiteLLM worker count (hiện: 4), (3) Open WebUI worker count (hiện: 6), (4) PostgreSQL connection pool sizing

#### Scenario: Horizontal scaling roadmap
- **WHEN** system cần scale beyond 200 users
- **THEN** tài liệu MUST outline: (1) middleware horizontal scaling strategy (Nginx upstream round-robin), (2) shared state migration (users.json → PostgreSQL), (3) media storage scaling (local → S3/MinIO), (4) estimated cost increase

### Requirement: httpx Connection Pooling
Middleware SHALL sử dụng shared httpx.AsyncClient connection pool thay vì tạo client mới mỗi request.

#### Scenario: Shared client initialization
- **WHEN** middleware application starts
- **THEN** app.state MUST chứa shared httpx.AsyncClient với `max_connections=100`, `max_keepalive_connections=50`, `timeout=600`

#### Scenario: Stream request uses shared pool
- **WHEN** streaming chat request được xử lý
- **THEN** middleware MUST sử dụng shared client từ `request.app.state.http_client` thay vì tạo `httpx.AsyncClient(timeout=600)` mới

#### Scenario: Connection pool graceful shutdown
- **WHEN** middleware application shuts down
- **THEN** shared client MUST được close properly để release tất cả connections
