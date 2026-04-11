## Context

### Kiến trúc hiện tại
Hệ thống Open WebUI Stack gồm 6 services Docker:

```
Browser → Nginx (:3000 HTTPS, NAT 51122→3000)
         ├→ Open WebUI (:8080, 6 workers, Redis WebSocket)
         ├→ Middleware (:5000, auth/quota/audit)
         │   └→ LiteLLM (:4000, 4 workers, multi-provider proxy)
         ├→ SearXNG (:8080, web search)
         └→ PostgreSQL (:5432, PGVector) + Redis
```

### Luồng Chat hiện tại
```
User message → Nginx → Open WebUI → Middleware(/v1/chat/completions)
  → require_user() (subkey auth)
  → assert_model_allowed() + maybe_reset_quota()
  → detect image model? → _handle_image_as_chat()
  → prepare body + headers + request_id
  → streaming? → _handle_streaming() → httpx.AsyncClient → LiteLLM
                                     → Provider (OpenAI/Gemini/xAI/Anthropic)
                                     → SSE chunks → parse usage → finalize
  → non-streaming? → _handle_non_streaming() → httpx.post → LiteLLM → Provider
  → calculate cost → bump quota → write audit
```

### Vấn đề hiện tại
1. **Cross-model errors**: Mỗi provider có format/params khác nhau (GPT-5 cần `max_completion_tokens`, xAI không hỗ trợ `size` param cho image)
2. **Image HTTPS**: Ảnh được materialize từ base64 → file trên middleware container, serve qua `MW_PUBLIC_URL`. Thiếu Nginx media caching, CORS headers
3. **Scalability**: Mỗi stream request tạo httpx.AsyncClient mới (line 816), users.json dùng file lock, single middleware upstream

## Goals / Non-Goals

**Goals:**
- Tạo tài liệu luồng chat chi tiết (sequence diagrams) cho tất cả providers
- Fix image serving qua HTTPS để hoạt động trên mọi thiết bị/mạng
- Fix cross-model chat errors (parameter normalization, response format)
- Đánh giá và tài liệu hóa bottleneck cho 200 concurrent users
- Xác định rủi ro khi nhiều người dùng chung 1 tài khoản
- Đưa ra recommendations cho bandwidth, latency, và resource optimization

**Non-Goals:**
- Không triển khai horizontal scaling (multiple middleware instances) trong phase này
- Không thay đổi authentication architecture (subkey system)
- Không thêm CDN (chỉ chuẩn bị CDN-ready architecture)
- Không thay đổi LiteLLM proxy configuration cơ bản

## Decisions

### D1: Shared httpx.AsyncClient Connection Pool
**Quyết định**: Thay thế việc tạo `httpx.AsyncClient()` mới mỗi stream request (chat.py line 816) bằng shared connection pool trên `app.state`.

**Lý do**: Hiện tại mỗi streaming request tạo `httpx.AsyncClient(timeout=600)` → TCP handshake overhead, không reuse connections. Với 200 concurrent users, sẽ tạo 200 TCP connections riêng biệt.

**Thay thế đã cân nhắc**:
- aiohttp session: Khác API, cần refactor nhiều hơn
- Per-request client giữ nguyên: Không scale

### D2: Nginx Media Caching & CORS
**Quyết định**: Thêm Nginx location block riêng cho `/v1/_mw/media/` với:
- Cache-Control headers (immutable, max-age=86400)
- CORS: `Access-Control-Allow-Origin: *` (media files are public by UUID)
- Content-Type detection từ file extension
- proxy_cache cho media files

**Lý do**: Media files hiện đi qua generic `/v1/_mw/` block, không có caching hay CORS. Browser trên máy khác có thể bị blocked bởi mixed content hoặc CORS policy.

**Thay thế đã cân nhắc**:
- Serve media trực tiếp từ Nginx (bypass middleware): Cần shared volume, phức tạp hơn nhưng hiệu quả hơn → Phase sau
- S3/MinIO storage: Over-engineering cho quy mô hiện tại

### D3: Provider Parameter Normalization Layer
**Quyết định**: Tạo `_normalize_provider_params(model, body)` function trong chat.py để xử lý:
- `max_tokens` → `max_completion_tokens` cho GPT-5+
- Remove unsupported params per provider (size cho xAI)
- Normalize response format differences

**Lý do**: Hiện tại chỉ handle GPT-5 max_tokens (line 752-755), các provider khác có thể fail silently.

### D4: Users.json → Database Migration Path
**Quyết định**: Giai đoạn này chỉ **tài liệu hóa** vấn đề và recommend migration path. Không thực hiện migration.

**Lý do**: File-based users.json với file lock là bottleneck lớn nhất cho concurrent access, nhưng migration cần planning riêng vì ảnh hưởng nhiều module.

### D5: Concurrent Session Analysis
**Quyết định**: Tài liệu hóa behavior khi multiple users share 1 account:
- Quota race condition potential
- Session token sharing behavior (JWT)
- WebSocket channel isolation

**Lý do**: Đây là analysis task, không cần code change. Sẽ đưa ra recommendations.

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| Shared httpx pool exhaustion under load | Requests queue/timeout | Set `max_connections=100`, `max_keepalive_connections=50` with limits |
| Nginx media cache serves stale content | User sees old images | UUID-based filenames → content is immutable, no staleness risk |
| Provider API changes break normalization | Chat errors return | LiteLLM `drop_params: true` already handles unknown params |
| users.json file lock contention at 200 users | Slow quota updates, potential data loss | Document issue, recommend DB migration (phase 2) |
| Multiple users same account → quota race | Over/under billing | File lock serializes writes; documented as acceptable trade-off |
| SSL certificate issues blocking media | Images not loading | Verify wildcard cert covers media subdomain/path |

## Migration Plan

### Phase 1: Non-breaking fixes (this change)
1. Add Nginx media location with caching + CORS
2. Fix httpx connection pooling
3. Add provider parameter normalization
4. Create comprehensive documentation

### Phase 2: Scalability improvements (future)
1. Migrate users.json to PostgreSQL
2. Add middleware horizontal scaling (multiple instances behind Nginx upstream)
3. Implement CDN for media serving

### Rollback Strategy
- Nginx changes: Revert nginx.conf, reload
- Code changes: Revert commit, rebuild middleware container
- No data migration involved → clean rollback

## Open Questions

1. **Bandwidth measurement**: Cần access server metrics (iftop/vnstat) để đo bandwidth thực tế → yêu cầu SSH access hoặc monitoring stack
2. **SSL Certificate**: Cần xác nhận wildcard cert `*.rangdong.com.vn` có valid hay không, expiry date
3. **Load testing tool**: Sử dụng locust hay k6 cho stress test? → Recommend locust (Python, dễ integrate)
4. **Max concurrent per account**: Có cần limit không? Hiện tại không có mechanism nào
