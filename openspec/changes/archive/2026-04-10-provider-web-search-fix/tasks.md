## 1. Middleware Refactoring

- [x] 1.1 Locate `_normalize_provider_params(model: str, body: dict) -> None:` in `llm-mw/api/chat.py`.
- [x] 1.2 Implement the dynamic logic: check if `"tools" in body and len(body["tools"]) > 0`.
- [x] 1.3 Add an `if/else` block inside the provider-native search logic: skip injecting `web_search_options` if `tools` are present. Add debug logging for skipped cases.
- [x] 1.4 Test the function by deploying the middleware container and verifying behavior with and without Code Interpreter enabled in OWUI.

## 2. Rollback Verification (Optional)
- [x] 2.1 Verify that the pre-change backup state of `chat.py` is safely tracked via Git in case user complains about missing Web Search.
