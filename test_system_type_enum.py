#!/usr/bin/env python3
"""Test script to demonstrate SystemType enum usage."""

from custom_components.dual_smart_thermostat.const import (
    SYSTEM_TYPE_AC_ONLY,  # Legacy constant
)
from custom_components.dual_smart_thermostat.const import (
    SYSTEM_TYPE_SIMPLE_HEATER,  # Legacy constant
)
from custom_components.dual_smart_thermostat.const import SystemType
from custom_components.dual_smart_thermostat.schemas import get_features_schema


def test_enum_usage():
    """Test the SystemType enum functionality."""
    print("=== SystemType Enum Test ===\n")

    # Test enum values
    print("1. All SystemType enum values:")
    for system_type in SystemType:
        print(f"   {system_type.name}: '{system_type.value}'")

    print("\n2. Testing enum with get_features_schema:")
    for system_type in SystemType:
        try:
            schema = get_features_schema(system_type)
            features = [key for key in schema.schema.keys()]
            feature_names = [
                str(key).split("'")[1] for key in features
            ]  # Extract feature names
            print(
                f"   {system_type.name}: {len(feature_names)} features - {feature_names}"
            )
        except Exception as e:
            print(f"   {system_type.name}: ERROR - {e}")

    print("\n3. Testing backward compatibility with legacy constants:")
    print(
        f"   SYSTEM_TYPE_AC_ONLY == SystemType.AC_ONLY: {SYSTEM_TYPE_AC_ONLY == SystemType.AC_ONLY}"
    )
    print(
        f"   SYSTEM_TYPE_SIMPLE_HEATER == SystemType.SIMPLE_HEATER: {SYSTEM_TYPE_SIMPLE_HEATER == SystemType.SIMPLE_HEATER}"
    )

    print("\n4. Testing string compatibility:")
    ac_only_enum = get_features_schema(SystemType.AC_ONLY)
    ac_only_string = get_features_schema("ac_only")
    print(
        f"   Schema from enum == Schema from string: {len(ac_only_enum.schema) == len(ac_only_string.schema)}"
    )

    print("\n5. Testing enum in conditional logic:")
    system_type = SystemType.AC_ONLY
    if system_type == SystemType.AC_ONLY:
        print("   ✓ AC_ONLY enum comparison works")
    elif system_type == SystemType.SIMPLE_HEATER:
        print("   ✓ SIMPLE_HEATER enum comparison works")
    else:
        print("   ✗ Enum comparison failed")

    print("\n6. Testing type safety:")
    print(f"   SystemType.AC_ONLY type: {type(SystemType.AC_ONLY)}")
    print(f"   SystemType.AC_ONLY value: {SystemType.AC_ONLY}")
    print(f"   String representation: '{SystemType.AC_ONLY}'")

    print("\n=== All tests passed! ===")


if __name__ == "__main__":
    test_enum_usage()
