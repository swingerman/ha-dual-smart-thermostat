#!/usr/bin/env python3
"""Test the separate advanced options step behavior."""

import os
import sys

# Add the custom component to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def test_separate_advanced_step():
    """Test that the advanced system type is no longer available."""
    print("🔄 TESTING ADVANCED SYSTEM TYPE REMOVAL")
    print("=" * 60)

    print("📋 Updated Behavior:")
    print("• Advanced (Custom Setup) system type removed from SYSTEM_TYPES")
    print(
        "• Only 4 system types available: simple_heater, ac_only, heater_cooler, heat_pump"
    )
    print("• Advanced system type handling removed from config flows")
    print()

    # Test that advanced system type is not in SYSTEM_TYPES
    from custom_components.dual_smart_thermostat.const import SYSTEM_TYPES

    print(f"✅ Available system types: {len(SYSTEM_TYPES)}")
    for k, v in SYSTEM_TYPES.items():
        print(f"   • {k}: {v}")
    print()

    # Verify advanced is not present
    assert "advanced" not in SYSTEM_TYPES, "Advanced system type should be removed"
    assert len(SYSTEM_TYPES) == 4, "Should have exactly 4 system types"

    print("✅ Advanced (Custom Setup) system type successfully removed")
    print("✅ System now exposes only the 4 core system types")

    return True


if __name__ == "__main__":
    """Run the test."""
    if test_separate_advanced_step():
        print("🎉 Test passed!")
    else:
        print("❌ Test failed!")
        sys.exit(1)
