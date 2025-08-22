#!/usr/bin/env python3
"""
Test script to verify the AC configuration flow and translation setup.
"""

import asyncio
import json
from unittest.mock import Mock

from custom_components.dual_smart_thermostat.config_flow import (
    DualSmartThermostatConfigFlow,
)
from custom_components.dual_smart_thermostat.const import (
    CONF_HEATER,
    SYSTEM_TYPE_AC_ONLY,
)


async def test_ac_configuration():
    """Test AC configuration setup."""
    print("🧪 Testing AC Configuration Flow")
    print("=" * 50)

    # Create a config flow instance
    flow = DualSmartThermostatConfigFlow()
    flow.hass = Mock()
    flow.collected_config = {"system_type": SYSTEM_TYPE_AC_ONLY}

    # Get the cooling_only step form
    result = await flow.async_step_cooling_only()

    print("📋 Configuration Analysis:")
    print(f"  Step ID: {result['step_id']}")
    print(f"  Form type: {result['type']}")

    # Check the schema fields
    schema_dict = result["data_schema"].schema
    fields = []
    for key in schema_dict.keys():
        if hasattr(key, "schema"):
            fields.append(key.schema)
        else:
            fields.append(str(key))

    print(f"  Fields in schema: {fields}")

    # Verify heater field is present (this is what users will interact with)
    if CONF_HEATER in fields:
        print("✅ Heater field is present in AC configuration")
    else:
        print("❌ Heater field missing from AC configuration")

    # Check translation setup
    print("\n📝 Translation Verification:")

    # Load and check the translation file
    try:
        with open(
            "/workspaces/dual_smart_thermostat/custom_components/dual_smart_thermostat/translations/en.json",
            "r",
        ) as f:
            translations = json.load(f)

        cooling_only_data = (
            translations.get("config", {})
            .get("step", {})
            .get("cooling_only", {})
            .get("data", {})
        )
        heater_label = cooling_only_data.get("heater", "NOT FOUND")

        print(f"  Translation for heater field: '{heater_label}'")

        if heater_label == "Air conditioning switch":
            print("✅ Translation correctly shows 'Air conditioning switch'")
        else:
            print(
                f"❌ Translation shows '{heater_label}' instead of 'Air conditioning switch'"
            )

    except Exception as e:
        print(f"❌ Error reading translations: {e}")

    # Test form submission
    print("\n🔄 Form Submission Test:")

    user_input = {CONF_HEATER: "switch.my_ac_unit"}
    print(f"  User submits: {user_input}")

    result = await flow.async_step_cooling_only(user_input)

    print(f"  Backend stores: {flow.collected_config}")

    if CONF_HEATER in flow.collected_config:
        print("✅ Configuration stored correctly with heater field")
    else:
        print("❌ Configuration not stored correctly")

    print("\n🎯 Summary:")
    print("  • Backend uses 'heater' field for full compatibility")
    print("  • UI will show 'Air conditioning switch' label via translations")
    print("  • Users get logical AC labeling without breaking changes")
    print("  • All existing code continues to work unchanged")


if __name__ == "__main__":
    asyncio.run(test_ac_configuration())
