"""
Migration script to add RBAC (role field) to users.json schema.

This script:
1. Backs up current users.json
2. Adds 'role' field to each user (default: 'user', first user gets 'admin')
3. Validates schema
4. Saves updated users.json

Run manually: python scripts/migrate_users_rbac.py
"""

import json
import os
import shutil
from datetime import datetime

def migrate_users_rbac():
    """Migrate users.json to add RBAC role field"""
    
    # Paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    users_file = os.path.join(base_dir, "llm-mw", "data", "users.json")
    
    if not os.path.exists(users_file):
        print(f"❌ users.json not found at {users_file}")
        return False
    
    # Backup
    backup_file = f"{users_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(users_file, backup_file)
    print(f"✅ Backed up to {backup_file}")
    
    # Load users
    with open(users_file, "r", encoding="utf-8") as f:
        users = json.load(f)
    
    print(f"📋 Found {len(users)} users")
    
    # Migrate each user
    modified_count = 0
    for i, user in enumerate(users):
        if "role" not in user:
            # First user gets admin, others get user
            if i == 0 or user.get("user_id") == "admin":
                user["role"] = "admin"
                print(f"  ✅ {user['user_id']}: role=admin")
            else:
                user["role"] = "user"
                print(f"  ✅ {user['user_id']}: role=user")
            modified_count += 1
        else:
            print(f"  ⏭️  {user['user_id']}: role already set ({user['role']})")
    
    if modified_count == 0:
        print("✅ All users already have role field, no migration needed")
        return True
    
    # Save updated users
    with open(users_file, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Migration complete: {modified_count} users updated")
    print(f"📁 Original backed up to: {backup_file}")
    
    return True


if __name__ == "__main__":
    print("="*60)
    print("USERS.JSON RBAC MIGRATION")
    print("="*60)
    print()
    
    success = migrate_users_rbac()
    
    print()
    if success:
        print("✅ MIGRATION SUCCESSFUL")
    else:
        print("❌ MIGRATION FAILED")
    
    print("="*60)
