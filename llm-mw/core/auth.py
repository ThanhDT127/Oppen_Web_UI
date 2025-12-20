"""
Authentication and user management for LLM middleware.
"""

import os
import json
import hmac
import hashlib
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, Request
from threading import Lock

from config import USERS_FILE, MW_SECRET

# Thread lock for user file access
_lock = Lock()


def hash_subkey(subkey: str) -> str:
    """
    Generate HMAC-SHA256 hash of subkey using MW_SECRET.
    Returns hex digest for storage/comparison.
    
    Args:
        subkey: Subkey to hash
        
    Returns:
        Hex digest string
    """
    return hmac.new(
        MW_SECRET.encode("utf-8"),
        subkey.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def load_users() -> List[Dict[str, Any]]:
    """
    Load users from users.json file.
    
    Returns:
        List of user dictionaries
    """
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_users(users: List[Dict[str, Any]]):
    """
    Save users to users.json file.
    
    Args:
        users: List of user dictionaries
    """
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def find_user(subkey: str) -> Optional[Dict[str, Any]]:
    """
    Find user by subkey. Compares hashed subkey for security.
    Falls back to plaintext comparison for migration compatibility.
    
    Args:
        subkey: Subkey to search for
        
    Returns:
        User dictionary or None if not found
    """
    subkey_hash = hash_subkey(subkey)
    for u in load_users():
        # Primary: hash comparison
        if u.get("subkey_hash") == subkey_hash:
            return u
        # Fallback: plaintext (for migration period)
        if u.get("subkey") == subkey:
            return u
    return None


def require_user(request: Request) -> Dict[str, Any]:
    """
    Require valid user authentication from Authorization header.
    Raises HTTPException if authentication fails.
    
    Args:
        request: FastAPI request
        
    Returns:
        User dictionary
        
    Raises:
        HTTPException: 401 if missing auth, 403 if invalid/inactive
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
    
    Args:
        user: User dictionary
        model: Model name
        
    Raises:
        HTTPException: 403 if model not allowed
    """
    allowed_models = user.get("allowed_models", [])
    if allowed_models != ["*"] and model not in allowed_models:
        raise HTTPException(403, f"Model '{model}' not allowed for {user['user_id']}")


def get_lock() -> Lock:
    """
    Get the shared thread lock for user file operations.
    
    Returns:
        Thread lock
    """
    return _lock
