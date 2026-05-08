- [x] 1. Backup: snapshot current docker-compose.yml
- [x] 2. Pin LiteLLM image: `ghcr.io/berriai/litellm:v1.83.14-stable`
- [x] 3. `docker compose pull litellm` ✅
- [x] 4. `docker compose up -d litellm` ✅
- [x] 5. Verify version: `1.83.14` (from 1.81.8)
- [x] 6. Test: all 19 models loaded
- [x] 7. Test: MW health OK, litellm="ok", active_users=18
- [x] 8. Fix MW health endpoint (`/v1/health` → `/health/liveliness`)
- [x] 9. Verify cost header: `x-litellm-response-cost = 0.000215` ✅ (chat-gpt-5 test)
- [x] 10. Docs: deferred to next phase (minor)

## Bonus fixes discovered during upgrade
- [x] MW health check broken on LiteLLM v1.83+ (endpoint changed)
- [x] LITELLM_BASE includes /v1 but health endpoint is at root — fixed with .replace()
