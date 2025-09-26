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
    print("• Only 4 system types available: simple_heater, ac_only, heater_cooler, heat_pump")
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
    print()

    # Check the fields in the AC features form
    print("📋 AC Features form fields:")
    for field in ac_features_schema.schema.keys():
        if hasattr(field, "schema"):
            field_name = field.schema
            if isinstance(field_name, str) and field_name.startswith("configure_"):
                print(f"   • {field_name}")
    print()

    # Verify the flow logic by checking the code
    try:
        with open("custom_components/dual_smart_thermostat/config_flow.py", "r") as f:
            content = f.read()

        # Check that AC features step redirects to advanced options
        redirect_found = "return await self.async_step_advanced_options()" in content

        # Check that options flow AC features doesn't use inline advanced
        # (we look for the specific options flow pattern)
        import re

        options_ac_features = re.search(
            r"async def async_step_ac_only_features.*?return self\.async_show_form\(",
            content,
            re.DOTALL,
        )

        inline_removed = True
        if options_ac_features:
            # In the options flow, it should use show_advanced=show_advanced (variable, not True)
            inline_removed = "show_advanced=True" not in options_ac_features.group(0)

        print("🔍 Code Analysis:")
        print(
            f"✅ Redirect to advanced step: {'FOUND' if redirect_found else 'MISSING'}"
        )
        print(
            f"✅ Options flow inline advanced removed: {'YES' if inline_removed else 'NO'}"
        )

        if redirect_found and inline_removed:
            print("\n🎯 SUCCESS: Advanced options now appear as separate step!")
            return True
if __name__ == "__main__":
    """Run the test."""
    if test_separate_advanced_step():
        print("🎉 Test passed!")
    else:
        print("❌ Test failed!")
        sys.exit(1)
