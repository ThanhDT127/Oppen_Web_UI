## Context

The current alerting system uses a JSON-based configuration (`alert_config.json`) which was previously modified manually. The goal is to expose this configuration through a secure admin-only UI in the dashboard.

## Goals / Non-Goals

**Goals:**
- Provide a responsive UI for managing system settings.
- Implement secure backend endpoints for reading and updating configuration.
- Ensure robust data persistence with fallback mechanisms (DB + File).
- Implement a connection testing utility for SMTP.

**Non-Goals:**
- Real-time notification of config changes to other running processes (config is reloaded per-check).
- Complex validation of SMTP server availability beyond a basic send test.

## Decisions

- **Admin Dashboard Integration**: Add a "Settings" tab to the existing modular dashboard. This keeps the admin UI consolidated.
- **RESTful Alert Config Endpoints**: Use `GET` and `PUT` on `/v1/_mw/admin/alerts/config`.
    - `PUT` will perform a deep merge to allow partial updates from the UI.
- **Dual Persistence**: Continue using the existing DB-first with file-fallback pattern in `core/alerting.py` to ensure settings are preserved even if the database is temporarily unavailable.
- **Frontend Modularization**: Create a separate `settings.js` module to handle settings-specific logic (fetching, form submission, SMTP testing) instead of bloating `main.js`.
- **CSS Grid Layout**: Use a grid layout for settings sections to ensure responsiveness and a modern feel.

## Risks / Trade-offs

- **[Risk] SMTP Password Exposure**: Storing passwords in plain text is a security risk.
    - **Mitigation**: The system uses a `password_env` reference. The UI only allows setting the environment variable name, not the password itself. The backend masks the password's existence in the `GET` response.
- **[Risk] Broken Frontend Module**: The `settings.js` file is currently missing despite being imported in `main.js`.
    - **Mitigation**: Reconstruct `settings.js` based on the forms and actions defined in `index.html`.
