## ADDED Requirements

### Requirement: Media Files Accessible via HTTPS from Any Device
Tất cả media files (ảnh sinh ra từ AI) SHALL có thể truy cập được qua HTTPS từ bất kỳ thiết bị/trình duyệt nào, không chỉ từ máy tạo request.

#### Scenario: Image accessible from different machine
- **WHEN** user A tạo ảnh bằng model image generation trên máy X
- **AND** user A (hoặc user B cùng tài khoản) truy cập chat history từ máy Y
- **THEN** ảnh MUST hiển thị đúng trên máy Y qua HTTPS URL

#### Scenario: Mixed content prevention
- **WHEN** browser truy cập Open WebUI qua HTTPS (`https://openwebui.example.com:51122`)
- **AND** ảnh được serve từ middleware
- **THEN** ảnh URL MUST sử dụng HTTPS protocol (không có mixed HTTP/HTTPS content)

### Requirement: Nginx Media Caching
Nginx SHALL cache media files để giảm tải cho middleware và cải thiện response time.

#### Scenario: First media request
- **WHEN** browser request một media file lần đầu
- **THEN** Nginx SHALL proxy request đến middleware, cache response, và trả về với `Cache-Control: public, max-age=86400, immutable`

#### Scenario: Subsequent media requests
- **WHEN** browser request cùng media file (same UUID filename)
- **AND** file đã có trong Nginx cache
- **THEN** Nginx SHALL serve từ cache mà không proxy đến middleware, response header MUST có `X-Cache-Status: HIT`

### Requirement: CORS Headers for Media Files
Media endpoint SHALL include CORS headers cho phép cross-origin access.

#### Scenario: Cross-origin image request
- **WHEN** browser từ domain khác request media file
- **THEN** response MUST include `Access-Control-Allow-Origin: *` header
- **AND** response MUST include `Access-Control-Allow-Methods: GET, HEAD, OPTIONS`

#### Scenario: Preflight CORS request
- **WHEN** browser gửi OPTIONS preflight request đến media endpoint
- **THEN** server MUST respond 204 với proper CORS headers
- **AND** response MUST include `Access-Control-Max-Age: 86400`

### Requirement: Correct Content-Type for Media Files
Media endpoint SHALL trả về đúng Content-Type header dựa trên file extension.

#### Scenario: PNG image served
- **WHEN** client request file có extension `.png`
- **THEN** response MUST có Content-Type `image/png`

#### Scenario: JPEG image served
- **WHEN** client request file có extension `.jpg` hoặc `.jpeg`
- **THEN** response MUST có Content-Type `image/jpeg`

#### Scenario: WebP image served
- **WHEN** client request file có extension `.webp`
- **THEN** response MUST có Content-Type `image/webp`
