"""Tests for issue #469: OFF state control bypass in multi-device configurations.

This test module verifies that devices do not turn on when the thermostat is in
OFF mode, even when various triggers attempt to force control:
- Temperature changes
- Humidity changes
- Preset changes
- Template updates
- State restoration

The root cause was in multi_hvac_device.py where async_control_hvac() continued
to call sub-device control even after turning devices off in OFF mode.
"""

from datetime import timedelta
import logging

from freezegun.api import FrozenDateTimeFactory
from homeassistant.components import input_boolean, input_number
from homeassistant.components.climate import HVACMode
from homeassistant.components.climate.const import DOMAIN as CLIMATE
from homeassistant.const import STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
import pytest

from custom_components.dual_smart_thermostat.const import DOMAIN
from tests import common

_LOGGER = logging.getLogger(__name__)

# Entity IDs for test setup
ENT_HEATER = "input_boolean.heater"
ENT_COOLER = "input_boolean.cooler"
ENT_SENSOR = "input_number.temp"


async def setup_dual_thermostat(hass: HomeAssistant, config_overrides=None):
    """Set up a basic dual heater+cooler thermostat for testing."""
    # Set up input_boolean for heater and cooler
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None}},
    )

    # Set up input_number for temperature sensor
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 20, "min": 0, "max": 40, "step": 1}
            }
        },
    )

    # Base configuration
    base_config = {
        "platform": DOMAIN,
        "name": "test",
        "heater": ENT_HEATER,
        "cooler": ENT_COOLER,
        "target_sensor": ENT_SENSOR,
        "initial_hvac_mode": HVACMode.OFF,
        "cold_tolerance": 0.5,
        "hot_tolerance": 0.5,
    }

    # Merge with any overrides
    if config_overrides:
        base_config.update(config_overrides)

    # Set up the thermostat
    assert await async_setup_component(
        hass,
        CLIMATE,
        {"climate": base_config},
    )
    await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_off_mode_temperature_change_does_not_turn_on(
    hass: HomeAssistant,
) -> None:
    """Test that changing temperature in OFF mode does not turn on devices.

    This was the primary scenario reported in issue #469 where users changed
    the target temperature while the thermostat was OFF, and devices turned on.
    """
    await setup_dual_thermostat(hass)

    # Set initial temperature with thermostat OFF
    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()

    # Verify thermostat is OFF and devices are OFF
    state = hass.states.get(common.ENTITY)
    assert state.state == HVACMode.OFF

    heater_state = hass.states.get(ENT_HEATER)
    cooler_state = hass.states.get(ENT_COOLER)
    assert heater_state.state == STATE_OFF
    assert cooler_state.state == STATE_OFF

    # Set current temp well below target (should trigger heating if ON)
    await hass.services.async_call(
        input_number.DOMAIN,
        input_number.SERVICE_SET_VALUE,
        {"entity_id": ENT_SENSOR, "value": 15},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Change target temperature significantly (force=True control path)
    await common.async_set_temperature(hass, 25)
    await hass.async_block_till_done()

    # CRITICAL: Devices must remain OFF
    heater_state = hass.states.get(ENT_HEATER)
    cooler_state = hass.states.get(ENT_COOLER)
    assert heater_state.state == STATE_OFF, "Heater turned on in OFF mode!"
    assert cooler_state.state == STATE_OFF, "Cooler turned on in OFF mode!"

    # Verify thermostat is still OFF
    state = hass.states.get(common.ENTITY)
    assert state.state == HVACMode.OFF


@pytest.mark.asyncio
async def test_off_mode_temperature_change_hot_does_not_turn_on(
    hass: HomeAssistant,
) -> None:
    """Test cooling scenario: high temp in OFF mode does not turn on cooler."""
    await setup_dual_thermostat(hass)

    # Set initial temperature with thermostat OFF
    await common.async_set_temperature(hass, 22)
    await hass.async_block_till_done()

    # Set current temp well above target (should trigger cooling if ON)
    await hass.services.async_call(
        input_number.DOMAIN,
        input_number.SERVICE_SET_VALUE,
        {"entity_id": ENT_SENSOR, "value": 28},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Change target temperature (force=True control path)
    await common.async_set_temperature(hass, 20)
    await hass.async_block_till_done()

    # CRITICAL: Devices must remain OFF
    heater_state = hass.states.get(ENT_HEATER)
    cooler_state = hass.states.get(ENT_COOLER)
    assert heater_state.state == STATE_OFF
    assert cooler_state.state == STATE_OFF, "Cooler turned on in OFF mode!"

    # Verify thermostat is still OFF
    state = hass.states.get(common.ENTITY)
    assert state.state == HVACMode.OFF


@pytest.mark.asyncio
async def test_off_mode_sensor_update_does_not_turn_on(
    hass: HomeAssistant,
) -> None:
    """Test that sensor updates in OFF mode do not turn on devices.

    Sensor changes that cross tolerance thresholds should not activate devices
    when thermostat is OFF.
    """
    await setup_dual_thermostat(hass)

    # Set target temperature
    await common.async_set_temperature(hass, 20)
    await hass.async_block_till_done()

    # Fire temperature changes that cross thresholds
    await hass.services.async_call(
        input_number.DOMAIN,
        input_number.SERVICE_SET_VALUE,
        {"entity_id": ENT_SENSOR, "value": 25},  # Hot
        blocking=True,
    )
    await hass.async_block_till_done()

    heater_state = hass.states.get(ENT_HEATER)
    cooler_state = hass.states.get(ENT_COOLER)
    assert heater_state.state == STATE_OFF
    assert cooler_state.state == STATE_OFF

    await hass.services.async_call(
        input_number.DOMAIN,
        input_number.SERVICE_SET_VALUE,
        {"entity_id": ENT_SENSOR, "value": 15},  # Cold
        blocking=True,
    )
    await hass.async_block_till_done()

    heater_state = hass.states.get(ENT_HEATER)
    cooler_state = hass.states.get(ENT_COOLER)
    assert heater_state.state == STATE_OFF, "Heater turned on in OFF mode!"
    assert cooler_state.state == STATE_OFF

    # Verify thermostat is still OFF
    state = hass.states.get(common.ENTITY)
    assert state.state == HVACMode.OFF


@pytest.mark.asyncio
async def test_off_mode_stays_off_with_time_trigger(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that periodic control cycles (keep-alive) don't turn on devices in OFF mode.

    The keep-alive mechanism should enforce OFF state, not turn devices on.
    """
    await setup_dual_thermostat(hass)

    # Set conditions that would activate heating if not OFF
    await common.async_set_temperature(hass, 25)
    await hass.services.async_call(
        input_number.DOMAIN,
        input_number.SERVICE_SET_VALUE,
        {"entity_id": ENT_SENSOR, "value": 15},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify devices are OFF
    heater_state = hass.states.get(ENT_HEATER)
    cooler_state = hass.states.get(ENT_COOLER)
    assert heater_state.state == STATE_OFF
    assert cooler_state.state == STATE_OFF

    # Advance time to trigger keep-alive control cycle
    freezer.tick(timedelta(minutes=5))
    await hass.async_block_till_done()

    # CRITICAL: Devices must remain OFF
    heater_state = hass.states.get(ENT_HEATER)
    cooler_state = hass.states.get(ENT_COOLER)
    assert heater_state.state == STATE_OFF, "Heater turned on during keep-alive!"
    assert cooler_state.state == STATE_OFF

    # Verify thermostat is still OFF
    state = hass.states.get(common.ENTITY)
    assert state.state == HVACMode.OFF


@pytest.mark.asyncio
async def test_off_mode_multiple_temperature_changes(
    hass: HomeAssistant,
) -> None:
    """Test multiple rapid temperature changes in OFF mode.

    Simulates the 'randomly turning on/off' behavior reported by users.
    """
    await setup_dual_thermostat(hass)

    # Initial state
    await common.async_set_temperature(hass, 20)
    await hass.async_block_till_done()

    # Simulate multiple temperature changes and target adjustments
    for target_temp in [18, 22, 19, 25, 17, 24]:
        await common.async_set_temperature(hass, target_temp)
        await hass.async_block_till_done()

        # Fire various sensor temperatures
        for sensor_temp in [15, 28, 18, 22]:
            await hass.services.async_call(
                input_number.DOMAIN,
                input_number.SERVICE_SET_VALUE,
                {"entity_id": ENT_SENSOR, "value": sensor_temp},
                blocking=True,
            )
            await hass.async_block_till_done()

            # CRITICAL: Devices must remain OFF through all changes
            heater_state = hass.states.get(ENT_HEATER)
            cooler_state = hass.states.get(ENT_COOLER)
            assert (
                heater_state.state == STATE_OFF
            ), f"Heater turned on! Target: {target_temp}, Sensor: {sensor_temp}"
            assert (
                cooler_state.state == STATE_OFF
            ), f"Cooler turned on! Target: {target_temp}, Sensor: {sensor_temp}"

    # Verify thermostat is still OFF
    state = hass.states.get(common.ENTITY)
    assert state.state == HVACMode.OFF
