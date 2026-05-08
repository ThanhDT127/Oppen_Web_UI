# API Features: Context Caching & Provider Search Cost Tracking

> **Phiên bản:** 2026-04-04  
> **Trạng thái:** Active  
> **Thay đổi liên quan:** `openspec/changes/enable-context-caching/`

---

## 1. Context Caching

### 1.1 Anthropic Prompt Caching (Active)

LiteLLM tự động inject `cache_control: {"type": "ephemeral"}` vào **system messages** cho Claude models.

**Cơ chế:**
```
Request flow: Open WebUI → Middleware → LiteLLM (inject cache_control) → Anthropic
```

- LiteLLM sử dụng `cache_control_injection_points` config để tự inject
- `drop_params: true` đảm bảo params tự động bị loại bỏ cho non-Anthropic models (OpenAI, xAI)
- TTL cache: **5 phút** (tự động renew khi truy cập)
- Minimum cacheable content: **1024 tokens**

**Chi phí:**

| STT | Loại               | Claude Opus 4.6 | Sonnet 4.6     | Haiku 4.5      |
| --- | ------------------ | --------------- | -------------- | -------------- |
| 01  | Input thường       | $5.00/MTok      | $3.00/MTok     | $1.00/MTok     |
| 02  | Cache write (+25%) | $6.25/MTok      | $3.75/MTok     | $1.25/MTok     |
| 03  | Cache read (-90%)  | **$0.50/MTok**  | **$0.30/MTok** | **$0.10/MTok** |

**Break-even:** Sau ~2 requests với cùng system prompt, chi phí caching đã có lời.

### 1.2 Gemini Implicit Caching (Automatic)

Google tự động cache content phổ biến cho Gemini 2.5+ models.

**Cơ chế:**
- **Không cần cấu hình** — hoạt động server-side
- Google tự detect khi requests có prefix giống nhau
- Giảm ~75% input token cost khi cache hit
- Không tính phí lưu trữ

**Models hỗ trợ:**
- `gemini-3.1-pro-preview` ✅
- `gemini-3.1-flash-lite-preview` ✅
- `gemini-2.5-flash` ✅

**Tối ưu cache hit rate:**
- Đặt content lớn (system prompt, RAG context) ở **ĐẦU** prompt
- Giữ system prompt nhất quán giữa requests
- Requests có tần suất cao → tỉ lệ cache hit cao hơn

### 1.3 Model Compatibility Matrix

> **Alias** = tên dùng khi gọi API (định nghĩa trong `litellm/litellm_config.yaml`).

| STT | Provider  | Alias (gọi API)              | Provider Model                      | Caching Type     | Cần config?                  | Trạng thái       |
| --- | --------- | ---------------------------- | ----------------------------------- | ---------------- | ---------------------------- | ---------------- |
| 01  | Anthropic | `chat-claude-opus-4.6`       | `anthropic/claude-opus-4-6`         | Prompt caching   | Đã bật (LiteLLM auto-inject) | ✅ Active         |
| 02  | Anthropic | `chat-claude-sonnet-4.6`     | `anthropic/claude-sonnet-4-6`       | Prompt caching   | Đã bật                       | ✅ Active         |
| 03  | Anthropic | `chat-claude-haiku-4.5`      | `anthropic/claude-haiku-4-5`        | Prompt caching   | Đã bật                       | ✅ Active         |
| 04  | Google    | `chat-gemini-3.1-pro`        | `gemini/gemini-3.1-pro-preview`     | Implicit caching | Không cần                    | ✅ Automatic      |
| 05  | Google    | `chat-gemini-3.1-flash-lite` | `gemini/gemini-3.1-flash-lite-preview` | Implicit caching | Không cần                 | ✅ Automatic      |
| 06  | Google    | `chat-gemini-2.5-flash`      | `gemini/gemini-2.5-flash`           | Implicit caching | Không cần                    | ✅ Automatic      |
| 07  | OpenAI    | `chat-gpt-5.4`               | `openai/gpt-5.4`                    | Server-side auto | Không kiểm soát              | ⚪ Not applicable |
| 08  | OpenAI    | `chat-gpt-5.2`               | `openai/gpt-5.2`                    | Server-side auto | Không kiểm soát              | ⚪ Not applicable |
| 09  | OpenAI    | `chat-gpt-5`                 | `openai/gpt-5`                      | Server-side auto | Không kiểm soát              | ⚪ Not applicable |
| 10  | xAI       | `chat-grok-4.20`             | `xai/grok-4.20-reasoning`           | Không hỗ trợ     | N/A                          | ❌ Not supported  |
| 11  | xAI       | `chat-grok-4.1-fast`         | `xai/grok-4-1-fast-reasoning`       | Không hỗ trợ     | N/A                          | ❌ Not supported  |
| 12  | xAI       | `chat-grok-4.1-fast-lite`    | `xai/grok-4-1-fast-non-reasoning`   | Không hỗ trợ     | N/A                          | ❌ Not supported  |

---

## 2. Provider Search Cost Tracking

### 2.1 Cơ chế hiện tại

Middleware tracking chi phí qua `x-litellm-response-cost` header:

```
Response flow: Provider → LiteLLM (tính cost + set header) → Middleware (đọc header) → Audit
```

**Code:** `services/litellm.py` → `get_cost_from_headers()` (dòng 13-32)  
đọc headers: `x-litellm-response-cost` hoặc `x-litellm-cost`

### 2.2 Provider Web Search — Chi phí đã tự động track

Khi model gọi provider web search (ví dụ Gemini Google Search Grounding), chi phí search tool invocation **đã bao gồm** trong `x-litellm-response-cost`:

| STT | Provider  | Tool name                 | Chi phí/1K calls    | Tracking             |
| --- | --------- | ------------------------- | ------------------- | -------------------- |
| 01  | OpenAI    | `web_search`              | $10                 | ✅ Qua LiteLLM header |
| 02  | Google    | `google_search` grounding | $35 (free 5K/tháng) | ✅ Qua LiteLLM header |
| 03  | xAI       | `web_search` + `x_search` | $5                  | ✅ Qua LiteLLM header |
| 04  | Anthropic | `web_search`              | $10                 | ✅ Qua LiteLLM header |

> **Lưu ý:** Hiện tại hệ thống dùng SearXNG (self-hosted, $0) cho web search. Provider search chỉ phát sinh nếu bật qua Open WebUI tools hoặc cấu hình riêng.

### 2.3 Cached Tokens Audit

Middleware ghi thêm 2 fields vào audit log:

| STT | Field                   | Ý nghĩa                            | Provider          |
| --- | ----------------------- | ---------------------------------- | ----------------- |
| 01  | `cached_tokens_created` | Tokens ghi vào cache lần đầu       | Anthropic         |
| 02  | `cached_tokens_read`    | Tokens đọc từ cache (giảm chi phí) | Anthropic, Gemini |

**Ví dụ audit line:**
```json
{
  "rid": "req_abc123",
  "model": "chat-claude-sonnet-4.6",
  "tokens_in": 5000,
  "tokens_out": 500,
  "cost_usd": 0.0165,
  "cached_tokens_created": 3500,
  "cached_tokens_read": 0
}
```

Request tiếp theo cùng conversation:
```json
{
  "rid": "req_def456",
  "model": "chat-claude-sonnet-4.6",
  "tokens_in": 5500,
  "tokens_out": 800,
  "cost_usd": 0.0039,
  "cached_tokens_created": 0,
  "cached_tokens_read": 3500
}
```
→ Chi phí giảm **76%** vì 3500 tokens được đọc từ cache ($0.30/MTok thay vì $3.00/MTok).

---

## 3. Cấu hình

### litellm_config.yaml

```yaml
litellm_settings:
  drop_params: true
  cache_control_injection_points:
    - location: "message"
      role: "system"
```

### Không cần thay đổi

- Middleware code forward body 1:1 (`json=body`) → caching params pass-through tự động
- `get_cost_from_headers()` đã track tổng cost (bao gồm cả search fees)
- SearXNG vẫn là primary search tool ($0 chi phí)
