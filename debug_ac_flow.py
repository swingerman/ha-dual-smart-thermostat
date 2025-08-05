#!/usr/bin/env python3
"""Debug AC config flow to see what's happening."""

import asyncio
import os
import sys

# Add the custom_components path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "custom_components"))

from unittest.mock import Mock  # noqa: E402

from custom_components.dual_smart_thermostat.config_flow import (  # noqa: E402
    ConfigFlowHandler,
)
from custom_components.dual_smart_thermostat.const import (  # noqa: E402
    CONF_COOLER,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    SYSTEM_TYPE_AC_ONLY,
)


async def debug_ac_config_flow():
    """Debug the AC config flow to see what's happening."""
    print("🧪 Debugging AC Config Flow")
    print("=" * 50)

    flow = ConfigFlowHandler()
    flow.hass = Mock()
    flow.collected_config = {}

    # Step 1: User selects AC-only system
    print("\n📋 Step 1: System Type Selection")
    user_input = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY}
    result = await flow.async_step_user(user_input)

    print("Result type:", result.get("type"))
    print("Result step_id:", result.get("step_id"))
    print("Errors:", result.get("errors", {}))

    # Step 2: Cooling configuration
    print("\n📋 Step 2: Cooling Configuration")
    cooling_input = {
        CONF_COOLER: "switch.ac_unit",
        CONF_SENSOR: "sensor.temperature",
        "ac_mode": True,
    }

    print("Input:", cooling_input)
    result = await flow.async_step_cooling_only(cooling_input)

    print("Result type:", result.get("type"))
    print("Result step_id:", result.get("step_id"))
    print("Errors:", result.get("errors", {}))
    print("Collected config:", flow.collected_config)

    if result.get("errors"):
        print("❌ Validation errors found!")
        for field, error in result["errors"].items():
            print("   {}: {}".format(field, error))
    else:
        print("✅ No validation errors")


if __name__ == "__main__":
    asyncio.run(debug_ac_config_flow())
