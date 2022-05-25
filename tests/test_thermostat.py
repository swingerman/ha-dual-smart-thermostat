"""The tests for the dual_smart_thermostat."""
from datetime import datetime, timezone, date
import logging

import pytest

from typing import Final

from homeassistant.core import HomeAssistant
from homeassistant.components import input_boolean, input_number
from homeassistant.util import dt
from homeassistant.components.climate.const import (
    DOMAIN as CLIMATE,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    STATE_OFF,
    STATE_ON,
)
import homeassistant.core as ha
from homeassistant.core import DOMAIN as HASS_DOMAIN, CoreState, State, callback
from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import METRIC_SYSTEM

from pytest_homeassistant_custom_component.common import (
    AsyncMock,
    Mock,
    MockConfigEntry,
)

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)

from custom_components.dual_smart_thermostat.const import *

from homeassistant.setup import async_setup_component

from custom_components.dual_smart_thermostat import (
    DOMAIN as DUAL_SMART_THERMOSTAT,
)

ENT_SWITCH = "switch.test"
HEAT_ENTITY = "climate.test_heat"
COOL_ENTITY = "climate.test_cool"
ATTR_AWAY_MODE = "away_mode"
MIN_TEMP = 3.0
MAX_TEMP = 65.0
TARGET_TEMP = 42.0
COLD_TOLERANCE = 0.5
HOT_TOLERANCE = 0.5
TARGET_TEMP_STEP = 0.5

SERVICE_SET_TEMPERATURE = "set_temperature"
SERVICE_SET_HVAC_MODE = "set_hvac_mode"
INPUT_SET_VALUE = "set_value"
ENTITY_MATCH_ALL: Final = "all"

ATTR_AUX_HEAT = "aux_heat"
ATTR_CURRENT_HUMIDITY = "current_humidity"
ATTR_CURRENT_TEMPERATURE = "current_temperature"
ATTR_FAN_MODES = "fan_modes"
ATTR_FAN_MODE = "fan_mode"
ATTR_PRESET_MODE = "preset_mode"
ATTR_PRESET_MODES = "preset_modes"
ATTR_HUMIDITY = "humidity"
ATTR_MAX_HUMIDITY = "max_humidity"
ATTR_MIN_HUMIDITY = "min_humidity"
ATTR_MAX_TEMP = "max_temp"
ATTR_MIN_TEMP = "min_temp"
ATTR_HVAC_ACTION = "hvac_action"
ATTR_HVAC_MODES = "hvac_modes"
ATTR_HVAC_MODE = "hvac_mode"
ATTR_SWING_MODES = "swing_modes"
ATTR_SWING_MODE = "swing_mode"
ATTR_TARGET_TEMP_HIGH = "target_temp_high"
ATTR_TARGET_TEMP_LOW = "target_temp_low"
ATTR_TARGET_TEMP_STEP = "target_temp_step"


_LOGGER = logging.getLogger(__name__)


async def test_valid_conf(hass):
    """Test set up dual_smart_thermostat with valid config values."""
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DUAL_SMART_THERMOSTAT,
                "name": "test",
                "heater": CONF_HEATER,
                "target_sensor": CONF_SENSOR,
            }
        },
    )


@pytest.fixture
async def setup_comp_1(hass):
    """Initialize components."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(hass, HASS_DOMAIN, {})
    await hass.async_block_till_done()


async def test_heater_mode(hass, setup_comp_1):
    """Test thermostat heater switch in heating mode."""
    heater_switch = "input_boolean.test"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
    )

    temp_input = "input_number.temp"
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1}
            }
        },
    )

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DUAL_SMART_THERMOSTAT,
                "name": "test",
                "heater": heater_switch,
                "target_sensor": temp_input,
                "initial_hvac_mode": HVACMode.HEAT,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 18)
    await hass.async_block_till_done()
    await async_set_temperature(hass, 23)

    assert hass.states.get(heater_switch).state == STATE_ON


async def test_cooler_mode(hass, setup_comp_1):
    """Test thermostat cooler switch in cooling mode."""
    cooler_switch = "input_boolean.test"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
    )

    temp_input = "input_number.temp"
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1}
            }
        },
    )

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DUAL_SMART_THERMOSTAT,
                "name": "test",
                "heater": cooler_switch,
                "ac_mode": "true",
                "target_sensor": temp_input,
                "initial_hvac_mode": HVACMode.COOL,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 23)
    await hass.async_block_till_done()
    await async_set_temperature(hass, 18)

    assert hass.states.get(cooler_switch).state == STATE_ON


async def test_heater_cooler_mode(hass, setup_comp_1):
    """Test thermostat heater and cooler switch in heat/cool mode."""

    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None}},
    )

    temp_input = "input_number.temp"
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1}
            }
        },
    )

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DUAL_SMART_THERMOSTAT,
                "name": "test",
                "cooler": cooler_switch,
                "heater": heater_switch,
                "target_sensor": temp_input,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 26)
    await hass.async_block_till_done()
    await async_set_temperature(hass, 18, "all", 25, 22)

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    _setup_sensor(hass, temp_input, 24)
    await hass.async_block_till_done()
    await async_set_temperature(hass, 18, "all", 25, 22)

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 18)
    await hass.async_block_till_done()
    await async_set_temperature(hass, 18, "all", 25, 22)

    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF


async def test_heater_cooler_switch_hvac_modes(hass, setup_comp_1):
    """Test thermostat heater and cooler switch to heater only mode."""

    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None}},
    )

    temp_input = "input_number.temp"
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1}
            }
        },
    )

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DUAL_SMART_THERMOSTAT,
                "name": "test",
                "cooler": cooler_switch,
                "heater": heater_switch,
                "target_sensor": temp_input,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 26)
    await hass.async_block_till_done()

    await async_set_hvac_mode(hass, "all", HVACMode.HEAT)
    assert hass.states.get("climate.test").state == HVAC_MODE_HEAT

    await async_set_hvac_mode(hass, "all", HVACMode.COOL)
    assert hass.states.get("climate.test").state == HVAC_MODE_COOL


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
            (ATTR_HVAC_MODE, hvac_mode),
        ]
        if value is not None
    }
    _LOGGER.debug("set_temperature start data=%s", kwargs)
    await hass.services.async_call(
        CLIMATE, SERVICE_SET_TEMPERATURE, kwargs, blocking=True
    )


async def async_set_hvac_mode(
    hass,
    entity_id="all",
    hvac_mode=HVACMode.OFF,
):
    """Set new HVAC mode."""
    kwargs = {
        key: value
        for key, value in [
            (ATTR_ENTITY_ID, entity_id),
            (ATTR_HVAC_MODE, hvac_mode),
        ]
        if value is not None
    }
    _LOGGER.debug("%s start data=%s", SERVICE_SET_HVAC_MODE, kwargs)
    await hass.services.async_call(
        CLIMATE, SERVICE_SET_HVAC_MODE, kwargs, blocking=True
    )
