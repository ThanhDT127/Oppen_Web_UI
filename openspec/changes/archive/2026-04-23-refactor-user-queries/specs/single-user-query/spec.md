## ADDED Requirements

### Requirement: Get user by ID
The system SHALL provide a function `get_user_by_id(user_id: str)` that retrieves a single user from the database using an indexed query (`SELECT ... WHERE user_id = %s`). The function SHALL return the user dict (same format as `load_users()` entries) or `None` if not found. When the database is unavailable, the function SHALL fallback to loading from JSON file and filtering.

#### Scenario: User exists in database
- **WHEN** `get_user_by_id("alice")` is called and user "alice" exists in `mw_users`
- **THEN** the function returns a dict with keys `user_id`, `subkey_hash`, `active`, `allowed_models`, `used_tokens`, `used_cost_usd`, `quota`, `alerts_sent` — populated from the single DB row

#### Scenario: User does not exist
- **WHEN** `get_user_by_id("nonexistent")` is called and no such user exists
- **THEN** the function returns `None`

#### Scenario: Database unavailable — file fallback
- **WHEN** the DB pool is not initialized and `get_user_by_id("alice")` is called
- **THEN** the function loads users from JSON file, filters by `user_id`, and returns the matching user or `None`

---

### Requirement: Atomic quota increment
The system SHALL provide a function `update_user_quota(user_id: str, add_tokens: int = 0, add_cost_usd: float = 0.0, add_image_requests: int = 0, add_stt_requests: int = 0)` that atomically increments usage counters in the database using `UPDATE ... SET field = field + %s WHERE user_id = %s`. The function SHALL also update the corresponding entry in the JSON backup file.

#### Scenario: Increment cost for existing user
- **WHEN** `update_user_quota("alice", add_cost_usd=0.05)` is called
- **THEN** the database executes `UPDATE mw_users SET quota = jsonb_set(quota, '{used_cost_usd}', ...) WHERE user_id = 'alice'` atomically, without loading other users
- **THEN** the JSON backup file is updated for only the "alice" entry

#### Scenario: Increment multiple fields
- **WHEN** `update_user_quota("alice", add_tokens=500, add_cost_usd=0.03)` is called
- **THEN** both `used_tokens` and `quota.used_cost_usd` are incremented in a single UPDATE statement

#### Scenario: User not found
- **WHEN** `update_user_quota("nonexistent", add_cost_usd=0.05)` is called
- **THEN** the function returns `False` (or raises appropriate error) indicating no rows updated

---

### Requirement: Update user alerts_sent field
The system SHALL provide a function `update_user_alerts(user_id: str, alerts_sent: dict)` that updates the `alerts_sent` JSON field for a single user without loading all users.

#### Scenario: Mark alert as sent
- **WHEN** `update_user_alerts("alice", {"alert_80": "2026-04-13T..."})` is called
- **THEN** only the `alerts_sent` column for user "alice" is updated in the database

---

### Requirement: Hot-path callers use single-user functions
All hot-path code (executed per every chat/embed request) SHALL use `get_user_by_id()` and `update_user_quota()` instead of `load_users()` + loop + `save_users()`.

#### Scenario: quota.py enforce_and_bump_quota
- **WHEN** `enforce_and_bump_quota("alice", add_cost_usd=0.05)` is called
- **THEN** it uses `get_user_by_id("alice")` to load only that user
- **THEN** it uses `update_user_quota("alice", add_cost_usd=0.05)` to persist changes

#### Scenario: chat.py _finalize_streaming
- **WHEN** `_finalize_streaming()` completes a streaming response for user "alice"
- **THEN** it uses `update_user_quota("alice", add_tokens=500, add_cost_usd=0.03)` instead of load-all → modify → save-all

#### Scenario: alerting.py check_and_send_alerts
- **WHEN** `check_and_send_alerts("alice")` runs after a request
- **THEN** it uses `get_user_by_id("alice")` to check quota thresholds
- **THEN** it uses `update_user_alerts("alice", alerts_sent)` to persist alert tracking

#### Scenario: embeddings.py quota bump
- **WHEN** embedding request finishes for user "alice"
- **THEN** it uses `update_user_quota("alice", add_tokens=100, add_cost_usd=0.01)` instead of load-all → modify → save-all

---

### Requirement: Backward compatibility
The existing `load_users()` and `save_users()` functions SHALL remain available and functional for admin-path callers (user listing, dashboard, bulk operations). No HTTP API endpoints SHALL change their request/response contract.

#### Scenario: Admin list users still works
- **WHEN** admin calls `GET /admin/users`
- **THEN** the endpoint still returns the full list of users (using `load_users()`)

#### Scenario: Dashboard stats still works
- **WHEN** admin accesses the dashboard usage tab
- **THEN** all charts and tables render correctly with data from the same DB
