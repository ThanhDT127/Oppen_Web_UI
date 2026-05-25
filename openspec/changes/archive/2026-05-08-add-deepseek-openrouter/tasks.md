## Prerequisites
- [x] 0. Change `upgrade-litellm` hoàn thành ✅ (1.81.8 → 1.83.14)

## Config
- [x] 1. Thêm `OPENROUTER_API_KEY` vào `.env` (placeholder)
- [x] 2. Thêm `OPENROUTER_API_KEY` env var vào `docker-compose.yml`
- [x] 3. Thêm 2 model entries vào `litellm/litellm_config.yaml`
- [x] 4. Thêm pricing vào `llm-mw/prices.json` (Flash $0.14/$0.28, Pro $1.74/$3.48)
- [x] 5. Thêm `deepseek` + `xai` + `anthropic` provider budgets vào `alert_config.json`

## Deploy
- [ ] 6. Chờ user cung cấp OPENROUTER_API_KEY thật → `docker compose up -d litellm`
- [ ] 7-10. Test chat (chờ API key)

## Docs
- [x] 11. Cập nhật `10-user-guide-vi.md` — 14 chat models / 5 providers
- [x] 12. Cập nhật `11-system-overview-report.md` — 5 providers (21 models)
- [x] 13. Cập nhật `01-tong-quan-he-thong.md` — 21 models / 5 providers
- [x] 14. Format tables aligned

## Note
> Deploy + test tasks (6-10) chờ user cung cấp OpenRouter API key.
> Khi có key: replace placeholder trong .env → docker compose up -d litellm → test.
