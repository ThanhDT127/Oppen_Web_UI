## 1. Backend Verification & Audit

- [x] 1.1 Audit `llm-mw/api/quota_status.py` for correct implementation of `GET` and `PUT` endpoints.
- [x] 1.2 Verify `llm-mw/core/alerting.py` handles default configurations and persistence correctly.
- [x] 1.3 Verify `llm-mw/api/health.py` enhanced logic and logging.
- [x] 1.4 Test `/v1/_mw/admin/alerts/test-email` endpoint with manual trigger.

## 2. Frontend Implementation

- [x] 2.1 Implement `llm-mw/dashboard/js/settings.js` with the following functions:
    - `loadSettings()`: Fetch current config and populate forms.
    - `saveSMTP()`: Submit SMTP form.
    - `testSMTP()`: Trigger SMTP test endpoint.
    - `saveQuotaThresholds()`: Submit threshold form.
    - `saveBudgets()`: Submit budget form.
    - `saveNotifToggles()`: Submit notification toggles.
- [x] 2.2 Verify `llm-mw/dashboard/js/main.js` correctly exposes `window.settingsAPI`.
- [x] 2.3 Verify `llm-mw/dashboard/index.html` structure and tab switching for "Settings".
- [x] 2.4 Verify `llm-mw/dashboard/css/dashboard.css` styles for the settings tab.

## 3. Integration & Testing

- [x] 3.1 Verify end-to-end flow: changing a setting in UI -> backend update -> persistence in `alert_config.json`.
- [x] 3.2 Verify notification triggers respect the new thresholds configured via UI.
- [x] 3.3 Verify SMTP test email is received when triggered from UI.
