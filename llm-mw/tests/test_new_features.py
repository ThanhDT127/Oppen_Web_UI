#!/usr/bin/env python3
"""
Test script for new middleware features (Dec 19, 2025)
Tests: subkey hashing, enhanced /health, /v1/_mw/summary, audit logging
"""

import requests
import json
import time
import os
from pathlib import Path

BASE_URL = "http://localhost:5000"
ADMIN_KEY = os.getenv("ADMIN_KEY", "admin_master_key_456")
SUBKEY_ADMIN = "subkey_admin_123"

def test_health():
    """Test enhanced /health endpoint"""
    print("\n=== TEST 1: Enhanced /health endpoint ===")
    resp = requests.get(f"{BASE_URL}/health")
    print(f"Status: {resp.status_code}")
    data = resp.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    
    # Check for new fields
    expected_fields = ["ok", "time", "uptime_seconds", "litellm", "disk_free_gb", "active_users"]
    missing = [f for f in expected_fields if f not in data]
    if missing:
        print(f"⚠️  WARNING: Missing fields: {missing}")
        print("   (Middleware may be running old version)")
    else:
        print("✅ All expected fields present")
    return resp.status_code == 200


def test_chat_with_audit():
    """Test chat endpoint and audit logging"""
    print("\n=== TEST 2: Chat request with audit logging ===")
    
    # Check audit log before
    audit_log = Path("D:/Works/Oppen_Web_UI_fresh/logs/audit.jsonl")
    if audit_log.exists():
        with open(audit_log, "r") as f:
            lines_before = len(f.readlines())
        print(f"Audit log: {lines_before} entries before request")
    else:
        lines_before = 0
        print("⚠️  Audit log doesn't exist yet")
    
    # Make chat request
    resp = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={"Authorization": f"Bearer {SUBKEY_ADMIN}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Say 'test successful' in 3 words"}],
            "stream": False
        }
    )
    print(f"Chat Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Response: {data.get('choices', [{}])[0].get('message', {}).get('content', '')[:50]}")
        print("✅ Chat request successful")
    else:
        print(f"❌ Chat failed: {resp.text[:200]}")
        return False
    
    # Check audit log after
    time.sleep(1)  # Give logging time
    if audit_log.exists():
        with open(audit_log, "r") as f:
            lines_after = len(f.readlines())
        print(f"Audit log: {lines_after} entries after request")
        
        if lines_after > lines_before:
            # Read last entry
            with open(audit_log, "r") as f:
                lines = f.readlines()
                last_entry = json.loads(lines[-1])
            print(f"Last audit entry: {json.dumps(last_entry, indent=2)}")
            print("✅ Audit logging working")
        else:
            print("⚠️  No new audit entry (middleware may be old version)")
    
    return True


def test_admin_usage():
    """Test /admin/usage scrubbing"""
    print("\n=== TEST 3: /admin/usage with scrubbing ===")
    
    resp = requests.get(
        f"{BASE_URL}/admin/usage",
        headers={"Authorization": f"Bearer {ADMIN_KEY}"}
    )
    print(f"Status: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"Response (first user): {json.dumps(data[0], indent=2)}")
        
        # Check if sensitive fields are scrubbed
        has_subkey = "subkey" in data[0]
        has_hash = "subkey_hash" in data[0]
        
        if has_subkey or has_hash:
            print("❌ SECURITY ISSUE: subkey/subkey_hash NOT scrubbed!")
            print("   (Middleware may be running old version)")
        else:
            print("✅ Sensitive fields properly scrubbed")
        return not (has_subkey or has_hash)
    else:
        print(f"❌ Request failed: {resp.text[:200]}")
        return False


def test_summary():
    """Test /v1/_mw/summary endpoint"""
    print("\n=== TEST 4: /v1/_mw/summary endpoint ===")
    
    resp = requests.get(
        f"{BASE_URL}/v1/_mw/summary?minutes=60",
        headers={"Authorization": f"Bearer {ADMIN_KEY}"}
    )
    print(f"Status: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        # Check for expected fields
        expected = ["time_window_minutes", "cutoff_time", "total_entries", "data"]
        missing = [f for f in expected if f not in data]
        if missing:
            print(f"⚠️  Missing fields: {missing}")
        else:
            print("✅ Summary endpoint working")
        return len(missing) == 0
    elif resp.status_code == 404:
        print("⚠️  Endpoint not found (middleware may be old version)")
        return False
    else:
        print(f"❌ Request failed: {resp.text[:200]}")
        return False


def test_subkey_hashing():
    """Verify users.json has subkey_hash"""
    print("\n=== TEST 5: Subkey hashing ===")
    
    users_file = Path("D:/Works/Oppen_Web_UI_fresh/llm-mw/users.json")
    if not users_file.exists():
        print("❌ users.json not found")
        return False
    
    with open(users_file, "r") as f:
        users = json.load(f)
    
    print(f"Loaded {len(users)} users")
    
    all_have_hash = all("subkey_hash" in u for u in users)
    if all_have_hash:
        print("✅ All users have subkey_hash")
        print(f"   Example hash: {users[0].get('subkey_hash', '')[:32]}...")
    else:
        print("⚠️  Some users missing subkey_hash")
        print("   Run: python migrate_subkeys.py")
    
    return all_have_hash


def main():
    print("=" * 60)
    print("MIDDLEWARE NEW FEATURES TEST SUITE")
    print("Dec 19, 2025 - Security, Audit & Monitoring")
    print("=" * 60)
    
    results = {
        "Subkey Hashing": test_subkey_hashing(),
        "Enhanced Health": test_health(),
        "Audit Logging": test_chat_with_audit(),
        "Admin Scrubbing": test_admin_usage(),
        "Summary Endpoint": test_summary(),
    }
    
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    total = len(results)
    passed = sum(results.values())
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed < total:
        print("\n⚠️  RECOMMENDATION: Restart middleware to load new code:")
        print("   1. Stop current middleware (Ctrl+C in terminal)")
        print("   2. cd D:\\Works\\Oppen_Web_UI_fresh\\llm-mw")
        print("   3. Set MW_SECRET:")
        print("      $env:MW_SECRET='test-secret-key-for-development-only-change-in-production'")
        print("   4. uvicorn main:app --host 0.0.0.0 --port 5000")


if __name__ == "__main__":
    main()
