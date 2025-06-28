"""The tests for the dual_smart_thermostat."""

import datetime
from datetime import timedelta
import logging

from freezegun import freeze_time
from freezegun.api import FrozenDateTimeFactory
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
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
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
    ATTR_HVAC_POWER_LEVEL,
    ATTR_HVAC_POWER_PERCENT,
    ATTR_PREV_TARGET,
    DOMAIN,
    PRESET_ANTI_FREEZE,
)
from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason import (
    HVACActionReason,
)
from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason_internal import (
    HVACActionReasonInternal,
)

from . import (  # noqa: F401
    common,
    setup_boolean,
    setup_comp_1,
    setup_comp_heat_ac_cool,
    setup_comp_heat_ac_cool_cycle,
    setup_comp_heat_ac_cool_cycle_kepp_alive,
    setup_comp_heat_ac_cool_fan_config,
    setup_comp_heat_ac_cool_presets,
    setup_comp_heat_ac_cool_presets_range,
    setup_comp_heat_ac_cool_safety_delay,
    setup_fan,
    setup_sensor,
    setup_switch,
)

COLD_TOLERANCE = 0.5
HOT_TOLERANCE = 0.5

_LOGGER = logging.getLogger(__name__)

###################
# COMMON FEATURES #
###################


async def test_unique_id(
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
                "ac_mode": "true",
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
                "ac_mode": "true",
            }
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get(common.ENTITY).attributes["current_temperature"] == 18


###################
# CHANGE SETTINGS #
###################


async def test_get_hvac_modes(
    hass: HomeAssistant, setup_comp_heat_ac_cool  # noqa: F811
) -> None:
    """Test that the operation list returns the correct modes."""
    state = hass.states.get(common.ENTITY)
    modes = state.attributes.get("hvac_modes")
    assert modes == [HVACMode.COOL, HVACMode.OFF]


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
    hass: HomeAssistant, setup_comp_heat_ac_cool_presets, preset, temp  # noqa: F811
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
    hass: HomeAssistant, setup_comp_heat_ac_cool_presets, preset, temp  # noqa: F811
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
    hass: HomeAssistant, setup_comp_heat_ac_cool_presets, preset, temp  # noqa: F811
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
    hass: HomeAssistant, setup_comp_heat_ac_cool_presets  # noqa: F811
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
    ("preset", "preset_temp"),
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
    setup_comp_heat_ac_cool_presets,  # noqa: F811
    preset,
    preset_temp,
) -> None:
    """Test the setting preset mode then set temperature.

    Verify preset mode preserved while temperature updated.
    """
    target_temp = 32

    # Sets the temperature and apply preset mode, temp should be preset_temp
    await common.async_set_temperature(hass, 23)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == preset_temp
    assert (
        state.attributes.get(ATTR_PREV_TARGET) == 23
        if preset is not PRESET_NONE
        else "none"
    )

    # Changes target temperature, preset mode should be preserved
    await common.async_set_temperature(hass, target_temp)
    assert state.attributes.get("supported_features") == 401
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == target_temp
    assert state.attributes.get("preset_mode") == preset
    assert (
        state.attributes.get(ATTR_PREV_TARGET) == 23
        if preset is not PRESET_NONE
        else "none"
    )
    assert state.attributes.get("supported_features") == 401

    # Changes preset_mode to None, temp should be picked from saved temp
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    assert (
        state.attributes.get("temperature") == target_temp
        if preset == PRESET_NONE
        else 23
    )


@pytest.mark.parametrize(
    ("preset", "preset_temp"),
    [
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
async def test_set_same_preset_mode_restores_preset_temp_from_modified(
    hass: HomeAssistant,
    setup_comp_heat_ac_cool_presets,  # noqa: F811
    preset,
    preset_temp,
) -> None:
    """Test the setting preset mode again after modifying temperature.

    Verify preset mode called twice restores presete temperatures.
    """

    target_temp = 32

    # Sets the temperature and apply preset mode, temp should be preset_temp
    await common.async_set_temperature(hass, 23)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == preset_temp
    assert state.attributes.get(ATTR_PREV_TARGET) == 23

    # Changes target temperature, preset mode should be preserved
    await common.async_set_temperature(hass, target_temp)

    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == target_temp
    assert state.attributes.get("preset_mode") == preset
    assert state.attributes.get(ATTR_PREV_TARGET) == 23

    # Sets the same preset_mode again, temp should be picked from preset
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == preset_temp

    # Sets the  preset_mode to none, temp should be picked from saved temp
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 23


@pytest.mark.parametrize(
    ("preset", "preset_temp"),
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
async def test_set_preset_mode_picks_temp_from_preset(
    hass: HomeAssistant,
    setup_comp_heat_ac_cool_presets_range,  # noqa: F811
    preset,
    preset_temp,
) -> None:
    """Test the setting preset mode then set temperature.

    Verify preset mode preserved while temperature updated.
    """
    target_temp = 32

    # Sets the temperature and apply preset mode, temp should be preset_temp
    await common.async_set_temperature(hass, 23)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == preset_temp
    assert (
        state.attributes.get(ATTR_PREV_TARGET) == 23
        if preset is not PRESET_NONE
        else "none"
    )

    # Changes target temperature, preset mode should be preserved
    await common.async_set_temperature(hass, target_temp)
    assert state.attributes.get("supported_features") == 401
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == target_temp
    assert state.attributes.get("preset_mode") == preset
    assert (
        state.attributes.get(ATTR_PREV_TARGET) == 23
        if preset is not PRESET_NONE
        else "none"
    )
    assert state.attributes.get("supported_features") == 401

    # Changes preset_mode to None, temp should be picked from saved temp
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    assert (
        state.attributes.get("temperature") == target_temp
        if preset == PRESET_NONE
        else 23
    )


async def test_set_target_temp_ac_off(
    hass: HomeAssistant, setup_comp_heat_ac_cool  # noqa: F811
) -> None:
    """Test if target temperature turn ac off."""
    calls = setup_switch(hass, True)
    setup_sensor(hass, 25)
    await common.async_set_temperature(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_set_target_temp_ac_and_hvac_mode(
    hass: HomeAssistant, setup_comp_heat_ac_cool  # noqa: F811
) -> None:
    """Test the setting of the target temperature and HVAC mode together."""

    # Given
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await hass.async_block_till_done()
    state = hass.states.get(common.ENTITY)
    assert state.state == HVACMode.OFF

    # When
    await common.async_set_temperature(hass, temperature=30, hvac_mode=HVACMode.COOL)
    await hass.async_block_till_done()

    # Then
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 30.0
    assert state.state == HVACMode.COOL


async def test_turn_away_mode_on_cooling(
    hass: HomeAssistant, setup_comp_heat_ac_cool  # noqa: F811
) -> None:
    """Test the setting away mode when cooling."""
    setup_switch(hass, True)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    state = hass.states.get(common.ENTITY)
    assert set(state.attributes.get("preset_modes")) == set([PRESET_NONE, PRESET_AWAY])
    await common.async_set_temperature(hass, 19)
    await common.async_set_preset_mode(hass, PRESET_AWAY)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 30


###################
# HVAC OPERATIONS #
###################


@pytest.mark.parametrize(
    ["from_hvac_mode", "to_hvac_mode"],
    [
        [HVACMode.OFF, HVACMode.COOL],
        [HVACMode.COOL, HVACMode.OFF],
    ],
)
async def test_toggle(
    hass: HomeAssistant,
    from_hvac_mode,
    to_hvac_mode,
    setup_comp_heat_ac_cool,  # noqa: F811
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


async def test_hvac_mode_cool(
    hass: HomeAssistant, setup_comp_heat_ac_cool  # noqa: F811
) -> None:
    """Test change mode from OFF to COOL.

    Switch turns on when temp below setpoint and mode changes.
    """
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    calls = setup_switch(hass, False)
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_sensor_chhange_dont_control_ac_on_when_off(
    hass: HomeAssistant, setup_comp_heat_ac_cool  # noqa: F811
) -> None:
    """Test if temperature change doesn't turn ac on when off."""
    # Given
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await common.async_set_temperature(hass, 25)
    await hass.async_block_till_done()
    calls = setup_switch(hass, False)

    # When
    setup_sensor(hass, 30)
    await hass.async_block_till_done()

    # Then
    assert len(calls) == 0

    # When
    setup_sensor(hass, 31)
    await hass.async_block_till_done()

    # Then
    assert len(calls) == 0


async def test_set_target_temp_ac_on(
    hass: HomeAssistant, setup_comp_heat_ac_cool  # noqa: F811
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


async def test_temp_change_ac_off_within_tolerance(
    hass: HomeAssistant, setup_comp_heat_ac_cool  # noqa: F811
) -> None:
    """Test if temperature change doesn't turn ac off within tolerance."""
    calls = setup_switch(hass, True)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 29.8)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_set_temp_change_ac_off_outside_tolerance(
    hass: HomeAssistant, setup_comp_heat_ac_cool  # noqa: F811
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


async def test_temp_change_ac_on_within_tolerance(
    hass: HomeAssistant, setup_comp_heat_ac_cool  # noqa: F811
) -> None:
    """Test if temperature change doesn't turn ac on within tolerance."""
    calls = setup_switch(hass, False)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 25.2)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_ac_on_outside_tolerance(
    hass: HomeAssistant, setup_comp_heat_ac_cool  # noqa: F811
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


async def test_running_when_operating_mode_is_off_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool  # noqa: F811
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


async def test_no_state_change_when_operation_mode_off_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool  # noqa: F811
) -> None:
    """Test that the switch doesn't turn on when enabled is False."""
    calls = setup_switch(hass, False)
    await common.async_set_temperature(hass, 30)
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    setup_sensor(hass, 35)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_ac_trigger_on_not_long_enough(
    hass: HomeAssistant, setup_comp_heat_ac_cool_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn ac on."""
    calls = setup_switch(hass, False)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_ac_trigger_on_long_enough(
    hass: HomeAssistant, setup_comp_heat_ac_cool_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn ac on."""
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


async def test_temp_change_ac_trigger_off_not_long_enough(
    hass: HomeAssistant, setup_comp_heat_ac_cool_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn ac on."""
    calls = setup_switch(hass, True)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_ac_trigger_off_long_enough(
    hass: HomeAssistant, setup_comp_heat_ac_cool_cycle  # noqa: F811
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


async def test_mode_change_ac_trigger_off_not_long_enough(
    hass: HomeAssistant, setup_comp_heat_ac_cool_cycle  # noqa: F811
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


async def test_mode_change_ac_trigger_on_not_long_enough(
    hass: HomeAssistant, setup_comp_heat_ac_cool_cycle  # noqa: F811
) -> None:
    """Test if mode change turns ac on despite minimum cycle."""
    calls = setup_switch(hass, False)
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


async def test_temp_change_ac_trigger_on_not_long_enough_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn ac on."""
    calls = setup_switch(hass, False)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_ac_trigger_on_long_enough_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn ac on."""
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


async def test_temp_change_ac_trigger_off_not_long_enough_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn ac on."""
    calls = setup_switch(hass, True)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_ac_trigger_off_long_enough_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_cycle  # noqa: F811
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


async def test_mode_change_ac_trigger_off_not_long_enough_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_cycle  # noqa: F811
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


async def test_mode_change_ac_trigger_on_not_long_enough_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_cycle  # noqa: F811
) -> None:
    """Test if mode change turns ac on despite minimum cycle."""
    calls = setup_switch(hass, False)
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


@pytest.mark.parametrize(
    "sensor_state",
    [30, STATE_UNAVAILABLE, STATE_UNKNOWN],
)
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_sensor_unknown_secure_ac_off_outside_stale_duration(
    hass: HomeAssistant,
    sensor_state,
    setup_comp_heat_ac_cool_safety_delay,  # noqa: F811
) -> None:
    """Test if sensor unavailable for defined delay turns off AC."""
    setup_sensor(hass, 30)
    await common.async_set_temperature(hass, 25)
    calls = setup_switch(hass, True)

    # set up sensor in th edesired state
    hass.states.async_set(common.ENT_SENSOR, sensor_state)
    await hass.async_block_till_done()

    # Wait 3 minutes
    common.async_fire_time_changed(
        hass, dt_util.utcnow() + datetime.timedelta(minutes=3)
    )
    await hass.async_block_till_done()

    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


@pytest.mark.parametrize(
    "sensor_state",
    [30, STATE_UNAVAILABLE, STATE_UNKNOWN],
)
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_sensor_stalled_secure_ac_off_outside_stale_duration_reason(
    hass: HomeAssistant,
    sensor_state,
    setup_comp_heat_ac_cool_safety_delay,  # noqa: F811
) -> None:
    """Test if sensor unavailable for defined delay turns off AC."""

    setup_sensor(hass, 30)
    await common.async_set_temperature(hass, 25)
    calls = setup_switch(hass, True)  # noqa: F841

    # set up sensor in th edesired state
    hass.states.async_set(common.ENT_SENSOR, sensor_state)
    await hass.async_block_till_done()

    # Wait 3 minutes
    common.async_fire_time_changed(
        hass, dt_util.utcnow() + datetime.timedelta(minutes=3)
    )
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReasonInternal.TEMPERATURE_SENSOR_STALLED
    )


@pytest.mark.parametrize(
    "sensor_state",
    [30, STATE_UNAVAILABLE, STATE_UNKNOWN],
)
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_sensor_restores_after_state_changes(
    hass: HomeAssistant,
    sensor_state,
    setup_comp_heat_ac_cool_safety_delay,  # noqa: F811
    caplog,
) -> None:
    """Test if sensor unavailable for defined delay turns off AC."""

    # Given
    setup_sensor(hass, 30)
    await common.async_set_temperature(hass, 25)
    calls = setup_switch(hass, True)  # noqa: F841

    # set up sensor in th edesired state
    hass.states.async_set(common.ENT_SENSOR, sensor_state)
    await hass.async_block_till_done()

    # When
    # Wait 3 minutes
    common.async_fire_time_changed(
        hass, dt_util.utcnow() + datetime.timedelta(minutes=3)
    )
    await hass.async_block_till_done()

    # Then
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReasonInternal.TEMPERATURE_SENSOR_STALLED
    )
    caplog.set_level(logging.WARNING)

    # When
    # Sensor state changes
    hass.states.async_set(common.ENT_SENSOR, 31)
    await hass.async_block_till_done()

    # Then
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.NONE
    )


async def test_cooler_mode(hass: HomeAssistant, setup_comp_1) -> None:  # noqa: F811
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
                "ac_mode": "true",
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.COOL,
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


async def test_cooler_mode_change(
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
                "ac_mode": "true",
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.COOL,
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

    setup_sensor(hass, 23)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_ON


async def test_cooler_mode_from_off_to_idle(
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
                "ac_mode": "true",
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


async def test_cooler_mode_off_switch_change_keeps_off(
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
                "ac_mode": "true",
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

    hass.states.async_set(cooler_switch, STATE_ON)

    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(common.ENTITY).attributes["hvac_action"] == HVACAction.OFF


async def test_cooler_mode_tolerance(
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
                "ac_mode": "true",
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.COOL,
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


@pytest.mark.parametrize(
    ["duration", "result_state"],
    [
        (timedelta(seconds=10), STATE_ON),
        (timedelta(seconds=30), STATE_OFF),
    ],
)
@pytest.mark.asyncio
async def test_cooler_mode_cycle(
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
                "ac_mode": "true",
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.COOL,
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


######################
# HVAC ACTION REASON #
######################


async def test_cooler_mode_opening_hvac_action_reason(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_comp_1  # noqa: F811
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
                "ac_mode": "true",
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.COOL,
                "openings": [
                    opening_1,
                    {"entity_id": opening_2, "timeout": {"seconds": 5}},
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

    # wait 5 seconds
    freezer.tick(timedelta(seconds=6))
    common.async_fire_time_changed(hass)
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

    # wait 5 seconds
    # common.async_fire_time_changed(
    #     hass, dt_util.utcnow() + datetime.timedelta(seconds=15)
    # )
    # await asyncio.sleep(5)
    freezer.tick(timedelta(seconds=6))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.OPENING
    )

    setup_boolean(hass, opening_2, "closed")
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.OPENING
    )

    # wait 5 seconds
    # common.async_fire_time_changed(
    #     hass, dt_util.utcnow() + datetime.timedelta(seconds=15)
    # )
    # await asyncio.sleep(5)
    freezer.tick(timedelta(seconds=6))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_TEMP_NOT_REACHED
    )


#######################
#  HVAC POWER VALUES  #
#######################


async def test_cooler_mode_hvac_power_value(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode."""
    cooler_switch = "input_boolean.test"
    opening_1 = "input_boolean.opening_1"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"test": None, "opening_1": None}},
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
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.COOL,
                "hvac_power_levels": 5,
                "openings": [opening_1],
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_LEVEL) == 0
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_PERCENT) == 0

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get("hvac_action")
        == HVACAction.COOLING
    )
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_LEVEL) == 5
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_PERCENT) == 100

    setup_boolean(hass, opening_1, STATE_OPEN)
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get("hvac_action") == HVACAction.IDLE
    )
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_LEVEL) == 0
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_PERCENT) == 0

    setup_boolean(hass, opening_1, STATE_CLOSED)
    setup_sensor(hass, 17)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_LEVEL) == 0
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_PERCENT) == 0

    setup_sensor(hass, 18.5)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_LEVEL) == 2
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_PERCENT) == 50

    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_LEVEL) == 0
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_PERCENT) == 0


async def test_cooler_mode_hvac_power_value_2(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode."""
    cooler_switch = "input_boolean.test"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {
            "input_boolean": {"test": None},
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
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.COOL,
                "hvac_power_levels": 3,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_LEVEL) == 0
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_PERCENT) == 0

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get("hvac_action")
        == HVACAction.COOLING
    )
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_LEVEL) == 3
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_PERCENT) == 100

    setup_sensor(hass, 18.5)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_LEVEL) == 2
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_PERCENT) == 50

    setup_sensor(hass, 18.3)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_LEVEL) == 1
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_PERCENT) == 33

    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_LEVEL) == 0
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_PERCENT) == 0


############
# OPENINGS #
############


async def test_cooler_mode_opening(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_comp_1  # noqa: F811
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
                "ac_mode": "true",
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.COOL,
                "openings": [
                    opening_1,
                    {"entity_id": opening_2, "timeout": {"seconds": 5}},
                ],
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_boolean(hass, opening_2, "closed")
    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    freezer.tick(timedelta(seconds=6))
    common.async_fire_time_changed(hass)
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

    # wait 5 seconds, actually 133 due to the other tests run time seems to affect this
    # needs to separate the tests
    # common.async_fire_time_changed(
    #     hass, dt_util.utcnow() + datetime.timedelta(minutes=10)
    # )
    # await asyncio.sleep(5)
    freezer.tick(timedelta(seconds=6))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_boolean(hass, opening_2, "closed")
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF

    # wait 5 seconds, actually 133 due to the other tests run time seems to affect this
    # needs to separate the tests
    # common.async_fire_time_changed(
    #     hass, dt_util.utcnow() + datetime.timedelta(minutes=10)
    # )
    freezer.tick(timedelta(seconds=6))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_ON


@pytest.mark.parametrize(
    ["hvac_mode", "oepning_scope", "switch_state"],
    [
        ([HVACMode.COOL, ["all"], STATE_OFF]),
        ([HVACMode.COOL, [HVACMode.COOL], STATE_OFF]),
        ([HVACMode.COOL, [HVACMode.FAN_ONLY], STATE_ON]),
    ],
)
async def test_cooler_mode_opening_scope(
    hass: HomeAssistant,
    hvac_mode,
    oepning_scope,
    switch_state,
    setup_comp_1,  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode."""
    cooler_switch = "input_boolean.test"

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

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()
    assert (
        hass.states.get(cooler_switch).state == STATE_ON
        if hvac_mode == HVACMode.COOL
        else STATE_OFF
    )

    setup_boolean(hass, opening_1, STATE_OPEN)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == switch_state

    setup_boolean(hass, opening_1, STATE_CLOSED)
    await hass.async_block_till_done()

    assert (
        hass.states.get(cooler_switch).state == STATE_ON
        if hvac_mode == HVACMode.COOL
        else STATE_OFF
    )
