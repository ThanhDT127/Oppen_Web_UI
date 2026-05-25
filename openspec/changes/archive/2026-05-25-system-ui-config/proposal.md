## Why

The system currently lacks a centralized UI for administrators to configure critical system parameters such as SMTP settings, quota thresholds, API budgets, and notification channels. Previously, these were likely managed through manual file edits or environment variables, which is error-prone and inefficient for ongoing operations.

## What Changes

- **System Settings Tab**: A new "Settings" tab in the dashboard for centralized configuration.
- **SMTP Configuration**: Ability to enable/disable SMTP, configure host, port, credentials, and test the connection.
- **Quota Thresholds**: Configurable percentage thresholds (Info, Warning, Critical) for user quota alerts.
- **API Budgets**: Monthly USD budget limits for providers like OpenAI and Gemini.
- **Notification Channels**: Toggles for user email alerts, admin realtime emails, dashboard alerts, and daily digests.
- **Backend API Endpoints**: New endpoints for retrieving and updating alert configurations, and testing SMTP.
- **Robust Health Check**: Improved health check logic with better error reporting and logging for LiteLLM.

## Capabilities

### New Capabilities
- `system-settings-ui`: Provides a comprehensive interface for managing system-wide configurations including SMTP, quotas, and notifications.

### Modified Capabilities
- `auth-diagnostics`: Updated to include health check improvements and better logging.

## Impact

- **Frontend**: `index.html`, `dashboard.css`, `main.js`, and a new `settings.js` (to be completed/verified).
- **Backend**: `llm-mw/main.py` (route registration), `llm-mw/api/quota_status.py` (new config endpoints), `llm-mw/api/health.py` (enhanced health check).
- **Core**: `llm-mw/core/alerting.py` (config persistence and defaults).
- **Data**: `llm-mw/data/alert_config.json` (schema update).
