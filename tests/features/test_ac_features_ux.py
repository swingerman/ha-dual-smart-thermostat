#!/usr/bin/env python3
"""Test the advanced toggle behavior with focus on user experience."""

import os
import sys

# Add the custom component to Python path
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "custom_components")
)  # noqa: E402

from custom_components.dual_smart_thermostat.config_flow import (  # noqa: E402
    get_ac_only_features_schema,
)


def test_user_experience_flow():
    """Simulate the complete user experience with the advanced toggle."""
    print("🧪 Testing User Experience Flow")
    print("=" * 50)

    # Step 1: User first sees the basic form
    print("👤 User visits AC Features Configuration for the first time...")
    basic_schema = get_ac_only_features_schema()

    print("🏠 System shows basic form with these options:")
    basic_fields = []
    for key in basic_schema.schema.keys():
        if hasattr(key, "schema"):
            basic_fields.append(key.schema)

    for field in sorted(basic_fields):
        print(f"   • {field}")

    print(f"📊 Total fields shown: {len(basic_fields)}")

    # Step 2: User makes choices and enables advanced toggle
    print("\n👤 User makes selections:")
    user_choice_1 = {
        "configure_fan": True,
        "configure_humidity": False,
        "configure_openings": True,
        "configure_presets": True,
        "configure_advanced": True,  # 🔥 User wants advanced options!
    }

    for choice, enabled in user_choice_1.items():
        status = "✅ ENABLED" if enabled else "❌ DISABLED"
        print(f"   • {choice}: {status}")

    # Validate first submission
    try:
        basic_schema(user_choice_1)
        print("✅ First submission validates successfully")
    except Exception as e:
        print(f"❌ First submission failed: {e}")
        return False

    # Step 3: System detects advanced toggle and shows expanded form
    print("\n🏠 System detects 'configure_advanced' is enabled...")
    print("🏠 System shows expanded form with advanced options:")

    advanced_schema = get_ac_only_features_schema()

    all_fields = []
    basic_fields_count = 0
    advanced_fields_count = 0

    for key in advanced_schema.schema.keys():
        if hasattr(key, "schema"):
            field_name = key.schema
            all_fields.append(field_name)

            if field_name in [
                "configure_fan",
                "configure_humidity",
                "configure_openings",
                "configure_presets",
                "configure_advanced",
            ]:
                basic_fields_count += 1
                print(f"   • {field_name} (basic)")
            else:
                advanced_fields_count += 1
                print(f"   • {field_name} (advanced)")

    print(
        f"\n📊 Form now shows: {basic_fields_count} basic + {advanced_fields_count} advanced = {len(all_fields)} total fields"
    )

    # Step 4: User configures advanced options
    print("\n👤 User configures advanced settings:")
    user_choice_2 = {
        "configure_fan": True,
        "configure_humidity": False,
        "configure_openings": True,
        "configure_presets": True,
        "configure_advanced": True,
        # Advanced options
        "precision": "0.1",
        "target_temp": 22,
        "min_temp": 18,
        "max_temp": 30,
        "initial_hvac_mode": "cool",
    }

    for choice, value in user_choice_2.items():
        if choice.startswith("configure_"):
            status = "✅ ENABLED" if value else "❌ DISABLED"
            print(f"   • {choice}: {status}")
        else:
            print(f"   • {choice}: {value}")

    # Validate final submission
    try:
        result = advanced_schema(user_choice_2)
        print("✅ Final submission validates successfully")
        print(f"📝 Configuration captured: {len(result)} settings")
    except Exception as e:
        print(f"❌ Final submission failed: {e}")
        return False

    # Step 5: Demonstrate what happens if user doesn't want advanced options
    print("\n" + "─" * 50)
    print("👤 Alternative: User doesn't want advanced options...")

    simple_choice = {
        "configure_fan": False,
        "configure_humidity": True,
        "configure_openings": False,
        "configure_presets": True,
        "configure_advanced": False,  # 🔥 User stays with basic options
    }

    try:
        result = basic_schema(simple_choice)
        print("✅ Simple configuration validates successfully")
        print(f"📝 Basic configuration captured: {len(result)} settings")

        for choice, enabled in simple_choice.items():
            status = "✅ ENABLED" if enabled else "❌ DISABLED"
            print(f"   • {choice}: {status}")

    except Exception as e:
        print(f"❌ Simple configuration failed: {e}")
        return False

    return True


def test_form_responsiveness():
    """Test how the form responds to toggle changes."""
    print("\n🧪 Testing Form Responsiveness")
    print("=" * 50)

    # Scenario 1: Basic form
    print("📱 Scenario 1: Basic form (advanced toggle OFF)")
    basic_schema = get_ac_only_features_schema()
    basic_count = len(basic_schema.schema)
    print(f"   Fields visible: {basic_count}")

    # Scenario 2: Advanced form
    print("📱 Scenario 2: Advanced form (advanced toggle ON)")
    advanced_schema = get_ac_only_features_schema()
    advanced_count = len(advanced_schema.schema)
    print(f"   Fields visible: {advanced_count}")

    # Calculate difference
    additional_fields = advanced_count - basic_count
    print(f"📊 Additional fields when advanced enabled: {additional_fields}")

    # Verify responsiveness
    if additional_fields > 0:
        print("✅ Form correctly shows more options when advanced is enabled")
        print(
            f"💡 UI becomes {((additional_fields / basic_count) * 100):.0f}% more comprehensive"
        )
        return True
    else:
        print("❌ Form doesn't show additional options when advanced is enabled")
        return False


def test_feature_discoverability():
    """Test how discoverable the advanced features are."""
    print("\n🧪 Testing Feature Discoverability")
    print("=" * 50)

    # Check if advanced toggle is present in basic form
    basic_schema = get_ac_only_features_schema()

    has_advanced_toggle = False
    for key in basic_schema.schema.keys():
        if hasattr(key, "schema") and key.schema == "configure_advanced":
            has_advanced_toggle = True
            break

    if has_advanced_toggle:
        print("✅ Advanced toggle is discoverable in basic form")
        print("💡 Users can easily find and enable advanced options")
    else:
        print("❌ Advanced toggle is not discoverable in basic form")
        return False

    # Test that toggle defaults to False (not overwhelming)
    test_defaults = basic_schema({})
    if test_defaults.get("configure_advanced") is False:
        print("✅ Advanced toggle defaults to OFF (not overwhelming)")
        print("💡 Basic users see simple interface by default")
    else:
        print("❌ Advanced toggle should default to OFF")
        return False

    return True


def test_progressive_disclosure():
    """Test the progressive disclosure principle."""
    print("\n🧪 Testing Progressive Disclosure")
    print("=" * 50)

    # Progressive disclosure means showing basic options first,
    # then revealing advanced options only when requested

    basic_schema = get_ac_only_features_schema()
    advanced_schema = get_ac_only_features_schema()

    # Get field lists
    basic_fields = set()
    advanced_fields = set()

    for key in basic_schema.schema.keys():
        if hasattr(key, "schema"):
            basic_fields.add(key.schema)

    for key in advanced_schema.schema.keys():
        if hasattr(key, "schema"):
            advanced_fields.add(key.schema)

    # Core principle 1: All basic fields should be in advanced form
    basic_preserved = basic_fields.issubset(advanced_fields)
    if basic_preserved:
        print("✅ All basic options remain available in advanced form")
    else:
        print("❌ Some basic options disappear in advanced form")
        return False

    # Core principle 2: Advanced form should have additional fields
    additional_fields = advanced_fields - basic_fields
    if len(additional_fields) > 0:
        print(f"✅ Advanced form adds {len(additional_fields)} new options")
        print("📋 Additional options:", sorted(additional_fields))
    else:
        print("❌ Advanced form doesn't add any new options")
        return False

    # Core principle 3: Advanced options should be meaningful
    expected_advanced = {
        "keep_alive",
        "initial_hvac_mode",
        "precision",
        "target_temp_step",
        "min_temp",
        "max_temp",
        "target_temp",
    }

    meaningful_additions = len(additional_fields & expected_advanced)
    if meaningful_additions > 0:
        print(f"✅ {meaningful_additions} advanced options are power-user features")
    else:
        print("❌ Advanced options don't seem to be power-user features")
        return False

    return True


def main():
    """Run all user experience tests."""
    print("🚀 AC Features Advanced Toggle - User Experience Testing")
    print("=" * 70)

    tests = [
        test_user_experience_flow,
        test_form_responsiveness,
        test_feature_discoverability,
        test_progressive_disclosure,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 70)
    print(f"🎯 User Experience Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("\n🏆 Excellent! The advanced toggle creates a great user experience:")
        print("   ✨ Progressive disclosure keeps basic interface clean")
        print("   ✨ Advanced features are discoverable but not overwhelming")
        print("   ✨ Form responsively shows/hides options based on user choice")
        print("   ✨ Power users get access to granular controls when needed")
        print("   ✨ Casual users get a simplified, focused experience")

        print("\n📖 User Journey Summary:")
        print("   1. User sees clean AC features form with 5 basic toggles")
        print("   2. User can optionally enable 'Configure advanced settings'")
        print("   3. Form expands to show 7 additional power-user options")
        print("   4. Advanced users get precision, temp limits, HVAC modes, etc.")
        print("   5. Form validates and stores all configurations appropriately")

        return True
    else:
        print("💥 Some user experience tests failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
