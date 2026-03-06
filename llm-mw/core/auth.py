"""
Authentication and user management for LLM middleware.
Data stored in PostgreSQL (mw_users table), with JSON file fallback.
"""

import os
import json
import hmac
import hashlib
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, Request
from threading import Lock

from config import USERS_FILE, MW_SECRET

# Thread lock for user operations (backward compat)
_lock = Lock()


def hash_subkey(subkey: str) -> str:
    """
    Generate HMAC-SHA256 hash of subkey using MW_SECRET.
    Returns hex digest for storage/comparison.
    """
    return hmac.new(
        MW_SECRET.encode("utf-8"),
        subkey.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def _db_available() -> bool:
    """Check if database pool is initialized."""
    try:
        from core.db import _pool
        return _pool is not None
    except Exception:
        return False


# ─── DB-backed implementations ───────────────────────────────

def _load_users_db() -> List[Dict[str, Any]]:
    """Load all users from mw_users table, returning same format as JSON."""
    from core.db import db_conn
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT user_id, subkey, subkey_hash, active, allowed_models,
                   used_tokens, used_cost_usd, quota, alerts_sent
            FROM mw_users
        """)
        rows = cur.fetchall()
        cur.close()

    users = []
    for row in rows:
        user = {
            "user_id": row[0],
            "subkey": row[1],
            "subkey_hash": row[2],
            "active": row[3],
            "allowed_models": row[4] if row[4] else ["*"],
            "used_tokens": row[5] or 0,
            "used_cost_usd": row[6] or 0.0,
            "quota": row[7] if row[7] else {},
            "alerts_sent": row[8] if row[8] else {},
        }
        users.append(user)
    return users


def _save_users_db(users: List[Dict[str, Any]]):
    """Save all users to mw_users table (upsert each user)."""
    from core.db import db_conn
    with db_conn() as conn:
        cur = conn.cursor()
        for u in users:
            cur.execute("""
                INSERT INTO mw_users
                    (user_id, subkey, subkey_hash, active, allowed_models,
                     used_tokens, used_cost_usd, quota, alerts_sent, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (user_id) DO UPDATE SET
                    subkey = EXCLUDED.subkey,
                    subkey_hash = EXCLUDED.subkey_hash,
                    active = EXCLUDED.active,
                    allowed_models = EXCLUDED.allowed_models,
                    used_tokens = EXCLUDED.used_tokens,
                    used_cost_usd = EXCLUDED.used_cost_usd,
                    quota = EXCLUDED.quota,
                    alerts_sent = EXCLUDED.alerts_sent,
                    updated_at = now()
            """, (
                u.get("user_id"),
                u.get("subkey"),
                u.get("subkey_hash"),
                u.get("active", True),
                json.dumps(u.get("allowed_models", ["*"])),
                u.get("used_tokens", 0),
                u.get("used_cost_usd", 0.0),
                json.dumps(u.get("quota", {})),
                json.dumps(u.get("alerts_sent", {})),
            ))
        cur.close()


def _find_user_db(subkey: str) -> Optional[Dict[str, Any]]:
    """Find user by subkey hash or plaintext subkey in DB."""
    subkey_hash_val = hash_subkey(subkey)
    from core.db import db_conn
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT user_id, subkey, subkey_hash, active, allowed_models,
                   used_tokens, used_cost_usd, quota, alerts_sent
            FROM mw_users
            WHERE subkey_hash = %s OR subkey = %s
            LIMIT 1
        """, (subkey_hash_val, subkey))
        row = cur.fetchone()
        cur.close()

    if not row:
        return None

    return {
        "user_id": row[0],
        "subkey": row[1],
        "subkey_hash": row[2],
        "active": row[3],
        "allowed_models": row[4] if row[4] else ["*"],
        "used_tokens": row[5] or 0,
        "used_cost_usd": row[6] or 0.0,
        "quota": row[7] if row[7] else {},
        "alerts_sent": row[8] if row[8] else {},
    }


# ─── File-backed implementations (fallback) ──────────────────

def _load_users_file() -> List[Dict[str, Any]]:
    """Load users from users.json file."""
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _save_users_file(users: List[Dict[str, Any]]):
    """Save users to users.json file."""
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def _find_user_file(subkey: str) -> Optional[Dict[str, Any]]:
    """Find user by subkey in JSON file."""
    subkey_hash_val = hash_subkey(subkey)
    for u in _load_users_file():
        if u.get("subkey_hash") == subkey_hash_val:
            return u
        if u.get("subkey") == subkey:
            return u
    return None


# ─── Public API (auto-selects DB or file) ─────────────────────

def load_users() -> List[Dict[str, Any]]:
    """
    Load users. Uses DB if available, falls back to JSON file.
    """
    if _db_available():
        return _load_users_db()
    return _load_users_file()


def save_users(users: List[Dict[str, Any]]):
    """
    Save users. Writes to DB if available, and always writes to JSON file (backup).
    """
    if _db_available():
        _save_users_db(users)
    # Always write to JSON file as backup
    _save_users_file(users)


def _delete_user_db(user_id: str) -> bool:
    """Delete a user from mw_users table. Returns True if deleted."""
    from core.db import db_conn
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM mw_users WHERE user_id = %s", (user_id,))
        deleted = cur.rowcount > 0
        cur.close()
    return deleted


def delete_user(user_id: str) -> bool:
    """
    Delete user by user_id. Removes from DB + JSON file.
    Returns True if user was found and deleted.
    """
    deleted = False
    if _db_available():
        deleted = _delete_user_db(user_id)
    # Also remove from JSON backup
    users = _load_users_file()
    original_len = len(users)
    users = [u for u in users if u.get("user_id") != user_id]
    if len(users) < original_len:
        _save_users_file(users)
        deleted = True
    return deleted


def find_user(subkey: str) -> Optional[Dict[str, Any]]:
    """
    Find user by subkey. Uses DB if available, falls back to JSON.
    """
    if _db_available():
        return _find_user_db(subkey)
    return _find_user_file(subkey)


def require_user(request: Request) -> Dict[str, Any]:
    """
    Require valid user authentication from Authorization header.
    Raises HTTPException if authentication fails.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing sub-key")
    subkey = auth.split(" ", 1)[1].strip()
    user = find_user(subkey)
    if not user or not user.get("active", True):
        raise HTTPException(403, "Invalid or inactive sub-key")
    request.state.mw_user_id = user.get("user_id")
    return user


def assert_model_allowed(user: Dict[str, Any], model: str):
    """
    Check if user is allowed to use specified model.
    """
    allowed_models = user.get("allowed_models", [])
    if allowed_models != ["*"] and model not in allowed_models:
        raise HTTPException(403, f"Model '{model}' not allowed for {user['user_id']}")


def get_lock() -> Lock:
    """Get the shared thread lock for user operations."""
    return _lock
