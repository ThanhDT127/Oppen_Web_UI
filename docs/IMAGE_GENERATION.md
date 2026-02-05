# Image Generation Configuration Guide

## Overview
This document explains how to configure OpenWebUI to use MDW (Middleware) for image generation with full control (auth, quota, audit, dashboard).

## Architecture Flow
```
OpenWebUI → MDW (llm-mw:5000) → LiteLLM (litellm:4000) → Providers (Gemini/OpenAI)
```

**Why route through MDW?**
- ✅ Centralized authentication (subkey)
- ✅ Per-user quota enforcement (limit_image_requests, cost_usd)
- ✅ Control-grade audit logging (purpose=image_gen, provider, fallback tracking)
- ✅ Dashboard metrics (image_calls, top users, cost breakdown)
- ✅ Abuse investigation (rid tracking, no noise)

---

## 1. MDW Configuration

### Supported Image Models
MDW exposes these models via `/v1/images/generations`:

| Model Name | Provider | Upstream Model | Default | Notes |
|------------|----------|----------------|---------|-------|
| `gemini-2.5-flash-image` | Gemini | `gemini/gemini-2.5-flash-image` | ✅ | Recommended (no org verification) |
| `gpt-image-1` | OpenAI | `openai/dall-e-3` | | Alias for DALL-E 3, requires verified org |

**Note:** `gpt-image-1` is an alias configured in `litellm_config.yaml`. For consistency, you can rename it to `dall-e-3` directly.

### Quota Schema (users.json)
```json
{
  "user_id": "admin",
  "subkey": "subkey_admin_123",
  "allowed_models": ["*"],  // Or specific: ["gemini-2.5-flash-image", "gpt-image-1"]
  "quota": {
    "period": "monthly",
    "limit_image_requests": 100,    // Max images per period (0 = unlimited)
    "limit_cost_usd": 10.0,         // Max cost per period
    "used_image_requests": 5,       // Current usage
    "used_cost_usd": 0.25
  }
}
```

**Quota Enforcement:**
- `limit_image_requests`: Hard limit on number of image generation requests
- `limit_cost_usd`: Cost-based limit (applies to all endpoints: chat + images)
- Period reset: Automatic based on `period` (weekly/monthly) and `timezone`

---

## 2. OpenWebUI Configuration

### Environment Variables

Add to your OpenWebUI environment (`.env` or docker-compose):

```bash
# Image Generation Engine
IMAGE_GENERATION_ENGINE=openai
IMAGES_OPENAI_API_BASE_URL=http://localhost:5000/v1
IMAGES_OPENAI_API_KEY=subkey_admin_123
IMAGE_GENERATION_MODEL=gemini-2.5-flash-image

# Default Settings
IMAGE_SIZE=1024x1024
IMAGE_STEPS=20
ENABLE_IMAGE_GENERATION=true
```

**Key Points:**
- `IMAGE_GENERATION_ENGINE=openai` - Use OpenAI-compatible API
- `IMAGES_OPENAI_API_BASE_URL` - Point to MDW (NOT LiteLLM directly!)
- `IMAGES_OPENAI_API_KEY` - Use your MDW subkey (NOT OpenAI key!)
- `IMAGE_GENERATION_MODEL` - Choose from supported models above

### Alternative: OpenWebUI Admin UI

1. Login as admin → Settings → Admin Settings → Images
2. Image Generation Engine: `OpenAI`
3. API Base URL: `http://localhost:5000/v1`
4. API Key: `subkey_admin_123`
5. Default Model: `gemini-2.5-flash-image`
6. Save changes

---

## 3. LiteLLM Configuration

### litellm_config.yaml
```yaml
model_list:
  # Gemini Image Model (Recommended)
  - model_name: gemini-2.5-flash-image
    litellm_params:
      model: gemini/gemini-2.5-flash-image
      api_key: os.environ/GEMINI_API_KEY

  # OpenAI Image Model (Requires verified org)
  # Note: gpt-image-1 is an alias for dall-e-3
  # You can use either name, but dall-e-3 is more standard
  - model_name: gpt-image-1  # or: dall-e-3
    litellm_params:
      model: openai/dall-e-3
      api_key: os.environ/OPENAI_API_KEY
```

**Provider Setup:**
- Gemini: Set `GEMINI_API_KEY` in environment
- OpenAI: Set `OPENAI_API_KEY` + ensure org is verified for DALL-E access

---

## 4. Audit Logging

### Audit Fields (audit.jsonl)
Image generation creates detailed audit entries:

```json
{
  "ts": "2026-01-07T10:30:00.000000+00:00",
  "rid": "mw_abc123def456",
  "user_id": "admin",
  "endpoint": "/v1/images/generations",
  "purpose": "image_gen",           // Filter images from other requests
  "model": "gemini-2.5-flash-image",
  "model_requested": null,          // Set if fallback occurred
  "provider": "gemini",             // gemini | openai | unknown
  "status": "ok",
  "status_code": 200,
  "upstream_status": 200,
  "latency_ms": 2345.6,
  "tokens_in": 0,
  "tokens_out": 0,
  "tokens_total": 0,
  "cost_usd": 0.002,
  "image_count": 1,
  "image_size": "1024x1024",
  "image_format": "url",            // url | b64_json
  "tts_chars": null,
  "stt_seconds": null,
  "video_count": null,
  "error_type": null,
  "error_message": null
}
```

**Key Audit Features:**
- `rid` always present (no "-" noise)
- `purpose=image_gen` for filtering
- `provider` tracking (gemini/openai)
- `model_requested` vs `model` tracks fallback (OpenAI → Gemini)
- `image_count`, `image_size`, `image_format` for capacity planning

---

## 5. Dashboard Metrics

### Summary Endpoint (`/v1/_mw/summary`)
```json
{
  "llm_calls_total": 150,
  "chat_calls": 120,
  "image_calls": 30,          // Breakdown by type
  "cost_total_usd": 2.45,
  "top_users": [
    {"user_id": "admin", "cost_usd": 1.50}
  ],
  "top_models": [
    {"model": "gemini-2.5-flash-image", "cost_usd": 0.60}
  ]
}
```

### Filtering Image Events
```bash
# Count image requests in last hour
curl -H "X-Admin-Key: $ADMIN_KEY" \
  "http://localhost:5000/v1/_mw/summary?minutes=60" | jq '.image_calls'

# Stream image events only
grep '"purpose":"image_gen"' logs/audit.jsonl | tail -f
```

---

## 6. Testing

### Test Image Generation via MDW
```bash
# Test with Gemini (default)
curl -X POST http://localhost:5000/v1/images/generations \
  -H "Authorization: Bearer subkey_admin_123" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-flash-image",
    "prompt": "A futuristic city at sunset",
    "n": 1,
    "size": "1024x1024",
    "response_format": "url"
  }'

# Test with OpenAI (if org verified)
curl -X POST http://localhost:5000/v1/images/generations \
  -H "Authorization: Bearer subkey_admin_123" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-image-1",
    "prompt": "A robot reading a book",
    "n": 1,
    "size": "1024x1024",
    "response_format": "url"
  }'
```

### Expected Response
```json
{
  "data": [
    {
      "url": "http://localhost:5000/v1/_mw/media/abc123.png",
      "revised_prompt": "..."
    }
  ],
  "_mw_user": "admin",
  "_mw_request_id": "mw_abc123def456",
  "_mw_added_cost_usd": 0.002
}
```

### Verify Quota Enforcement
```bash
# Set low limit in users.json
{
  "quota": {
    "limit_image_requests": 2,
    "used_image_requests": 0
  }
}

# Generate 3 images (3rd should fail with 403)
for i in {1..3}; do
  curl -X POST http://localhost:5000/v1/images/generations \
    -H "Authorization: Bearer subkey_admin_123" \
    -H "Content-Type: application/json" \
    -d '{"prompt":"test","n":1}'
done
```

---

## 7. Troubleshooting

### Problem: OpenWebUI not generating images
**Check:**
1. `IMAGE_GENERATION_ENGINE=openai` (not "automatic")
2. `IMAGES_OPENAI_API_BASE_URL=http://localhost:5000/v1` (not :4000)
3. `IMAGES_OPENAI_API_KEY` matches a valid subkey in users.json

### Problem: 403 Quota Exceeded
**Check:**
```bash
# View current quota
curl -H "X-Admin-Key: $ADMIN_KEY" http://localhost:5000/admin/usage | jq '.[] | select(.user_id=="admin") | .quota'

# Reset quota
curl -X POST -H "X-Admin-Key: $ADMIN_KEY" \
  http://localhost:5000/admin/reset \
  -d '{"user_id":"admin"}'
```

### Problem: OpenAI org verification error
**Solution:** Use Gemini model instead:
- In OpenWebUI: Change `IMAGE_GENERATION_MODEL=gemini-2.5-flash-image`
- MDW automatically falls back to Gemini if OpenAI fails verification

### Problem: Images not displaying
**Check:**
1. MDW media endpoint accessible: `http://localhost:5000/v1/_mw/media/test.png`
2. Check `logs/middleware.log` for media materialization errors
3. Verify `output_format` in response (should be "url", not b64_json)

---

## 8. Security Considerations

**DO:**
- ✅ Use unique subkeys per user
- ✅ Set `limit_image_requests` to prevent abuse
- ✅ Set `limit_cost_usd` for cost control
- ✅ Regularly audit logs: `grep image_gen logs/audit.jsonl`
- ✅ Monitor `top_users` in dashboard for anomalies

**DON'T:**
- ❌ Expose OpenAI/Gemini keys to OpenWebUI
- ❌ Allow OpenWebUI to call LiteLLM directly (bypass MDW)
- ❌ Set `allowed_models: ["*"]` for untrusted users
- ❌ Commit `.env`, `users.json`, or `logs/` to git

---

## 9. Example Configurations

### Development Setup
```bash
# start.sh
export IMAGE_GENERATION_ENGINE=openai
export IMAGES_OPENAI_API_BASE_URL=http://localhost:5000/v1
export IMAGES_OPENAI_API_KEY=subkey_admin_123
export IMAGE_GENERATION_MODEL=gemini-2.5-flash-image
export ENABLE_IMAGE_GENERATION=true

open-webui serve --port 3000
```

### Production Docker Compose
```yaml
services:
  openwebui:
    image: ghcr.io/open-webui/open-webui:main
    environment:
      - IMAGE_GENERATION_ENGINE=openai
      - IMAGES_OPENAI_API_BASE_URL=http://llm-mw:5000/v1
      - IMAGES_OPENAI_API_KEY=subkey_production_xyz
      - IMAGE_GENERATION_MODEL=gemini-2.5-flash-image
      - ENABLE_IMAGE_GENERATION=true
    depends_on:
      - llm-mw
      
  llm-mw:
    build: ./llm-mw
    ports:
      - "5000:5000"
    environment:
      - LITELLM_BASE=http://litellm:4000/v1
      - ADMIN_KEY=${ADMIN_KEY}
      - MW_SECRET=${MW_SECRET}
    depends_on:
      - litellm
      
  litellm:
    image: ghcr.io/berriai/litellm:main
    command: --config /app/litellm_config.yaml
    volumes:
      - ./litellm/litellm_config.yaml:/app/litellm_config.yaml
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
```

---

## 10. Reference Links

- [OpenAI Images API Spec](https://platform.openai.com/docs/api-reference/images)
- [OpenWebUI Image Generation Docs](https://docs.openwebui.com/features/image-generation)
- [LiteLLM Image Generation](https://docs.litellm.ai/docs/providers/openai#image-generation)
- [Gemini Image Generation](https://ai.google.dev/api/generate-content#images)

---

**Questions?** Check [DASHBOARD.md](./DASHBOARD.md) for dashboard usage or [ARCHITECTURE.md](./ARCHITECTURE.md) for system design.
