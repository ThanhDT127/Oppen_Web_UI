#!/usr/bin/env python
"""Quick test script to verify middleware setup"""
import sys
import os

# Ensure we're in the right directory
os.chdir(r'D:\Works\Oppen_Web_UI_fresh\llm-mw')
sys.path.insert(0, r'D:\Works\Oppen_Web_UI_fresh\llm-mw')

# Set environment variables
os.environ['MW_SECRET'] = 'test-secret-key-for-development-only-change-in-production'
os.environ['LITELLM_BASE'] = 'http://127.0.0.1:4000/v1'
os.environ['LITELLM_KEY'] = 'sk-1234'
os.environ['ADMIN_KEY'] = 'admin_master_key_456'

print("=" * 60)
print("TESTING MODULAR MIDDLEWARE")
print("=" * 60)

# Test imports
print("\n[1/5] Testing imports...")
try:
    import main
    print("✓ main.py imported successfully")
    print(f"  Routes registered: {len(main.app.routes)}")
except Exception as e:
    print(f"✗ Failed to import main.py: {e}")
    sys.exit(1)

# Test config
print("\n[2/5] Testing config module...")
try:
    from config import LITELLM_BASE, USERS_FILE, logger
    print(f"✓ Config loaded")
    print(f"  LITELLM_BASE: {LITELLM_BASE}")
    print(f"  USERS_FILE: {USERS_FILE}")
except Exception as e:
    print(f"✗ Config error: {e}")
    sys.exit(1)

# Test auth module
print("\n[3/5] Testing auth module...")
try:
    from core.auth import load_users, hash_subkey
    users = load_users()
    print(f"✓ Auth module working")
    print(f"  Users loaded: {len(users)}")
    test_hash = hash_subkey("test")
    print(f"  Hash function working: {test_hash[:16]}...")
except Exception as e:
    print(f"✗ Auth error: {e}")
    sys.exit(1)

# Test quota module
print("\n[4/5] Testing quota module...")
try:
    from core.quota import period_anchor_ms
    import datetime as dt
    anchor = period_anchor_ms('monthly', 'UTC')
    print(f"✓ Quota module working")
    print(f"  Period anchor: {dt.datetime.fromtimestamp(anchor/1000).strftime('%Y-%m-%d')}")
except Exception as e:
    print(f"✗ Quota error: {e}")
    sys.exit(1)

# Test cost module
print("\n[5/5] Testing cost module...")
try:
    from core.cost import load_prices, calc_cost_usd
    prices = load_prices()
    print(f"✓ Cost module working")
    print(f"  Prices loaded: {len(prices)} models")
except Exception as e:
    print(f"✗ Cost error: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("ALL TESTS PASSED ✓")
print("=" * 60)
print("\nReady to start server with:")
print("  uvicorn main:app --host 0.0.0.0 --port 5000")
