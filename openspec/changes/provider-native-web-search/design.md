## Context

Hệ thống hiện tại sử dụng SearXNG (self-hosted meta search engine) để web search. Open WebUI orchestrate luồng search: tạo query → gọi SearXNG → inject kết quả → gửi model. Mỗi lần search tốn 2-3 API calls, tăng latency và chi phí token.

Cả 4 provider đều hỗ trợ native web search:
- **Gemini**: Google Search Grounding (5,000 free queries/tháng)
- **Claude**: `web_search` server-side tool (Anthropic xử lý hoàn toàn)
- **Grok**: `web_search` + `x_search` native tools
- **OpenAI**: `web_search` qua Responses API (LiteLLM auto-bridge từ `/chat/completions`)

LiteLLM cung cấp tham số **`web_search_options`** thống nhất cho tất cả provider qua `/chat/completions`. LiteLLM tự convert sang format riêng từng provider và auto-bridge sang `/responses` cho OpenAI.

Middleware (`chat.py`) đã có pattern `_normalize_provider_params()` để modify request body per-provider. Cũng đã có `_is_system_task_prompt()` để detect task nội bộ của Open WebUI.

## Goals / Non-Goals

**Goals:**
- Model tự search bằng provider's native search khi cần thông tin realtime
- Chỉ inject web search cho request chat thường, không inject cho system tasks
- Không ảnh hưởng luồng hiện tại (title, tags, follow-up, search query generation)
- Không cần sửa LiteLLM config hay Open WebUI code

**Non-Goals:**
- Fallback SearXNG khi provider search fail (tạm chưa implement)
- Custom search filters per model (domain filtering, location)
- Tắt SearXNG container (giữ nguyên, có thể bật lại)
- Thay đổi response format hiển thị cho user

## Decisions

### Decision 1: Inject ở Middleware, không phải LiteLLM config

**Chọn:** Middleware inject `web_search_options` vào body trong `_normalize_provider_params()`

**Lý do:**
- LiteLLM config `web_search_options: {}` áp dụng cho **TẤT CẢ** requests → system tasks (title, tags) cũng bị search → lãng phí
- Middleware có `_is_system_task_prompt()` → có thể detect và skip system tasks
- Cùng pattern đã có sẵn (GPT-5 max_tokens normalization, Claude temp clamping, Grok size removal)

**Alternatives considered:**
- *LiteLLM config per model*: Đơn giản nhưng không phân biệt được chat vs system task
- *Open WebUI Function Calling = Native*: Phụ thuộc OWUI version (v0.7.2), không chắc hoạt động đúng

### Decision 2: Dùng `web_search_options` thống nhất cho cả 4 provider

**Chọn:** Inject `web_search_options: {"search_context_size": "medium"}` cho tất cả model

**Lý do:**
- LiteLLM tự convert sang format riêng từng provider
- OpenAI: LiteLLM auto-bridge `/chat/completions` → `/responses` + `web_search` tool
- Gemini: Convert thành Google Search Grounding
- Claude: Convert thành `web_search` server-side tool
- Grok: Pass-through `web_search`
- 1 param duy nhất, không cần logic riêng per-provider

**`search_context_size: "medium"`** là default balance giữa quality và cost. Options: "low" (ít context, rẻ), "medium" (balanced), "high" (nhiều context, đắt).

### Decision 3: Tắt OWUI Web Search qua Admin Panel

**Chọn:** Tắt "Default Features > Web Search" per model trong Admin UI

**Lý do:**
- Nếu vẫn bật, OWUI orchestrate SearXNG song song → double search
- OWUI search query generation vẫn trigger system task → lãng phí 1 API call
- Tắt trong UI, không cần sửa `docker-compose.yml` (giữ `ENABLE_RAG_WEB_SEARCH=true` để có thể rollback)

### Decision 4: Detect system tasks bằng `_is_system_task_prompt()` hiện tại

**Chọn:** Tận dụng hàm `_is_system_task_prompt()` đã có để skip injection

**Lý do:**
- Hàm đã detect 4 loại task: title, tags, follow-up, search query generation
- Pattern matching qua `_TASK_PATTERNS` — ổn định, đã test trong production
- Không cần logic mới

## Risks / Trade-offs

- **[Provider search cost]** → Provider có thể tính phí search riêng ngoài token cost. Mitigation: Monitor qua dashboard, Gemini có 5K free queries/tháng.

- **[Model tự quyết search timing]** → Model có thể search khi không cần thiết (ví dụ: hỏi toán, viết code). Mitigation: Provider's search classifier thường chính xác; `search_context_size: "medium"` giữ chi phí vừa phải.

- **[LiteLLM auto-bridge cho OpenAI]** → Feature mới, có thể chưa ổn định 100%. Mitigation: `drop_params: true` đã set → nếu bridge fail, param bị drop silently, model trả lời bình thường không search (degraded gracefully).

- **[System task detection miss]** → Nếu OWUI thêm task pattern mới trong bản update, `_is_system_task_prompt()` có thể miss → task bị search. Mitigation: Impact thấp (chỉ tốn thêm search cost), fix đơn giản (thêm pattern).

- **[SearXNG vẫn chạy nhưng không dùng]** → Tốn resource container. Mitigation: Resource rất nhỏ, giữ để có thể rollback nhanh.
