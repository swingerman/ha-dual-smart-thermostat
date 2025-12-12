"""Test for issue #10 - Tolerance/precision behavior in heat/cool mode.

Issue: https://github.com/swingerman/ha-dual-smart-thermostat/issues/10

In heating mode (within heat/cool mode), if tolerance is set to 1F and precision to 0.1F,
and the setpoint to 68F, it turns on at 66.9F but turns off right away when it gets to 67.1F.

Expected behavior: Turn on at 67F (68 - 1), turn off at 68F.
Actual behavior: Turn on at 66.9F, turn off at 67.1F.
"""

import logging

from homeassistant.components.climate import DOMAIN as CLIMATE, HVACMode
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
import homeassistant.core as ha
from homeassistant.core import callback
from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM
import pytest

from custom_components.dual_smart_thermostat.const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ATTR_TARGET_TEMP_HIGH = "target_temp_high"
ATTR_TARGET_TEMP_LOW = "target_temp_low"
SERVICE_SET_TEMPERATURE = "set_temperature"


def _setup_sensor(hass, sensor, temp):
    """Set up the test sensor."""
    hass.states.async_set(sensor, temp)


async def async_set_temperature(
    hass,
    temperature=None,
    entity_id="all",
    target_temp_high=None,
    target_temp_low=None,
    hvac_mode=None,
):
    """Set new target temperature."""
    kwargs = {
        key: value
        for key, value in [
            (ATTR_TEMPERATURE, temperature),
            (ATTR_TARGET_TEMP_HIGH, target_temp_high),
            (ATTR_TARGET_TEMP_LOW, target_temp_low),
            (ATTR_ENTITY_ID, entity_id),
            ("hvac_mode", hvac_mode),
        ]
        if value is not None
    }
    _LOGGER.debug("set_temperature start data=%s", kwargs)
    await hass.services.async_call(
        CLIMATE, SERVICE_SET_TEMPERATURE, kwargs, blocking=True
    )


@pytest.fixture
async def setup_comp_issue_10(hass):
    """Initialize components."""
    hass.config.units = US_CUSTOMARY_SYSTEM  # Use Fahrenheit
    await hass.async_block_till_done()


async def test_issue_10_tolerance_precision_heat_cool_mode(hass, setup_comp_issue_10):
    """Test tolerance/precision behavior in heat/cool mode - Issue #10.

    Configuration from issue:
    - tolerance: 1°F (both hot and cold)
    - precision: 0.1°F
    - target_temp_low: 68°F (heating setpoint in heat/cool mode)
    - target_temp_high: 71°F (cooling setpoint)

    Expected behavior when heating:
    - Turn heater ON when temp <= 67°F (68 - 1)
    - Turn heater OFF when temp >= 68°F (setpoint)

    Actual buggy behavior:
    - Turn heater ON at 66.9°F
    - Turn heater OFF at 67.1°F (immediately after starting)
    """
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    temp_input = "sensor.temp"

    # Set up switches
    hass.states.async_set(heater_switch, STATE_OFF, {})
    hass.states.async_set(cooler_switch, STATE_OFF, {})

    # Set up temperature sensor
    hass.states.async_set(temp_input, 70.0, {})

    # Register homeassistant.turn_on/turn_off services for switch control
    @callback
    def async_turn_on(call) -> None:
        """Mock turn_on service."""
        entity_id = call.data.get(ATTR_ENTITY_ID)
        if isinstance(entity_id, list):
            for eid in entity_id:
                hass.states.async_set(eid, STATE_ON, {})
        else:
            hass.states.async_set(entity_id, STATE_ON, {})

    @callback
    def async_turn_off(call) -> None:
        """Mock turn_off service."""
        entity_id = call.data.get(ATTR_ENTITY_ID)
        if isinstance(entity_id, list):
            for eid in entity_id:
                hass.states.async_set(eid, STATE_OFF, {})
        else:
            hass.states.async_set(entity_id, STATE_OFF, {})

    hass.services.async_register(ha.DOMAIN, SERVICE_TURN_ON, async_turn_on)
    hass.services.async_register(ha.DOMAIN, SERVICE_TURN_OFF, async_turn_off)

    await hass.async_block_till_done()

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "heater": heater_switch,
                "cooler": cooler_switch,
                "target_sensor": temp_input,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
                "cold_tolerance": 1.0,  # 1°F tolerance
                "hot_tolerance": 1.0,  # 1°F tolerance
                "precision": 0.1,  # 0.1°F precision
                "target_temp_high": 71,  # Set initial high
                "target_temp_low": 68,  # Set initial low
                "heat_cool_mode": True,  # Enable heat_cool mode
            }
        },
    )
    await hass.async_block_till_done()

    # Both should be off initially
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # Set target temps: low=68°F (heat), high=71°F (cool)
    await async_set_temperature(hass, None, "all", 71, 68)
    await hass.async_block_till_done()

    # Test 1: Temperature at 70°F - should be in comfort zone, nothing on
    _setup_sensor(hass, temp_input, 70)
    await hass.async_block_till_done()

    assert (
        hass.states.get(heater_switch).state == STATE_OFF
    ), "Heater should be OFF at 70°F"
    assert (
        hass.states.get(cooler_switch).state == STATE_OFF
    ), "Cooler should be OFF at 70°F"

    # Test 2: Temperature drops to 67°F - should turn heater ON (68 - 1 = 67)
    _setup_sensor(hass, temp_input, 67.0)
    await hass.async_block_till_done()

    assert (
        hass.states.get(heater_switch).state == STATE_ON
    ), "Heater should turn ON at 67°F"
    assert hass.states.get(cooler_switch).state == STATE_OFF, "Cooler should stay OFF"

    # Test 3: Temperature rises to 67.1°F - heater should STAY ON (not turn off)
    # This is the buggy behavior: heater incorrectly turns off at 67.1°F
    _setup_sensor(hass, temp_input, 67.1)
    await hass.async_block_till_done()

    assert (
        hass.states.get(heater_switch).state == STATE_ON
    ), "Heater should STAY ON at 67.1°F (bug: it turns off)"
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # Test 4: Temperature rises to 67.5°F - heater should STAY ON
    _setup_sensor(hass, temp_input, 67.5)
    await hass.async_block_till_done()

    assert (
        hass.states.get(heater_switch).state == STATE_ON
    ), "Heater should STAY ON at 67.5°F"
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # Test 5: Temperature reaches 68°F - heater should turn OFF (reached setpoint)
    _setup_sensor(hass, temp_input, 68.0)
    await hass.async_block_till_done()

    assert (
        hass.states.get(heater_switch).state == STATE_OFF
    ), "Heater should turn OFF at 68°F (setpoint reached)"
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # Test 6: Temperature continues to 68.5°F - heater should STAY OFF
    _setup_sensor(hass, temp_input, 68.5)
    await hass.async_block_till_done()

    assert (
        hass.states.get(heater_switch).state == STATE_OFF
    ), "Heater should STAY OFF at 68.5°F"
    assert hass.states.get(cooler_switch).state == STATE_OFF


async def test_issue_10_cooling_side(hass, setup_comp_issue_10):
    """Test that the cooling side might have similar issues."""
    heater_switch = "input_boolean.heater2"
    cooler_switch = "input_boolean.cooler2"
    temp_input = "sensor.temp2"

    # Set up switches
    hass.states.async_set(heater_switch, STATE_OFF, {})
    hass.states.async_set(cooler_switch, STATE_OFF, {})

    # Set up temperature sensor
    hass.states.async_set(temp_input, 70.0, {})

    # Register homeassistant.turn_on/turn_off services for switch control
    @callback
    def async_turn_on(call) -> None:
        """Mock turn_on service."""
        entity_id = call.data.get(ATTR_ENTITY_ID)
        if isinstance(entity_id, list):
            for eid in entity_id:
                hass.states.async_set(eid, STATE_ON, {})
        else:
            hass.states.async_set(entity_id, STATE_ON, {})

    @callback
    def async_turn_off(call) -> None:
        """Mock turn_off service."""
        entity_id = call.data.get(ATTR_ENTITY_ID)
        if isinstance(entity_id, list):
            for eid in entity_id:
                hass.states.async_set(eid, STATE_OFF, {})
        else:
            hass.states.async_set(entity_id, STATE_OFF, {})

    hass.services.async_register(ha.DOMAIN, SERVICE_TURN_ON, async_turn_on)
    hass.services.async_register(ha.DOMAIN, SERVICE_TURN_OFF, async_turn_off)

    await hass.async_block_till_done()

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test2",
                "heater": heater_switch,
                "cooler": cooler_switch,
                "target_sensor": temp_input,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
                "cold_tolerance": 1.0,
                "hot_tolerance": 1.0,
                "precision": 0.1,
                "target_temp_high": 71,  # Set initial high
                "target_temp_low": 68,  # Set initial low
                "heat_cool_mode": True,  # Enable heat_cool mode
            }
        },
    )
    await hass.async_block_till_done()

    # Set target temps: low=68°F (heat), high=71°F (cool)
    await async_set_temperature(hass, None, "all", 71, 68)
    await hass.async_block_till_done()

    # Temperature at 70°F - comfort zone
    _setup_sensor(hass, temp_input, 70)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # Temperature rises to 72°F - should turn cooler ON (71 + 1 = 72)
    _setup_sensor(hass, temp_input, 72.0)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert (
        hass.states.get(cooler_switch).state == STATE_ON
    ), "Cooler should turn ON at 72°F"

    # Temperature drops to 71.9°F - cooler should STAY ON
    _setup_sensor(hass, temp_input, 71.9)
    await hass.async_block_till_done()

    assert (
        hass.states.get(cooler_switch).state == STATE_ON
    ), "Cooler should STAY ON at 71.9°F (bug: it might turn off)"
    assert hass.states.get(heater_switch).state == STATE_OFF

    # Temperature reaches 71°F - cooler should turn OFF (reached setpoint)
    _setup_sensor(hass, temp_input, 71.0)
    await hass.async_block_till_done()

    assert (
        hass.states.get(cooler_switch).state == STATE_OFF
    ), "Cooler should turn OFF at 71°F (setpoint reached)"
    assert hass.states.get(heater_switch).state == STATE_OFF
