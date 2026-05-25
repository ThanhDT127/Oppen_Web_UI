## ADDED Requirements

### Requirement: Dynamic Tools Stripping for Native Search
The middleware SHALL dynamically evaluate the presence of custom tools before injecting native web search parameters, avoiding HTTP 400 errors from strict providers like Gemini.

#### Scenario: Request contains custom tools
- **WHEN** the incoming HTTP request body has a `tools` key with a non-empty array
- **THEN** the middleware SHALL skip injecting `web_search_options` for that request

#### Scenario: Request has no custom tools
- **WHEN** the incoming HTTP request body does not have a `tools` key (or it is empty)
- **THEN** the middleware SHALL inject `"web_search_options": {"search_context_size": "medium"}` into the request payload

#### Scenario: Model is excluded via Task checks
- **WHEN** the incoming HTTP request represents a system task (like Title generation) or an image model
- **THEN** the middleware SHALL NOT inject `web_search_options` regardless of empty toolsets
