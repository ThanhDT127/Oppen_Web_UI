"""
Tests for audit system fixes:
1. Double-log prevention for streaming
2. Reconcile idempotency
3. Summary not counting pending
4. Dashboard cookie authentication
"""

import os
import json
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

os.environ['ADMIN_KEY'] = 'test_admin_fix_key'
os.environ['JWT_SECRET'] = 'test_jwt_secret_for_fixes'

from main import app
from utils.jwt_auth import create_session_token, verify_session_token
from utils.auth_guard import require_admin_or_session


@pytest.fixture
def client():
    return TestClient(app)


# ============================================================================
# FIX 1: Double-log Prevention
# ============================================================================

def test_streaming_marks_audit_logged():
    """Test that streaming sets mw_audit_already_logged flag"""
    from core.audit_state import init_audit_state, mark_audit_logged, should_skip_audit
    from fastapi import Request
    
    class MockRequest:
        def __init__(self):
            self.state = type('State', (), {})()
    
    req = MockRequest()
    init_audit_state(req, 'user1', '/v1/chat/completions', 'gpt-4o-mini')
    
    # Initially should not skip
    assert not should_skip_audit(req)
    
    # After marking
    mark_audit_logged(req)
    assert should_skip_audit(req)
    assert req.state.mw_audit_already_logged


# ============================================================================
# FIX 2: Reconcile Idempotency
# ============================================================================

def test_reconcile_idempotent(client):
    """Test reconcile returns early if already reconciled"""
    import config
    import shutil
    from pathlib import Path
    
    # Backup original audit file
    audit_file = Path(config.AUDIT_LOG_FILE)
    backup_file = audit_file.with_suffix('.jsonl.backup2')
    
    if audit_file.exists():
        shutil.copy(audit_file, backup_file)
    
    try:
        # Write reconciled audit line
        reconciled_line = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "rid": "mw_test_idempotent",
            "user_id": "admin",
            "endpoint": "/v1/chat/completions",
            "model": "gpt-4o-mini",
            "status": "reconciled",
            "tokens_total": 300,
            "cost_usd": 0.00045
        }
        
        with open(audit_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(reconciled_line) + '\n')
        
        # Try to reconcile again
        response = client.post(
            '/admin/reconcile',
            headers={'X-Admin-Key': 'test_admin_fix_key'},
            json={
                'request_id': 'mw_test_idempotent',
                'user_id': 'admin'
            }
        )
        
        # Should return early with "Already reconciled"
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert 'already reconciled' in data['message'].lower()
    
    finally:
        # Restore original audit file
        if backup_file.exists():
            shutil.move(backup_file, audit_file)
        elif audit_file.exists():
            audit_file.unlink()


# ============================================================================
# FIX 3: Summary Not Counting Pending
# ============================================================================

def test_summary_excludes_pending(client):
    """Test summary does not count pending in tokens/cost"""
    import config
    import shutil
    from pathlib import Path
    
    # Backup original audit file
    audit_file = Path(config.AUDIT_LOG_FILE)
    backup_file = audit_file.with_suffix('.jsonl.backup')
    
    if audit_file.exists():
        shutil.copy(audit_file, backup_file)
    
    try:
        now = datetime.now(timezone.utc)
        
        # Write mix of statuses
        entries = [
            # OK entry - should count
            {
                "ts": now.isoformat(),
                "rid": "mw_ok_1",
                "user_id": "admin",
                "endpoint": "/v1/chat/completions",
                "model": "gpt-4o-mini",
                "status": "ok",
                "status_code": 200,
                "latency_ms": 1000.0,
                "tokens_in": 100,
                "tokens_out": 200,
                "tokens_total": 300,
                "cost_usd": 0.00045,
                "image_count": None,
                "tts_chars": None,
                "stt_seconds": None,
                "video_count": None,
                "error_type": None,
                "error_message": None
            },
            # Pending entry - should NOT count in tokens/cost
            {
                "ts": now.isoformat(),
                "rid": "mw_pending_1",
                "user_id": "admin",
                "endpoint": "/v1/chat/completions",
                "model": "gpt-4o-mini",
                "status": "pending",
                "status_code": None,
                "latency_ms": None,
                "tokens_in": 0,
                "tokens_out": 0,
                "tokens_total": 0,
                "cost_usd": 0.0,
                "image_count": None,
                "tts_chars": None,
                "stt_seconds": None,
                "video_count": None,
                "error_type": None,
                "error_message": None
            },
            # Reconciled entry - should count
            {
                "ts": now.isoformat(),
                "rid": "mw_reconciled_1",
                "user_id": "admin",
                "endpoint": "/v1/chat/completions",
                "model": "gpt-4o-mini",
                "status": "reconciled",
                "status_code": 200,
                "latency_ms": None,
                "tokens_in": 150,
                "tokens_out": 250,
                "tokens_total": 400,
                "cost_usd": 0.0006,
                "image_count": None,
                "tts_chars": None,
                "stt_seconds": None,
                "video_count": None,
                "error_type": None,
                "error_message": None
            }
        ]
        
        # Overwrite audit file with test data
        with open(audit_file, 'w', encoding='utf-8') as f:
            for entry in entries:
                f.write(json.dumps(entry) + '\n')
        
        # Call summary
        response = client.get(
            '/v1/_mw/summary?minutes=60',
            headers={'X-Admin-Key': 'test_admin_fix_key'}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify counts
        assert data['requests_total'] == 2  # ok + reconciled (NOT pending)
        assert data['pending_count'] == 1  # Only pending counted here
        assert data['tokens_total'] == 700  # 300 + 400 (NOT 0 from pending)
        assert abs(data['cost_total_usd'] - 0.00105) < 0.0001  # 0.00045 + 0.0006
    
    finally:
        # Restore original audit file
        if backup_file.exists():
            shutil.move(backup_file, audit_file)
        elif audit_file.exists():
            audit_file.unlink()


# ============================================================================
# FIX 4: JWT Session Authentication
# ============================================================================

def test_jwt_create_and_verify():
    """Test JWT token creation and verification"""
    token = create_session_token('test_admin_fix_key', expiry_hours=1)
    
    # Token should have 3 parts
    assert len(token.split('.')) == 3
    
    # Verify token
    payload = verify_session_token(token)
    assert 'iat' in payload
    assert 'exp' in payload
    assert 'key_hash' in payload


def test_jwt_expired():
    """Test expired token raises error"""
    # Create token with -1 hour expiry (expired)
    token = create_session_token('test_admin_fix_key', expiry_hours=-1)
    
    with pytest.raises(ValueError, match='expired'):
        verify_session_token(token)


def test_jwt_invalid_signature():
    """Test invalid signature raises error"""
    token = create_session_token('test_admin_fix_key')
    
    # Tamper with token
    parts = token.split('.')
    parts[2] = 'invalid_signature'
    bad_token = '.'.join(parts)
    
    with pytest.raises(ValueError):
        verify_session_token(bad_token)


# ============================================================================
# FIX 5: Dashboard Login Endpoint
# ============================================================================

def test_dashboard_login_success(client):
    """Test successful dashboard login sets cookie"""
    response = client.post(
        '/v1/_mw/dashboard/login',
        json={'admin_key': 'test_admin_fix_key'}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data['ok'] is True
    
    # Check cookie is set
    assert 'set-cookie' in response.headers
    cookie_header = response.headers['set-cookie']
    assert 'mw_admin_session' in cookie_header
    assert 'HttpOnly' in cookie_header
    assert 'SameSite=Lax' in cookie_header or 'SameSite=lax' in cookie_header


def test_dashboard_login_invalid_key(client):
    """Test login with invalid key returns 403"""
    response = client.post(
        '/v1/_mw/dashboard/login',
        json={'admin_key': 'wrong_key'}
    )
    
    assert response.status_code == 403
    data = response.json()
    assert 'error' in data


def test_dashboard_logout(client):
    """Test logout clears cookie"""
    response = client.post('/v1/_mw/dashboard/logout')
    
    assert response.status_code == 200
    data = response.json()
    assert data['ok'] is True


# ============================================================================
# FIX 6: Auth Guard with Cookie
# ============================================================================

def test_auth_guard_accepts_admin_key(client):
    """Test auth guard accepts X-Admin-Key header"""
    response = client.get(
        '/v1/_mw/summary?minutes=5',
        headers={'X-Admin-Key': 'test_admin_fix_key'}
    )
    
    # Should not be 403
    assert response.status_code != 403


def test_auth_guard_accepts_session_cookie(client):
    """Test auth guard accepts valid session cookie"""
    # Login to get session cookie
    login_response = client.post(
        '/v1/_mw/dashboard/login',
        json={'admin_key': 'test_admin_fix_key'}
    )
    
    # Extract cookie
    cookies = login_response.cookies
    
    # Use cookie to access protected endpoint
    response = client.get(
        '/v1/_mw/summary?minutes=5',
        cookies=cookies
    )
    
    # Should not be 403
    assert response.status_code != 403


def test_auth_guard_rejects_no_auth(client):
    """Test auth guard rejects requests without auth"""
    response = client.get('/v1/_mw/summary?minutes=5')
    
    assert response.status_code == 403


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_full_dashboard_flow(client):
    """Test complete dashboard authentication flow"""
    # Step 1: Try to access without auth - should fail
    response = client.get('/v1/_mw/summary?minutes=5')
    assert response.status_code == 403
    
    # Step 2: Login with admin key
    login_response = client.post(
        '/v1/_mw/dashboard/login',
        json={'admin_key': 'test_admin_fix_key'}
    )
    assert login_response.status_code == 200
    cookies = login_response.cookies
    
    # Step 3: Access with cookie - should work
    response = client.get(
        '/v1/_mw/summary?minutes=5',
        cookies=cookies
    )
    assert response.status_code == 200
    
    # Step 4: Logout
    logout_response = client.post(
        '/v1/_mw/dashboard/logout',
        cookies=cookies
    )
    assert logout_response.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
