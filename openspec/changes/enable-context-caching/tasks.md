## Tasks

### 1. Bật Anthropic Prompt Caching via LiteLLM Config
- [x] Thêm `cache_control_injection_points` vào `litellm_settings` trong `litellm/litellm_config.yaml`
- [ ] Verify LiteLLM version tương thích (>=1.71.0) — **cần kiểm tra trên server deploy**
- [ ] Restart LiteLLM container để apply config — **cần chạy trên server deploy**

### 2. Thêm cached_tokens Tracking
- [x] Thêm `cached_tokens_created` và `cached_tokens_read` vào `_handle_non_streaming()` trong `chat.py`
- [x] Thêm `cached_tokens_created` và `cached_tokens_read` vào `_finalize_streaming()` trong `chat.py`
- [x] Thêm fields vào `write_audit_line()` calls

### 3. Document Provider Search Cost Tracking
- [x] Tạo doc `docs/api-features-context-caching.md` giải thích cơ chế caching + search cost tracking + model compatibility matrix

### 4. Verification
- [ ] Test Anthropic caching: gửi 2 requests liên tiếp, verify response có `cache_read_input_tokens > 0` — **cần deploy**
- [ ] Test Gemini implicit caching: gửi requests, check `cachedContentTokenCount` in usage — **cần deploy**
- [x] Test non-Anthropic models: `drop_params: true` drop `cache_control` — verified qua config review
- [x] Test audit log: verify `cached_tokens_created` và `cached_tokens_read` fields có trong code
