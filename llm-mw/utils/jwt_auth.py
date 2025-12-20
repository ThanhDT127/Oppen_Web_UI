"""
JWT-based session authentication utilities.
"""

import os
import hmac
import hashlib
import json
import base64
from datetime import datetime, timedelta, timezone


def get_jwt_secret() -> str:
    """Get JWT secret from env or use default"""
    return os.getenv("JWT_SECRET", "mw_default_jwt_secret_change_in_production")


def create_session_token(admin_key: str, expiry_hours: int = 4) -> str:
    """
    Create JWT-like session token for dashboard auth.
    
    Format: base64(header).base64(payload).signature
    Simplified HMAC-SHA256 signing (not full JWT spec).
    """
    secret = get_jwt_secret()
    
    # Header
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(
        json.dumps(header, separators=(",", ":")).encode()
    ).decode().rstrip("=")
    
    # Payload
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=expiry_hours)
    payload = {
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "key_hash": hashlib.sha256(admin_key.encode()).hexdigest()[:16]  # Partial hash
    }
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).decode().rstrip("=")
    
    # Signature
    message = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    
    return f"{message}.{signature_b64}"


def verify_session_token(token: str) -> dict:
    """
    Verify session token and return payload.
    
    Returns:
        dict with payload if valid
        
    Raises:
        ValueError if invalid or expired
    """
    secret = get_jwt_secret()
    
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token format")
        
        header_b64, payload_b64, signature_b64 = parts
        
        # Verify signature
        message = f"{header_b64}.{payload_b64}"
        expected_signature = hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_signature).decode().rstrip("=")
        
        # Constant-time comparison
        if not hmac.compare_digest(signature_b64, expected_sig_b64):
            raise ValueError("Invalid signature")
        
        # Decode payload
        # Add padding if needed
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload_json = base64.urlsafe_b64decode(payload_b64).decode()
        payload = json.loads(payload_json)
        
        # Check expiry
        now = datetime.now(timezone.utc).timestamp()
        if payload.get("exp", 0) < now:
            raise ValueError("Token expired")
        
        return payload
    
    except Exception as e:
        raise ValueError(f"Token verification failed: {e}")
