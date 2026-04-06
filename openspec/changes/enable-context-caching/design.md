## Context

Middleware proxy body 1:1 lên LiteLLM (`json=body` tại `chat.py` dòng 827, 985). LiteLLM config có `drop_params: true` → params không hỗ trợ bởi model sẽ tự động bị loại bỏ, an toàn. Chi phí hiện track qua 2 cơ chế: `x-litellm-response-cost` header (non-streaming) và `find_usage_in_log()` fallback (streaming).

## Goals / Non-Goals

**Goals:**
- Bật Anthropic prompt caching cho Claude Opus 4.6, Sonnet 4.6, Haiku 4.5 → giảm 75-90% input cost
- Xác nhận Gemini implicit caching đã hoạt động cho Gemini 3.1 Pro, 3.1 Flash, 2.5 Flash
- Thêm `cached_tokens` tracking vào audit log (khi LiteLLM trả `cache_creation_input_tokens`, `cache_read_input_tokens`)
- Document cơ chế provider search cost tracking

**Non-Goals:**
- Không bật explicit caching cho Gemini (cần quản lý TTL, phức tạp)
- Không bật provider web search thay thế SearXNG (SearXNG vẫn primary, $0 cost)
- Không sửa đổi quota logic hay pricing logic
- Không hỗ trợ OpenAI/xAI prompt caching (server-side tự động / không hỗ trợ)

## Decisions

### D1: Bật Anthropic caching qua LiteLLM auto-injection

**Decision**: Thêm `cache_control_injection_points` vào `litellm_config.yaml` để LiteLLM tự inject `cache_control: {"type": "ephemeral"}` vào system messages cho Anthropic models.

**Rationale**: 
- Không cần sửa middleware code — LiteLLM xử lý injection
- `drop_params: true` đảm bảo an toàn cho non-Anthropic models (params tự drop)
- System prompts thường lặp lại giữa requests → tỷ lệ cache hit cao
- Chi phí: cache write +25%, cache read -90% → break-even sau ~2 requests

**Config change:**
```yaml
litellm_settings:
  drop_params: true
  cache_control_injection_points:
    - location: "message"
      role: "system"
```

### D2: Track cached_tokens trong audit

**Decision**: Trong `_handle_non_streaming()` và `_finalize_streaming()`, extract `cache_creation_input_tokens` và `cache_read_input_tokens` từ response usage object, write vào audit log.

**Rationale**: Cho phép admin theo dõi hiệu quả caching qua dashboard — biết được bao nhiêu requests hit cache.

**Implementation**: Thêm 2 fields vào `write_audit_line()`:
```python
usage = data.get("usage", {})
cached_tokens_created = usage.get("cache_creation_input_tokens", 0)
cached_tokens_read = usage.get("cache_read_input_tokens", 0)
```

### D3: Document provider search cost tracking

**Decision**: Tạo tài liệu xác nhận rằng `get_cost_from_headers()` (services/litellm.py dòng 13-32) đã track provider search fees qua `x-litellm-response-cost` header. Không cần code change.

**Rationale**: Provider search fees (OpenAI $10/1K, Gemini $35/1K, xAI $5/1K, Anthropic $10/1K) đều được LiteLLM tính vào response cost header → middleware tracking tự động bao gồm.

## Risks / Trade-offs

- **[Cache write cost +25%]** → First request sẽ đắt hơn 25%, nhưng subsequent requests giảm 90%. Break-even ≈ 2 requests. Với chat (multi-turn), luôn có lời.
- **[drop_params false positive]** → Rủi ro rất thấp. `drop_params: true` đã hoạt động cho existing params. LiteLLM sẽ drop `cache_control` cho OpenAI/xAI.
- **[LiteLLM version requirement]** → Cần LiteLLM v1.71.0+ cho web search/cache features. Cần verify version hiện tại.
- **[Gemini implicit caching không đảm bảo]** → Google quyết định khi nào cache hit. Không có cách ép. Chỉ có thể tối ưu bằng cách đặt content lớn ở đầu prompt.
