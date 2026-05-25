## Context

The Open WebUI Middleware proxies chat completion requests to various providers via LiteLLM. Recently, we decided to leverage Provider-Native Web Search (specifically Google Grounding) to replace the legacy SearXNG-orchestrated RAG approach. Google's API strictly rejects any request that attempts to define custom "function declarations" while also passing the built-in `google_search` tool. Since Open WebUI bundles optional capabilities like "Code Interpreter" running off custom tools, these mechanisms conflict heavily. If both are enabled, the request surfaces an HTTP 400.

## Goals / Non-Goals

**Goals:**
- Eliminate the `INVALID_ARGUMENT` 400 error from Gemini models when Open WebUI sends conflicting tool architectures.
- Safely enable Google Search Grounding dynamically (only when user-defined tools are absent).
- Provide a clear fallback mechanism that prioritizes user-defined function calling over web search.
- Do not affect other provider configurations (like OpenAI/Claude).

**Non-Goals:**
- Rewrite the native Open WebUI frontend to disallow selection of both features simultaneously (Frontend is outside the scope of middleware changes).
- Solve complex multi-agent function invocation with Gemini (Focus solely on proxy param normalization).

## Decisions

- **Dynamic Stripping Logic:** Inside `_normalize_provider_params(model, body)`, we will inspect the exact payload `body`. We will check if `tools` array is present and length > 0.
  - *Rationale:* Instead of a blanket strip (which breaks Code Interpreter indefinitely for Gemini), we gracefully back off from injecting web search if tools are provided by the user via UI configuration. This makes the proxy intelligent.
- **Rollback Option:** As requested, a rollback stringent option is designed. The previous behavior (where 400 errors happen) or a hard-coded strip can be returned by simply `git checkout` to a specific historic commit or maintaining the original `if` snippet as a comment.

## Risks / Trade-offs

- **[Risk] Users wonder why Web Search doesn't work (silent failure):** If "Builtin Tools" is checked on UI by default, tools are always sent. The middleware strips web search silently to avoid crashes, preventing users from ever seeing a web search unless they explicitly uncheck "Builtin Tools" in UI.
  - *Mitigation:* Document this carefully. The user is aware and willing to train endpoint operators to disable "Builtin Tools" for Native Web Search.

## Rollback Plan (Phương án dự phòng)
- `git checkout HEAD -- llm-mw/api/chat.py` or manually reverting the changes to `_normalize_provider_params` logic. The previous un-dynamic fallback state allowed all `body["tools"]` to pass through completely unmodified.
