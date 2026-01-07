"""
Auth check endpoint for dashboard debugging
"""
from fastapi import Request
from datetime import datetime
from utils.auth_guard import require_admin_or_session

async def get_auth_check(request: Request) -> dict:
    """
    Check auth status - useful for debugging cookie/session issues
    
    Returns:
        - ok: true if authenticated
        - ts: current timestamp
        - cookie_present: whether mw_admin_session cookie was sent
        - auth_method: 'cookie' or 'header'
    """
    # This decorator will raise 403 if not authenticated
    auth_info = require_admin_or_session(request)
    
    # Check if cookie was present
    cookie_present = request.cookies.get('mw_admin_session') is not None
    auth_method = 'cookie' if cookie_present else 'header'
    
    return {
        "ok": True,
        "ts": datetime.utcnow().isoformat() + 'Z',
        "cookie_present": cookie_present,
        "auth_method": auth_method,
        "message": "Authentication successful"
    }
