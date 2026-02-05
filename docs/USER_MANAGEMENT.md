# User Management Guide

## Overview

The LLM Middleware now includes comprehensive user management with RBAC (Role-Based Access Control), key lifecycle management, and audit trail for administrative operations.

## User Schema

Each user in `llm-mw/data/users.json` has the following structure:

```json
{
  "user_id": "admin",
  "role": "admin",  // New: admin | manager | user
  "subkey_hash": "...",  // Hash only, plaintext never stored long-term
  "active": true,
  "allowed_models": ["*"],
  "quota": {
    "period": "monthly",
    "timezone": "Asia/Bangkok",
    "limit_tokens": 0,
    "limit_cost_usd": 0,
    "limit_image_requests": 0,
    "used_tokens": 0,
    "used_cost_usd": 0.0,
    "used_image_requests": 0
  }
}
```

### Roles

- **admin**: Full access to all admin endpoints (user management)
- **manager**: (Future) Read-only admin access
- **user**: Standard API user with quota limits

## Migration

To add RBAC to existing users.json:

```bash
python scripts/migrate_users_rbac.py
```

This script:
1. Backs up current users.json
2. Adds 'role' field (first user gets 'admin', others get 'user')
3. Validates and saves

## Admin API Endpoints

All endpoints require admin authentication (cookie session or X-Admin-Key header).

### List Users

```bash
GET /v1/_mw/admin/users
```

**Response:**
```json
{
  "users": [
    {
      "user_id": "admin",
      "role": "admin",
      "active": true,
      "allowed_models": ["*"],
      "quota": {...}
    }
  ],
  "total": 2
}
```

**Note:** Keys and hashes are scrubbed from response.

---

### Create User

```bash
POST /v1/_mw/admin/users
Content-Type: application/json

{
  "user_id": "new_user",
  "role": "user",
  "allowed_models": ["gemini-2.5-flash", "gpt-4o-mini"],
  "limit_tokens": 100000,
  "limit_cost_usd": 5.0,
  "limit_image_requests": 50,
  "period": "monthly",
  "timezone": "Asia/Bangkok"
}
```

**Response:**
```json
{
  "message": "User created successfully",
  "user": {...},
  "subkey": "sk_abc123...",  // ⚠️ Shown ONLY once!
  "warning": "Save this subkey securely. It will not be shown again."
}
```

**⚠️ CRITICAL:** Copy the `subkey` immediately. It cannot be retrieved later.

---

### Update User

```bash
PATCH /v1/_mw/admin/users/{user_id}
Content-Type: application/json

{
  "role": "manager",
  "active": true,
  "allowed_models": ["*"],
  "limit_cost_usd": 10.0
}
```

**Response:**
```json
{
  "message": "User updated successfully",
  "user": {...},
  "changes": {
    "role": "manager",
    "limit_cost_usd": 10.0
  }
}
```

**Fields:** All fields are optional. Only provided fields will be updated.

---

### Rotate Key

```bash
POST /v1/_mw/admin/users/{user_id}/rotate_key
```

**Response:**
```json
{
  "message": "Key rotated successfully",
  "user_id": "user1",
  "subkey": "sk_new_key_xyz...",  // ⚠️ Shown ONLY once!
  "warning": "Save this subkey securely. The old key is now invalid."
}
```

**⚠️ IMPORTANT:** The old key is immediately invalidated.

---

### Disable User

```bash
POST /v1/_mw/admin/users/{user_id}/disable
```

**Response:**
```json
{
  "message": "User user1 disabled successfully",
  "user": {...}
}
```

Disabled users cannot authenticate (403 Forbidden).

---

### Enable User

```bash
POST /v1/_mw/admin/users/{user_id}/enable
```

**Response:**
```json
{
  "message": "User user1 enabled successfully",
  "user": {...}
}
```

---

### Admin Audit Trail

```bash
GET /v1/_mw/admin/audit?minutes=1440
```

**Response:**
```json
{
  "audit_trail": [
    {
      "ts": "2026-01-07T16:19:45.123456+00:00",
      "actor": "admin_session",
      "action": "create_user",
      "target_user": "new_user",
      "changes": {"role": "user", "allowed_models": ["*"]},
      "status": "ok",
      "ip": "127.0.0.1",
      "user_agent": "curl/7.68.0"
    }
  ],
  "total": 10
}
```

**Query params:**
- `minutes`: Time window (default: 1440 = 24 hours)
- `start` / `end`: ISO datetime strings for custom range

## Audit Log File

Admin operations are logged to `logs/admin_audit.jsonl` (rotating, 20MB max, 5 backups).

Each entry includes:
- `ts`: Timestamp (ISO UTC)
- `actor`: Admin session identifier
- `action`: Operation performed (create_user, update_user, rotate_key, disable_user, enable_user)
- `target_user`: User ID affected
- `changes`: Summary of changes made
- `status`: ok | error
- `ip`: Client IP address
- `user_agent`: Client user agent

## Security Best Practices

1. **Key Storage:**
   - Never log or display subkeys except on create/rotate
   - Only hashes (HMAC-SHA256) are stored in users.json
   - Use environment variable `MW_SECRET` for hash salt

2. **Key Rotation:**
   - Rotate keys periodically (e.g., every 90 days)
   - Rotate immediately if key is compromised
   - Old key is invalidated instantly

3. **RBAC:**
   - Assign 'admin' role sparingly
   - Use 'user' role for API consumers
   - Future: 'manager' role for read-only admin access

4. **Audit Trail:**
   - Review admin_audit.jsonl regularly
   - Monitor for unauthorized admin operations
   - Correlate with IP addresses for investigation

## Examples

### Create User via curl

```bash
curl -X POST http://localhost:5000/v1/_mw/admin/users \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "role": "user",
    "allowed_models": ["gemini-2.5-flash"],
    "limit_cost_usd": 5.0,
    "period": "monthly"
  }'
```

### Rotate Key via curl

```bash
curl -X POST http://localhost:5000/v1/_mw/admin/users/alice/rotate_key \
  -H "X-Admin-Key: $ADMIN_KEY"
```

### Disable User via curl

```bash
curl -X POST http://localhost:5000/v1/_mw/admin/users/alice/disable \
  -H "X-Admin-Key: $ADMIN_KEY"
```

## Troubleshooting

### Error: "Invalid admin key or session"

**Solution:** 
- For curl: Use `-H "X-Admin-Key: $ADMIN_KEY"`
- For dashboard: Login with admin key to get session cookie

### Error: "User already exists"

**Solution:** User IDs must be unique. Choose a different user_id or update existing user.

### Key lost, can't authenticate

**Solution:** Admin must rotate the key and provide new one. Old key cannot be recovered.

### Audit log not found

**Solution:** Admin audit log is created on first admin operation. File path: `logs/admin_audit.jsonl`
