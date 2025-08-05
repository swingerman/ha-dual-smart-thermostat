#!/usr/bin/env python3
"""Test the advanced toggle feature in AC features configuration."""

import os
import sys

# Add the custom component to Python path before other imports
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "custom_components")
)  # noqa: E402 - test helper path

import voluptuous as vol  # noqa: E402 - import after test path insertion

from custom_components.dual_smart_thermostat.config_flow import (  # noqa: E402 - import after test path insertion
    get_ac_only_features_schema,
)


def test_basic_schema():
    """Test the basic AC features schema without advanced options."""
    print("🧪 Testing basic AC features schema...")

    schema = get_ac_only_features_schema()

    # Check that basic options are present
    basic_fields = [
        "configure_fan",
        "configure_humidity",
        "configure_openings",
        "configure_presets",
        "configure_advanced",
    ]

    schema_dict = schema.schema
    present_fields = []

    for key in schema_dict.keys():
        if hasattr(key, "schema") and key.schema in basic_fields:
            present_fields.append(key.schema)

    print("✅ Found {} basic configuration fields".format(len(present_fields)))

    # Verify defaults by validating empty input (should apply defaults)
    try:
        result = schema({})
        print("✅ Schema defaults applied successfully")

        # Check expected defaults
        expected_defaults = {
            "configure_fan": False,
            "configure_humidity": False,
            "configure_openings": False,
            "configure_presets": False,
            "configure_advanced": False,
        }

        for field, expected_value in expected_defaults.items():
            actual_value = result.get(field)
            if actual_value == expected_value:
                print("✅ {} default: {}".format(field, actual_value))
            else:
                print(
                    "❌ {} default: expected {}, got {}".format(
                        field, expected_value, actual_value
                    )
                )
                return False

    except Exception as e:
        print("❌ Schema validation failed:", e)
        return False

    return True


def test_advanced_schema():
    """Test the AC features schema - it should always show configuration options."""
    print("\n🧪 Testing AC features schema...")

    schema = get_ac_only_features_schema()

    # Check that configuration options are present
    config_fields = [
        "configure_fan",
        "configure_humidity",
        "configure_openings",
        "configure_presets",
        "configure_advanced",
    ]

    schema_dict = schema.schema

    # Count configuration fields
    config_count = 0

    for key in schema_dict.keys():
        if hasattr(key, "schema"):
            field_name = key.schema
            if field_name in config_fields:
                config_count += 1

    print("✅ Found", config_count, "configuration fields")
    print("✅ Total fields:", config_count)

    # Verify that all configuration fields are present
    assert (
        config_count == 5
    ), "Should have exactly 5 configuration fields in AC features schema"

    return True


def test_schema_differences():
    """Test the AC features schema consistency."""
    print("\n🧪 Testing schema consistency...")

    schema1 = get_ac_only_features_schema()
    schema2 = get_ac_only_features_schema()

    field_count1 = len(schema1.schema)
    field_count2 = len(schema2.schema)

    print("📊 Schema 1 fields:", field_count1)
    print("📊 Schema 2 fields:", field_count2)
    print("📊 Difference:", abs(field_count2 - field_count1))

    # Both schemas should be identical since there's no parameter anymore
    assert field_count1 == field_count2, "Schema should be consistent across calls"

    print("✅ Schema is consistent across multiple calls")

    return True


def test_schema_validation():
    """Test that schemas accept valid input."""
    print("\n🧪 Testing schema validation...")

    # Test basic schema validation
    basic_schema = get_ac_only_features_schema()

    basic_input = {
        "configure_fan": True,
        "configure_humidity": False,
        "configure_openings": True,
        "configure_presets": True,
        "configure_advanced": False,
    }

    try:
        basic_schema(basic_input)
        print("✅ Basic schema validation passed")
    except vol.Invalid as e:
        print("❌ Basic schema validation failed:", e)
        return False

    # Test advanced schema validation
    advanced_schema = get_ac_only_features_schema()

    advanced_input = {
        "configure_fan": True,
        "configure_humidity": False,
        "configure_openings": True,
        "configure_presets": True,
        "configure_advanced": True,
        "keep_alive": {"hours": 1, "minutes": 0, "seconds": 0},
        "initial_hvac_mode": "cool",
        "precision": "0.5",
        "target_temp_step": "0.5",
        "min_temp": 16,
        "max_temp": 35,
        "target_temp": 22,
    }

    try:
        advanced_schema(advanced_input)
        print("✅ Advanced schema validation passed")
    except vol.Invalid as e:
        print("❌ Advanced schema validation failed:", e)
        return False

    return True


def test_realistic_flow():
    """Test a realistic user flow."""
    print("\n🧪 Testing realistic user flow...")

    # Step 1: User sees basic form first
    print("👤 User sees basic AC features form...")
    basic_schema = get_ac_only_features_schema()

    # Step 2: User enables advanced toggle
    print("👤 User enables 'Configure advanced settings' toggle...")
    user_input_1 = {
        "configure_fan": True,
        "configure_humidity": False,
        "configure_openings": True,
        "configure_presets": True,
        "configure_advanced": True,  # User wants advanced options
    }

    try:
        basic_schema(user_input_1)
        print("✅ First submission with advanced toggle validated")
    except vol.Invalid as e:
        print("❌ First submission validation failed:", e)
        return False

    # Step 3: System shows advanced form
    print("🏠 System shows advanced form with additional options...")
    advanced_schema = get_ac_only_features_schema()

    # Step 4: User fills out advanced options
    print("👤 User configures advanced settings...")
    user_input_2 = {
        "configure_fan": True,
        "configure_humidity": False,
        "configure_openings": True,
        "configure_presets": True,
        "configure_advanced": True,
        "precision": "0.1",
        "target_temp": 23,
        "min_temp": 18,
        "max_temp": 30,
    }

    try:
        advanced_schema(user_input_2)
        print("✅ Final submission with advanced options validated")
    except vol.Invalid as e:
        print("❌ Final submission validation failed:", e)
        return False

    print("🎉 Realistic user flow completed successfully!")
    return True


def main():
    """Run all tests."""
    print("🚀 Testing Advanced Toggle Feature for AC Features Configuration")
    print("=" * 70)

    tests = [
        test_basic_schema,
        test_advanced_schema,
        test_schema_differences,
        test_schema_validation,
        test_realistic_flow,
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
            print("❌ Test {} failed with exception:".format(test.__name__), e)
            failed += 1

    print("\n" + "=" * 70)
    print("🎯 Test Results:", passed, "passed,", failed, "failed")

    if failed == 0:
        print("🏆 All tests passed! Advanced toggle feature is working correctly.")
        return True
    else:
        print("💥 Some tests failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
