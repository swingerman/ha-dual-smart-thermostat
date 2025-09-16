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

    # Mock config entry for AC-only system
    mock_config_entry = Mock()
    mock_config_entry.data = {
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY,
        CONF_HEATER: "switch.ac_unit",
        CONF_SENSOR: "sensor.temperature",
        CONF_COLD_TOLERANCE: 0.3,
        CONF_HOT_TOLERANCE: 0.3,
        CONF_MIN_DUR: {"minutes": 5},
    }

    # Create handler
    handler = OptionsFlowHandler(mock_config_entry)

    # Test flow progression to identify all steps
    steps_visited = []

    # Start with init step (system type selection)
    result = await handler.async_step_init({CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY})
    assert result["type"] == "form"
    assert result["step_id"] == "basic"
    steps_visited.append("init")

    # Core step (main system configuration)
    result = await handler.async_step_basic(
        {
            CONF_HEATER: "switch.ac_unit",
            CONF_SENSOR: "sensor.temperature",
            CONF_COLD_TOLERANCE: 0.3,
            CONF_HOT_TOLERANCE: 0.3,
            CONF_MIN_DUR: {"minutes": 5},
        }
    )
    assert result["type"] == "form"
    steps_visited.append("core")
    print(f"After core step, next step is: {result['step_id']}")

    # Fan toggle step - ENABLE the fan
    if result["step_id"] == "fan_toggle":
        steps_visited.append("fan_toggle")
        result = await handler.async_step_fan_toggle({"enable_fan": True})
        assert result["type"] == "form"
        print(f"After fan toggle (enabled), next step is: {result['step_id']}")

    # Fan options step
    if result["step_id"] == "fan_options":
        steps_visited.append("fan_options")
        result = await handler.async_step_fan_options({})
        assert result["type"] == "form"
        print(f"After fan options, next step is: {result['step_id']}")

    # Humidity toggle step - ENABLE humidity
    if result["step_id"] == "humidity_toggle":
        steps_visited.append("humidity_toggle")
        result = await handler.async_step_humidity_toggle({"enable_humidity": True})
        assert result["type"] == "form"
        print(f"After humidity toggle (enabled), next step is: {result['step_id']}")

    # Continue through the flow to see all steps
    current_step = result["step_id"]
    max_iterations = 10  # Prevent infinite loops
    iteration = 0

    while current_step != "final" and iteration < max_iterations:
        iteration += 1
        steps_visited.append(current_step)

        # Get the appropriate step method
        step_method = getattr(handler, f"async_step_{current_step}")

        # Call with empty input to see next step
        try:
            result = await step_method({})
            if result["type"] == "create_entry":
                # We've reached the end
                steps_visited.append("create_entry")
                break
            elif result["type"] == "form":
                current_step = result["step_id"]
                print(f"Next step: {current_step}")
            else:
                print(f"Unexpected result type: {result['type']}")
                break
        except Exception as e:
            print(f"Error in step {current_step}: {e}")
            break

    print(f"\nSteps visited in options flow: {steps_visited}")

    # Check that we have the key steps including both fan_options and humidity_options since we enabled them
    required_steps = [
        "core",
        "fan_toggle",
        "fan_options",
        "humidity_toggle",
        "humidity_options",
        "openings_options",
        "advanced_options",
        "preset_selection",
    ]
    missing_steps = [step for step in required_steps if step not in steps_visited]

    if missing_steps:
        print(f"❌ MISSING STEPS: {missing_steps}")
        return False
    else:
        print("✅ All required steps are present in the options flow")
        print("✅ Fan options appeared (fan was enabled)")
        print("✅ Humidity options appeared (humidity was enabled)")
        return True


if __name__ == "__main__":
    success = asyncio.run(test_ac_only_options_flow_with_fan_and_humidity_enabled())
    if not success:
        sys.exit(1)
    print("✅ Options flow completeness test with fan and humidity enabled passed!")
