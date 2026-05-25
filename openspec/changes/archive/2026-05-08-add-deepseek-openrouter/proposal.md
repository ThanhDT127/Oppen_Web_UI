# Add DeepSeek V4 (Flash + Pro) via OpenRouter

## Lý do

- DeepSeek V4 Flash cực rẻ ($0.14/MTok input) — rẻ hơn Gemini Flash
- DeepSeek V4 Pro performance ngang Sonnet nhưng giá thấp hơn
- Dùng qua OpenRouter — 1 API key quản lý nhiều provider

## Pricing

| Model | Input | Output | So sánh |
|-------|-------|--------|---------|
| V4 Flash (OpenRouter) | $0.14/MTok | $0.28/MTok | Rẻ nhất fleet |
| V4 Pro (OpenRouter) | $1.74/MTok | $3.48/MTok | Promo hết, giá full |

> [!IMPORTANT]
> V4 Pro qua OpenRouter đắt 4x so với direct API ($0.435→$1.74 input).
> Nếu dùng nhiều Pro, cân nhắc direct API key riêng sau.

## Scope

### [MODIFY] [docker-compose.yml](file:///C:/Code/openwebui_fetch/Oppen_Web_UI/docker-compose.yml)
- Thêm `OPENROUTER_API_KEY` env var cho LiteLLM container

### [MODIFY] [litellm_config.yaml](file:///C:/Code/openwebui_fetch/Oppen_Web_UI/litellm/litellm_config.yaml)
- Thêm 2 model entries: `chat-deepseek-v4-pro`, `chat-deepseek-v4-flash`
- Provider: `openrouter/deepseek/deepseek-v4-pro` và `deepseek-v4-flash`

### [MODIFY] .env
- Thêm `OPENROUTER_API_KEY=...`

### [MODIFY] prices.json
- Thêm pricing cho deepseek models

### [MODIFY] alert_config.json
- Thêm provider budget `deepseek` với model_prefixes `["chat-deepseek"]`

### [MODIFY] Docs (07, 10, 11, 13, api-features-context-caching)
- Cập nhật model count: 14→16 chat, tổng 21→23
- Thêm DeepSeek vào bảng models, pricing, compatibility matrix

## Prerequisites

- **upgrade-litellm** phải hoàn thành trước (cần ≥1.83.x cho DeepSeek V4 support)
- OpenRouter API key phải có sẵn

## Verification

- Test chat với `chat-deepseek-v4-flash` và `chat-deepseek-v4-pro`
- Verify cost tracking qua `x-litellm-response-cost` header
- Verify audit log ghi đúng model name
- Verify provider budget alert hoạt động
