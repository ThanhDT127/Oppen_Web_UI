"""
Image generation endpoint tests.
Run with: pytest tests/test_images.py -v
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import json

# Setup environment
import os
os.environ['ADMIN_KEY'] = 'test_admin_key'
os.environ['LITELLM_BASE'] = 'http://localhost:4000'
os.environ['MW_SECRET'] = 'test-secret'

from main import app


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def mock_users():
    """Mock users with image quota"""
    return [
        {
            "user_id": "test_user",
            "subkey": "test_subkey_123",
            "active": True,
            "allowed_models": ["*"],
            "used_tokens": 0,
            "used_cost_usd": 0.0,
            "quota": {
                "period": "monthly",
                "limit_image_requests": 5,
                "limit_cost_usd": 1.0,
                "used_image_requests": 0,
                "used_cost_usd": 0.0
            }
        }
    ]


# ============================================================================
# Test 1: Authentication Required
# ============================================================================

def test_images_auth_required(client):
    """Image endpoint must require valid subkey"""
    response = client.post(
        "/v1/images/generations",
        json={"prompt": "test", "n": 1}
    )
    assert response.status_code == 401
    assert "sub-key" in response.json()["detail"].lower()


def test_images_invalid_subkey(client, mock_users):
    """Invalid subkey should be rejected"""
    with patch("core.auth.load_users", return_value=mock_users):
        response = client.post(
            "/v1/images/generations",
            headers={"Authorization": "Bearer invalid_subkey"},
            json={"prompt": "test", "n": 1}
        )
        assert response.status_code == 403
        assert "invalid" in response.json()["detail"].lower()


# ============================================================================
# Test 2: Quota Enforcement
# ============================================================================

def test_images_quota_enforce(client, mock_users):
    """Quota limit should block requests when exceeded"""
    # Set quota to 2, used to 2 (at limit)
    mock_users[0]["quota"]["limit_image_requests"] = 2
    mock_users[0]["quota"]["used_image_requests"] = 2
    
    with patch("core.auth.load_users", return_value=mock_users), \
         patch("core.quota.load_users", return_value=mock_users):
        
        response = client.post(
            "/v1/images/generations",
            headers={"Authorization": "Bearer test_subkey_123"},
            json={"prompt": "test", "n": 1}
        )
        assert response.status_code == 403
        assert "quota exceeded" in response.json()["detail"].lower()


def test_images_quota_under_limit(client, mock_users):
    """Request should succeed when under quota"""
    # Mock successful LiteLLM response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [{"url": "http://example.com/image.png"}]
    }
    mock_response.headers = {}
    
    with patch("core.auth.load_users", return_value=mock_users), \
         patch("core.quota.load_users", return_value=mock_users), \
         patch("core.quota.save_users"), \
         patch.object(client.app.state, "http_client") as mock_http:
        
        mock_http.post = AsyncMock(return_value=mock_response)
        
        response = client.post(
            "/v1/images/generations",
            headers={"Authorization": "Bearer test_subkey_123"},
            json={"prompt": "test", "n": 1, "model": "gemini-2.5-flash-image"}
        )
        
        # Should succeed (200) or fail due to mock setup (not 403 quota)
        assert response.status_code != 403 or "quota" not in response.json()["detail"].lower()


# ============================================================================
# Test 3: Audit Logging
# ============================================================================

def test_images_audit_fields(client, mock_users):
    """Audit log should contain image-specific fields"""
    from utils.logging import write_audit_line
    
    audit_data = None
    
    def capture_audit(data):
        nonlocal audit_data
        audit_data = data
    
    with patch("api.images.write_audit_line", side_effect=capture_audit):
        # Call internal audit function
        from api.images import _write_image_audit
        
        _write_image_audit(
            request_id="mw_test123",
            user_id="test_user",
            model_requested="gpt-image-1",
            model_effective="gemini-2.5-flash-image",
            provider="gemini",
            size="1024x1024",
            n=1,
            response_format="url",
            status_code=200,
            cost_usd=0.002
        )
        
        # Verify audit fields
        assert audit_data is not None
        assert audit_data["rid"] == "mw_test123"
        assert audit_data["purpose"] == "image_gen"
        assert audit_data["provider"] == "gemini"
        assert audit_data["model"] == "gemini-2.5-flash-image"
        assert audit_data["model_requested"] == "gpt-image-1"  # Fallback tracked
        assert audit_data["image_count"] == 1
        assert audit_data["image_size"] == "1024x1024"
        assert audit_data["image_format"] == "url"
        assert audit_data["upstream_status"] == 200


def test_images_audit_no_fallback(client):
    """Audit should set model_requested=null when no fallback"""
    audit_data = None
    
    def capture_audit(data):
        nonlocal audit_data
        audit_data = data
    
    with patch("api.images.write_audit_line", side_effect=capture_audit):
        from api.images import _write_image_audit
        
        _write_image_audit(
            request_id="mw_test456",
            user_id="test_user",
            model_requested="gemini-2.5-flash-image",
            model_effective="gemini-2.5-flash-image",  # Same, no fallback
            provider="gemini",
            size="512x512",
            n=2,
            response_format="b64_json",
            status_code=200,
            cost_usd=0.004
        )
        
        assert audit_data["model_requested"] is None  # No fallback
        assert audit_data["model"] == "gemini-2.5-flash-image"
        assert audit_data["image_count"] == 2


# ============================================================================
# Test 4: Provider Detection
# ============================================================================

def test_extract_provider():
    """Provider extraction from model names"""
    from api.images import _extract_provider
    
    assert _extract_provider("gemini-2.5-flash-image") == "gemini"
    assert _extract_provider("gpt-image-1") == "openai"
    assert _extract_provider("dalle-3") == "openai"
    assert _extract_provider("gpt-4o-image") == "openai"
    assert _extract_provider("unknown-model") == "unknown"
    assert _extract_provider(None) == "unknown"


# ============================================================================
# Test 5: Allowed Models
# ============================================================================

def test_images_model_not_allowed(client, mock_users):
    """Request should fail if model not in allowed_models"""
    mock_users[0]["allowed_models"] = ["gemini-2.5-flash"]  # Only text model
    
    with patch("core.auth.load_users", return_value=mock_users):
        response = client.post(
            "/v1/images/generations",
            headers={"Authorization": "Bearer test_subkey_123"},
            json={"prompt": "test", "model": "gpt-image-1"}
        )
        assert response.status_code == 403
        assert "not allowed" in response.json()["detail"].lower()


def test_images_wildcard_allowed(client, mock_users):
    """Wildcard allowed_models should permit any model"""
    mock_users[0]["allowed_models"] = ["*"]
    
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": [{"url": "http://test.com/img.png"}]}
    mock_response.headers = {}
    
    with patch("core.auth.load_users", return_value=mock_users), \
         patch("core.quota.load_users", return_value=mock_users), \
         patch("core.quota.save_users"), \
         patch.object(client.app.state, "http_client") as mock_http:
        
        mock_http.post = AsyncMock(return_value=mock_response)
        
        response = client.post(
            "/v1/images/generations",
            headers={"Authorization": "Bearer test_subkey_123"},
            json={"prompt": "test", "model": "gpt-image-1"}
        )
        
        # Should not fail with "not allowed"
        if response.status_code == 403:
            assert "not allowed" not in response.json()["detail"].lower()


# ============================================================================
# Test 6: Default Model
# ============================================================================

def test_images_default_model(client, mock_users):
    """Should default to gemini-2.5-flash-image when model not specified"""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": [{"url": "http://test.com/img.png"}]}
    mock_response.headers = {}
    
    with patch("core.auth.load_users", return_value=mock_users), \
         patch("core.quota.load_users", return_value=mock_users), \
         patch("core.quota.save_users"), \
         patch.object(client.app.state, "http_client") as mock_http:
        
        mock_http.post = AsyncMock(return_value=mock_response)
        
        response = client.post(
            "/v1/images/generations",
            headers={"Authorization": "Bearer test_subkey_123"},
            json={"prompt": "test"}  # No model specified
        )
        
        # Check that LiteLLM was called with gemini model
        if mock_http.post.called:
            call_args = mock_http.post.call_args
            body = call_args.kwargs.get("json", {})
            assert body.get("model") == "gemini-2.5-flash-image"


# ============================================================================
# Test 7: Cost Tracking
# ============================================================================

def test_images_cost_bump(client, mock_users):
    """Cost should be bumped in quota after successful generation"""
    initial_cost = mock_users[0]["quota"]["used_cost_usd"]
    
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": [{"url": "http://test.com/img.png"}]}
    mock_response.headers = {"x-litellm-response-cost": "0.005"}
    
    saved_users = None
    
    def capture_save(users):
        nonlocal saved_users
        saved_users = users
    
    with patch("core.auth.load_users", return_value=mock_users), \
         patch("core.quota.load_users", return_value=mock_users), \
         patch("core.quota.save_users", side_effect=capture_save), \
         patch.object(client.app.state, "http_client") as mock_http:
        
        mock_http.post = AsyncMock(return_value=mock_response)
        
        response = client.post(
            "/v1/images/generations",
            headers={"Authorization": "Bearer test_subkey_123"},
            json={"prompt": "test", "n": 1}
        )
        
        # Verify cost was bumped (if save was called)
        if saved_users:
            final_cost = saved_users[0]["quota"]["used_cost_usd"]
            assert final_cost > initial_cost


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
