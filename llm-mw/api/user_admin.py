"""
User administration API endpoints.
Provides CRUD operations for user management with RBAC, key lifecycle, and audit trail.
"""

import json
import secrets
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import Request, HTTPException
from pydantic import BaseModel

from config import USERS_FILE, MW_SECRET, LOG_DIR, BACKUP_LOG_DIR, logger
from core.auth import load_users, save_users, hash_subkey, find_user, delete_user as auth_delete_user
from threading import Lock
import os
from logging.handlers import RotatingFileHandler
import logging

# Thread lock for user operations
_user_lock = Lock()

# Admin audit logger
_admin_audit_logger = None


def _get_admin_audit_logger():
    """Get or create admin audit logger"""
    global _admin_audit_logger
    if _admin_audit_logger is None:
        _admin_audit_logger = logging.getLogger("llm_mw_admin_audit")
        if not _admin_audit_logger.handlers:
            _admin_audit_logger.setLevel(logging.INFO)
            audit_file = os.path.join(BACKUP_LOG_DIR, "admin_audit.jsonl")
            handler = RotatingFileHandler(
                audit_file, maxBytes=20_000_000, backupCount=5, encoding="utf-8"
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
            _admin_audit_logger.addHandler(handler)
    return _admin_audit_logger


def _write_admin_audit(actor: str, action: str, target_user: str, changes: Dict, status: str, request: Request):
    """Write admin audit trail entry"""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "action": action,
        "target_user": target_user,
        "changes": changes,
        "status": status,
        "ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown")
    }
    _get_admin_audit_logger().info(json.dumps(entry, ensure_ascii=False))


def _generate_subkey() -> str:
    """Generate a secure random subkey"""
    return f"sk_{secrets.token_urlsafe(32)}"


def _scrub_user(user: Dict[str, Any]) -> Dict[str, Any]:
    """Remove sensitive fields from user dict for API responses.
    Keeps subkey_hash (safe for admin view), removes plaintext subkey."""
    scrubbed = user.copy()
    # Remove plaintext key only — hash is safe for admin dashboard
    scrubbed.pop("subkey", None)
    return scrubbed


# Request/Response models
class CreateUserRequest(BaseModel):
    user_id: str
    role: str = "user"  # admin | manager | user
    allowed_models: List[str] = ["*"]
    limit_tokens: int = 0  # 0 = unlimited
    limit_cost_usd: float = 0.0
    limit_image_requests: int = 0
    period: str = "monthly"
    timezone: str = "Asia/Bangkok"


class UpdateUserRequest(BaseModel):
    role: Optional[str] = None
    active: Optional[bool] = None
    allowed_models: Optional[List[str]] = None
    limit_tokens: Optional[int] = None
    limit_cost_usd: Optional[float] = None
    limit_image_requests: Optional[int] = None


# ============================================================================
# API ENDPOINTS
# ============================================================================

def list_users(request: Request):
    """
    GET /v1/_mw/admin/users
    List all users (scrubbed - no keys/hashes)
    """
    from utils.auth_guard import require_admin_or_session
    require_admin_or_session(request)
    
    users = load_users()
    scrubbed_users = [_scrub_user(u) for u in users]
    
    return {
        "users": scrubbed_users,
        "total": len(scrubbed_users)
    }


async def create_user(request: Request):
    """
    POST /v1/_mw/admin/users
    Create new user with generated subkey (returned once)
    """
    from utils.auth_guard import require_admin_or_session
    require_admin_or_session(request)
    
    try:
        body = await request.json()
        req = CreateUserRequest(**body)
    except Exception as e:
        raise HTTPException(400, f"Invalid request: {e}")
    
    # Validate role
    if req.role not in ["admin", "manager", "user"]:
        raise HTTPException(400, "Invalid role. Must be: admin, manager, or user")
    
    with _user_lock:
        users = load_users()
        
        # Check if user_id already exists
        if any(u["user_id"] == req.user_id for u in users):
            raise HTTPException(409, f"User {req.user_id} already exists")
        
        # Generate subkey
        subkey = _generate_subkey()
        subkey_hash = hash_subkey(subkey)
        
        # Create user object (store both subkey + hash for DB and JSON sync)
        new_user = {
            "user_id": req.user_id,
            "role": req.role,
            "subkey": subkey,
            "subkey_hash": subkey_hash,
            "active": True,
            "allowed_models": req.allowed_models,
            "used_tokens": 0,
            "used_cost_usd": 0.0,
            "quota": {
                "period": req.period,
                "timezone": req.timezone,
                "limit_tokens": req.limit_tokens,
                "limit_cost_usd": req.limit_cost_usd,
                "limit_image_requests": req.limit_image_requests,
                "period_start": int(datetime.now(timezone.utc).timestamp() * 1000),
                "used_tokens": 0,
                "used_cost_usd": 0.0,
                "used_image_requests": 0
            }
        }
        
        users.append(new_user)
        save_users(users)
        
        # Audit trail
        _write_admin_audit(
            actor="admin_session",
            action="create_user",
            target_user=req.user_id,
            changes={"role": req.role, "allowed_models": req.allowed_models},
            status="ok",
            request=request
        )
        
        logger.info(f"Created user: {req.user_id} (role={req.role})")
        
        return {
            "message": "User created successfully",
            "user": _scrub_user(new_user),
            "subkey": subkey,  # ⚠️ Only returned once!
            "warning": "Save this subkey securely. It will not be shown again."
        }


async def update_user(request: Request, user_id: str):
    """
    PATCH /v1/_mw/admin/users/{user_id}
    Update user role, active status, allowed models, or quota limits
    """
    from utils.auth_guard import require_admin_or_session
    require_admin_or_session(request)
    
    try:
        body = await request.json()
        req = UpdateUserRequest(**body)
    except Exception as e:
        raise HTTPException(400, f"Invalid request: {e}")
    
    with _user_lock:
        users = load_users()
        
        # Find user
        user = next((u for u in users if u["user_id"] == user_id), None)
        if not user:
            raise HTTPException(404, f"User {user_id} not found")
        
        changes = {}
        
        # Update role
        if req.role is not None:
            if req.role not in ["admin", "manager", "user"]:
                raise HTTPException(400, "Invalid role")
            user["role"] = req.role
            changes["role"] = req.role
        
        # Update active
        if req.active is not None:
            user["active"] = req.active
            changes["active"] = req.active
        
        # Update allowed models
        if req.allowed_models is not None:
            user["allowed_models"] = req.allowed_models
            changes["allowed_models"] = req.allowed_models
        
        # Update quota limits
        if req.limit_tokens is not None:
            user["quota"]["limit_tokens"] = req.limit_tokens
            changes["limit_tokens"] = req.limit_tokens
        
        if req.limit_cost_usd is not None:
            user["quota"]["limit_cost_usd"] = req.limit_cost_usd
            changes["limit_cost_usd"] = req.limit_cost_usd
        
        if req.limit_image_requests is not None:
            user["quota"]["limit_image_requests"] = req.limit_image_requests
            changes["limit_image_requests"] = req.limit_image_requests
        
        if not changes:
            return {"message": "No changes provided"}
        
        save_users(users)
        
        # Audit trail
        _write_admin_audit(
            actor="admin_session",
            action="update_user",
            target_user=user_id,
            changes=changes,
            status="ok",
            request=request
        )
        
        logger.info(f"Updated user: {user_id} - {changes}")
        
        return {
            "message": "User updated successfully",
            "user": _scrub_user(user),
            "changes": changes
        }


async def rotate_user_key(request: Request, user_id: str):
    """
    POST /v1/_mw/admin/users/{user_id}/rotate_key
    Rotate user's subkey (generates new key, invalidates old)
    """
    from utils.auth_guard import require_admin_or_session
    require_admin_or_session(request)
    
    with _user_lock:
        users = load_users()
        
        user = next((u for u in users if u["user_id"] == user_id), None)
        if not user:
            raise HTTPException(404, f"User {user_id} not found")
        
        # Generate new subkey
        new_subkey = _generate_subkey()
        new_hash = hash_subkey(new_subkey)
        
        # Update user
        user["subkey_hash"] = new_hash
        # Remove plaintext if exists (migration compat)
        user.pop("subkey", None)
        
        save_users(users)
        
        # Audit trail
        _write_admin_audit(
            actor="admin_session",
            action="rotate_key",
            target_user=user_id,
            changes={"key_rotated": True},
            status="ok",
            request=request
        )
        
        logger.info(f"Rotated key for user: {user_id}")
        
        return {
            "message": "Key rotated successfully",
            "user_id": user_id,
            "subkey": new_subkey,  # ⚠️ Only returned once!
            "warning": "Save this subkey securely. The old key is now invalid."
        }


async def disable_user(request: Request, user_id: str):
    """
    POST /v1/_mw/admin/users/{user_id}/disable
    Disable user (sets active=False)
    """
    from utils.auth_guard import require_admin_or_session
    require_admin_or_session(request)
    
    with _user_lock:
        users = load_users()
        
        user = next((u for u in users if u["user_id"] == user_id), None)
        if not user:
            raise HTTPException(404, f"User {user_id} not found")
        
        user["active"] = False
        save_users(users)
        
        # Audit trail
        _write_admin_audit(
            actor="admin_session",
            action="disable_user",
            target_user=user_id,
            changes={"active": False},
            status="ok",
            request=request
        )
        
        logger.info(f"Disabled user: {user_id}")
        
        return {
            "message": f"User {user_id} disabled successfully",
            "user": _scrub_user(user)
        }


async def enable_user(request: Request, user_id: str):
    """
    POST /v1/_mw/admin/users/{user_id}/enable
    Enable user (sets active=True)
    """
    from utils.auth_guard import require_admin_or_session
    require_admin_or_session(request)
    
    with _user_lock:
        users = load_users()
        
        user = next((u for u in users if u["user_id"] == user_id), None)
        if not user:
            raise HTTPException(404, f"User {user_id} not found")
        
        user["active"] = True
        save_users(users)
        
        # Audit trail
        _write_admin_audit(
            actor="admin_session",
            action="enable_user",
            target_user=user_id,
            changes={"active": True},
            status="ok",
            request=request
        )
        
        logger.info(f"Enabled user: {user_id}")
        
        return {
            "message": f"User {user_id} enabled successfully",
            "user": _scrub_user(user)
        }


async def delete_user_endpoint(request: Request, user_id: str):
    """
    DELETE /v1/_mw/admin/users/{user_id}
    Permanently delete a user
    """
    from utils.auth_guard import require_admin_or_session
    require_admin_or_session(request)
    
    with _user_lock:
        users = load_users()
        
        # Check user exists
        user = next((u for u in users if u["user_id"] == user_id), None)
        if not user:
            raise HTTPException(404, f"User {user_id} not found")
        
        # Prevent self-deletion
        if hasattr(request.state, 'mw_user_id') and request.state.mw_user_id == user_id:
            raise HTTPException(400, "Cannot delete yourself")
        
        # Delete from DB + JSON
        deleted = auth_delete_user(user_id)
        if not deleted:
            raise HTTPException(500, f"Failed to delete user {user_id}")
        
        # Audit trail
        _write_admin_audit(
            actor="admin_session",
            action="delete_user",
            target_user=user_id,
            changes={"deleted": True, "role": user.get("role"), "active": user.get("active")},
            status="ok",
            request=request
        )
        
        logger.info(f"Deleted user: {user_id}")
        
        return {
            "message": f"User {user_id} deleted permanently",
            "user_id": user_id
        }


def get_admin_audit(
    request: Request,
    minutes: Optional[int] = None,
    start: Optional[str] = None,
    end: Optional[str] = None
):
    """
    GET /v1/_mw/admin/audit
    Get admin audit trail
    """
    from utils.auth_guard import require_admin_or_session
    require_admin_or_session(request)
    
    audit_file = os.path.join(BACKUP_LOG_DIR, "admin_audit.jsonl")
    
    if not os.path.exists(audit_file):
        return {"audit_trail": [], "total": 0}
    
    # Determine time range
    now_utc = datetime.now(timezone.utc)
    
    if start and end:
        try:
            cutoff = datetime.fromisoformat(start)
            end_time = datetime.fromisoformat(end)
        except ValueError as e:
            raise HTTPException(400, f"Invalid datetime format: {e}")
    else:
        if minutes is None:
            minutes = 1440  # Default: last 24 hours
        cutoff = now_utc - __import__('datetime').timedelta(minutes=minutes)
        end_time = now_utc
    
    # Read audit log
    entries = []
    try:
        with open(audit_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    entry_time = datetime.fromisoformat(entry.get("ts", ""))
                    
                    if cutoff <= entry_time <= end_time:
                        entries.append(entry)
                except Exception:
                    continue
    except Exception as e:
        return {"error": str(e)}
    
    # Sort by timestamp descending (newest first)
    entries.sort(key=lambda x: x.get("ts", ""), reverse=True)
    
    return {
        "audit_trail": entries[:100],  # Last 100 events
        "total": len(entries)
    }
