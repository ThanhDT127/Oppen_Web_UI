# Smart Routing Per-Provider + Quota Auto Downgrade

## Lý do

- User thấy 16+ models trên UI → khó chọn, gây confusion
- Mỗi provider có 2-3 tier model → hệ thống nên tự chọn dựa trên complexity
- Khi quota đạt 60% → tự động chuyển sang model rẻ nhất để tiết kiệm

## Kiến trúc

```
User gửi request (model="openai-auto")
         │
         ▼
┌──────────────────────────────────┐
│  MIDDLEWARE (Pre-routing)        │
│                                  │
│  1. Check quota %                │
│     >=60% → force SIMPLE tier   │
│     >=100% → 403 Forbidden      │
│                                  │
│  2. Keyword boost (optional):   │
│     "phân tích", "so sánh",     │
│     "code", "debug" → +score    │
│                                  │
│  3. Vision/file detect → +score │
│                                  │
│  4. Pass to LiteLLM with        │
│     complexity hints             │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  LITELLM Complexity Router      │
│                                  │
│  model="openai-auto" → tiers:   │
│    SIMPLE → chat-gpt-5          │
│    MEDIUM → chat-gpt-5.2        │
│    COMPLEX → chat-gpt-5.4       │
│    REASONING → chat-gpt-5.4     │
└──────────────────────────────────┘
```

## UI — Option B (ẩn models cũ)

Trên Open WebUI, user chỉ thấy 5 "super models":

| UI Name | Model Name (internal) | Provider | Tiers |
|---------|----------------------|----------|-------|
| ✨ OpenAI | `openai-auto` | OpenAI | gpt-5 / 5.2 / 5.4 |
| ✨ Gemini | `gemini-auto` | Google | 2.5-flash / 3.1-flash-lite / 3.1-pro |
| ✨ Grok | `grok-auto` | xAI | 4.1-fast-lite / 4.1-fast / 4.20 |
| ✨ Claude | `claude-auto` | Anthropic | haiku-4.5 / sonnet-4.6 / opus-4.6 |
| ✨ DeepSeek | `deepseek-auto` | DeepSeek | v4-flash / v4-pro |

Admin vẫn có thể dùng model cụ thể nếu cần (không xóa, chỉ ẩn trên UI).

## Quota Auto Downgrade (60%)

```
0%────────60%────────────100%
│          │              │
│ FULL     │ BUDGET       │ BLOCKED
│ (4 tier) │ (flash only) │ (403)
```

- `< 60%`: Smart route bình thường (SIMPLE/MEDIUM/COMPLEX/REASONING)
- `>= 60%`: Force SIMPLE tier (cheapest model per provider)
- `>= 100%`: 403 Forbidden (giữ nguyên logic hiện tại)
- Inject warning message: "⚠️ Quota đạt X%, đã chuyển sang model tiết kiệm"

## Scope

### [MODIFY] [litellm_config.yaml](file:///C:/Code/openwebui_fetch/Oppen_Web_UI/litellm/litellm_config.yaml)
- Thêm 5 `auto_router/complexity_router` entries (1 per provider)
- Mỗi entry define 4 tiers mapping

### [MODIFY] [api/chat.py](file:///C:/Code/openwebui_fetch/Oppen_Web_UI/llm-mw/api/chat.py)
- Pre-routing logic: quota check → model rewrite
- Keyword scoring boost (Vietnamese + English)
- Vision/file attachment detection → boost complexity

### [MODIFY] Open WebUI Admin Settings
- Ẩn models cũ (individual), chỉ show 5 auto models
- Config trong Admin Panel → Models → Toggle visibility

### [MODIFY] Docs
- Cập nhật user guide, model list, architecture diagrams

## Prerequisites

- **upgrade-litellm** (cần Complexity Router improvements ≥1.83.x)
- **add-deepseek-openrouter** (DeepSeek models phải available trước)

## Rủi ro

> [!WARNING]
> Smart routing accuracy ~70-80% (heuristic-based). Câu ngắn nhưng phức tạp có thể bị route sai.
> Mitigation: User có thể feedback, admin có thể override.

## Verification

- Test routing accuracy: 10 câu simple → verify dùng flash
- Test routing accuracy: 10 câu complex → verify dùng pro
- Test quota downgrade: set user quota thấp → verify force flash tại 60%
- Test quota block: verify 403 tại 100%
- Test warning message injection
