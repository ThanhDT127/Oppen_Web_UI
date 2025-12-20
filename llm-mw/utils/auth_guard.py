"""
Auth guard utilities for admin endpoints.
"""

from fastapi import Request, HTTPException
from config import ADMIN_KEY
from utils.jwt_auth import verify_session_token


def require_admin_or_session(request: Request) -> bool:
    """
    Check if request has valid admin authentication.
    
    Accepts either:
    1. X-Admin-Key header (for curl/ops)
    2. mw_admin_session cookie (for dashboard)
    
    Raises:
        HTTPException(403) if neither is valid
        
    Returns:
        True if authenticated
    """
    # Check X-Admin-Key header (for curl/ops)
    admin_key_header = request.headers.get("X-Admin-Key", "")
    if admin_key_header == ADMIN_KEY:
        return True
    
    # Check Authorization: Bearer header (backward compat)
    auth_header = request.headers.get("Authorization", "")
    if auth_header == f"Bearer {ADMIN_KEY}":
        return True
    
    # Check mw_admin_session cookie (for dashboard)
    session_cookie = request.cookies.get("mw_admin_session", "")
    if session_cookie:
        try:
            payload = verify_session_token(session_cookie)
            # Token is valid and not expired
            return True
        except ValueError:
            # Invalid or expired token - fall through to 403
            pass
    
    raise HTTPException(403, "Invalid admin key or session")


def get_admin_key_hash() -> str:
    """Get partial hash of admin key for session validation"""
    import hashlib
    return hashlib.sha256(ADMIN_KEY.encode()).hexdigest()[:16]
