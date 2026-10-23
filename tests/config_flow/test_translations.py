#!/usr/bin/env python3
"""
Test script to verify config flow translations are complete.
"""

import json
from pathlib import Path


def test_config_flow_translations():
    """Test that all config flow steps have proper translations."""

    print("🧪 Testing Config Flow Translations")
    print("=" * 50)

    # Load translations
    translations_path = Path(
        "custom_components/dual_smart_thermostat/translations/en.json"
    )
    with open(translations_path) as f:
        translations = json.load(f)

    # Expected config flow steps from the code
    expected_steps = [
        "user",
        "basic",
        "basic_ac_only",
        "heater_cooler",
        "heat_pump",
        "two_stage",
        "dual_stage",
        "dual_stage_config",
        "floor_heating",
        "floor_config",
        "heat_cool_mode",
        "fan",
        "humidity",
        "additional_sensors",
        "power_management",
        "presets",
    ]

    # Expected options flow steps
    expected_options_steps = [
        "init",
        "dual_stage_options",
        "floor_options",
        "fan_options",
        "humidity_options",
        "advanced_options",
    ]

    config_steps = translations["config"]["step"]
    options_steps = translations["options"]["step"]

    print("📋 Config Flow Steps:")
    missing_config = []
    for step in expected_steps:
        if step in config_steps:
            has_desc = "data_description" in config_steps[step]
            status = "✅" if has_desc else "⚠️"
            print(
                f"  {status} {step}: {'with descriptions' if has_desc else 'missing descriptions'}"
            )
        else:
            missing_config.append(step)
            print(f"  ❌ {step}: MISSING")

    print("\\n📋 Options Flow Steps:")
    missing_options = []
    for step in expected_options_steps:
        if step in options_steps:
            has_desc = "data_description" in options_steps[step]
            status = "✅" if has_desc else "⚠️"
            print(
                f"  {status} {step}: {'with descriptions' if has_desc else 'missing descriptions'}"
            )
        else:
            missing_options.append(step)
            print(f"  ❌ {step}: MISSING")

    print("\\n📊 Summary:")
    print(f"  • Config steps: {len(config_steps)}/{len(expected_steps)} present")
    print(
        f"  • Options steps: {len(options_steps)}/{len(expected_options_steps)} present"
    )

    if missing_config:
        print(f"  • Missing config steps: {', '.join(missing_config)}")
    if missing_options:
        print(f"  • Missing options steps: {', '.join(missing_options)}")

    # Test specific field that was reported missing
    print("\\n🔍 Testing target_sensor field:")
    for step_name, step_data in config_steps.items():
        if "target_sensor" in step_data.get("data", {}):
            has_desc = "target_sensor" in step_data.get("data_description", {})
            status = "✅" if has_desc else "❌"
            print(
                f"  {status} {step_name}: target_sensor {'with description' if has_desc else 'missing description'}"
            )

    if not missing_config and not missing_options:
        print("\\n✅ All translations are complete!")
        return True
    else:
        print("\\n⚠️ Some translations are missing!")
        return False


if __name__ == "__main__":
    test_config_flow_translations()


def test_climate_control_strings_exist_in_english():
    """The climate_control steps, their errors and the style options are translated."""
    with open("custom_components/dual_smart_thermostat/translations/en.json") as f:
        en = json.load(f)
    keys = {
        "control_style",
        "follow_device_changes",
        "heater_setpoint_offset",
        "cooler_setpoint_offset",
    }
    step = en["config"]["step"]["climate_control"]
    assert keys <= set(step["data"])
    assert keys <= set(step["data_description"])
    options = en["options"]["step"]["climate_control_options"]
    assert keys <= set(options["data"])
    assert keys <= set(options["data_description"])
    errors = {
        "sensor_required",
        "setpoint_heat_pump_unsupported",
        "setpoint_heat_cool_shared_climate",
        "setpoint_needs_heater_or_cooler",
    }
    assert errors <= set(en["config"]["error"])
    assert errors - {"sensor_required"} <= set(en["options"]["error"])
    assert {"on_off", "setpoint"} <= set(en["selector"]["control_style"]["options"])
