#!/usr/bin/env python3

"""Test options flow completeness with both fan and humidity enabled."""

import asyncio
import os
import sys
from unittest.mock import Mock

# Add the custom component to the path
sys.path.insert(  # noqa: E402 - test helper adds local path for imports
    0,
    os.path.join(
        os.path.dirname(__file__), "custom_components", "dual_smart_thermostat"
    ),
)

from custom_components.dual_smart_thermostat.const import (  # noqa: E402
    CONF_COLD_TOLERANCE,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_MIN_DUR,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    SYSTEM_TYPE_AC_ONLY,
)
from custom_components.dual_smart_thermostat.options_flow import (  # noqa: E402
    OptionsFlowHandler,
)


async def test_ac_only_options_flow_with_fan_and_humidity_enabled():
    """Test that AC-only options flow includes both fan and humidity options when enabled."""
    print("Testing AC-only options flow completeness with fan and humidity enabled...")

    # Mock config entry for AC-only system with features already configured
    mock_config_entry = Mock()
    mock_config_entry.data = {
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY,
        CONF_HEATER: "switch.ac_unit",
        CONF_SENSOR: "sensor.temperature",
        CONF_COLD_TOLERANCE: 0.3,
        CONF_HOT_TOLERANCE: 0.3,
        CONF_MIN_DUR: {"minutes": 5},
        # Pre-configure fan and humidity features
        "fan": "switch.fan",
        "humidity_sensor": "sensor.humidity",
        # Pre-configure openings
        "openings": ["binary_sensor.window"],
        # Pre-configure presets
        "presets": ["away", "home"],
        "away_temp": 16,
        "home_temp": 21,
    }
    mock_config_entry.options = {}

    # Create handler
    handler = OptionsFlowHandler(mock_config_entry)
    handler.hass = Mock()

    # Test flow progression to identify all steps
    steps_visited = []

    # Start with init step (runtime tuning parameters)
    result = await handler.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "init"
    steps_visited.append("init")
    print("✅ Init step shows runtime tuning parameters")

    # Submit init step with runtime tuning
    result = await handler.async_step_init(
        {
            CONF_COLD_TOLERANCE: 0.3,
            CONF_HOT_TOLERANCE: 0.3,
        }
    )
    # After init, flow should proceed to feature-specific options
    print(
        f"After init step, result type: {result['type']}, step: {result.get('step_id', 'N/A')}"
    )

    # Continue through the flow to see all steps
    max_iterations = 10  # Prevent infinite loops
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        if result["type"] == "create_entry":
            # We've reached the end
            steps_visited.append("create_entry")
            break
        elif result["type"] == "form":
            current_step = result["step_id"]
            steps_visited.append(current_step)
            print(f"Next step: {current_step}")

            # Get the appropriate step method
            step_method = getattr(handler, f"async_step_{current_step}")

            # Call with empty input to see next step
            try:
                result = await step_method({})
            except Exception as e:
                print(f"Error in step {current_step}: {e}")
                break
        else:
            print(f"Unexpected result type: {result['type']}")
            break

    print(f"\nSteps visited in options flow: {steps_visited}")

    # Check that we have the key steps - since features are pre-configured,
    # they should appear in the flow for tuning
    expected_steps = [
        "init",  # Runtime tuning
        "fan_options",  # Fan is configured
        "humidity_options",  # Humidity is configured
        "openings_options",  # Openings are configured
        "preset_selection",  # Presets are configured
    ]

    missing_steps = [step for step in expected_steps if step not in steps_visited]

    if missing_steps:
        print(f"❌ MISSING STEPS: {missing_steps}")
        return False
    else:
        print("✅ All required steps are present in the options flow")
        print("✅ Fan options appeared (fan was pre-configured)")
        print("✅ Humidity options appeared (humidity was pre-configured)")
        print("✅ Openings options appeared (openings were pre-configured)")
        print("✅ Preset selection appeared (presets were pre-configured)")
        return True


if __name__ == "__main__":
    success = asyncio.run(test_ac_only_options_flow_with_fan_and_humidity_enabled())
    if not success:
        sys.exit(1)
    print("✅ Options flow completeness test with fan and humidity enabled passed!")
