#!/usr/bin/env python3
"""
Setup Home Assistant for E2E testing
Creates a user and bypasses onboarding
"""

import json
from pathlib import Path
import sys


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
        create_onboarding_marker()
        print("🎉 Setup complete! Onboarding bypassed.")
        return 0
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
