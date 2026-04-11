## ADDED Requirements

### Requirement: Non-streaming quota warning injection
The middleware SHALL append a quota warning message to the end of non-streaming chat responses when user quota usage exceeds configured thresholds.

#### Scenario: User at 80% quota receives warning
- **WHEN** a user with ≥80% and <95% quota usage receives a non-streaming chat response
- **THEN** the system SHALL append a `\n\n---\n⚠️ Bạn đã sử dụng X% quota tháng này (còn ~$Y.YY).` to the assistant message content

#### Scenario: User at 95% quota receives critical warning  
- **WHEN** a user with ≥95% quota usage receives a non-streaming chat response
- **THEN** the system SHALL append a `\n\n---\n🔴 **Cảnh báo quota**: Bạn đã sử dụng X% quota (còn ~$Y.YY). Vui lòng liên hệ admin nếu cần tăng quota.` to the assistant message content

#### Scenario: User with unlimited quota receives no warning
- **WHEN** a user with no cost limit (limit_cost_usd = 0) receives a chat response
- **THEN** the system SHALL NOT append any quota warning

### Requirement: Streaming quota warning injection
The middleware SHALL inject a quota warning as additional SSE chunks at the end of streaming chat responses when user quota exceeds thresholds.

#### Scenario: Post-stream quota warning
- **WHEN** a streaming response completes and the user's updated quota usage ≥80%
- **THEN** the system SHALL yield additional SSE data chunks containing the quota warning text before the `[DONE]` marker

#### Scenario: Pre-stream quota block for exhausted quota
- **WHEN** a user has ≥100% quota usage BEFORE a streaming request starts
- **THEN** the system SHALL return HTTP 403 with a descriptive JSON error instead of starting the stream

### Requirement: Descriptive quota exceeded error
The middleware SHALL return a descriptive, user-friendly error message when quota is exceeded.

#### Scenario: Cost quota exceeded returns descriptive message
- **WHEN** a request is rejected because cost quota is exceeded
- **THEN** the system SHALL return HTTP 403 with JSON body containing `detail` field with Vietnamese message: "⚠️ Bạn đã hết quota tháng này (đã dùng $X.XX/$Y.YY). Vui lòng liên hệ admin để được nâng hạn mức."

#### Scenario: Token quota exceeded returns descriptive message
- **WHEN** a request is rejected because token quota is exceeded
- **THEN** the system SHALL return HTTP 403 with JSON body containing `detail` field with a descriptive token usage message

### Requirement: Filter Function user_id mapping fix
The `quota_alert_filter.py` SHALL correctly identify the middleware user_id from Open WebUI user context.

#### Scenario: Filter finds user by name
- **WHEN** the Open WebUI `__user__["name"]` matches a middleware user_id
- **THEN** the filter SHALL display quota warning from that user's status

#### Scenario: Filter handles quota exceeded gracefully
- **WHEN** the quota API returns that user is at 100% and remaining is $0
- **THEN** the filter SHALL display a critical warning indicating quota is exhausted
