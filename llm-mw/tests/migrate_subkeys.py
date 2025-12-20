#!/usr/bin/env python3
"""
Migrate users.json from plaintext subkeys to hashed subkeys.
BACKUP users.json before running!

Usage:
    python migrate_subkeys.py
"""

import json
import os
import hashlib
import hmac
from datetime import datetime

USERS_FILE = "users.json"
BACKUP_FILE = f"users.json.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _hash_subkey(subkey: str, secret: str) -> str:
    """Generate HMAC-SHA256 hash matching main.py implementation."""
    return hmac.new(
        secret.encode("utf-8"),
        subkey.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def migrate():
    # Load MW_SECRET from environment
    secret = os.getenv("MW_SECRET", "")
    if not secret or secret == "default-secret-CHANGE-IN-PRODUCTION":
        print("ERROR: MW_SECRET not set or using default value!")
        print("Set MW_SECRET environment variable before migrating:")
        print("  export MW_SECRET='your-production-secret-here'")
        return False

    # Backup original file
    if not os.path.exists(USERS_FILE):
        print(f"ERROR: {USERS_FILE} not found!")
        return False

    print(f"Creating backup: {BACKUP_FILE}")
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        data = f.read()
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        f.write(data)

    # Load users
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        users = json.load(f)

    if not isinstance(users, list):
        users = [users]

    # Migrate each user
    migrated = 0
    for user in users:
        subkey = user.get("subkey", "")
        if subkey and "subkey_hash" not in user:
            user["subkey_hash"] = _hash_subkey(subkey, secret)
            # Remove plaintext subkey after migration (optional - keep for rollback)
            # del user["subkey"]
            migrated += 1
            print(f"✓ Migrated user: {user.get('user_id', 'unknown')}")
        elif "subkey_hash" in user:
            print(f"- Already migrated: {user.get('user_id', 'unknown')}")
        else:
            print(f"! No subkey found: {user.get('user_id', 'unknown')}")

    # Save migrated data
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Migration complete! Migrated {migrated} users.")
    print(f"✓ Backup saved: {BACKUP_FILE}")
    print("\nNOTE: Plaintext 'subkey' field kept for rollback compatibility.")
    print("After testing, you can manually remove 'subkey' fields from users.json")
    return True


if __name__ == "__main__":
    migrate()
