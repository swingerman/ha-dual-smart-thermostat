"""The tests for the dual_smart_thermostat."""
from datetime import timedelta, datetime, timezone, date
from unittest.mock import patch

import yaml

from typing import Any

from homeassistant import setup

from homeassistant.components.sensor import DOMAIN as SENSOR
from homeassistant.core import HomeAssistant
from homeassistant.components import input_boolean
from homeassistant.util import dt

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

from pytest_homeassistant_custom_component.common import AsyncMock, Mock

from custom_components.dual_smart_thermostat.const import *

from homeassistant.setup import async_setup_component


def capital_case(x):
    return x.capitalize()


def test_capital_case():
    assert capital_case("semaphore") == "Semaphore"
