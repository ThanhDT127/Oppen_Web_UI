## Prerequisites
- [x] 0a. Change `upgrade-litellm` hoàn thành ✅
- [x] 0b. Change `add-deepseek-openrouter` hoàn thành ✅

## Smart Routing Module
- [x] 1. Tạo `core/smart_routing.py` — complexity scoring + tier mapping
  - 5 providers × 4 tiers (SIMPLE/MEDIUM/COMPLEX/REASONING)
  - Keyword boost: Vietnamese + English
  - Conversation depth + message length scoring
  - Quota downgrade at 60%
- [x] 2-5. Tier mappings cho openai/gemini/grok/claude/deepseek (tất cả trong 1 module)

## Middleware Integration
- [x] 7. Integrate smart routing vào `api/chat.py`
  - Auto-model detection → resolve before LiteLLM call
  - body["model"] rewritten to concrete model
  - Quota % calculation from user data
  - Vision/file detection → boost complexity
- [x] 8. Quota >=60% → force SIMPLE tier
- [x] 9. Warning message injection (streaming + non-streaming)
  - Routing downgrade warning: "⚡ Quota đạt X%, đã chuyển sang model tiết kiệm"
  - Combined with existing quota warning
- [x] 10. Keyword scoring boost (Vietnamese + English)
- [x] 11. Vision/file attachment detection → boost

## Auth Integration
- [x] Updated `assert_model_allowed` to handle auto-model names

## Deploy
- [x] 12-13. Docker build + restart ✅

## Testing
- [x] 14. Test smart routing: simple query → SIMPLE tier ✅
- [x] 15. Test model list API: auto models injected ✅
- [x] 16. Test auth: auto-model allowed check ✅
- [x] 17. Test quota >=60% → force SIMPLE ✅
- [x] 18. Test warning message injection ✅

## Docs
- [x] 19. Cập nhật user guide `10-user-guide-vi.md` ✅ (thêm Smart Routing section + bảng auto models)
- [x] 20. Cập nhật architecture `03-architecture.md` ✅ (thêm 3 rows: Smart Routing, Quota downgrade, Warning)
- [x] 21. Cập nhật API reference `07-api-reference.md` ✅ (thêm auto models vào /v1/models response, v2.2)
