## ADDED Requirements

### Requirement: Auth diagnostic endpoint
The middleware SHALL provide a `GET /v1/_mw/auth-test` endpoint that validates the Bearer token and returns user authentication status without requiring access to any downstream service (LiteLLM).

#### Scenario: Valid active user subkey
- **WHEN** a request is made to `GET /v1/_mw/auth-test` with a valid Bearer token for an active user
- **THEN** the system SHALL return HTTP 200 with JSON body containing `user_id`, `active: true`, `allowed_models` list, and current `quota_status`

#### Scenario: Invalid subkey
- **WHEN** a request is made to `GET /v1/_mw/auth-test` with an invalid Bearer token (subkey not found in database)
- **THEN** the system SHALL return HTTP 401 with `{"detail": "Invalid sub-key", "error_code": "INVALID_SUBKEY"}`

#### Scenario: Inactive user subkey
- **WHEN** a request is made to `GET /v1/_mw/auth-test` with a valid Bearer token for an inactive (disabled) user
- **THEN** the system SHALL return HTTP 403 with `{"detail": "User account is deactivated", "error_code": "USER_INACTIVE"}`

#### Scenario: Missing authorization header
- **WHEN** a request is made to `GET /v1/_mw/auth-test` without an Authorization header or without Bearer prefix
- **THEN** the system SHALL return HTTP 401 with `{"detail": "Missing sub-key", "error_code": "MISSING_SUBKEY"}`

### Requirement: Enhanced authentication error responses
The `require_user()` function SHALL provide differentiated error codes in its HTTP error responses to distinguish between authentication failure modes.

#### Scenario: Missing Bearer token on any authenticated endpoint
- **WHEN** a request to an authenticated endpoint lacks the Authorization header
- **THEN** the system SHALL return HTTP 401 with detail containing "Missing sub-key"

#### Scenario: Invalid subkey on any authenticated endpoint
- **WHEN** a request to an authenticated endpoint contains a Bearer token that does not match any user in the database
- **THEN** the system SHALL return HTTP 401 with detail containing "Invalid sub-key" and log the failure with the first 8 characters of the subkey hash

#### Scenario: Inactive user on any authenticated endpoint
- **WHEN** a request to an authenticated endpoint contains a Bearer token for a deactivated user
- **THEN** the system SHALL return HTTP 403 with detail containing "User account is deactivated" and log the user_id

### Requirement: CORS configuration supports browser connections
The middleware CORS configuration SHALL accept browser requests originating from the Open WebUI public URL to enable Direct Connection verification from the Settings UI.

#### Scenario: Browser preflight from Open WebUI domain
- **WHEN** a browser sends an OPTIONS preflight request from origin `https://openwebui.example.com:51122`
- **THEN** the middleware SHALL respond with valid CORS headers allowing the request

#### Scenario: Internal Docker network requests
- **WHEN** Open WebUI server sends requests from internal Docker network without an Origin header
- **THEN** the middleware SHALL accept the request without CORS restrictions (server-to-server communication)

### Requirement: Authentication failure logging
The middleware SHALL log all authentication failures with sufficient detail for debugging, without exposing sensitive information.

#### Scenario: Log failed subkey lookup
- **WHEN** a subkey authentication lookup fails (no matching user found)
- **THEN** the system SHALL log a WARNING with the hashed subkey (first 8 chars), the request path, and the client IP address

#### Scenario: Log inactive user access attempt
- **WHEN** a deactivated user attempts to authenticate
- **THEN** the system SHALL log a WARNING with the user_id and request path
