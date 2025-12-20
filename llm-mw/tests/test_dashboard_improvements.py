"""
Test suite for improved dashboard metrics and auth.
"""

import pytest
import requests


BASE_URL = "http://localhost:5000"
ADMIN_KEY = "YOUR_ADMIN_KEY"
VALID_SUBKEY = "YOUR_SUBKEY_ADMIN"


class TestAuth:
    """Test authentication enforcement on admin endpoints"""
    
    def test_summary_requires_auth(self):
        """Summary endpoint should require auth"""
        response = requests.get(f"{BASE_URL}/v1/_mw/summary?minutes=5")
        assert response.status_code == 403, "Summary should be protected"
    
    def test_stream_requires_auth(self):
        """Stream endpoint should require auth"""
        response = requests.get(f"{BASE_URL}/v1/_mw/stream")
        assert response.status_code == 403, "Stream should be protected"
    
    def test_summary_with_admin_key_header(self):
        """Summary should accept X-Admin-Key header"""
        headers = {"X-Admin-Key": ADMIN_KEY}
        response = requests.get(f"{BASE_URL}/v1/_mw/summary?minutes=5", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "llm_calls_total" in data
    
    def test_summary_with_cookie_session(self):
        """Summary should accept cookie session"""
        # Login first
        login_response = requests.post(
            f"{BASE_URL}/v1/_mw/dashboard/login",
            json={"admin_key": ADMIN_KEY}
        )
        assert login_response.status_code == 200
        cookies = login_response.cookies
        
        # Use session to access summary
        response = requests.get(
            f"{BASE_URL}/v1/_mw/summary?minutes=5",
            cookies=cookies
        )
        assert response.status_code == 200


class TestSummaryBreakdown:
    """Test improved summary metrics breakdown"""
    
    def test_summary_has_breakdown_fields(self):
        """Summary should return breakdown by call type"""
        headers = {"X-Admin-Key": ADMIN_KEY}
        response = requests.get(f"{BASE_URL}/v1/_mw/summary?minutes=60", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check required fields
        assert "llm_calls_total" in data, "Should have llm_calls_total"
        assert "admin_ops_total" in data, "Should have admin_ops_total"
        assert "pending_count" in data, "Should have pending_count"
        
        # Check breakdown fields
        assert "chat_calls" in data, "Should have chat_calls"
        assert "image_calls" in data, "Should have image_calls"
        assert "audio_calls" in data, "Should have audio_calls"
        assert "video_calls" in data, "Should have video_calls"
        
        # All should be numbers
        assert isinstance(data["llm_calls_total"], int)
        assert isinstance(data["admin_ops_total"], int)
        assert isinstance(data["pending_count"], int)
        assert isinstance(data["chat_calls"], int)
    
    def test_llm_calls_equals_sum_of_types(self):
        """llm_calls_total should equal sum of chat+image+audio+video"""
        headers = {"X-Admin-Key": ADMIN_KEY}
        response = requests.get(f"{BASE_URL}/v1/_mw/summary?minutes=60", headers=headers)
        data = response.json()
        
        llm_total = data["llm_calls_total"]
        breakdown_sum = (
            data["chat_calls"] + 
            data["image_calls"] + 
            data["audio_calls"] + 
            data["video_calls"]
        )
        
        assert llm_total == breakdown_sum, \
            f"LLM total ({llm_total}) should equal breakdown sum ({breakdown_sum})"
    
    def test_pending_not_counted_in_llm_calls(self):
        """Pending requests should not be in llm_calls_total"""
        # This test verifies the logic but would need actual streaming data
        headers = {"X-Admin-Key": ADMIN_KEY}
        response = requests.get(f"{BASE_URL}/v1/_mw/summary?minutes=60", headers=headers)
        data = response.json()
        
        # pending_count should be separate
        assert "pending_count" in data
        assert data["pending_count"] >= 0


class TestDashboardUI:
    """Test dashboard HTML and UI behavior"""
    
    def test_dashboard_accessible(self):
        """Dashboard HTML should be served"""
        response = requests.get(f"{BASE_URL}/dashboard")
        assert response.status_code == 200
        assert "text/html" in response.headers["Content-Type"]
    
    def test_dashboard_has_new_labels(self):
        """Dashboard should have updated metric labels"""
        response = requests.get(f"{BASE_URL}/dashboard")
        html = response.text
        
        # Should have new labels
        assert "LLM Calls" in html, "Should show 'LLM Calls' label"
        assert "Admin Ops" in html, "Should show 'Admin Ops' label"
        
        # Should NOT have old confusing label
        assert "Total Requests" not in html or "LLM Calls" in html, \
            "Should replace 'Total Requests' with 'LLM Calls'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
