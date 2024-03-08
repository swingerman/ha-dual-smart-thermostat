"""The tests for the dual_smart_thermostat."""

from datetime import timedelta
import logging
from unittest.mock import patch

from homeassistant.components import input_boolean, input_number
from homeassistant.components.climate import HVACMode
from homeassistant.components.climate.const import DOMAIN as CLIMATE
from homeassistant.const import ENTITY_MATCH_ALL, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt
import pytest

from custom_components.dual_smart_thermostat import DOMAIN

from . import common, setup_comp_1, setup_floor_sensor, setup_sensor  # noqa: F401

COLD_TOLERANCE = 0.3
HOT_TOLERANCE = 0.3

ATTR_HVAC_MODES = "hvac_modes"

_LOGGER = logging.getLogger(__name__)


async def test_dual_mode_cooler(hass: HomeAssistant, setup_comp_1):  # noqa: F811
    """Test thermostat cooler switch in cooling mode."""
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None}},
    )

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
                "platform": DOMAIN,
                "name": "test",
                "heater": heater_switch,
                "cooler": cooler_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.COOL,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    setup_sensor(hass, 17)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF


@pytest.mark.parametrize(
    ["duration", "result_state"],
    [
        (timedelta(seconds=10), STATE_ON),
        (timedelta(seconds=30), STATE_OFF),
    ],
)
async def test_dual_mode_cooler_cycle(
    hass: HomeAssistant, duration, result_state, setup_comp_1  # noqa: F811
):
    """Test thermostat cooler switch in cooling mode with cycle duration."""
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None}},
    )

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
                "platform": DOMAIN,
                "name": "test",
                "heater": heater_switch,
                "cooler": cooler_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.COOL,
                "min_cycle_duration": timedelta(seconds=15),
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    fake_changed = dt.utcnow() - duration
    with patch(
        "homeassistant.helpers.condition.dt_util.utcnow", return_value=fake_changed
    ):
        await common.async_set_temperature(hass, 18)
        await hass.async_block_till_done()
        assert hass.states.get(heater_switch).state == STATE_OFF
        assert hass.states.get(cooler_switch).state == STATE_ON

    setup_sensor(hass, 17)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == result_state


async def test_dual_mode(hass: HomeAssistant, setup_comp_1):  # noqa: F811
    """Test thermostat heater and cooler switch in heat/cool mode."""

    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None}},
    )

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
                "platform": DOMAIN,
                "name": "test",
                "cooler": cooler_switch,
                "heater": heater_switch,
                "heat_cool_mode": True,
                "target_sensor": common.ENT_SENSOR,
            }
        },
    )
    await hass.async_block_till_done()

    # check if all hvac modes are available
    hvac_modes = hass.states.get("climate.test").attributes.get(ATTR_HVAC_MODES)
    assert HVACMode.HEAT in hvac_modes
    assert HVACMode.COOL in hvac_modes
    assert HVACMode.HEAT_COOL in hvac_modes
    assert HVACMode.OFF in hvac_modes

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await common.async_set_temperature(hass, 18, ENTITY_MATCH_ALL, 25, 22)
    setup_sensor(hass, 26)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    setup_sensor(hass, 24)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 18)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # switch to heat only mode
    await common.async_set_hvac_mode(hass, HVACMode.HEAT)
    await common.async_set_temperature(hass, 25, ENTITY_MATCH_ALL, 25, 22)
    await hass.async_block_till_done()

    setup_sensor(hass, 20)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 26)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 20)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # switch to cool only mode
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF


async def test_dual_mode_floor_temp(hass: HomeAssistant, setup_comp_1):  # noqa: F811
    """Test thermostat heater and cooler switch in heat/cool mode. with floor temp caps"""

    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None}},
    )

    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "temp", "initial": 10, "min": 0, "max": 40, "step": 1}
            }
        },
    )

    floor_temp_input = "input_number.floor_temp"
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {
                    "name": "floor_temp",
                    "initial": 10,
                    "min": 0,
                    "max": 40,
                    "step": 1,
                }
            }
        },
    )

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cooler": cooler_switch,
                "heater": heater_switch,
                "heat_cool_mode": True,
                "target_sensor": common.ENT_SENSOR,
                "floor_sensor": floor_temp_input,
                "min_floor_temp": 5,
                "max_floor_temp": 28,
            }
        },
    )
    await hass.async_block_till_done()

    # check if all hvac modes are available
    hvac_modes = hass.states.get("climate.test").attributes.get(ATTR_HVAC_MODES)
    assert HVACMode.HEAT in hvac_modes
    assert HVACMode.COOL in hvac_modes
    assert HVACMode.HEAT_COOL in hvac_modes
    assert HVACMode.OFF in hvac_modes

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 26)
    setup_floor_sensor(hass, 10)
    await hass.async_block_till_done()

    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await common.async_set_temperature(hass, 18, ENTITY_MATCH_ALL, 25, 22)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    setup_sensor(hass, 24)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    """If floor temp is below min_floor_temp, heater should be on"""
    setup_floor_sensor(hass, 4)
    # setup_sensor(hass, 24)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    """If floor temp is above min_floor_temp, heater should be off"""
    setup_floor_sensor(hass, 10)
    setup_sensor(hass, 24)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 18)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF


@pytest.mark.parametrize(
    ["duration", "result_state"],
    [
        (timedelta(seconds=10), STATE_ON),
        (timedelta(seconds=30), STATE_OFF),
    ],
)
async def test_dual_mode_cycle_heat(
    hass: HomeAssistant, duration, result_state, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler switch in heat mode with min_cycle_duration."""
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    fake_changed = dt.utcnow() - duration
    with patch(
        "homeassistant.helpers.condition.dt_util.utcnow", return_value=fake_changed
    ):
        assert await async_setup_component(
            hass,
            input_boolean.DOMAIN,
            {"input_boolean": {"heater": None, "cooler": None}},
        )

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
                "platform": DOMAIN,
                "name": "test",
                "cooler": cooler_switch,
                "heater": heater_switch,
                "heat_cool_mode": True,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
                "min_cycle_duration": timedelta(seconds=15),
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 20)
    await hass.async_block_till_done()

    fake_changed = dt.utcnow() - duration
    with patch(
        "homeassistant.helpers.condition.dt_util.utcnow", return_value=fake_changed
    ):
        await common.async_set_temperature(hass, None, ENTITY_MATCH_ALL, 25, 22)
        await hass.async_block_till_done()
        assert hass.states.get(heater_switch).state == STATE_ON
        assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 24)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == result_state
    assert hass.states.get(cooler_switch).state == STATE_OFF


@pytest.mark.parametrize(
    ["duration", "result_state"],
    [
        (timedelta(seconds=10), STATE_ON),
        (timedelta(seconds=30), STATE_OFF),
    ],
)
async def test_dual_mode_cycle_cool(
    hass: HomeAssistant, duration, result_state, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler switch in cool mode with min_cycle_duration."""
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    fake_changed = dt.utcnow() - duration
    with patch(
        "homeassistant.helpers.condition.dt_util.utcnow", return_value=fake_changed
    ):
        assert await async_setup_component(
            hass,
            input_boolean.DOMAIN,
            {"input_boolean": {"heater": None, "cooler": None}},
        )

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
                "platform": DOMAIN,
                "name": "test",
                "cooler": cooler_switch,
                "heater": heater_switch,
                "heat_cool_mode": True,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
                "min_cycle_duration": timedelta(seconds=15),
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 26)
    await hass.async_block_till_done()

    fake_changed = dt.utcnow() - duration
    with patch(
        "homeassistant.helpers.condition.dt_util.utcnow", return_value=fake_changed
    ):
        await common.async_set_temperature(hass, None, ENTITY_MATCH_ALL, 25, 22)
        await hass.async_block_till_done()
        assert hass.states.get(heater_switch).state == STATE_OFF
        assert hass.states.get(cooler_switch).state == STATE_ON

    setup_sensor(hass, 24)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == result_state


async def test_dual_switch_hvac_modes(hass: HomeAssistant, setup_comp_1):  # noqa: F811
    """Test thermostat heater and cooler switch to heater only mode."""
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None}},
    )

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
                "platform": DOMAIN,
                "name": "test",
                "cooler": cooler_switch,
                "heater": heater_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # setup_sensor(hass, 26)
    # await hass.async_block_till_done()

    # await common.async_set_hvac_mode(hass, HVACMode.HEAT)
    # await hass.async_block_till_done()
    # assert hass.states.get("climate.test").state == HVAC_MODE_HEAT

    # await common.async_set_hvac_mode(hass, HVACMode.COOL)
    # await hass.async_block_till_done()
    # assert hass.states.get("climate.test").state == HVAC_MODE_COOL


async def test_dual_mode_tolerances(hass: HomeAssistant, setup_comp_1):  # noqa: F811
    """Test thermostat heater and cooler mode tolerances."""
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None}},
    )

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
                "platform": DOMAIN,
                "name": "test",
                "cooler": cooler_switch,
                "heater": heater_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
                "heat_cool_mode": True,
                "hot_tolerance": HOT_TOLERANCE,
                "cold_tolerance": COLD_TOLERANCE,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 24)
    await hass.async_block_till_done()
    await common.async_set_temperature(hass, 18, ENTITY_MATCH_ALL, 25, 22)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 21.7)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 22.1)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 22.3)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # since both heater and cooler are off, we expect the cooler not
    # to turn on until the temperature is 0.3 degrees above the target
    setup_sensor(hass, 24.7)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 25.0)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 25.3)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    # since cooler is on we expect it keep on until reaches 0.3 degrees
    # below the target
    setup_sensor(hass, 25.0)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    setup_sensor(hass, 24.7)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF
