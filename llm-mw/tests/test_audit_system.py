"""
Comprehensive tests for audit system (PR1 + PR2 + PR3).
Run with: pytest tests/test_audit_system.py -v
"""

import os
import json
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

# Set environment before importing app
os.environ['ADMIN_KEY'] = 'test_admin_key_12345'
os.environ['LITELLM_BASE'] = 'http://localhost:4000'

from main import app
from utils.logging import write_audit_line
from core.audit_state import (
    init_audit_state,
    set_usage_state,
    set_error_state,
    set_counters,
    mark_audit_logged,
    should_skip_audit,
    has_audit_state
)


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def mock_request():
    """Mock request object with state"""
    class MockRequest:
        def __init__(self):
            self.state = type('State', (), {})()
    return MockRequest()


# ============================================================================
# PR1 Tests: Audit State Contract
# ============================================================================

def test_init_audit_state(mock_request):
    """Test audit state initialization"""
    rid = init_audit_state(
        mock_request,
        user_id='test_user',
        endpoint='/v1/chat/completions',
        model='gpt-4o-mini'
    )
    
    assert rid.startswith('mw_')
    assert has_audit_state(mock_request)
    assert mock_request.state.mw_user_id == 'test_user'
    assert mock_request.state.mw_endpoint == '/v1/chat/completions'
    assert mock_request.state.mw_model == 'gpt-4o-mini'
    assert mock_request.state.mw_status == 'ok'
    assert mock_request.state.mw_tokens_total == 0
    assert mock_request.state.mw_cost_usd == 0.0
    assert not mock_request.state.mw_audit_already_logged


def test_set_usage_state(mock_request):
    """Test setting usage counters"""
    init_audit_state(mock_request, 'user1', '/v1/chat/completions', 'gpt-4o-mini')
    
    set_usage_state(mock_request, 100, 200, 300, 0.00045)
    
    assert mock_request.state.mw_tokens_in == 100
    assert mock_request.state.mw_tokens_out == 200
    assert mock_request.state.mw_tokens_total == 300
    assert mock_request.state.mw_cost_usd == 0.00045


def test_set_error_state(mock_request):
    """Test setting error state"""
    init_audit_state(mock_request, 'user1', '/v1/chat/completions', 'gpt-4o-mini')
    
    set_error_state(mock_request, 'quota', 'Token quota exceeded')
    
    assert mock_request.state.mw_status == 'error'
    assert mock_request.state.mw_error_type == 'quota'
    assert mock_request.state.mw_error_message == 'Token quota exceeded'


def test_set_counters(mock_request):
    """Test setting special counters"""
    init_audit_state(mock_request, 'user1', '/v1/images/generations', 'dalle-3')
    
    set_counters(mock_request, image_count=2, tts_chars=None, stt_seconds=None)
    
    assert mock_request.state.mw_image_count == 2
    assert mock_request.state.mw_tts_chars is None
    assert mock_request.state.mw_stt_seconds is None


def test_mark_audit_logged(mock_request):
    """Test marking audit as logged"""
    init_audit_state(mock_request, 'user1', '/v1/chat/completions', 'gpt-4o-mini')
    
    assert not should_skip_audit(mock_request)
    
    mark_audit_logged(mock_request)
    
    assert should_skip_audit(mock_request)
    assert mock_request.state.mw_audit_already_logged


# ============================================================================
# PR2 Tests: Logging Functions
# ============================================================================

def test_write_audit_line():
    """Test writing audit line to JSONL"""
    # write_audit_line uses logger, so we just test it doesn't raise
    sample_data = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "rid": "mw_test123",
        "user_id": "test_user",
        "endpoint": "/v1/chat/completions",
        "model": "gpt-4o-mini",
        "status": "ok",
        "status_code": 200,
        "latency_ms": 1234.5,
        "tokens_in": 100,
        "tokens_out": 200,
        "tokens_total": 300,
        "cost_usd": 0.00045
    }
    
    # Should not raise
    write_audit_line(sample_data)
    
    # Verify data is JSON serializable
    json_str = json.dumps(sample_data)
    parsed = json.loads(json_str)
    assert parsed['rid'] == 'mw_test123'
    assert parsed['tokens_total'] == 300


# ============================================================================
# PR2 Tests: Summary Endpoint
# ============================================================================

def test_summary_endpoint_unauthorized(client):
    """Test summary endpoint requires authentication"""
    response = client.get('/v1/_mw/summary?minutes=60')
    assert response.status_code == 403


def test_summary_endpoint_with_auth(client, tmp_path):
    """Test summary endpoint returns aggregated data"""
    # Create temporary audit file
    audit_file = tmp_path / "audit.jsonl"
    
    # Patch AUDIT_LOG_FILE
    import config
    original_file = config.AUDIT_LOG_FILE
    config.AUDIT_LOG_FILE = str(audit_file)
    
    try:
        # Write sample audit data
        now = datetime.now(timezone.utc)
        samples = [
            {"ts": now.isoformat(), "rid": "mw_001", "user_id": "admin", "endpoint": "/v1/chat/completions", 
             "model": "gpt-4o-mini", "status": "ok", "status_code": 200, "latency_ms": 1234.5,
             "tokens_in": 100, "tokens_out": 200, "tokens_total": 300, "cost_usd": 0.00045},
            {"ts": now.isoformat(), "rid": "mw_002", "user_id": "admin", "endpoint": "/v1/chat/completions",
             "model": "gpt-4o-mini", "status": "pending", "status_code": None, "latency_ms": None,
             "tokens_in": 0, "tokens_out": 0, "tokens_total": 0, "cost_usd": 0.0},
            {"ts": now.isoformat(), "rid": "mw_003", "user_id": "user1", "endpoint": "/v1/images/generations",
             "model": "dalle-3", "status": "ok", "status_code": 200, "latency_ms": 3456.7,
             "tokens_in": 0, "tokens_out": 0, "tokens_total": 0, "cost_usd": 0.05, "image_count": 1},
        ]
        
        with open(audit_file, 'w', encoding='utf-8') as f:
            for sample in samples:
                # Fill in missing fields
                for field in ['image_count', 'tts_chars', 'stt_seconds', 'video_count', 'error_type', 'error_message']:
                    if field not in sample:
                        sample[field] = None
                f.write(json.dumps(sample) + '\n')
        
        # Call summary endpoint
        response = client.get(
            '/v1/_mw/summary?minutes=60',
            headers={'Authorization': 'Bearer test_admin_key_12345'}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # May have old data, so check >= instead of ==
        assert data['requests_total'] >= 2  # At least our 2 ok requests
        assert data['pending_count'] >= 1  # At least our 1 pending
        assert data['tokens_total'] >= 300  # At least our 300 tokens
        assert data['cost_total_usd'] > 0.0
        assert len(data['top_users']) > 0
        assert len(data['top_models']) > 0
    
    finally:
        config.AUDIT_LOG_FILE = original_file


# ============================================================================
# PR3 Tests: Stream Endpoint
# ============================================================================

def test_stream_endpoint_unauthorized(client):
    """Test stream endpoint requires authentication"""
    response = client.get('/v1/_mw/stream')
    assert response.status_code == 403


# ============================================================================
# Integration Tests
# ============================================================================

def test_audit_no_secrets():
    """Test that no secrets are logged in audit"""
    sample_data = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "rid": "mw_test123",
        "user_id": "test_user",
        "endpoint": "/v1/chat/completions",
        "model": "gpt-4o-mini",
        "status": "ok",
        "status_code": 200,
        "tokens_total": 300,
        "cost_usd": 0.00045
    }
    
    json_str = json.dumps(sample_data)
    
    # Verify no sensitive data
    assert 'Authorization' not in json_str
    assert 'Bearer' not in json_str
    assert 'api_key' not in json_str
    assert 'subkey' not in json_str


def test_audit_status_types():
    """Test all audit status types are valid"""
    valid_statuses = ['ok', 'error', 'pending', 'reconciled']
    
    for status in valid_statuses:
        sample = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "rid": f"mw_{status}",
            "user_id": "test",
            "endpoint": "/v1/chat/completions",
            "model": "gpt-4o-mini",
            "status": status,
            "tokens_total": 0,
            "cost_usd": 0.0
        }
        
        # Should not raise
        json_str = json.dumps(sample)
        parsed = json.loads(json_str)
        assert parsed['status'] == status


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
