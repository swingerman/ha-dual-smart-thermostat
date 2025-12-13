"""Test for issue #461 - Redundant HVAC commands causing excessive beeping.

Reproduces the exact scenario from user's Hitachi AC configuration:
- Dual heater/cooler system (heat_cool mode)
- No keep_alive configured
- 0.2°C tolerances, 0.1°C precision
- Target temp 20°C
"""

import logging

from homeassistant.components import climate, input_boolean, input_number
from homeassistant.components.climate import HVACMode
from homeassistant.const import SERVICE_TURN_OFF, SERVICE_TURN_ON, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest

from custom_components.dual_smart_thermostat.const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_issue_461_ac_dual_system_sensor_updates(hass: HomeAssistant) -> None:
    """Test AC dual system with sensor updates matching user's exact config.

    User config:
    - Hitachi AC (beeps with each command)
    - Dual heater/cooler (heat_cool mode)
    - Target: 20°C, tolerance: 0.2°C, precision: 0.1°C
    - NO keep_alive
    - Reports: "beeps with each temperature change"
    """
    heater_switch = "input_boolean.bedroom_heat"
    cooler_switch = "input_boolean.bedroom_cool"
    sensor = "input_number.bedroom_temp"

    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(hass, "homeassistant", {})

    # Set up input entities
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {
            "input_boolean": {
                "bedroom_heat": None,
                "bedroom_cool": None,
            }
        },
    )

    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "bedroom_temp": {
                    "min": 0,
                    "max": 40,
                    "initial": 19.5,  # Start slightly below target
                    "step": 0.1,  # User's precision
                }
            }
        },
    )

    await hass.async_block_till_done()

    # Track service calls
    calls = []

    def _record_call(call_data):
        """Record service calls."""
        _LOGGER.info(f"Service call: {call_data.service} -> {call_data.data}")
        calls.append(call_data)

    hass.services.async_register("homeassistant", SERVICE_TURN_ON, _record_call)
    hass.services.async_register("homeassistant", SERVICE_TURN_OFF, _record_call)

    # Set up thermostat with user's exact configuration
    assert await async_setup_component(
        hass,
        climate.DOMAIN,
        {
            climate.DOMAIN: {
                "platform": DOMAIN,
                "name": "bedroom_ac",
                "heater": heater_switch,
                "cooler": cooler_switch,
                "target_sensor": sensor,
                "initial_hvac_mode": HVACMode.HEAT,  # User in heating mode
                "target_temp": 20.0,
                "cold_tolerance": 0.2,  # User's tolerance
                "hot_tolerance": 0.2,  # User's tolerance
                "precision": 0.1,  # User's precision
                # NO keep_alive - user confirmed no polling
            }
        },
    )
    await hass.async_block_till_done()

    # Simulate: temp is 19.5°C, target is 20°C, so heater should turn ON
    hass.states.async_set(sensor, 19.5)
    await hass.async_block_till_done()

    # Check heater turned on
    initial_calls = len([c for c in calls if c.service == SERVICE_TURN_ON])
    _LOGGER.info(f"Initial turn_on calls after setup: {initial_calls}")
    assert initial_calls > 0, "Heater should have turned on"

    # Clear calls and manually set heater ON
    calls.clear()
    hass.states.async_set(heater_switch, STATE_ON)
    hass.states.async_set(cooler_switch, STATE_OFF)
    await hass.async_block_till_done()

    # Now simulate what user experiences: small temperature fluctuations
    # Temperature sensor updates while heating is active
    # These are typical 0.1°C changes the user would see

    _LOGGER.info("=== Simulating temperature sensor updates ===")

    # Update 1: 19.6°C (still below target, heater should stay ON)
    hass.states.async_set(sensor, 19.6)
    await hass.async_block_till_done()

    # Update 2: 19.7°C (still below target)
    hass.states.async_set(sensor, 19.7)
    await hass.async_block_till_done()

    # Update 3: 19.8°C (approaching target, still in cold tolerance)
    hass.states.async_set(sensor, 19.8)
    await hass.async_block_till_done()

    # Update 4: Small fluctuation back down
    hass.states.async_set(sensor, 19.7)
    await hass.async_block_till_done()

    # Update 5: Back up
    hass.states.async_set(sensor, 19.8)
    await hass.async_block_till_done()

    # Check for redundant turn_on calls
    redundant_turn_on = [c for c in calls if c.service == SERVICE_TURN_ON]

    _LOGGER.info(
        f"Redundant turn_on calls after sensor updates: {len(redundant_turn_on)}"
    )
    for i, call in enumerate(redundant_turn_on):
        _LOGGER.info(f"  Call {i + 1}: {call.service} -> {call.data}")

    # ASSERTION: Should be 0 redundant commands
    assert len(redundant_turn_on) == 0, (
        f"BUG FOUND: turn_on was called {len(redundant_turn_on)} times even though "
        f"heater is already ON. This causes the AC to beep with each temperature update. "
        f"Calls: {redundant_turn_on}"
    )

    _LOGGER.info("✓ Test passed: No redundant commands with sensor updates")


@pytest.mark.parametrize("expected_lingering_timers", [True])
@pytest.mark.asyncio
async def test_issue_461_ac_cooling_with_default_keepalive(hass: HomeAssistant) -> None:
    """Test AC in cooling mode with DEFAULT keep_alive (300s).

    This reproduces the actual user issue:
    - AC in COOL mode (user's actual use case)
    - keep_alive defaults to 300 seconds (5 minutes) even if not explicitly set
    - Every 5 minutes, keep_alive sends turn_on to AC that's already ON
    - This causes the Hitachi AC to beep
    """
    from datetime import timedelta

    import homeassistant.util.dt as dt_util

    from tests.common import async_fire_time_changed

    heater_switch = "input_boolean.bedroom_heat"
    cooler_switch = "input_boolean.bedroom_cool"
    sensor = "input_number.bedroom_temp"

    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(hass, "homeassistant", {})

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"bedroom_heat": None, "bedroom_cool": None}},
    )

    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "bedroom_temp": {
                    "min": 0,
                    "max": 40,
                    "initial": 20.5,  # Above target for cooling
                    "step": 0.1,
                }
            }
        },
    )

    await hass.async_block_till_done()

    calls = []

    def _record_call(call_data):
        _LOGGER.info(f"AC Service call: {call_data.service} -> {call_data.data}")
        calls.append(call_data)

    hass.services.async_register("homeassistant", SERVICE_TURN_ON, _record_call)
    hass.services.async_register("homeassistant", SERVICE_TURN_OFF, _record_call)

    # User's config with DEFAULT keep_alive (300s)
    assert await async_setup_component(
        hass,
        climate.DOMAIN,
        {
            climate.DOMAIN: {
                "platform": DOMAIN,
                "name": "bedroom_ac",
                "heater": heater_switch,
                "cooler": cooler_switch,
                "target_sensor": sensor,
                "initial_hvac_mode": HVACMode.COOL,  # User is cooling
                "target_temp": 20.0,
                "cold_tolerance": 0.2,
                "hot_tolerance": 0.2,
                "precision": 0.1,
                "keep_alive": 300,  # DEFAULT value (5 minutes)
            }
        },
    )
    await hass.async_block_till_done()

    # Set temp above target - cooler should turn ON
    hass.states.async_set(sensor, 20.5)
    await hass.async_block_till_done()

    initial_calls = len([c for c in calls if c.service == SERVICE_TURN_ON])
    _LOGGER.info(f"Initial turn_on to cooler: {initial_calls}")
    assert initial_calls > 0, "Cooler should have turned on"

    calls.clear()
    hass.states.async_set(cooler_switch, STATE_ON)
    hass.states.async_set(heater_switch, STATE_OFF)
    await hass.async_block_till_done()

    _LOGGER.info("=== Simulating keep-alive triggering while AC is cooling ===")

    # Temperature is cooling, AC stays ON
    hass.states.async_set(sensor, 20.4)
    await hass.async_block_till_done()

    # Trigger keep-alive after 5 minutes (300 seconds)
    now = dt_util.utcnow()
    async_fire_time_changed(hass, now + timedelta(seconds=301))
    await hass.async_block_till_done()

    # Check for redundant turn_on command
    redundant_turn_on = [c for c in calls if c.service == SERVICE_TURN_ON]

    _LOGGER.info(f"Redundant turn_on calls after keep-alive: {len(redundant_turn_on)}")

    # BUG: Keep-alive sends turn_on even though AC is already ON!
    assert len(redundant_turn_on) > 0, (
        "Expected BUG to be reproduced: keep-alive should send redundant turn_on "
        "to AC that's already ON (causing beep)"
    )

    _LOGGER.info(
        f"✓ BUG REPRODUCED: AC received {len(redundant_turn_on)} redundant commands causing beeping!"
    )


@pytest.mark.parametrize("expected_lingering_timers", [True])
@pytest.mark.asyncio
async def test_issue_461_solution_disable_keepalive(hass: HomeAssistant) -> None:
    """Test SOLUTION for issue #461: Set keep_alive: 0 to disable it.

    Solution for users with beeping ACs:
    - Set keep_alive: 0 in configuration
    - This disables the keep-alive timer
    - No redundant commands will be sent
    """
    from datetime import timedelta

    import homeassistant.util.dt as dt_util

    from tests.common import async_fire_time_changed

    heater_switch = "input_boolean.bedroom_heat"
    cooler_switch = "input_boolean.bedroom_cool"
    sensor = "input_number.bedroom_temp"

    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(hass, "homeassistant", {})

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"bedroom_heat": None, "bedroom_cool": None}},
    )

    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "bedroom_temp": {
                    "min": 0,
                    "max": 40,
                    "initial": 20.5,
                    "step": 0.1,
                }
            }
        },
    )

    await hass.async_block_till_done()

    calls = []

    def _record_call(call_data):
        _LOGGER.info(f"Service call: {call_data.service} -> {call_data.data}")
        calls.append(call_data)

    hass.services.async_register("homeassistant", SERVICE_TURN_ON, _record_call)
    hass.services.async_register("homeassistant", SERVICE_TURN_OFF, _record_call)

    # SOLUTION: Set keep_alive: 0 to disable it
    assert await async_setup_component(
        hass,
        climate.DOMAIN,
        {
            climate.DOMAIN: {
                "platform": DOMAIN,
                "name": "bedroom_ac",
                "heater": heater_switch,
                "cooler": cooler_switch,
                "target_sensor": sensor,
                "initial_hvac_mode": HVACMode.COOL,
                "target_temp": 20.0,
                "cold_tolerance": 0.2,
                "hot_tolerance": 0.2,
                "precision": 0.1,
                "keep_alive": 0,  # SOLUTION: Set to 0 to disable keep-alive!
            }
        },
    )
    await hass.async_block_till_done()

    # Set temp above target - cooler should turn ON
    hass.states.async_set(sensor, 20.5)
    await hass.async_block_till_done()

    initial_calls = len([c for c in calls if c.service == SERVICE_TURN_ON])
    assert initial_calls > 0, "Cooler should have turned on"

    calls.clear()
    hass.states.async_set(cooler_switch, STATE_ON)
    hass.states.async_set(heater_switch, STATE_OFF)
    await hass.async_block_till_done()

    _LOGGER.info("=== Testing with keep_alive: 0 (disabled) ===")

    # Temperature is cooling, AC stays ON
    hass.states.async_set(sensor, 20.4)
    await hass.async_block_till_done()

    # Fast forward 5 minutes - keep-alive SHOULD NOT trigger since it's disabled
    now = dt_util.utcnow()
    async_fire_time_changed(hass, now + timedelta(seconds=301))
    await hass.async_block_till_done()

    # Check for redundant commands
    redundant_turn_on = [c for c in calls if c.service == SERVICE_TURN_ON]

    _LOGGER.info(
        f"Commands after 5 minutes with keep_alive: 0: {len(redundant_turn_on)}"
    )

    # SOLUTION VERIFIED: No redundant commands!
    assert len(redundant_turn_on) == 0, (
        f"With keep_alive: 0, no redundant commands should be sent. "
        f"Got {len(redundant_turn_on)} commands: {redundant_turn_on}"
    )

    _LOGGER.info("✓ SOLUTION VERIFIED: Setting keep_alive: 0 prevents beeping!")
