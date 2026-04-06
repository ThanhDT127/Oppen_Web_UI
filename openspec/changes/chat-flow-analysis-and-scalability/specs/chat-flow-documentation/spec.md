## ADDED Requirements

### Requirement: Chat Flow Sequence Documentation
Hệ thống SHALL có tài liệu chi tiết mô tả luồng chat end-to-end dưới dạng sequence diagram, bao gồm tất cả các thành phần: Browser, Nginx, Open WebUI, Middleware, LiteLLM, và Provider APIs.

#### Scenario: Complete chat flow documentation
- **WHEN** developer hoặc admin cần hiểu luồng chat
- **THEN** tài liệu MUST bao gồm sequence diagram cho: (1) streaming chat request, (2) non-streaming chat request, (3) image generation request, với tất cả error paths được ghi nhận

#### Scenario: Provider-specific flow documentation
- **WHEN** developer cần debug lỗi với một provider cụ thể
- **THEN** tài liệu MUST mô tả khác biệt trong request/response handling cho mỗi provider: OpenAI, Gemini, xAI Grok, Anthropic Claude

### Requirement: Cross-Model Error Path Documentation
Hệ thống SHALL tài liệu hóa tất cả error paths khi chuyển đổi giữa các mô hình, bao gồm parameter incompatibilities và response format differences.

#### Scenario: Parameter compatibility matrix
- **WHEN** admin cần kiểm tra model nào hỗ trợ parameter nào
- **THEN** tài liệu MUST có bảng compatibility matrix ghi rõ: `max_tokens` vs `max_completion_tokens`, `size` parameter support, `stream_options` support, và response format cho tất cả 12 chat models + 6 image models

#### Scenario: Error recovery documentation
- **WHEN** chat request fail với một model
- **THEN** tài liệu MUST mô tả error flow: HTTP status codes trả về, retry behavior (LiteLLM `num_retries: 2`), và user-facing error messages

### Requirement: Provider Parameter Normalization
Middleware SHALL tự động normalize parameters trước khi gửi request đến LiteLLM dựa trên provider type.

#### Scenario: GPT-5 max_tokens normalization
- **WHEN** user gửi chat request đến model `gpt-5*` với `max_tokens` parameter
- **THEN** middleware MUST convert `max_tokens` thành `max_completion_tokens` và remove `max_tokens` khỏi request body

#### Scenario: xAI image parameter cleanup
- **WHEN** user gửi image generation request đến model `img-grok-*`
- **THEN** middleware MUST NOT include `size` parameter trong request body (xAI sử dụng `aspect_ratio` thay thế)

#### Scenario: Unknown provider parameters
- **WHEN** request body chứa parameter không được provider hỗ trợ
- **THEN** LiteLLM `drop_params: true` setting SHALL silently drop unsupported parameters thay vì trả error
