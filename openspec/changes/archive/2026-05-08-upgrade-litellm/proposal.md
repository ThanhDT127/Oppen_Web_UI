# Upgrade LiteLLM 1.81.8 → 1.84.0

## Lý do

- **CVE-2026-42208**: SQL injection trong API key verification (ảnh hưởng v1.81.16–v1.83.6). Bản 1.81.8 hiện tại **có thể bị ảnh hưởng**
- DeepSeek V4 support cần ≥1.83.x
- Complexity Router cải thiện (cần cho smart-routing-per-provider)
- GPT-5.5 day-0 support (v1.83.14)

## Scope

- Pin Docker image tag từ `main-latest` → `1.84.0`
- Test tất cả model routes (chat, image, embedding, audio)
- Verify cost tracking headers vẫn hoạt động
- Cập nhật docs

## Rủi ro

> [!WARNING]
> **Supply chain attack**: PyPI bản 1.82.7/1.82.8 bị compromise (Mar 2026).
> Ta dùng Docker image (ghcr.io) nên **KHÔNG bị ảnh hưởng**, nhưng KHÔNG được dùng `pip install litellm==1.82.7`.

- Breaking changes nhỏ trong versioning format (dropped `-stable`/`-nightly` suffixes)
- Config format không đổi — `litellm_config.yaml` giữ nguyên

## Thay đổi

### [MODIFY] [docker-compose.yml](file:///C:/Code/openwebui_fetch/Oppen_Web_UI/docker-compose.yml)
- `image: ghcr.io/berriai/litellm:main-latest` → `image: ghcr.io/berriai/litellm:1.84.0`

### [MODIFY] Docs
- Cập nhật version reference trong docs nếu có

## Verification

- `docker exec openwebui-litellm pip show litellm` → Version: 1.84.0
- Test chat completion qua tất cả providers
- Test image generation
- Test embedding
- Verify `x-litellm-response-cost` header vẫn trả về
