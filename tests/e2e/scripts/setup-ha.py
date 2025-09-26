#!/usr/bin/env python3
"""
Setup Home Assistant for E2E testing
Creates a user and bypasses onboarding
"""

import json
from pathlib import Path
import secrets
import sys


def create_user():
    """Create a test user in the auth storage"""
    # Generate a user ID (Home Assistant uses UUID-like format)
    user_id = secrets.token_hex(16)

    # Note: HA uses bcrypt for password hashing in real scenarios
    # For E2E testing, we just create the user structure

    user_data = {
        "id": user_id,
        "group_ids": ["system-admin"],
        "is_owner": True,
        "is_active": True,
        "name": "Test User",
        "system_generated": False,
        "local_only": True,
        "username": "testuser",
    }

    # Read existing auth file or create new one
    auth_file = Path("/config/.storage/auth")
    if auth_file.exists():
        with open(auth_file, "r") as f:
            auth_data = json.load(f)
    else:
        auth_data = {
            "version": 1,
            "minor_version": 1,
            "key": "auth",
            "data": {"users": []},
        }

    # Add our test user
    auth_data["data"]["users"].append(user_data)

    # Ensure storage directory exists
    auth_file.parent.mkdir(exist_ok=True)

    # Write updated auth file
    with open(auth_file, "w") as f:
        json.dump(auth_data, f, indent=2)

    print(f"✅ Created test user: {user_data['name']} (ID: {user_id})")


def create_onboarding_marker():
    """Create the onboarding completion marker"""
    onboarding_data = {
        "version": 4,
        "minor_version": 1,
        "key": "onboarding",
        "data": {
            "done": [
                "user",
                "core_config",
                "integration",
                "analytics",
                "integration",
                "core_config",
                "analytics",
            ]
        },
    }

    storage_dir = Path("/config/.storage")
    storage_dir.mkdir(exist_ok=True)

    onboarding_file = storage_dir / "onboarding"
    with open(onboarding_file, "w") as f:
        json.dump(onboarding_data, f, indent=2)

    print(f"✅ Created onboarding marker at {onboarding_file}")


def main():
    print("🔧 Setting up Home Assistant for E2E testing...")

    try:
        create_user()
        create_onboarding_marker()
        print("🎉 Setup complete! User created and onboarding bypassed.")
        return 0
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
