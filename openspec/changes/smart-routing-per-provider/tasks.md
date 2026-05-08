## Prerequisites
- [ ] 0a. Change `upgrade-litellm` phải hoàn thành
- [ ] 0b. Change `add-deepseek-openrouter` phải hoàn thành

## LiteLLM Config
- [ ] 1. Thêm `openai-auto` complexity router vào litellm_config.yaml
- [ ] 2. Thêm `gemini-auto` complexity router
- [ ] 3. Thêm `grok-auto` complexity router
- [ ] 4. Thêm `claude-auto` complexity router
- [ ] 5. Thêm `deepseek-auto` complexity router
- [ ] 6. Test routing: verify tier selection cho 5 providers

## Middleware Pre-routing
- [ ] 7. Implement quota % check trong api/chat.py
- [ ] 8. Implement model rewrite logic (>=60% → force SIMPLE)
- [ ] 9. Implement warning message injection
- [ ] 10. (Optional) Keyword scoring boost
- [ ] 11. (Optional) Vision/file attachment detection → boost

## Open WebUI Config
- [ ] 12. Ẩn individual model visibility (chỉ admin thấy)
- [ ] 13. Show 5 auto models cho user

## Testing
- [ ] 14. Test routing: 10 simple queries → flash
- [ ] 15. Test routing: 10 complex queries → pro
- [ ] 16. Test quota 60% → force flash
- [ ] 17. Test quota 100% → 403
- [ ] 18. Test warning message trong chat response

## Docs
- [ ] 19. Cập nhật user guide (model selection → auto)
- [ ] 20. Cập nhật architecture docs
- [ ] 21. Cập nhật API reference
