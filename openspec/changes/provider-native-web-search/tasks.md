## 1. Middleware Code Change

- [x] 1.1 Thêm logic inject `web_search_options` vào function `_normalize_provider_params()` trong `llm-mw/api/chat.py` — chỉ inject khi KHÔNG phải system task prompt và KHÔNG phải image model
- [x] 1.2 Thêm guard: không overwrite nếu body đã có `web_search_options`
- [x] 1.3 Thêm logging: log khi inject web_search_options (`logger.debug`)

## 2. Open WebUI Admin Config

- [x] 2.1 Tắt "Default Features > Web Search" cho tất cả 12 chat models trong Admin Panel (tránh double search SearXNG + provider) *(user tự thực hiện)*

## 3. Testing & Verification

- [ ] 3.1 Test Gemini model: gửi câu hỏi cần thông tin realtime (ví dụ "Giá vàng hôm nay?"), xác nhận response có thông tin cập nhật từ Google Search
- [ ] 3.2 Test Claude model: gửi câu hỏi tương tự, xác nhận Anthropic web_search tool hoạt động
- [ ] 3.3 Test Grok model: gửi câu hỏi tương tự, xác nhận xAI web search hoạt động
- [ ] 3.4 Test OpenAI model: gửi câu hỏi tương tự, xác nhận LiteLLM auto-bridge sang `/responses` hoạt động
- [ ] 3.5 Test system task: xác nhận title/tags/follow-up generation KHÔNG trigger web search (kiểm tra log)
- [ ] 3.6 Test image model: xác nhận image generation request KHÔNG có web_search_options (kiểm tra log)
- [ ] 3.7 Test streaming + quota warning: xác nhận streaming response và quota warning injection vẫn hoạt động bình thường
