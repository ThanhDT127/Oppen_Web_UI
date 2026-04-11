## ADDED Requirements

### Requirement: Middleware injects web_search_options for chat requests
The middleware SHALL inject `web_search_options` parameter into the request body for all chat completion requests that are NOT system task prompts. The injected value SHALL be `{"search_context_size": "medium"}`.

#### Scenario: Normal chat request gets web search injected
- **WHEN** a user sends a chat message (e.g., "Giá vàng hôm nay?")
- **THEN** middleware MUST add `web_search_options: {"search_context_size": "medium"}` to the request body before forwarding to LiteLLM

#### Scenario: System task prompt is excluded from web search injection
- **WHEN** Open WebUI sends a system task prompt (title generation, tag generation, follow-up suggestions, or search query generation)
- **THEN** middleware MUST NOT inject `web_search_options` into the request body

#### Scenario: Request already has web_search_options
- **WHEN** the incoming request body already contains a `web_search_options` field
- **THEN** middleware MUST NOT overwrite the existing value

### Requirement: Web search works for all 4 providers
The middleware SHALL inject `web_search_options` regardless of the model/provider. LiteLLM handles the per-provider conversion automatically.

#### Scenario: Gemini model receives web search
- **WHEN** request is for a Gemini model (e.g., `chat-gemini-2.5-flash`)
- **THEN** LiteLLM SHALL convert `web_search_options` to Google Search Grounding format and the model SHALL be able to search the web

#### Scenario: Claude model receives web search
- **WHEN** request is for a Claude model (e.g., `chat-claude-haiku-4.5`)
- **THEN** LiteLLM SHALL convert `web_search_options` to Anthropic `web_search` server-side tool and the model SHALL be able to search the web

#### Scenario: Grok model receives web search
- **WHEN** request is for a Grok model (e.g., `chat-grok-4.1-fast`)
- **THEN** LiteLLM SHALL pass through `web_search_options` as xAI native web search and the model SHALL be able to search the web

#### Scenario: OpenAI model receives web search
- **WHEN** request is for an OpenAI model (e.g., `chat-gpt-5`)
- **THEN** LiteLLM SHALL auto-bridge the request to OpenAI's `/responses` endpoint with `web_search` tool and the model SHALL be able to search the web

### Requirement: Image generation models are excluded
The middleware SHALL NOT inject `web_search_options` for image generation models, as they do not support web search.

#### Scenario: Image model request is not modified
- **WHEN** request is for an image generation model (e.g., `img-gpt-1.5`, `img-gemini-3.1-flash`)
- **THEN** middleware MUST NOT inject `web_search_options` into the request body

### Requirement: No impact on existing system flows
The change MUST NOT alter the behavior of any existing middleware functionality including quota tracking, cost calculation, streaming, audit logging, and provider parameter normalization.

#### Scenario: Quota and cost tracking unaffected
- **WHEN** a chat request with web search is processed
- **THEN** token usage, cost calculation, and quota enforcement SHALL continue to work as before

#### Scenario: Streaming responses work normally
- **WHEN** a streaming chat request with web search is processed
- **THEN** SSE streaming, quota warning injection, and [DONE] marker handling SHALL work as before
