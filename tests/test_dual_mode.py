"""The tests for the dual_smart_thermostat."""

from datetime import timedelta
import logging
from unittest.mock import patch

from homeassistant.components import input_boolean, input_number
from homeassistant.components.climate import (
    PRESET_ACTIVITY,
    PRESET_AWAY,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_HOME,
    PRESET_NONE,
    PRESET_SLEEP,
    HVACMode,
)
from homeassistant.components.climate.const import DOMAIN as CLIMATE
from homeassistant.const import ENTITY_MATCH_ALL, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest
import voluptuous as vol

from custom_components.dual_smart_thermostat.const import DOMAIN, PRESET_ANTI_FREEZE

from . import (  # noqa: F401
    common,
    setup_comp_1,
    setup_comp_dual,
    setup_comp_dual_presets,
    setup_floor_sensor,
    setup_sensor,
)

COLD_TOLERANCE = 0.3
HOT_TOLERANCE = 0.3

ATTR_HVAC_MODES = "hvac_modes"

_LOGGER = logging.getLogger(__name__)

###################
# COMMON FEATURES #
###################


async def test_unique_id(
    hass: HomeAssistant, entity_registry: er.EntityRegistry, setup_comp_1  # noqa: F811
) -> None:
    """Test setting a unique ID."""
    unique_id = "some_unique_id"
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
                "unique_id": unique_id,
            }
        },
    )
    await hass.async_block_till_done()

    entry = entity_registry.async_get(common.ENTITY)
    assert entry
    assert entry.unique_id == unique_id


async def test_setup_defaults_to_unknown(hass: HomeAssistant) -> None:  # noqa: F811
    """Test the setting of defaults to unknown."""
    heater_switch = "input_boolean.test"
    cooler_switvh = "input_boolean.test_cooler"
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "heater": heater_switch,
                "cooler": cooler_switvh,
                "target_sensor": common.ENT_SENSOR,
                "heat_cool_mode": True,
            }
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get(common.ENTITY).state == HVACMode.OFF


async def test_setup_gets_current_temp_from_sensor(
    hass: HomeAssistant,
) -> None:  # noqa: F811
    """Test that current temperature is updated on entity addition."""
    hass.config.units = METRIC_SYSTEM
    setup_sensor(hass, 18)
    await hass.async_block_till_done()

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cold_tolerance": 2,
                "hot_tolerance": 4,
                "heater": common.ENT_HEATER,
                "cooler": common.ENT_COOLER,
                "target_sensor": common.ENT_SENSOR,
                "heat_cool_mode": True,
            }
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get(common.ENTITY).attributes["current_temperature"] == 18


async def test_default_setup_params(
    hass: HomeAssistant, setup_comp_dual  # noqa: F811
) -> None:
    """Test the setup with default parameters."""
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("min_temp") == 7
    assert state.attributes.get("max_temp") == 35
    assert state.attributes.get("target_temp_low") == 7
    assert state.attributes.get("target_temp_high") == 35
    assert state.attributes.get("target_temp_step") == 0.1


###################
# CHANGE SETTINGS #
###################


async def test_get_hvac_modes(
    hass: HomeAssistant, setup_comp_dual  # noqa: F811
) -> None:
    """Test that the operation list returns the correct modes."""
    state = hass.states.get(common.ENTITY)
    modes = state.attributes.get("hvac_modes")
    assert modes == [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.HEAT_COOL]


async def test_set_target_temp(
    hass: HomeAssistant, setup_comp_dual  # noqa: F811
) -> None:
    """Test the setting of the target temperature."""
    await common.async_set_temperature(hass, 30, common.ENTITY, 25, 22)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_high") == 25.0
    assert state.attributes.get("target_temp_low") == 22.0
    with pytest.raises(vol.Invalid):
        await common.async_set_temperature(hass, None)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_high") == 25.0
    assert state.attributes.get("target_temp_low") == 22.0


@pytest.mark.parametrize(
    ("preset", "temp_low", "temp_high"),
    [
        (PRESET_NONE, 18, 22),
        (PRESET_AWAY, 16, 30),
        (PRESET_COMFORT, 20, 27),
        (PRESET_ECO, 18, 29),
        (PRESET_HOME, 19, 23),
        (PRESET_SLEEP, 17, 24),
        (PRESET_ACTIVITY, 21, 28),
        (PRESET_ANTI_FREEZE, 5, 32),
    ],
)
async def test_set_preset_mode(
    hass: HomeAssistant,
    setup_comp_dual_presets,  # noqa: F811
    preset,
    temp_low,
    temp_high,
) -> None:
    """Test the setting preset mode."""
    await common.async_set_temperature(hass, 23, common.ENTITY, 22, 18)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == temp_low
    assert state.attributes.get("target_temp_high") == temp_high


@pytest.mark.parametrize(
    ("preset", "temp_low", "temp_high"),
    [
        (PRESET_NONE, 18, 22),
        (PRESET_AWAY, 16, 30),
        (PRESET_COMFORT, 20, 27),
        (PRESET_ECO, 18, 29),
        (PRESET_HOME, 19, 23),
        (PRESET_SLEEP, 17, 24),
        (PRESET_ACTIVITY, 21, 28),
        (PRESET_ANTI_FREEZE, 5, 32),
    ],
)
async def test_set_preset_mode_and_restore_prev_temp(
    hass: HomeAssistant,
    setup_comp_dual_presets,  # noqa: F811
    preset,
    temp_low,
    temp_high,
) -> None:
    """Test the setting preset mode.

    Verify original temperature is restored.
    """
    await common.async_set_temperature(hass, 23, common.ENTITY, 22, 18)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == temp_low
    assert state.attributes.get("target_temp_high") == temp_high
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == 18
    assert state.attributes.get("target_temp_high") == 22


@pytest.mark.parametrize(
    ("preset", "temp_low", "temp_high"),
    [
        (PRESET_NONE, 18, 22),
        (PRESET_AWAY, 16, 30),
        (PRESET_COMFORT, 20, 27),
        (PRESET_ECO, 18, 29),
        (PRESET_HOME, 19, 23),
        (PRESET_SLEEP, 17, 24),
        (PRESET_ACTIVITY, 21, 28),
        (PRESET_ANTI_FREEZE, 5, 32),
    ],
)
async def test_set_preset_modet_twice_and_restore_prev_temp(
    hass: HomeAssistant,
    setup_comp_dual_presets,  # noqa: F811
    preset,
    temp_low,
    temp_high,
) -> None:
    """Test the setting preset mode twice in a row.

    Verify original temperature is restored.
    """
    await common.async_set_temperature(hass, 23, common.ENTITY, 22, 18)
    await common.async_set_preset_mode(hass, preset)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == temp_low
    assert state.attributes.get("target_temp_high") == temp_high
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == 18
    assert state.attributes.get("target_temp_high") == 22


async def test_set_preset_mode_invalid(
    hass: HomeAssistant, setup_comp_dual_presets  # noqa: F811
) -> None:
    """Test an invalid mode raises an error and ignore case when checking modes."""
    await common.async_set_temperature(hass, 23, common.ENTITY, 22, 18)
    await common.async_set_preset_mode(hass, "away")
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == "away"
    await common.async_set_preset_mode(hass, "none")
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == "none"
    with pytest.raises(ServiceValidationError):
        await common.async_set_preset_mode(hass, "Sleep")
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == "none"


@pytest.mark.parametrize(
    ("preset", "temp_low", "temp_high"),
    [
        (PRESET_NONE, 18, 22),
        (PRESET_AWAY, 16, 30),
        (PRESET_COMFORT, 20, 27),
        (PRESET_ECO, 18, 29),
        (PRESET_HOME, 19, 23),
        (PRESET_SLEEP, 17, 24),
        (PRESET_ACTIVITY, 21, 28),
        (PRESET_ANTI_FREEZE, 5, 32),
    ],
)
async def test_set_preset_mode_set_temp_keeps_preset_mode(
    hass: HomeAssistant,
    setup_comp_dual_presets,  # noqa: F811
    preset,
    temp_low,
    temp_high,
) -> None:
    """Test the setting preset mode then set temperature.

    Verify preset mode preserved while temperature updated.
    """
    test_target_temp_low = 3
    test_target_temp_high = 33
    await common.async_set_temperature(hass, 18, common.ENTITY, 22, 18)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == temp_low
    assert state.attributes.get("target_temp_high") == temp_high
    await common.async_set_temperature(
        hass,
        test_target_temp_low,
        common.ENTITY,
        test_target_temp_high,
        test_target_temp_low,
    )
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == test_target_temp_low
    assert state.attributes.get("target_temp_high") == test_target_temp_high
    assert state.attributes.get("preset_mode") == preset
    assert state.attributes.get("supported_features") == 146
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    if preset == PRESET_NONE:
        assert state.attributes.get("target_temp_low") == test_target_temp_low
        assert state.attributes.get("target_temp_high") == test_target_temp_high
    else:
        assert state.attributes.get("target_temp_low") == 18
        assert state.attributes.get("target_temp_high") == 22


async def test_hvac_mode_mode_heat_cool(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
):
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
    hvac_modes = hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_MODES)
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


async def test_hvac_mode_heat_cool_floor_temp(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
):
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
    hvac_modes = hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_MODES)
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


async def test_hvac_mode_cool(hass: HomeAssistant, setup_comp_1):  # noqa: F811
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
async def test_hvac_mode_cool_cycle(
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


@pytest.mark.parametrize(
    ["duration", "result_state"],
    [
        (timedelta(seconds=10), STATE_ON),
        (timedelta(seconds=30), STATE_OFF),
    ],
)
async def test_hvac_mode_heat_cycle(
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
async def test_hvac_mode_heat_cool_cycle(
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


async def test_hvac_mode_heat_cool_switch_preset_modes(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
):
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
                "heat_cool_mode": True,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
                PRESET_AWAY: {},
                PRESET_HOME: {},
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


async def test_hvac_mode_heat_cool_tolerances(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
):
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
