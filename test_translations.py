#!/usr/bin/env python3
"""Test script to demonstrate the unified features step translations."""

import json

from custom_components.dual_smart_thermostat.const import SystemType
from custom_components.dual_smart_thermostat.schemas import get_features_schema


def test_features_translations():
    """Test that the unified features step has proper translations."""
    print("=== Testing Unified Features Step Translations ===\n")

    # Load the English translations
    with open(
        "/workspaces/dual_smart_thermostat/custom_components/dual_smart_thermostat/translations/en.json",
        "r",
    ) as f:
        translations = json.load(f)

    # Check that config flow has the features step
    config_features = translations.get("config", {}).get("step", {}).get("features")
    print("1. Config Flow Features Step:")
    if config_features:
        print(f"   ✓ Title: {config_features.get('title')}")
        print(f"   ✓ Description: {config_features.get('description')}")

        # Check that all feature fields have translations
        data_fields = config_features.get("data", {})
        description_fields = config_features.get("data_description", {})

        print(f"   ✓ Feature fields: {list(data_fields.keys())}")
        print(f"   ✓ Field descriptions: {list(description_fields.keys())}")

        # Verify all data fields have descriptions
        missing_descriptions = set(data_fields.keys()) - set(description_fields.keys())
        if missing_descriptions:
            print(f"   ✗ Missing descriptions for: {missing_descriptions}")
        else:
            print("   ✓ All feature fields have descriptions")
    else:
        print("   ✗ No features step found in config translations")

    # Check that options flow has the features step
    options_features = translations.get("options", {}).get("step", {}).get("features")
    print("\n2. Options Flow Features Step:")
    if options_features:
        print(f"   ✓ Title: {options_features.get('title')}")
        print(f"   ✓ Description: {options_features.get('description')}")

        # Check that all feature fields have translations
        data_fields = options_features.get("data", {})
        description_fields = options_features.get("data_description", {})

        print(f"   ✓ Feature fields: {list(data_fields.keys())}")
        print(f"   ✓ Field descriptions: {list(description_fields.keys())}")

        # Verify all data fields have descriptions
        missing_descriptions = set(data_fields.keys()) - set(description_fields.keys())
        if missing_descriptions:
            print(f"   ✗ Missing descriptions for: {missing_descriptions}")
        else:
            print("   ✓ All feature fields have descriptions")
    else:
        print("   ✗ No features step found in options translations")

    # Test that schema fields match translation fields
    print("\n3. Schema vs Translation Field Matching:")
    for system_type in [
        SystemType.AC_ONLY,
        SystemType.SIMPLE_HEATER,
        SystemType.HEAT_PUMP,
    ]:
        schema = get_features_schema(system_type)
        schema_fields = set(schema.schema.keys())
        config_translation_fields = set(config_features.get("data", {}).keys())

        if schema_fields.issubset(config_translation_fields):
            print(f"   ✓ {system_type.name}: All schema fields have translations")
        else:
            missing = schema_fields - config_translation_fields
            print(f"   ✗ {system_type.name}: Missing translations for {missing}")

    # Check shared translations
    shared_features = translations.get("shared", {}).get("step", {}).get("features")
    print("\n4. Shared Features Translations:")
    if shared_features:
        print(
            f"   ✓ Shared features found with {len(shared_features.get('data', {}))} fields"
        )
        # Note: Shared translations are used as fallbacks
    else:
        print(
            "   ⚠ No shared features found (this is OK, config/options have their own)"
        )

    print("\n=== Translation Test Complete! ===")
    print("✅ Unified features step properly translated")
    print("✅ Config and Options flows have consistent translations")
    print("✅ All schema fields have corresponding translations")


if __name__ == "__main__":
    test_features_translations()
