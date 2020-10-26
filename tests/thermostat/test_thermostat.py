"""The tests for the dual_smart_thermostat."""
import datetime
from os import path

import pytest
import pytz
import voluptuous as vol

from homeassistant import config as hass_config
from homeassistant.components import input_boolean, switch
from homeassistant.components.climate.const import (
    ATTR_PRESET_MODE,
    DOMAIN,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    PRESET_AWAY,
    PRESET_NONE,
)
from custom_components.dual_smart_thermostat import (
    DOMAIN as DUAL_SMART_THERMOSTAT_DOMAIN,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    SERVICE_RELOAD,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)
import homeassistant.core as ha
from homeassistant.core import DOMAIN as HASS_DOMAIN, CoreState, State, callback
from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import METRIC_SYSTEM

from tests.async_mock import patch
from tests.common import (
    assert_setup_component,
    async_fire_time_changed,
    mock_restore_cache,
)
from tests.components.climate import common

ENTITY = "climate.test"
ENT_SENSOR = "sensor.test"
ENT_SWITCH = "switch.test"
HEAT_ENTITY = "climate.test_heat"
COOL_ENTITY = "climate.test_cool"
ATTR_AWAY_MODE = "away_mode"
MIN_TEMP = 3.0
MAX_TEMP = 65.0
TARGET_TEMP = 42.0
COLD_TOLERANCE = 0.5
HOT_TOLERANCE = 0.5


async def test_setup_missing_conf(hass):
    """Test set up heat_control with missing config values."""
    config = {
        "platform": "dual_smart_thermostat",
        "name": "test",
        "target_sensor": ENT_SENSOR,
    }
    with assert_setup_component(0):
        await async_setup_component(hass, "climate", {"climate": config})

async def test_valid_conf(hass):
    """Test set up dual_smart_thermostat with valid config values."""
    assert await async_setup_component(
        hass,
        "climate",
        {
            "climate": {
                "platform": "dual_smart_thermostat",
                "name": "test",
                "heater": ENT_SWITCH,
                "target_sensor": ENT_SENSOR,
            }
        },
    )

@pytest.fixture
async def setup_comp_1(hass):
    """Initialize components."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(hass, "homeassistant", {})
    await hass.async_block_till_done()


async def test_heater_input_boolean(hass, setup_comp_1):
    """Test heater switching input_boolean."""
    heater_switch = "input_boolean.test"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
    )

    assert await async_setup_component(
        hass,
        DOMAIN,
        {
            "climate": {
                "platform": "dual_smart_thermostat",
                "name": "test",
                "heater": heater_switch,
                "target_sensor": ENT_SENSOR,
                "initial_hvac_mode": HVAC_MODE_HEAT,
            }
        },
    )
    await hass.async_block_till_done()

    assert STATE_OFF == hass.states.get(heater_switch).state

    _setup_sensor(hass, 18)
    await hass.async_block_till_done()
    await common.async_set_temperature(hass, 23)

    assert STATE_ON == hass.states.get(heater_switch).state