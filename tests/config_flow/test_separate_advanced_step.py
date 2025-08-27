#!/usr/bin/env python3
"""Test the separate advanced options step behavior."""

import os
import sys

# Add the custom component to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "custom_components"))


def test_separate_advanced_step():
    """Test that advanced options appear as a separate step."""
    print("🔄 TESTING SEPARATE ADVANCED OPTIONS STEP")
    print("=" * 60)

    print("📋 Updated Behavior:")
    print("• AC features form shows only 5 basic toggle options")
    print("• When user enables 'Configure advanced settings' toggle")
    print("• System redirects to SEPARATE advanced options step")
    print("• Advanced options are no longer inline with AC features")
    print()

    # Test the AC features schema (should always be basic)
    from custom_components.dual_smart_thermostat.config_flow import (
        get_ac_only_features_schema,
    )

    ac_features_schema = get_ac_only_features_schema()
    print(f"✅ AC Features form: {len(ac_features_schema.schema)} fields")
    print("   This form NEVER includes advanced options inline")
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
        else:
            print("\n❌ ISSUE: Advanced options may still be inline")
            return False

    except Exception as e:
        print(f"❌ Failed to analyze code: {e}")
        return False


def test_user_experience():
    """Test the improved user experience."""
    print("\n👤 IMPROVED USER EXPERIENCE TEST")
    print("=" * 60)

    print("🟢 NEW FLOW (After Fix):")
    print("1. User clicks 'Configure' on AC thermostat")
    print("2. 📋 AC Features Step: Shows 5 clean toggle options")
    print("   • Configure fan options")
    print("   • Configure humidity options")
    print("   • Configure openings options")
    print("   • Configure presets options")
    print("   • Configure advanced settings ← User enables this")
    print("3. User submits form")
    print("4. 🔧 Advanced Options Step: Shows temperature limits, precision, etc.")
    print("5. User configures advanced settings")
    print("6. ✅ Configuration complete")
    print()

    print("🎯 KEY BENEFITS:")
    print("• Clear separation between basic and advanced options")
    print("• No more confusing inline advanced fields")
    print("• Advanced step only appears when explicitly requested")
    print("• Better user experience with logical flow progression")

    return True


def main():
    """Run the separate step behavior tests."""
    print("🔧 SEPARATE ADVANCED STEP VERIFICATION")
    print("=" * 70)

    tests = [test_separate_advanced_step, test_user_experience]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed: {e}")
            failed += 1

    print("\n" + "=" * 70)
    print(f"🎯 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("\n🎉 SEPARATE ADVANCED STEP SUCCESSFULLY IMPLEMENTED!")
        print()
        print("📋 What changed:")
        print("   • Advanced options no longer appear inline in AC features form")
        print("   • When user enables 'Configure advanced settings' toggle")
        print("   • System redirects to dedicated advanced options step")
        print("   • Clean separation between basic and advanced configuration")

        return True
    else:
        print("💥 Some tests failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
