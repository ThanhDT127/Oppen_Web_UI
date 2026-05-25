## Why

Hiện tại, khi user chat và cần thông tin thời sự, Open WebUI tự orchestrate web search qua SearXNG: tạo search query (1 API call) → gọi SearXNG → inject kết quả vào context → gửi model (1 API call nữa). Quy trình này tốn 2-3 API calls mỗi lần search, tăng chi phí token và latency. Trong khi đó, cả 4 provider (Gemini, Claude, Grok, OpenAI) đều đã hỗ trợ native web search — model tự quyết khi nào cần search, tự tìm và tổng hợp kết quả trong 1 request duy nhất.

## What Changes

- **Middleware inject `web_search_options`**: Trong `chat.py`, tự động thêm `web_search_options` vào request body khi phát hiện là request chat thường (không phải system task như tạo title, tags, follow-up).
- **LiteLLM xử lý per-provider**: LiteLLM tự động convert `web_search_options` thành format tương ứng cho từng provider (Google Search Grounding, Anthropic web_search tool, xAI web search, OpenAI auto-bridge sang `/responses`).
- **Tắt OWUI SearXNG orchestration**: Disable "Default Features > Web Search" trong Open WebUI Admin Panel cho tất cả model để tránh double search (vừa SearXNG vừa provider).
- **SearXNG giữ nguyên**: Container SearXNG vẫn chạy, không thay đổi. Có thể bật lại bất cứ lúc nào.
- **System task prompts không bị ảnh hưởng**: Các luồng nội bộ (title generation, tag generation, search query generation, follow-up suggestions) không bị inject web search.

## Capabilities

### New Capabilities
- `provider-web-search`: Inject `web_search_options` vào request body tại middleware cho request chat thường, cho phép model tự search qua provider's native search engine thay vì SearXNG. Áp dụng cho cả 4 provider: Gemini (Google Search Grounding), Claude (web_search tool), Grok (xAI web search), OpenAI (auto-bridge `/responses`).

### Modified Capabilities
<!-- No existing spec-level behavior changes. Implementation-only changes in middleware. -->

## Impact

- **`llm-mw/api/chat.py`**: Sửa function `_normalize_provider_params()` — thêm logic detect system task và inject `web_search_options`.
- **Open WebUI Admin Panel**: Tắt "Default Features > Web Search" per model (manual config, không sửa code).
- **LiteLLM**: Không cần thay đổi config. `web_search_options` được pass-through tự động. LiteLLM auto-bridge `/chat/completions` → `/responses` cho OpenAI models.
- **SearXNG**: Không thay đổi. Container vẫn chạy bình thường.
- **Cost**: Provider search có thể tính phí riêng (Gemini: 5,000 free queries/tháng; Anthropic, xAI, OpenAI: tính theo usage). Cần monitor qua dashboard.
- **Response format**: Không thay đổi — LiteLLM normalize response về chuẩn OpenAI `/chat/completions` format.
