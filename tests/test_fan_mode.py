"""The tests for the dual_smart_thermostat."""

import asyncio
import datetime
from datetime import timedelta
import logging

from freezegun import freeze_time
from homeassistant.components import input_boolean, input_number
from homeassistant.components.climate import (
    PRESET_ACTIVITY,
    PRESET_AWAY,
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_HOME,
    PRESET_NONE,
    PRESET_SLEEP,
    HVACAction,
    HVACMode,
)
from homeassistant.components.climate.const import DOMAIN as CLIMATE
from homeassistant.const import (
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_CLOSED,
    STATE_OFF,
    STATE_ON,
    STATE_OPEN,
)
from homeassistant.core import DOMAIN as HASS_DOMAIN, HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt, dt as dt_util
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest

from custom_components.dual_smart_thermostat.const import (
    ATTR_HVAC_ACTION_REASON,
    DOMAIN,
    PRESET_ANTI_FREEZE,
)
from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason import (
    HVACActionReason,
)

from . import (  # noqa: F401
    common,
    setup_boolean,
    setup_comp_1,
    setup_comp_fan_only_config,
    setup_comp_fan_only_config_cycle,
    setup_comp_fan_only_config_presets,
    setup_comp_heat_ac_cool,
    setup_comp_heat_ac_cool_cycle,
    setup_comp_heat_ac_cool_cycle_kepp_alive,
    setup_comp_heat_ac_cool_fan_config,
    setup_comp_heat_ac_cool_fan_config_cycle,
    setup_comp_heat_ac_cool_fan_config_presets,
    setup_comp_heat_ac_cool_fan_config_tolerance,
    setup_comp_heat_ac_cool_presets,
    setup_fan,
    setup_sensor,
    setup_switch,
    setup_switch_dual,
)

COLD_TOLERANCE = 0.5
HOT_TOLERANCE = 0.5

_LOGGER = logging.getLogger(__name__)

###################
# COMMON FEATURES #
###################


async def test_cooler_fan_unique_id(
    hass: HomeAssistant, entity_registry: er.EntityRegistry, setup_comp_1  # noqa: F811
) -> None:
    """Test setting a unique ID."""
    unique_id = "some_unique_id"
    heater_switch = "input_boolean.test"
    fan_switch = "input_boolean.test_fan"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None, "test_fan": None}}
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
                "ac_mode": "true",
                "fan": fan_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT,
                "unique_id": unique_id,
            }
        },
    )
    await hass.async_block_till_done()

    entry = entity_registry.async_get(common.ENTITY)
    assert entry
    assert entry.unique_id == unique_id


async def test_fan_only_unique_id(
    hass: HomeAssistant, entity_registry: er.EntityRegistry, setup_comp_1  # noqa: F811
) -> None:
    """Test setting a unique ID."""
    unique_id = "some_unique_id"
    heater_switch = "input_boolean.test"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
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
                "ac_mode": "true",
                "fan_mode": "true",
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT,
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

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "heater": heater_switch,
                "target_sensor": common.ENT_SENSOR,
                "fan_mode": "true",
            }
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get(common.ENTITY).state == HVACMode.OFF


async def test_cool_fan_setup_defaults_to_unknown(
    hass: HomeAssistant,
) -> None:  # noqa: F811
    """Test the setting of defaults to unknown."""
    heater_switch = "input_boolean.test"
    fan_switch = "input_boolean.test_fan"
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "heater": heater_switch,
                "target_sensor": common.ENT_SENSOR,
                "ac_mode": "true",
                "fan": fan_switch,
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
                "target_sensor": common.ENT_SENSOR,
                "fan_mode": "true",
            }
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get(common.ENTITY).attributes["current_temperature"] == 18


async def test_setup_cool_fan_gets_current_temp_from_sensor(
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
                "fan": common.ENT_FAN,
                "target_sensor": common.ENT_SENSOR,
                "ac_mode": "true",
            }
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get(common.ENTITY).attributes["current_temperature"] == 18


###################
# CHANGE SETTINGS #
###################


async def test_get_hvac_modes_cool_fan_configured(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config  # noqa: F811
) -> None:
    """Test that the operation list returns the correct modes."""
    state = hass.states.get(common.ENTITY)
    modes = state.attributes.get("hvac_modes")
    assert set(modes) == set([HVACMode.COOL, HVACMode.OFF, HVACMode.FAN_ONLY])


async def test_get_hvac_modes_fan_only_configured(
    hass: HomeAssistant, setup_comp_fan_only_config  # noqa: F811
) -> None:
    """Test that the operation list returns the correct modes."""
    state = hass.states.get(common.ENTITY)
    modes = state.attributes.get("hvac_modes")
    assert set(modes) == set([HVACMode.OFF, HVACMode.FAN_ONLY])


@pytest.mark.parametrize(
    ("preset", "temp"),
    [
        (PRESET_NONE, 23),
        (PRESET_AWAY, 16),
        (PRESET_COMFORT, 20),
        (PRESET_ECO, 18),
        (PRESET_HOME, 19),
        (PRESET_SLEEP, 17),
        (PRESET_ACTIVITY, 21),
        (PRESET_BOOST, 10),
        (PRESET_ANTI_FREEZE, 5),
    ],
)
async def test_set_preset_mode(
    hass: HomeAssistant,
    setup_comp_heat_ac_cool_fan_config_presets,  # noqa: F811
    preset,
    temp,
) -> None:
    """Test the setting preset mode."""
    await common.async_set_temperature(hass, 23)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == temp


@pytest.mark.parametrize(
    ("preset", "temp"),
    [
        (PRESET_NONE, 23),
        (PRESET_AWAY, 16),
        (PRESET_COMFORT, 20),
        (PRESET_ECO, 18),
        (PRESET_HOME, 19),
        (PRESET_SLEEP, 17),
        (PRESET_ACTIVITY, 21),
        (PRESET_BOOST, 10),
        (PRESET_ANTI_FREEZE, 5),
    ],
)
async def test_fan_only_set_preset_mode(
    hass: HomeAssistant, setup_comp_fan_only_config_presets, preset, temp  # noqa: F811
) -> None:
    """Test the setting preset mode."""
    await common.async_set_temperature(hass, 23)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == temp


@pytest.mark.parametrize(
    ("preset", "temp"),
    [
        (PRESET_NONE, 23),
        (PRESET_AWAY, 16),
        (PRESET_COMFORT, 20),
        (PRESET_ECO, 18),
        (PRESET_HOME, 19),
        (PRESET_SLEEP, 17),
        (PRESET_ACTIVITY, 21),
        (PRESET_BOOST, 10),
        (PRESET_ANTI_FREEZE, 5),
    ],
)
async def test_set_preset_mode_and_restore_prev_temp(
    hass: HomeAssistant,
    setup_comp_heat_ac_cool_fan_config_presets,  # noqa: F811
    preset,
    temp,
) -> None:
    """Test the setting preset mode.

    Verify original temperature is restored.
    """
    await common.async_set_temperature(hass, 23)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == temp
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 23


@pytest.mark.parametrize(
    ("preset", "temp"),
    [
        (PRESET_NONE, 23),
        (PRESET_AWAY, 16),
        (PRESET_COMFORT, 20),
        (PRESET_ECO, 18),
        (PRESET_HOME, 19),
        (PRESET_SLEEP, 17),
        (PRESET_ACTIVITY, 21),
        (PRESET_BOOST, 10),
        (PRESET_ANTI_FREEZE, 5),
    ],
)
async def test_fan_only_set_preset_mode_and_restore_prev_temp(
    hass: HomeAssistant, setup_comp_fan_only_config_presets, preset, temp  # noqa: F811
) -> None:
    """Test the setting preset mode.

    Verify original temperature is restored.
    """
    await common.async_set_temperature(hass, 23)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == temp
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 23


@pytest.mark.parametrize(
    ("preset", "temp"),
    [
        (PRESET_NONE, 23),
        (PRESET_AWAY, 16),
        (PRESET_COMFORT, 20),
        (PRESET_ECO, 18),
        (PRESET_HOME, 19),
        (PRESET_SLEEP, 17),
        (PRESET_BOOST, 10),
        (PRESET_ACTIVITY, 21),
        (PRESET_ANTI_FREEZE, 5),
    ],
)
async def test_set_preset_modet_twice_and_restore_prev_temp(
    hass: HomeAssistant,
    setup_comp_heat_ac_cool_fan_config_presets,  # noqa: F811
    preset,
    temp,
) -> None:
    """Test the setting preset mode twice in a row.

    Verify original temperature is restored.
    """
    await common.async_set_temperature(hass, 23)
    await common.async_set_preset_mode(hass, preset)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == temp
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 23


@pytest.mark.parametrize(
    ("preset", "temp"),
    [
        (PRESET_NONE, 23),
        (PRESET_AWAY, 16),
        (PRESET_COMFORT, 20),
        (PRESET_ECO, 18),
        (PRESET_HOME, 19),
        (PRESET_SLEEP, 17),
        (PRESET_BOOST, 10),
        (PRESET_ACTIVITY, 21),
        (PRESET_ANTI_FREEZE, 5),
    ],
)
async def test_fan_only_set_preset_modet_twice_and_restore_prev_temp(
    hass: HomeAssistant, setup_comp_fan_only_config_presets, preset, temp  # noqa: F811
) -> None:
    """Test the setting preset mode twice in a row.

    Verify original temperature is restored.
    """
    await common.async_set_temperature(hass, 23)
    await common.async_set_preset_mode(hass, preset)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == temp
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 23


async def test_set_preset_mode_invalid(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config_presets  # noqa: F811
) -> None:
    """Test an invalid mode raises an error and ignore case when checking modes."""
    await common.async_set_temperature(hass, 23)
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


async def test_fan_only_set_preset_mode_invalid(
    hass: HomeAssistant, setup_comp_fan_only_config_presets  # noqa: F811
) -> None:
    """Test an invalid mode raises an error and ignore case when checking modes."""
    await common.async_set_temperature(hass, 23)
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
    ("preset", "temp"),
    [
        (PRESET_NONE, 23),
        (PRESET_AWAY, 16),
        (PRESET_COMFORT, 20),
        (PRESET_ECO, 18),
        (PRESET_HOME, 19),
        (PRESET_SLEEP, 17),
        (PRESET_BOOST, 10),
        (PRESET_ACTIVITY, 21),
        (PRESET_ANTI_FREEZE, 5),
    ],
)
async def test_set_preset_mode_set_temp_keeps_preset_mode(
    hass: HomeAssistant,
    setup_comp_heat_ac_cool_fan_config_presets,  # noqa: F811
    preset,
    temp,
) -> None:
    """Test the setting preset mode then set temperature.

    Verify preset mode preserved while temperature updated.
    """
    target_temp = 32
    await common.async_set_temperature(hass, 23)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == temp
    await common.async_set_temperature(hass, target_temp)
    assert state.attributes.get("supported_features") == 401
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == target_temp
    assert state.attributes.get("preset_mode") == preset
    assert state.attributes.get("supported_features") == 401
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    if preset == PRESET_NONE:
        assert state.attributes.get("temperature") == target_temp
    else:
        assert state.attributes.get("temperature") == 23


@pytest.mark.parametrize(
    ("preset", "temp"),
    [
        (PRESET_NONE, 23),
        (PRESET_AWAY, 16),
        (PRESET_COMFORT, 20),
        (PRESET_ECO, 18),
        (PRESET_HOME, 19),
        (PRESET_SLEEP, 17),
        (PRESET_BOOST, 10),
        (PRESET_ACTIVITY, 21),
        (PRESET_ANTI_FREEZE, 5),
    ],
)
async def test_fan_only_set_preset_mode_set_temp_keeps_preset_mode(
    hass: HomeAssistant, setup_comp_fan_only_config_presets, preset, temp  # noqa: F811
) -> None:
    """Test the setting preset mode then set temperature.

    Verify preset mode preserved while temperature updated.
    """
    target_temp = 32
    await common.async_set_temperature(hass, 23)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == temp
    await common.async_set_temperature(hass, target_temp)
    assert state.attributes.get("supported_features") == 401
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == target_temp
    assert state.attributes.get("preset_mode") == preset
    assert state.attributes.get("supported_features") == 401
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    if preset == PRESET_NONE:
        assert state.attributes.get("temperature") == target_temp
    else:
        assert state.attributes.get("temperature") == 23


async def test_turn_away_mode_on_fan(
    hass: HomeAssistant, setup_comp_fan_only_config  # noqa: F811
) -> None:
    """Test the setting away mode when cooling."""
    setup_switch(hass, True)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_modes") == [PRESET_NONE, PRESET_AWAY]
    await common.async_set_temperature(hass, 19)
    await common.async_set_preset_mode(hass, PRESET_AWAY)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 30


async def test_turn_away_mode_on_cooling(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config  # noqa: F811
) -> None:
    """Test the setting away mode when cooling."""
    setup_switch(hass, True)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_modes") == [PRESET_NONE, PRESET_AWAY]
    await common.async_set_temperature(hass, 19)
    await common.async_set_preset_mode(hass, PRESET_AWAY)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 30


###################
# HVAC OPERATIONS #
###################


async def test_toggle_fan_only(
    hass: HomeAssistant, setup_comp_fan_only_config  # noqa: F811
) -> None:
    """Test change mode from OFF to COOL.

    Switch turns on when temp below setpoint and mode changes.
    """
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await common.async_toggle(hass)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.state == HVACMode.FAN_ONLY

    await common.async_toggle(hass)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.state == HVACMode.OFF


async def test_hvac_mode_fan_only(
    hass: HomeAssistant, setup_comp_fan_only_config  # noqa: F811
) -> None:
    """Test change mode from OFF to COOL.

    Switch turns on when temp below setpoint and mode changes.
    """
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    calls = setup_switch(hass, False)
    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


@pytest.mark.parametrize(
    ["from_hvac_mode", "to_hvac_mode"],
    [
        [HVACMode.OFF, HVACMode.COOL],
        [HVACMode.COOL, HVACMode.OFF],
        [HVACMode.FAN_ONLY, HVACMode.OFF],
    ],
)
async def test_toggle_cool_fan(
    hass: HomeAssistant,
    from_hvac_mode,
    to_hvac_mode,
    setup_comp_heat_ac_cool_fan_config,  # noqa: F811
) -> None:
    """Test change mode from OFF to COOL.

    Switch turns on when temp below setpoint and mode changes.
    """
    await common.async_set_hvac_mode(hass, from_hvac_mode)
    await common.async_toggle(hass)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.state == to_hvac_mode

    await common.async_toggle(hass)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.state == from_hvac_mode


async def test_hvac_mode_cool_fan(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config  # noqa: F811
) -> None:
    """Test change mode from OFF to COOL.

    Switch turns on when temp below setpoint and mode changes.
    """
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    # cooler
    calls = setup_switch(hass, False)
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH
    # fan
    calls = setup_switch_dual(hass, common.ENT_FAN, True, False)
    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
    assert len(calls) == 2
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH

    call = calls[1]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_FAN


async def test_set_target_temp_fan_off(
    hass: HomeAssistant, setup_comp_fan_only_config  # noqa: F811
) -> None:
    """Test if target temperature turn fan off."""
    calls = setup_switch(hass, True)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    await common.async_set_temperature(hass, 30)
    assert len(calls) == 2
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_set_target_temp_cool_fan_off(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config  # noqa: F811
) -> None:
    """Test if target temperature turn ac off."""
    calls = setup_switch_dual(hass, common.ENT_FAN, True, True)

    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    await common.async_set_temperature(hass, 30)
    assert len(calls) == 4

    call_switch = calls[0]
    assert call_switch.domain == HASS_DOMAIN
    assert call_switch.service == SERVICE_TURN_OFF
    assert call_switch.data["entity_id"] == common.ENT_SWITCH

    call_fan = calls[1]
    assert call_fan.domain == HASS_DOMAIN
    assert call_fan.service == SERVICE_TURN_OFF
    assert call_fan.data["entity_id"] == common.ENT_FAN


async def test_set_target_temp_fan_on(
    hass: HomeAssistant, setup_comp_fan_only_config  # noqa: F811
) -> None:
    """Test if target temperature turn ac on."""
    calls = setup_switch(hass, False)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    await common.async_set_temperature(hass, 25)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_set_target_temp_cooler_on(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config  # noqa: F811
) -> None:
    """Test if target temperature turn ac on."""
    calls = setup_switch_dual(hass, common.ENT_FAN, False, False)
    setup_sensor(hass, 30)
    # only turns on if in COOL mode
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    await hass.async_block_till_done()
    await common.async_set_temperature(hass, 25)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_set_target_temp_cooler_fan_on(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config  # noqa: F811
) -> None:
    """Test if target temperature turn fan on."""
    calls = setup_switch_dual(hass, common.ENT_FAN, False, False)
    setup_sensor(hass, 30)
    # only turns on if in COOL mode
    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
    await hass.async_block_till_done()
    await common.async_set_temperature(hass, 25)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_FAN


async def test_temp_change_fan_off_within_tolerance(
    hass: HomeAssistant, setup_comp_fan_only_config  # noqa: F811
) -> None:
    """Test if temperature change doesn't turn ac off within tolerance."""
    calls = setup_switch(hass, True)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 29.8)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_cooler_fan_ac_off_within_tolerance(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config  # noqa: F811
) -> None:
    """Test if temperature change doesn't turn ac off within tolerance."""
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    calls = setup_switch_dual(hass, common.ENT_FAN, True, False)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 29.8)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_cooler_fan_off_within_tolerance(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config  # noqa: F811
) -> None:
    """Test if temperature change doesn't turn fan off within tolerance."""
    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
    calls = setup_switch_dual(hass, common.ENT_FAN, False, True)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 29.8)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_set_temp_change_fan_off_outside_tolerance(
    hass: HomeAssistant, setup_comp_fan_only_config  # noqa: F811
) -> None:
    """Test if temperature change turn ac off."""
    calls = setup_switch(hass, True)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 27)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_set_temp_change_cooler_fan_ac_off_outside_tolerance(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config  # noqa: F811
) -> None:
    """Test if temperature change turn ac off."""
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    calls = setup_switch_dual(hass, common.ENT_FAN, True, False)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 27)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_set_temp_change_cooler_fan_off_outside_tolerance(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config  # noqa: F811
) -> None:
    """Test if temperature change turn ac off."""
    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
    calls = setup_switch_dual(hass, common.ENT_FAN, False, True)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 27)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_FAN


async def test_temp_change_fan_on_within_tolerance(
    hass: HomeAssistant, setup_comp_fan_only_config  # noqa: F811
) -> None:
    """Test if temperature change doesn't turn fan on within tolerance."""
    calls = setup_switch(hass, False)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 25.2)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_cooler_fan_ac_on_within_tolerance(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config  # noqa: F811
) -> None:
    """Test if temperature change doesn't turn ac on within tolerance."""
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    calls = setup_switch_dual(hass, common.ENT_FAN, False, False)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 25.2)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_cooler_fan_on_within_tolerance(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config  # noqa: F811
) -> None:
    """Test if temperature change doesn't turn ac on within tolerance."""
    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
    calls = setup_switch_dual(hass, common.ENT_FAN, False, False)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 25.2)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_fan_on_outside_tolerance(
    hass: HomeAssistant, setup_comp_fan_only_config  # noqa: F811
) -> None:
    """Test if temperature change turn ac on."""
    calls = setup_switch(hass, False)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_temp_change_cooler_fan_ac_on_outside_tolerance(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config  # noqa: F811
) -> None:
    """Test if temperature change turn ac on."""
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    calls = setup_switch_dual(hass, common.ENT_FAN, False, False)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_temp_change_cooler_fan_on_outside_tolerance(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config  # noqa: F811
) -> None:
    """Test if temperature change turn ac on."""
    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
    calls = setup_switch_dual(hass, common.ENT_FAN, False, False)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_FAN


async def test_running_fan_when_operating_mode_is_off_2(
    hass: HomeAssistant, setup_comp_fan_only_config  # noqa: F811
) -> None:
    """Test that the switch turns off when enabled is set False."""
    calls = setup_switch(hass, True)
    await common.async_set_temperature(hass, 30)
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_running_cooler_fan_ac_when_operating_mode_is_off_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config  # noqa: F811
) -> None:
    """Test that the switch turns off when enabled is set False."""
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    calls = setup_switch_dual(hass, common.ENT_FAN, True, False)
    await common.async_set_temperature(hass, 30)
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_running_cooler_fan_when_operating_mode_is_off_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config  # noqa: F811
) -> None:
    """Test that the switch turns off when enabled is set False."""
    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
    calls = setup_switch_dual(hass, common.ENT_FAN, False, True)
    await common.async_set_temperature(hass, 30)
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_FAN


async def test_no_state_change_fan_when_operation_mode_off_2(
    hass: HomeAssistant, setup_comp_fan_only_config  # noqa: F811
) -> None:
    """Test that the switch doesn't turn on when enabled is False."""
    calls = setup_switch(hass, False)
    await common.async_set_temperature(hass, 30)
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    setup_sensor(hass, 35)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_no_state_cooler_fan_ac_change_when_operation_mode_off_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config  # noqa: F811
) -> None:
    """Test that the switch doesn't turn on when enabled is False."""
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    calls = setup_switch_dual(hass, common.ENT_FAN, False, False)
    await common.async_set_temperature(hass, 30)
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    setup_sensor(hass, 35)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_no_state_cooler_fan_change_when_operation_mode_off_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config  # noqa: F811
) -> None:
    """Test that the switch doesn't turn on when enabled is False."""
    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
    calls = setup_switch_dual(hass, common.ENT_FAN, False, False)
    await common.async_set_temperature(hass, 30)
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    setup_sensor(hass, 35)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_fan_trigger_on_not_long_enough(
    hass: HomeAssistant, setup_comp_fan_only_config_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn fan on."""
    calls = setup_switch(hass, False)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_cooler_fan_ac_trigger_on_not_long_enough(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn ac on."""
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    calls = setup_switch_dual(hass, common.ENT_FAN, False, False)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_cooler_fan_trigger_on_not_long_enough(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn ac on."""
    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
    calls = setup_switch_dual(hass, common.ENT_FAN, False, False)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_fan_trigger_on_long_enough(
    hass: HomeAssistant, setup_comp_fan_only_config_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn fan on."""
    fake_changed = datetime.datetime(1970, 11, 11, 11, 11, 11, tzinfo=dt_util.UTC)
    with freeze_time(fake_changed):
        calls = setup_switch(hass, False)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_temp_change_cooler_fan_ac_trigger_on_long_enough(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn ac on."""
    fake_changed = datetime.datetime(1970, 11, 11, 11, 11, 11, tzinfo=dt_util.UTC)
    with freeze_time(fake_changed):
        await common.async_set_hvac_mode(hass, HVACMode.COOL)
        calls = setup_switch_dual(hass, common.ENT_FAN, False, False)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_temp_change_cooler_fan_trigger_on_long_enough(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn fan on."""
    fake_changed = datetime.datetime(1970, 11, 11, 11, 11, 11, tzinfo=dt_util.UTC)
    with freeze_time(fake_changed):
        await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
        calls = setup_switch_dual(hass, common.ENT_FAN, False, False)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_FAN


async def test_temp_change_fan_trigger_off_not_long_enough(
    hass: HomeAssistant, setup_comp_fan_only_config_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn fan on."""
    calls = setup_switch(hass, True)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_cooler_fan_ac_trigger_off_not_long_enough(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn ac on."""
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    calls = setup_switch_dual(hass, common.ENT_FAN, True, False)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_cooler_fan_trigger_off_not_long_enough(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn fan on."""
    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
    calls = setup_switch_dual(hass, common.ENT_FAN, False, True)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_fan_trigger_off_long_enough(
    hass: HomeAssistant, setup_comp_fan_only_config_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn ac on."""
    fake_changed = datetime.datetime(1970, 11, 11, 11, 11, 11, tzinfo=dt_util.UTC)
    with freeze_time(fake_changed):
        calls = setup_switch(hass, True)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_temp_change_cooler_fan_ac_trigger_off_long_enough(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn ac on."""
    fake_changed = datetime.datetime(1970, 11, 11, 11, 11, 11, tzinfo=dt_util.UTC)
    with freeze_time(fake_changed):
        await common.async_set_hvac_mode(hass, HVACMode.COOL)
        calls = setup_switch_dual(hass, common.ENT_FAN, True, False)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_temp_change_cooler_fan_trigger_off_long_enough(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn fan on."""
    fake_changed = datetime.datetime(1970, 11, 11, 11, 11, 11, tzinfo=dt_util.UTC)
    with freeze_time(fake_changed):
        await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
        calls = setup_switch_dual(hass, common.ENT_FAN, False, True)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_FAN


async def test_mode_change_fan_trigger_off_not_long_enough(
    hass: HomeAssistant, setup_comp_fan_only_config_cycle  # noqa: F811
) -> None:
    """Test if mode change turns fan off despite minimum cycle."""
    calls = setup_switch(hass, True)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    assert len(calls) == 0
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == "homeassistant"
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_mode_change_cooler_fan_ac_trigger_off_not_long_enough(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config_cycle  # noqa: F811
) -> None:
    """Test if mode change turns ac off despite minimum cycle."""
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    calls = setup_switch_dual(hass, common.ENT_FAN, True, False)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    assert len(calls) == 0
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == "homeassistant"
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_mode_change_cooler_fan_trigger_off_not_long_enough(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config_cycle  # noqa: F811
) -> None:
    """Test if mode change turns fan off despite minimum cycle."""
    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
    calls = setup_switch_dual(hass, common.ENT_FAN, False, True)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    assert len(calls) == 0
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == "homeassistant"
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_FAN


async def test_mode_change_fan_trigger_on_not_long_enough(
    hass: HomeAssistant, setup_comp_fan_only_config_cycle  # noqa: F811
) -> None:
    """Test if mode change turns fan on despite minimum cycle."""
    calls = setup_switch(hass, False)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 0
    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == "homeassistant"
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_mode_change_cooler_fan_ac_trigger_on_not_long_enough(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config_cycle  # noqa: F811
) -> None:
    """Test if mode change turns ac on despite minimum cycle."""
    calls = setup_switch_dual(hass, common.ENT_FAN, False, False)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 0
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == "homeassistant"
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_mode_change_cooler_fan_trigger_on_not_long_enough(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config_cycle  # noqa: F811
) -> None:
    """Test if mode change turns fan on despite minimum cycle."""
    calls = setup_switch_dual(hass, common.ENT_FAN, False, False)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 0
    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == "homeassistant"
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_FAN


async def test_temp_change_fan_trigger_on_not_long_enough_2(
    hass: HomeAssistant, setup_comp_fan_only_config_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn fan on."""
    calls = setup_switch(hass, False)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_cooler_fan_ac_trigger_on_not_long_enough_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn ac on."""
    calls = setup_switch_dual(hass, common.ENT_FAN, False, False)
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_cooler_fan_trigger_on_not_long_enough_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn ac on."""
    calls = setup_switch_dual(hass, common.ENT_FAN, False, False)
    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_fan_trigger_on_long_enough_2(
    hass: HomeAssistant, setup_comp_fan_only_config_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn fan on."""
    fake_changed = datetime.datetime(1970, 11, 11, 11, 11, 11, tzinfo=dt_util.UTC)
    with freeze_time(fake_changed):
        calls = setup_switch(hass, False)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_temp_change_cooler_fan_ac_trigger_on_long_enough_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn ac on."""
    fake_changed = datetime.datetime(1970, 11, 11, 11, 11, 11, tzinfo=dt_util.UTC)
    with freeze_time(fake_changed):
        calls = setup_switch_dual(hass, common.ENT_FAN, False, False)
        await common.async_set_hvac_mode(hass, HVACMode.COOL)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_temp_change_cooler_fan_trigger_on_long_enough_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn fan on."""
    fake_changed = datetime.datetime(1970, 11, 11, 11, 11, 11, tzinfo=dt_util.UTC)
    with freeze_time(fake_changed):
        calls = setup_switch_dual(hass, common.ENT_FAN, False, False)
        await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_FAN


async def test_temp_change_fan_trigger_off_not_long_enough_2(
    hass: HomeAssistant, setup_comp_fan_only_config_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn fan on."""
    calls = setup_switch(hass, True)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_cooler_fan_ac_trigger_off_not_long_enough_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn ac on."""
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    calls = setup_switch_dual(hass, common.ENT_FAN, True, False)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_cooler_fan_trigger_off_not_long_enough_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn fan on."""
    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
    calls = setup_switch_dual(hass, common.ENT_FAN, False, True)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_fan_trigger_off_long_enough_2(
    hass: HomeAssistant, setup_comp_fan_only_config_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn ac on."""
    fake_changed = datetime.datetime(1970, 11, 11, 11, 11, 11, tzinfo=dt_util.UTC)
    with freeze_time(fake_changed):
        calls = setup_switch(hass, True)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_temp_change_cooler_fan_ac_trigger_off_long_enough_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn ac on."""
    fake_changed = datetime.datetime(1970, 11, 11, 11, 11, 11, tzinfo=dt_util.UTC)
    with freeze_time(fake_changed):
        await common.async_set_hvac_mode(hass, HVACMode.COOL)
        calls = setup_switch_dual(hass, common.ENT_FAN, True, False)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_temp_change_cooler_fan_trigger_off_long_enough_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn fan on."""
    fake_changed = datetime.datetime(1970, 11, 11, 11, 11, 11, tzinfo=dt_util.UTC)
    with freeze_time(fake_changed):
        await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
        calls = setup_switch_dual(hass, common.ENT_FAN, False, True)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_FAN


async def test_mode_change_fan_trigger_off_not_long_enough_2(
    hass: HomeAssistant, setup_comp_fan_only_config_cycle  # noqa: F811
) -> None:
    """Test if mode change turns ac off despite minimum cycle."""
    calls = setup_switch(hass, True)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    assert len(calls) == 0
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == "homeassistant"
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_mode_change_cooler_fan_ac_trigger_off_not_long_enough_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config_cycle  # noqa: F811
) -> None:
    """Test if mode change turns ac off despite minimum cycle."""
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    calls = setup_switch_dual(hass, common.ENT_FAN, True, False)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    assert len(calls) == 0
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == "homeassistant"
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_mode_change_cooler_fan_trigger_off_not_long_enough_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config_cycle  # noqa: F811
) -> None:
    """Test if mode change turns fan off despite minimum cycle."""
    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
    calls = setup_switch_dual(hass, common.ENT_FAN, False, True)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    assert len(calls) == 0
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == "homeassistant"
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_FAN


async def test_mode_change_fan_trigger_on_not_long_enough_2(
    hass: HomeAssistant, setup_comp_fan_only_config_cycle  # noqa: F811
) -> None:
    """Test if mode change turns fan on despite minimum cycle."""
    calls = setup_switch(hass, False)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 0
    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == "homeassistant"
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_mode_change_cooler_fan_ac_trigger_on_not_long_enough_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config_cycle  # noqa: F811
) -> None:
    """Test if mode change turns ac on despite minimum cycle."""
    calls = setup_switch_dual(hass, common.ENT_FAN, False, False)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 0
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == "homeassistant"
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_mode_change_cooler_fan_trigger_on_not_long_enough_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config_cycle  # noqa: F811
) -> None:
    """Test if mode change turns fan on despite minimum cycle."""
    calls = setup_switch_dual(hass, common.ENT_FAN, False, False)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 0
    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == "homeassistant"
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_FAN


async def test_fan_mode(hass: HomeAssistant, setup_comp_1) -> None:  # noqa: F811
    """Test thermostat cooler switch in cooling mode."""
    cooler_switch = "input_boolean.test"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
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
                "heater": cooler_switch,
                "fan_mode": "true",
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.FAN_ONLY,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_ON

    setup_sensor(hass, 17)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_OFF


async def test_cooler_fan_cool_mode(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode."""
    cooler_switch = "input_boolean.test"
    fan_switch = "input_boolean.test_fan"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None, "test_fan": None}}
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
                "heater": cooler_switch,
                "ac_mode": "true",
                "fan": fan_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.COOL,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(fan_switch).state == STATE_OFF

    setup_sensor(hass, 17)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF


async def test_cooler_fan_fan_mode(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling fan mode."""
    cooler_switch = "input_boolean.test"
    fan_switch = "input_boolean.test_fan"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None, "test_fan": None}}
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
                "heater": cooler_switch,
                "ac_mode": "true",
                "fan": fan_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.FAN_ONLY,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_ON

    setup_sensor(hass, 17)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF


async def test_fan_mode_from_off_to_idle(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat switch state if HVAC mode changes."""
    cooler_switch = "input_boolean.test"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
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
                "heater": cooler_switch,
                "fan_mode": "true",
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.OFF,
                "target_temp": 25,
            }
        },
    )
    await hass.async_block_till_done()

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).attributes["hvac_action"] == HVACAction.OFF

    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).attributes["hvac_action"] == HVACAction.IDLE


async def test_cooler_fan_cooler_mode_from_off_to_idle(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat switch state if HVAC mode changes."""
    cooler_switch = "input_boolean.test"
    fan_switch = "input_boolean.test_fan"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None, "test_fan": None}}
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
                "heater": cooler_switch,
                "ac_mode": "true",
                "fan": fan_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.OFF,
                "target_temp": 25,
            }
        },
    )
    await hass.async_block_till_done()

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).attributes["hvac_action"] == HVACAction.OFF

    await common.async_set_hvac_mode(hass, HVACMode.COOL)

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).attributes["hvac_action"] == HVACAction.IDLE


async def test_cooler_fan_fan_mode_from_off_to_idle(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat switch state if HVAC mode changes."""
    cooler_switch = "input_boolean.test"
    fan_switch = "input_boolean.test_fan"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None, "test_fan": None}}
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
                "heater": cooler_switch,
                "ac_mode": "true",
                "fan": fan_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.OFF,
                "target_temp": 25,
            }
        },
    )
    await hass.async_block_till_done()

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).attributes["hvac_action"] == HVACAction.OFF

    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).attributes["hvac_action"] == HVACAction.IDLE


async def test_fan_mode_tolerance(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode."""
    cooler_switch = "input_boolean.test"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
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
                "heater": cooler_switch,
                "fan_mode": "true",
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.FAN_ONLY,
                "cold_tolerance": COLD_TOLERANCE,
                "hot_tolerance": HOT_TOLERANCE,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 22.4)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 22)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 22.5)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_ON

    setup_sensor(hass, 21.6)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_ON

    setup_sensor(hass, 21.5)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_OFF


async def test_cooler_fan_cooler_mode_tolerance(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode."""
    cooler_switch = "input_boolean.test"
    fan_switch = "input_boolean.test_fan"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None, "test_fan": None}}
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
                "heater": cooler_switch,
                "ac_mode": "true",
                "fan": fan_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.COOL,
                "cold_tolerance": COLD_TOLERANCE,
                "hot_tolerance": HOT_TOLERANCE,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    setup_sensor(hass, 22.4)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 22)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    setup_sensor(hass, 22.5)
    await hass.async_block_till_done()
    assert hass.states.get(fan_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    setup_sensor(hass, 21.6)
    await hass.async_block_till_done()
    assert hass.states.get(fan_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    setup_sensor(hass, 21.5)
    await hass.async_block_till_done()
    assert hass.states.get(fan_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF


async def test_cooler_fan_mode_tolerance(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode."""
    cooler_switch = "input_boolean.test"
    fan_switch = "input_boolean.test_fan"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None, "test_fan": None}}
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
                "heater": cooler_switch,
                "ac_mode": "true",
                "fan": fan_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.FAN_ONLY,
                "cold_tolerance": COLD_TOLERANCE,
                "hot_tolerance": HOT_TOLERANCE,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    setup_sensor(hass, 22.4)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 22)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    setup_sensor(hass, 22.5)
    await hass.async_block_till_done()
    assert hass.states.get(fan_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 21.6)
    await hass.async_block_till_done()
    assert hass.states.get(fan_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 21.5)
    await hass.async_block_till_done()
    assert hass.states.get(fan_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF


async def test_cooler_fan_ac_and_mode(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode."""
    cooler_switch = "input_boolean.test"
    fan_switch = "input_boolean.test_fan"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None, "test_fan": None}}
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
                "heater": cooler_switch,
                "ac_mode": "true",
                "fan": fan_switch,
                "fan_on_with_ac": "true",
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.COOL,
                "cold_tolerance": COLD_TOLERANCE,
                "hot_tolerance": HOT_TOLERANCE,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    setup_sensor(hass, 22.4)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 22)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    setup_sensor(hass, 22.5)
    await hass.async_block_till_done()
    assert hass.states.get(fan_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_ON

    setup_sensor(hass, 21.6)
    await hass.async_block_till_done()
    assert hass.states.get(fan_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_ON

    setup_sensor(hass, 21.5)
    await hass.async_block_till_done()
    assert hass.states.get(fan_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF


@pytest.mark.parametrize(
    ["duration", "result_state"],
    [
        (timedelta(seconds=10), STATE_ON),
        (timedelta(seconds=30), STATE_OFF),
    ],
)
@pytest.mark.asyncio
async def test_fan_mode_cycle(
    hass: HomeAssistant, duration, result_state, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode with cycle duration."""
    cooler_switch = "input_boolean.test"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
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
                "heater": cooler_switch,
                "fan_mode": "true",
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.FAN_ONLY,
                "min_cycle_duration": timedelta(seconds=15),
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    fake_changed = dt.utcnow() - duration
    with freeze_time(fake_changed):
        await common.async_set_temperature(hass, 18)
        await hass.async_block_till_done()
        assert hass.states.get(cooler_switch).state == STATE_ON

    setup_sensor(hass, 17)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == result_state


@pytest.mark.parametrize(
    ["duration", "hvac_mode", "cooler_result_state", "fan_result_state"],
    [
        (timedelta(seconds=10), HVACMode.COOL, STATE_ON, STATE_OFF),
        (timedelta(seconds=30), HVACMode.COOL, STATE_OFF, STATE_OFF),
        (timedelta(seconds=10), HVACMode.FAN_ONLY, STATE_OFF, STATE_ON),
        (timedelta(seconds=30), HVACMode.FAN_ONLY, STATE_OFF, STATE_OFF),
    ],
)
@pytest.mark.asyncio
async def test_cooler_fan_mode_cycle(
    hass: HomeAssistant,
    duration,
    hvac_mode,
    cooler_result_state,
    fan_result_state,
    setup_comp_1,  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode with cycle duration."""
    cooler_switch = "input_boolean.test"
    fan_switch = "input_boolean.test_fan"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None, "test_fan": None}}
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
                "heater": cooler_switch,
                "ac_mode": "true",
                "fan": fan_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": hvac_mode,
                "min_cycle_duration": timedelta(seconds=15),
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    fake_changed = dt.utcnow() - duration
    with freeze_time(fake_changed):

        await common.async_set_temperature(hass, 18)
        await hass.async_block_till_done()
        assert (
            hass.states.get(cooler_switch).state == STATE_ON
            if hvac_mode == HVACMode.COOL
            else STATE_OFF
        )
        assert (
            hass.states.get(fan_switch).state == STATE_OFF
            if hvac_mode == HVACMode.COOL
            else STATE_ON
        )

    setup_sensor(hass, 17)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == cooler_result_state
    assert hass.states.get(fan_switch).state == fan_result_state


async def test_hvac_mode_cool_fan_only(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config  # noqa: F811
) -> None:
    """Test change mode from OFF to FAN_ONLY.

    Switch turns on when temp below setpoint and mode changes.
    """
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    calls = setup_fan(hass, False)
    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_FAN


async def test_set_target_temp_ac_fan_on(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config  # noqa: F811
) -> None:
    """Test if target temperature turn ac on."""
    calls = setup_fan(hass, False)
    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 25)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_FAN


async def test_set_target_temp_ac_on_after_fan_tolerance(
    hass: HomeAssistant, setup_comp_heat_ac_cool_fan_config_tolerance  # noqa: F811
) -> None:
    """Test if target temperature turn ac on."""
    calls = setup_switch_dual(hass, common.ENT_FAN, False, False)
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    setup_sensor(hass, 26)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 21)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_FAN

    await common.async_set_temperature(hass, 22)
    await hass.async_block_till_done()
    assert len(calls) == 2
    call = calls[1]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_FAN


async def test_set_target_temp_ac_on_after_fan_tolerance_2(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    cooler_switch = "input_boolean.test"
    fan_switch = "input_boolean.fan"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"test": None, "fan": None}},
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
                "cold_tolerance": 0.2,
                "hot_tolerance": 0.2,
                "ac_mode": True,
                "heater": cooler_switch,
                "target_sensor": common.ENT_SENSOR,
                "fan": fan_switch,
                "fan_hot_tolerance": 0.5,
                "initial_hvac_mode": HVACMode.OFF,
            }
        },
    )
    await hass.async_block_till_done()

    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    await common.async_set_temperature(hass, 20)

    # below hot_tolerance
    setup_sensor(hass, 20)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    # within hot_tolerance and fan_hot_tolerance
    setup_sensor(hass, 20.2)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_ON

    # within hot_tolerance and fan_hot_tolerance
    setup_sensor(hass, 20.5)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_ON

    # within hot_tolerance and fan_hot_tolerance
    setup_sensor(hass, 20.7)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_ON

    # outside fan_hot_tolerance, within hot_tolerance
    setup_sensor(hass, 20.8)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(fan_switch).state == STATE_OFF


######################
# HVAC ACTION REASON #
######################


async def test_fan_mode_opening_hvac_action_reason(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode."""
    cooler_switch = "input_boolean.test"
    opening_1 = "input_boolean.opening_1"
    opening_2 = "input_boolean.opening_2"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"test": None, "opening_1": None, "opening_2": None}},
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
                "heater": cooler_switch,
                "fan_mode": "true",
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.FAN_ONLY,
                "openings": [
                    opening_1,
                    {"entity_id": opening_2, "timeout": {"seconds": 10}},
                ],
            }
        },
    )
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.NONE
    )

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_TEMP_NOT_REACHED
    )

    setup_boolean(hass, opening_1, "open")
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.OPENING
    )

    setup_boolean(hass, opening_1, "closed")
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_TEMP_NOT_REACHED
    )

    setup_boolean(hass, opening_2, "open")
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_TEMP_NOT_REACHED
    )

    # wait 10 seconds, actually 133 due to the other tests run time seems to affect this
    # needs to separate the tests
    await asyncio.sleep(13)
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.OPENING
    )

    setup_boolean(hass, opening_2, "closed")
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_TEMP_NOT_REACHED
    )


@pytest.mark.parametrize(
    "hvac_mode",
    [
        (HVACMode.COOL),
        (HVACMode.FAN_ONLY),
    ],
)
async def test_cooler_fan_mode_opening_hvac_action_reason(
    hass: HomeAssistant, hvac_mode, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode."""
    cooler_switch = "input_boolean.test"
    fan_switch = "input_boolean.test_fan"

    opening_1 = "input_boolean.opening_1"
    opening_2 = "input_boolean.opening_2"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {
            "input_boolean": {
                "test": None,
                "test_fan": None,
                "opening_1": None,
                "opening_2": None,
            }
        },
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
                "heater": cooler_switch,
                "ac_mode": "true",
                "fan": fan_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": hvac_mode,
                "openings": [
                    opening_1,
                    {"entity_id": opening_2, "timeout": {"seconds": 10}},
                ],
            }
        },
    )
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.NONE
    )

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 18, common.ENTITY_MATCH_ALL, 18, 10)
    await hass.async_block_till_done()
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_TEMP_NOT_REACHED
    )

    setup_boolean(hass, opening_1, "open")
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.OPENING
    )

    setup_boolean(hass, opening_1, "closed")
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_TEMP_NOT_REACHED
    )

    setup_boolean(hass, opening_2, "open")
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_TEMP_NOT_REACHED
    )

    # wait 10 seconds, actually 133 due to the other tests run time seems to affect this
    # needs to separate the tests
    await asyncio.sleep(13)
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.OPENING
    )

    setup_boolean(hass, opening_2, "closed")
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_TEMP_NOT_REACHED
    )


############
# OPENINGS #
############


async def test_fan_mode_opening(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode."""
    cooler_switch = "input_boolean.test"
    opening_1 = "input_boolean.opening_1"
    opening_2 = "input_boolean.opening_2"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"test": None, "opening_1": None, "opening_2": None}},
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
                "heater": cooler_switch,
                "fan_mode": "true",
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.FAN_ONLY,
                "openings": [
                    opening_1,
                    {"entity_id": opening_2, "timeout": {"seconds": 10}},
                ],
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_ON

    setup_boolean(hass, opening_1, "open")
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_boolean(hass, opening_1, "closed")
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_ON

    setup_boolean(hass, opening_2, "open")
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_ON

    # wait 10 seconds, actually 133 due to the other tests run time seems to affect this
    # needs to separate the tests
    await asyncio.sleep(13)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_boolean(hass, opening_2, "closed")
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_ON


@pytest.mark.parametrize(
    "hvac_mode",
    [
        (HVACMode.COOL),
        (HVACMode.FAN_ONLY),
    ],
)
async def test_cooler_fan_mode_opening(
    hass: HomeAssistant, hvac_mode, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode."""
    cooler_switch = "input_boolean.test"
    fan_switch = "input_boolean.test_fan"

    opening_1 = "input_boolean.opening_1"
    opening_2 = "input_boolean.opening_2"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {
            "input_boolean": {
                "test": None,
                "test_fan": None,
                "opening_1": None,
                "opening_2": None,
            }
        },
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
                "heater": cooler_switch,
                "ac_mode": "true",
                "fan": fan_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": hvac_mode,
                "openings": [
                    opening_1,
                    {"entity_id": opening_2, "timeout": {"seconds": 10}},
                ],
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()
    assert (
        hass.states.get(cooler_switch).state == STATE_ON
        if hvac_mode == HVACMode.COOL
        else STATE_OFF
    )
    assert (
        hass.states.get(fan_switch).state == STATE_OFF
        if hvac_mode == HVACMode.COOL
        else STATE_ON
    )

    setup_boolean(hass, opening_1, "open")
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    setup_boolean(hass, opening_1, "closed")
    await hass.async_block_till_done()

    assert (
        hass.states.get(cooler_switch).state == STATE_ON
        if hvac_mode == HVACMode.COOL
        else STATE_OFF
    )
    assert (
        hass.states.get(fan_switch).state == STATE_OFF
        if hvac_mode == HVACMode.COOL
        else STATE_ON
    )

    setup_boolean(hass, opening_2, "open")
    await hass.async_block_till_done()

    assert (
        hass.states.get(cooler_switch).state == STATE_ON
        if hvac_mode == HVACMode.COOL
        else STATE_OFF
    )
    assert (
        hass.states.get(fan_switch).state == STATE_OFF
        if hvac_mode == HVACMode.COOL
        else STATE_ON
    )

    # wait 10 seconds, actually 133 due to the other tests run time seems to affect this
    # needs to separate the tests
    await asyncio.sleep(13)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    setup_boolean(hass, opening_2, "closed")
    await hass.async_block_till_done()

    assert (
        hass.states.get(cooler_switch).state == STATE_ON
        if hvac_mode == HVACMode.COOL
        else STATE_OFF
    )
    assert (
        hass.states.get(fan_switch).state == STATE_OFF
        if hvac_mode == HVACMode.COOL
        else STATE_ON
    )


@pytest.mark.parametrize(
    ["hvac_mode", "oepning_scope", "switch_state", "fan_state"],
    [
        ([HVACMode.COOL, ["all"], STATE_OFF, STATE_OFF]),
        ([HVACMode.COOL, [HVACMode.COOL], STATE_OFF, STATE_OFF]),
        ([HVACMode.COOL, [HVACMode.FAN_ONLY], STATE_ON, STATE_OFF]),
        ([HVACMode.FAN_ONLY, ["all"], STATE_OFF, STATE_OFF]),
        ([HVACMode.FAN_ONLY, [HVACMode.COOL], STATE_OFF, STATE_ON]),
        ([HVACMode.FAN_ONLY, [HVACMode.FAN_ONLY], STATE_OFF, STATE_OFF]),
    ],
)
async def test_cooler_fan_mode_opening_scope(
    hass: HomeAssistant,
    hvac_mode,
    oepning_scope,
    switch_state,
    fan_state,
    setup_comp_1,  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode."""
    cooler_switch = "input_boolean.test"
    fan_switch = "input_boolean.test_fan"

    opening_1 = "input_boolean.opening_1"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {
            "input_boolean": {
                "test": None,
                "test_fan": None,
                "opening_1": None,
                "opening_2": None,
            }
        },
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
                "heater": cooler_switch,
                "ac_mode": "true",
                "fan": fan_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": hvac_mode,
                "openings": [
                    opening_1,
                ],
                "openings_scope": oepning_scope,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()
    assert (
        hass.states.get(cooler_switch).state == STATE_ON
        if hvac_mode == HVACMode.COOL
        else STATE_OFF
    )
    assert (
        hass.states.get(fan_switch).state == STATE_OFF
        if hvac_mode == HVACMode.COOL
        else STATE_ON
    )

    setup_boolean(hass, opening_1, STATE_OPEN)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == switch_state
    assert hass.states.get(fan_switch).state == fan_state

    setup_boolean(hass, opening_1, STATE_CLOSED)
    await hass.async_block_till_done()

    assert (
        hass.states.get(cooler_switch).state == STATE_ON
        if hvac_mode == HVACMode.COOL
        else STATE_OFF
    )
    assert (
        hass.states.get(fan_switch).state == STATE_OFF
        if hvac_mode == HVACMode.COOL
        else STATE_ON
    )
