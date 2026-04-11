## Why

Google Gemini models (specifically Gemini 2.5) strictly reject HTTP requests where both a built-in search tool (`google_search`) and a custom function calling tool (`tools: [...]`) are provided simultaneously. The Open WebUI currently sends the custom `tools` param if features like "Code Interpreter" or "Builtin Tools" are enabled. When our middleware subsequently injects the `web_search_options` for Provider-Native Web Search, it triggers an HTTP 400 Bad Request (`INVALID_ARGUMENT`) from Gemini. We need to implement a dynamic tool stripping logic to gracefully handle this conflict while prioritizing Function Calling over Web Search if the user explicitly chose to use tools.

## What Changes

- Implement dynamic tool detection in the `_normalize_provider_params` function inside `llm-mw/api/chat.py`.
- If `web_search_options` is about to be injected, check if `body.get("tools")` exists and is non-empty.
- **Rule:** If `tools` exist, **skip** injecting `web_search_options` to allow the user's custom tools to function properly and prevent the API conflict.
- **Rule:** If `tools` is missing or empty, **inject** `web_search_options` to enable blazing-fast, provider-native web search grounded via Google Search Engine.
- Provide a clear Rollback/Backup Plan in case the dynamic logic causes unintended side-effects.

## Capabilities

### New Capabilities
- `provider-dynamic-tools-strip`: The capability to conditionally strip native web search injections from the proxy request when custom tools are already present in the user prompt, avoiding conflicting tool behaviors for Gemini API.

### Modified Capabilities

- `<existing-name>`: 

## Impact

- Middleware Chat proxy (`llm-mw/api/chat.py`).
- No impact on OpenAI, Grok, or Claude models (they generally tolerate mixed tool requests, but skipping injection when tools exist is a safe universal default).
- For users to explicitly use Native Web Search on Gemini, they must now un-check "Builtin Tools" in the Open WebUI Model Settings.

## Rollback Plan (Phương án backup rollback)
**Trigger to rollback:** If user complains that Web Search is completely broken across all models or `chat.py` fails to route properly.
**Action:** Revert changes in `llm-mw/api/chat.py` around the `web_search_options` injection back to its state prior to this feature, effectively restoring the naive injection. A simple `git checkout` of the specific file or maintaining a commented-out legacy block will be used.
