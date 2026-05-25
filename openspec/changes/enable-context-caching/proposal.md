## Why

Chi phí API chiếm phần lớn ngân sách vận hành. Hiện tại hệ thống chưa tận dụng 2 tính năng **miễn phí/giảm phí** từ nhà cung cấp:

1. **Context Caching** — Anthropic và Gemini đều hỗ trợ cache system prompt/context, giảm 75-90% chi phí input tokens cho các requests lặp lại. Middleware forward body 1:1 nhưng LiteLLM chưa được cấu hình `cache_control_injection_points`.

2. **Provider Web Search Cost Tracking** — Middleware đã track chi phí qua `x-litellm-response-cost` header. Nếu sau này bật provider search (Gemini Grounding có 5K queries miễn phí/tháng), chi phí sẽ được track tự động. Nhưng cần xác nhận và document rõ cơ chế này.

## What Changes

- Bật Anthropic prompt caching qua `cache_control_injection_points` trong `litellm_config.yaml`
- Xác nhận Gemini implicit caching đã hoạt động (chỉ verify, không cần config)
- Thêm `cached_tokens` tracking trong middleware audit (nếu LiteLLM trả về)
- Document cơ chế provider search cost tracking qua `x-litellm-response-cost`

## Capabilities

### New Capabilities
- `context-caching`: LiteLLM tự động inject `cache_control` vào system messages cho Anthropic models, Gemini implicit caching xác nhận hoạt động. Giảm 75-90% input cost cho requests lặp lại.

### Modified Capabilities
_(Không modify caps hiện có, chỉ bổ sung config và tracking)_

## Impact

- **Code affected**: `litellm/litellm_config.yaml` (thêm cache_control_injection_points), `llm-mw/api/chat.py` (thêm cached_tokens tracking), `llm-mw/utils/logging.py` (log cached_tokens), docs
- **APIs**: Không thay đổi API interface
- **Dependencies**: Không thêm dependency mới
- **Systems**: LiteLLM container cần restart sau config change

## Model Compatibility

### Context Caching

| Provider | Model | Hỗ trợ caching | Ghi chú |
|---|---|---|---|
| **Anthropic** | claude-opus-4-6 | ✅ Prompt caching | Min 1024 tokens, TTL 5 phút |
| **Anthropic** | claude-sonnet-4-6 | ✅ Prompt caching | Min 1024 tokens, TTL 5 phút |
| **Anthropic** | claude-haiku-4-5 | ✅ Prompt caching | Min 1024 tokens, TTL 5 phút |
| **Google** | gemini-3.1-pro-preview | ✅ Implicit caching | Tự động, không cần config |
| **Google** | gemini-3.1-flash-lite-preview | ✅ Implicit caching | Tự động, không cần config |
| **Google** | gemini-2.5-flash | ✅ Implicit caching | Tự động, không cần config |
| **OpenAI** | gpt-5.4 | ❌ Không hỗ trợ prompt caching kiểu Anthropic | OpenAI dùng cơ chế khác (automatic, server-side) |
| **OpenAI** | gpt-5.2 | ❌ Không hỗ trợ prompt caching kiểu Anthropic | OpenAI dùng cơ chế khác |
| **OpenAI** | gpt-5 | ❌ Không hỗ trợ prompt caching kiểu Anthropic | OpenAI dùng cơ chế khác |
| **xAI** | grok-4.20-reasoning | ❌ Không hỗ trợ prompt caching | Không có API caching |
| **xAI** | grok-4-1-fast-reasoning | ❌ Không hỗ trợ prompt caching | Không có API caching |
| **xAI** | grok-4-1-fast-non-reasoning | ❌ Không hỗ trợ prompt caching | Không có API caching |

> **⚠️ BÁO CÁO:** OpenAI (3 models) và xAI (3 models) **KHÔNG hỗ trợ** prompt caching theo cách Anthropic/Gemini. OpenAI có caching tự động server-side (không cần config), xAI không có caching. `cache_control_injection_points` của LiteLLM chỉ áp dụng cho Anthropic — an toàn vì `drop_params: true` sẽ loại bỏ params không hỗ trợ cho OpenAI/xAI.

### Provider Web Search

| Provider | Tool name | Chi phí/1K calls | Hỗ trợ qua LiteLLM |
|---|---|---|---|
| **OpenAI** | `web_search` | $10 | ✅ Qua `openai/responses/` prefix |
| **Google** | `google_search` grounding | $35 (free 5K/tháng) | ✅ Native support |
| **xAI** | `web_search` + `x_search` | $5 | ✅ Pass-through |
| **Anthropic** | `web_search` | $10 | ✅ Pass-through |
