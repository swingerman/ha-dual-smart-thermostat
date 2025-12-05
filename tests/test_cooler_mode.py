"""The tests for the dual_smart_thermostat."""

import datetime
from datetime import timedelta
import logging

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
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
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


###################
# CHANGE SETTINGS #
###################


async def test_get_hvac_modes(
    hass: HomeAssistant, setup_comp_heat_ac_cool  # noqa: F811
) -> None:
    """Test that the operation list returns the correct modes."""
    # GIVEN: A thermostat configured for cooling
    # (setup via fixture)

    # WHEN: Retrieving HVAC modes from the entity state
    state = hass.states.get(common.ENTITY)
    modes = state.attributes.get("hvac_modes")

    # THEN: Only COOL and OFF modes should be available
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
    # GIVEN: Thermostat with target temperature set to 23
    await common.async_set_temperature(hass, 23)

    # WHEN: Setting a preset mode
    await common.async_set_preset_mode(hass, preset)

    # THEN: Temperature should match the preset temperature
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
    # GIVEN: Thermostat with target temperature set to 23
    await common.async_set_temperature(hass, 23)

    # WHEN: Setting a preset mode
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)

    # THEN: Temperature should match the preset temperature
    assert state.attributes.get("temperature") == temp

    # WHEN: Resetting to PRESET_NONE
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)

    # THEN: Original temperature (23) should be restored
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
    # GIVEN: Thermostat with target temperature set to 23
    await common.async_set_temperature(hass, 23)

    # WHEN: Setting the same preset mode twice in a row
    await common.async_set_preset_mode(hass, preset)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)

    # THEN: Temperature should match the preset temperature
    assert state.attributes.get("temperature") == temp

    # WHEN: Resetting to PRESET_NONE
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)

    # THEN: Original temperature (23) should be restored
    assert state.attributes.get("temperature") == 23


async def test_set_preset_mode_invalid(
    hass: HomeAssistant, setup_comp_heat_ac_cool_presets  # noqa: F811
) -> None:
    """Test preset mode is case-insensitive and invalid case raises error."""
    # GIVEN: Thermostat with target temperature set to 23
    await common.async_set_temperature(hass, 23)

    # WHEN: Setting preset mode with lowercase "away"
    await common.async_set_preset_mode(hass, "away")
    state = hass.states.get(common.ENTITY)

    # THEN: Preset mode should be accepted (case insensitive)
    assert state.attributes.get("preset_mode") == "away"

    # WHEN: Setting preset mode with lowercase "none"
    await common.async_set_preset_mode(hass, "none")
    state = hass.states.get(common.ENTITY)

    # THEN: Preset mode should be accepted
    assert state.attributes.get("preset_mode") == "none"

    # WHEN: Attempting to set invalid preset mode with wrong case "Sleep"
    # THEN: Should raise ServiceValidationError
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

    # GIVEN: Thermostat with temperature set to 23 and preset mode applied
    await common.async_set_temperature(hass, 23)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)

    # THEN: Temperature should match preset_temp and previous target should be saved
    assert state.attributes.get("temperature") == preset_temp
    assert (
        state.attributes.get(ATTR_PREV_TARGET) == 23
        if preset is not PRESET_NONE
        else "none"
    )

    # WHEN: Changing target temperature while in preset mode
    await common.async_set_temperature(hass, target_temp)
    assert state.attributes.get("supported_features") == 401
    state = hass.states.get(common.ENTITY)

    # THEN: Temperature should be updated and preset mode should be preserved
    assert state.attributes.get("temperature") == target_temp
    assert state.attributes.get("preset_mode") == preset
    assert (
        state.attributes.get(ATTR_PREV_TARGET) == 23
        if preset is not PRESET_NONE
        else "none"
    )
    assert state.attributes.get("supported_features") == 401

    # WHEN: Changing preset_mode to None
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)

    # THEN: Temp should be picked from saved temp (or target_temp if was PRESET_NONE)
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

    # GIVEN: Thermostat with temperature set to 23 and preset mode applied
    await common.async_set_temperature(hass, 23)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)

    # THEN: Temperature should match preset_temp and previous target should be saved
    assert state.attributes.get("temperature") == preset_temp
    assert state.attributes.get(ATTR_PREV_TARGET) == 23

    # WHEN: Changing target temperature while in preset mode
    await common.async_set_temperature(hass, target_temp)
    state = hass.states.get(common.ENTITY)

    # THEN: Temperature should be updated and preset mode should be preserved
    assert state.attributes.get("temperature") == target_temp
    assert state.attributes.get("preset_mode") == preset
    assert state.attributes.get(ATTR_PREV_TARGET) == 23

    # WHEN: Setting the same preset_mode again
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)

    # THEN: Temperature should be restored from preset definition
    assert state.attributes.get("temperature") == preset_temp

    # WHEN: Setting preset_mode to none
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)

    # THEN: Temperature should be restored from saved temp
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

    # GIVEN: Thermostat with temperature set to 23 and preset mode applied
    await common.async_set_temperature(hass, 23)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)

    # THEN: Temperature should match preset_temp and previous target should be saved
    assert state.attributes.get("temperature") == preset_temp
    assert (
        state.attributes.get(ATTR_PREV_TARGET) == 23
        if preset is not PRESET_NONE
        else "none"
    )

    # WHEN: Changing target temperature while in preset mode
    await common.async_set_temperature(hass, target_temp)
    assert state.attributes.get("supported_features") == 401
    state = hass.states.get(common.ENTITY)

    # THEN: Temperature should be updated and preset mode should be preserved
    assert state.attributes.get("temperature") == target_temp
    assert state.attributes.get("preset_mode") == preset
    assert (
        state.attributes.get(ATTR_PREV_TARGET) == 23
        if preset is not PRESET_NONE
        else "none"
    )
    assert state.attributes.get("supported_features") == 401

    # WHEN: Changing preset_mode to None
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)

    # THEN: Temp should be picked from saved temp (or target_temp if was PRESET_NONE)
    assert (
        state.attributes.get("temperature") == target_temp
        if preset == PRESET_NONE
        else 23
    )


async def test_set_target_temp_ac_off(
    hass: HomeAssistant, setup_comp_heat_ac_cool  # noqa: F811
) -> None:
    """Test if target temperature turn ac off."""
    # GIVEN: AC is on and current temperature is 25
    calls = setup_switch(hass, True)
    setup_sensor(hass, 25)

    # WHEN: Setting target temperature above current (30 > 25)
    await common.async_set_temperature(hass, 30)
    await hass.async_block_till_done()

    # THEN: AC should turn off (no cooling needed)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_set_target_temp_ac_and_hvac_mode(
    hass: HomeAssistant, setup_comp_heat_ac_cool  # noqa: F811
) -> None:
    """Test the setting of the target temperature and HVAC mode together."""

    # GIVEN: Thermostat in OFF mode
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await hass.async_block_till_done()
    state = hass.states.get(common.ENTITY)
    assert state.state == HVACMode.OFF

    # WHEN: Setting temperature and HVAC mode together
    await common.async_set_temperature(hass, temperature=30, hvac_mode=HVACMode.COOL)
    await hass.async_block_till_done()

    # THEN: Both temperature and mode should be updated
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 30.0
    assert state.state == HVACMode.COOL


async def test_turn_away_mode_on_cooling(
    hass: HomeAssistant, setup_comp_heat_ac_cool  # noqa: F811
) -> None:
    """Test the setting away mode when cooling."""
    # GIVEN: AC on with current temperature 25
    setup_switch(hass, True)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    state = hass.states.get(common.ENTITY)

    # THEN: Should have PRESET_NONE and PRESET_AWAY modes available
    assert set(state.attributes.get("preset_modes")) == set([PRESET_NONE, PRESET_AWAY])

    # WHEN: Setting temperature to 19 and switching to PRESET_AWAY
    await common.async_set_temperature(hass, 19)
    await common.async_set_preset_mode(hass, PRESET_AWAY)
    state = hass.states.get(common.ENTITY)

    # THEN: Temperature should change to away preset (30)
    assert state.attributes.get("temperature") == 30


###################
# HVAC OPERATIONS #
###################


@pytest.mark.parametrize(
    ["from_hvac_mode", "to_hvac_mode"],
    [[HVACMode.OFF, HVACMode.COOL], [HVACMode.COOL, HVACMode.OFF]],
)
async def test_toggle(
    hass: HomeAssistant,
    from_hvac_mode,
    to_hvac_mode,
    setup_comp_heat_ac_cool,  # noqa: F811
) -> None:
    """Test toggling HVAC mode between OFF and COOL."""
    # GIVEN: Thermostat in from_hvac_mode
    await common.async_set_hvac_mode(hass, from_hvac_mode)

    # WHEN: Toggling the thermostat
    await common.async_toggle(hass)
    await hass.async_block_till_done()
    state = hass.states.get(common.ENTITY)

    # THEN: Mode should switch to to_hvac_mode
    assert state.state == to_hvac_mode

    # WHEN: Toggling again
    await common.async_toggle(hass)
    await hass.async_block_till_done()
    state = hass.states.get(common.ENTITY)

    # THEN: Mode should switch back to from_hvac_mode
    assert state.state == from_hvac_mode


async def test_hvac_mode_cool(
    hass: HomeAssistant, setup_comp_heat_ac_cool  # noqa: F811
) -> None:
    """Test change mode from OFF to COOL.

    Switch turns on when temp above target and mode changes.
    """
    # GIVEN: Thermostat OFF, target 25, current temp 30, switch off
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    calls = setup_switch(hass, False)

    # WHEN: Changing mode to COOL
    await common.async_set_hvac_mode(hass, HVACMode.COOL)

    # THEN: AC should turn on (current temp 30 > target 25)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_sensor_chhange_dont_control_ac_on_when_off(
    hass: HomeAssistant, setup_comp_heat_ac_cool  # noqa: F811
) -> None:
    """Test if temperature change doesn't turn ac on when off."""
    # GIVEN: Thermostat OFF, target 25, switch off
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await common.async_set_temperature(hass, 25)
    await hass.async_block_till_done()
    calls = setup_switch(hass, False)

    # WHEN: Temperature changes to 30 (above target)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()

    # THEN: AC should not turn on (mode is OFF)
    assert len(calls) == 0

    # WHEN: Temperature changes to 31 (even further above target)
    setup_sensor(hass, 31)
    await hass.async_block_till_done()

    # THEN: AC should still not turn on (mode is OFF)
    assert len(calls) == 0


async def test_set_target_temp_ac_on(
    hass: HomeAssistant, setup_comp_heat_ac_cool  # noqa: F811
) -> None:
    """Test if target temperature turn ac on."""
    # GIVEN: AC off, current temperature 30
    calls = setup_switch(hass, False)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()

    # WHEN: Setting target temperature below current (25 < 30)
    await common.async_set_temperature(hass, 25)

    # THEN: AC should turn on (cooling needed)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_temp_change_ac_off_within_tolerance(
    hass: HomeAssistant, setup_comp_heat_ac_cool  # noqa: F811
) -> None:
    """Test if temperature change doesn't turn ac off within tolerance."""
    # GIVEN: AC on, target temperature 30
    calls = setup_switch(hass, True)
    await common.async_set_temperature(hass, 30)

    # WHEN: Temperature changes to 29.8 (within tolerance of 30)
    setup_sensor(hass, 29.8)
    await hass.async_block_till_done()

    # THEN: AC should remain on (within tolerance)
    assert len(calls) == 0


async def test_set_temp_change_ac_off_outside_tolerance(
    hass: HomeAssistant, setup_comp_heat_ac_cool  # noqa: F811
) -> None:
    """Test if temperature change turn ac off."""
    # GIVEN: AC on, target temperature 30
    calls = setup_switch(hass, True)
    await common.async_set_temperature(hass, 30)

    # WHEN: Temperature changes to 27 (below target - tolerance)
    setup_sensor(hass, 27)
    await hass.async_block_till_done()

    # THEN: AC should turn off (target reached)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_temp_change_ac_on_within_tolerance(
    hass: HomeAssistant, setup_comp_heat_ac_cool  # noqa: F811
) -> None:
    """Test if temperature change doesn't turn ac on within tolerance."""
    # GIVEN: AC off, target temperature 25
    calls = setup_switch(hass, False)
    await common.async_set_temperature(hass, 25)

    # WHEN: Temperature changes to 25.2 (within tolerance of 25)
    setup_sensor(hass, 25.2)
    await hass.async_block_till_done()

    # THEN: AC should remain off (within tolerance)
    assert len(calls) == 0


async def test_temp_change_ac_on_outside_tolerance(
    hass: HomeAssistant, setup_comp_heat_ac_cool  # noqa: F811
) -> None:
    """Test if temperature change turn ac on."""
    # GIVEN: AC off, target temperature 25
    calls = setup_switch(hass, False)
    await common.async_set_temperature(hass, 25)

    # WHEN: Temperature changes to 30 (above target + tolerance)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()

    # THEN: AC should turn on (cooling needed)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_running_when_operating_mode_is_off_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool  # noqa: F811
) -> None:
    """Test that the switch turns off when HVAC mode is set to OFF."""
    # GIVEN: AC on, target temperature 30
    calls = setup_switch(hass, True)
    await common.async_set_temperature(hass, 30)

    # WHEN: Setting HVAC mode to OFF
    await common.async_set_hvac_mode(hass, HVACMode.OFF)

    # THEN: AC should turn off
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_no_state_change_when_operation_mode_off_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool  # noqa: F811
) -> None:
    """Test that the switch doesn't turn on when HVAC mode is OFF."""
    # GIVEN: AC off, target 30, mode OFF
    calls = setup_switch(hass, False)
    await common.async_set_temperature(hass, 30)
    await common.async_set_hvac_mode(hass, HVACMode.OFF)

    # WHEN: Temperature changes to 35 (well above target)
    setup_sensor(hass, 35)
    await hass.async_block_till_done()

    # THEN: AC should not turn on (mode is OFF)
    assert len(calls) == 0


@pytest.mark.parametrize("sw_on", [True, False])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_temp_change_ac_trigger_long_enough(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    sw_on,
    setup_comp_heat_ac_cool_cycle,  # noqa: F811
) -> None:
    """Test if temperature change respects minimum cycle duration before switching."""
    # GIVEN: AC in state sw_on, target 28, temperature appropriate for current state
    calls = setup_switch(hass, sw_on)
    await common.async_set_temperature(hass, 28)
    setup_sensor(hass, 30 if sw_on else 25)
    await hass.async_block_till_done()

    # Wait 6 minutes
    freezer.tick(timedelta(minutes=6))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # WHEN: Temperature changes to trigger opposite state
    setup_sensor(hass, 25 if sw_on else 30)
    await hass.async_block_till_done()

    # THEN: No call yet (min cycle duration not met)
    assert len(calls) == 0

    # WHEN: Temperature changes back (no switch needed)
    setup_sensor(hass, 30 if sw_on else 25)
    await hass.async_block_till_done()

    # Wait another 6 minutes (go over cycle time)
    freezer.tick(timedelta(minutes=6))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # THEN: Still no call (temperature doesn't require switching)
    assert len(calls) == 0

    # WHEN: Temperature changes to trigger switch again
    setup_sensor(hass, 25 if sw_on else 30)
    await hass.async_block_till_done()

    # THEN: Switch should trigger (cycle time met and temperature requires it)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF if sw_on else SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


@pytest.mark.parametrize("sw_on", [True, False])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_time_change_ac_trigger_long_enough(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    sw_on,
    setup_comp_heat_ac_cool_cycle,  # noqa: F811
) -> None:
    """Test if temperature change turn ac on or off when cycle time is past."""
    # GIVEN: AC in state sw_on, target 28, temperature appropriate for current state
    calls = setup_switch(hass, sw_on)
    await common.async_set_temperature(hass, 28)
    setup_sensor(hass, 30 if sw_on else 25)
    await hass.async_block_till_done()

    # Wait 6 minutes
    freezer.tick(timedelta(minutes=6))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # WHEN: Temperature changes to trigger opposite state
    setup_sensor(hass, 25 if sw_on else 30)
    await hass.async_block_till_done()

    # THEN: No call yet (min cycle duration not met)
    assert len(calls) == 0

    # WHEN: Time advances to complete cycle time
    freezer.tick(timedelta(minutes=5))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # THEN: Switch should trigger (cycle time met)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF if sw_on else SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


@pytest.mark.parametrize("sw_on", [True, False])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_mode_change_ac_trigger_not_long_enough(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    sw_on,
    setup_comp_heat_ac_cool_cycle,  # noqa: F811
) -> None:
    """Test if mode change turns ac off or on despite minimum cycle."""
    # GIVEN: AC in state sw_on, target 28, temperature appropriate for current state
    calls = setup_switch(hass, sw_on)
    await common.async_set_temperature(hass, 28)
    setup_sensor(hass, 30 if sw_on else 25)
    await hass.async_block_till_done()

    # Wait 6 minutes
    freezer.tick(timedelta(minutes=6))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # WHEN: Temperature changes to trigger opposite state
    setup_sensor(hass, 25 if sw_on else 30)
    await hass.async_block_till_done()

    # THEN: No call yet (min cycle duration not met)
    assert len(calls) == 0

    # WHEN: HVAC mode changes (bypasses minimum cycle)
    await common.async_set_hvac_mode(hass, HVACMode.OFF if sw_on else HVACMode.COOL)

    # THEN: Switch should trigger immediately (mode change overrides cycle time)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF if sw_on else SERVICE_TURN_ON
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
    # GIVEN: AC on, current temp 30, target 25
    setup_sensor(hass, 30)
    await common.async_set_temperature(hass, 25)
    calls = setup_switch(hass, True)

    # WHEN: Sensor becomes unavailable/unknown/stale
    hass.states.async_set(common.ENT_SENSOR, sensor_state)
    await hass.async_block_till_done()

    # Wait 3 minutes (past safety delay)
    common.async_fire_time_changed(
        hass, dt_util.utcnow() + datetime.timedelta(minutes=3)
    )
    await hass.async_block_till_done()

    # THEN: AC should turn off for safety
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
    """Test if sensor unavailable sets HVAC action reason to TEMPERATURE_SENSOR_STALLED."""

    # GIVEN: AC on, current temp 30, target 25
    setup_sensor(hass, 30)
    await common.async_set_temperature(hass, 25)
    calls = setup_switch(hass, True)  # noqa: F841

    # WHEN: Sensor becomes unavailable/unknown/stale
    hass.states.async_set(common.ENT_SENSOR, sensor_state)
    await hass.async_block_till_done()

    # Wait 3 minutes (past safety delay)
    common.async_fire_time_changed(
        hass, dt_util.utcnow() + datetime.timedelta(minutes=3)
    )
    await hass.async_block_till_done()

    # THEN: HVAC action reason should indicate stalled sensor
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
    """Test if sensor recovery resets HVAC action reason to NONE."""

    # GIVEN: AC on, current temp 30, target 25
    setup_sensor(hass, 30)
    await common.async_set_temperature(hass, 25)
    calls = setup_switch(hass, True)  # noqa: F841

    # WHEN: Sensor becomes unavailable/unknown/stale
    hass.states.async_set(common.ENT_SENSOR, sensor_state)
    await hass.async_block_till_done()

    # Wait 3 minutes (past safety delay)
    common.async_fire_time_changed(
        hass, dt_util.utcnow() + datetime.timedelta(minutes=3)
    )
    await hass.async_block_till_done()

    # THEN: HVAC action reason should indicate stalled sensor
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReasonInternal.TEMPERATURE_SENSOR_STALLED
    )
    caplog.set_level(logging.WARNING)

    # WHEN: Sensor state changes back to valid
    hass.states.async_set(common.ENT_SENSOR, 31)
    await hass.async_block_till_done()

    # THEN: HVAC action reason should be reset to NONE
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.NONE
    )


async def test_cooler_mode(hass: HomeAssistant, setup_comp_1) -> None:  # noqa: F811
    """Test thermostat cooler switch in cooling mode."""
    # GIVEN: Thermostat configured in AC mode with COOL initial state
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

    # THEN: Cooler should be off initially
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Current temp 23, target 18 (cooling needed)
    setup_sensor(hass, 23)
    await hass.async_block_till_done()
    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()

    # THEN: Cooler should turn on
    assert hass.states.get(cooler_switch).state == STATE_ON

    # WHEN: Temperature drops to 17 (below target)
    setup_sensor(hass, 17)
    await hass.async_block_till_done()

    # THEN: Cooler should turn off
    assert hass.states.get(cooler_switch).state == STATE_OFF


async def test_cooler_mode_change(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat cooler cycles on and off based on temperature changes."""
    # GIVEN: Thermostat configured in AC mode with COOL initial state
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

    # THEN: Cooler should be off initially
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Current temp 23, target 18 (cooling needed)
    setup_sensor(hass, 23)
    await hass.async_block_till_done()
    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()

    # THEN: Cooler should turn on
    assert hass.states.get(cooler_switch).state == STATE_ON

    # WHEN: Temperature drops to 17 (below target)
    setup_sensor(hass, 17)
    await hass.async_block_till_done()

    # THEN: Cooler should turn off
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Temperature rises back to 23 (above target)
    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    # THEN: Cooler should turn back on
    assert hass.states.get(cooler_switch).state == STATE_ON


async def test_cooler_mode_from_off_to_idle(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat switch state if HVAC mode changes."""
    # GIVEN: Thermostat configured in OFF mode, target 25, current temp 23
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

    # THEN: Switch should be off and HVAC action should be OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).attributes["hvac_action"] == HVACAction.OFF

    # WHEN: Changing HVAC mode to COOL
    await common.async_set_hvac_mode(hass, HVACMode.COOL)

    # THEN: Switch stays off but HVAC action changes to IDLE (temp below target)
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).attributes["hvac_action"] == HVACAction.IDLE


async def test_cooler_mode_off_switch_change_keeps_off(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test manual switch state changes don't affect HVAC action when mode is OFF."""
    # GIVEN: Thermostat configured in OFF mode, target 25, current temp 23
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

    # THEN: Switch should be off and HVAC action should be OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).attributes["hvac_action"] == HVACAction.OFF

    # WHEN: Manually turning switch on (simulating external change)
    hass.states.async_set(cooler_switch, STATE_ON)
    await hass.async_block_till_done()

    # THEN: Switch state changes but HVAC action remains OFF (mode is OFF)
    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(common.ENTITY).attributes["hvac_action"] == HVACAction.OFF


async def test_cooler_mode_tolerance(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test cooler respects hot and cold tolerance boundaries."""
    # GIVEN: Thermostat configured in COOL mode with tolerances (0.5)
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

    # THEN: Cooler should be off initially
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Current temp 22.4, target 22 (within tolerance 22 + 0.5)
    setup_sensor(hass, 22.4)
    await hass.async_block_till_done()
    await common.async_set_temperature(hass, 22)
    await hass.async_block_till_done()

    # THEN: Cooler should remain off (within tolerance)
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Temperature rises to 22.5 (at tolerance boundary 22 + 0.5)
    setup_sensor(hass, 22.5)
    await hass.async_block_till_done()

    # THEN: Cooler should turn on (reached hot tolerance)
    assert hass.states.get(cooler_switch).state == STATE_ON

    # WHEN: Temperature drops to 21.6 (within tolerance 22 - 0.5)
    setup_sensor(hass, 21.6)
    await hass.async_block_till_done()

    # THEN: Cooler should remain on (within cold tolerance)
    assert hass.states.get(cooler_switch).state == STATE_ON

    # WHEN: Temperature drops to 21.5 (at cold tolerance boundary 22 - 0.5)
    setup_sensor(hass, 21.5)
    await hass.async_block_till_done()

    # THEN: Cooler should turn off (reached cold tolerance)
    assert hass.states.get(cooler_switch).state == STATE_OFF


@pytest.mark.parametrize(
    ["duration", "result_state"],
    [(timedelta(seconds=10), STATE_ON), (timedelta(seconds=30), STATE_OFF)],
)
@pytest.mark.asyncio
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_cooler_mode_cycle(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    duration,
    result_state,
    setup_comp_1,  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode with cycle duration."""
    # GIVEN: Thermostat in COOL mode with 15s min cycle duration
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

    # THEN: Cooler should be off initially
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Current temp 23, target 18 (cooling needed)
    setup_sensor(hass, 23)
    await hass.async_block_till_done()
    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()

    # THEN: Cooler should turn on
    assert hass.states.get(cooler_switch).state == STATE_ON

    # WHEN: Time advances by duration and temperature drops to 17
    freezer.tick(duration)
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()
    setup_sensor(hass, 17)
    await hass.async_block_till_done()

    # THEN: Cooler state depends on cycle duration met
    # (10s -> still ON, 30s -> OFF as min cycle duration met)
    assert hass.states.get(cooler_switch).state == result_state


######################
# HVAC ACTION REASON #
######################


async def test_cooler_mode_opening_hvac_action_reason(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_comp_1  # noqa: F811
) -> None:
    """Test HVAC action reasons with opening sensors and timeouts in cooling mode."""
    # GIVEN: Thermostat with two openings (immediate and 5s timeout)
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
                    {
                        "entity_id": opening_2,
                        "timeout": {"seconds": 5},
                        "closing_timeout": {"seconds": 3},
                    },
                ],
            }
        },
    )
    await hass.async_block_till_done()

    # THEN: Initial HVAC action reason should be NONE
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.NONE
    )

    # WHEN: Setting temp 23, target 18 (cooling needed)
    setup_sensor(hass, 23)
    await hass.async_block_till_done()
    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()

    # THEN: HVAC action reason should be TARGET_TEMP_NOT_REACHED
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_TEMP_NOT_REACHED
    )

    # WHEN: Opening_1 opens (immediate action)
    setup_boolean(hass, opening_1, "open")
    await hass.async_block_till_done()

    # THEN: HVAC action reason should be OPENING
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.OPENING
    )

    # WHEN: Opening_1 closes
    setup_boolean(hass, opening_1, "closed")
    await hass.async_block_till_done()

    # THEN: HVAC action reason should revert to TARGET_TEMP_NOT_REACHED
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_TEMP_NOT_REACHED
    )

    # WHEN: Opening_2 opens (with 5s timeout)
    setup_boolean(hass, opening_2, "open")
    await hass.async_block_till_done()

    # THEN: HVAC action reason stays TARGET_TEMP_NOT_REACHED (timeout not met)
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_TEMP_NOT_REACHED
    )

    # WHEN: Wait 6 seconds (past 5s timeout)
    freezer.tick(timedelta(seconds=6))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # THEN: HVAC action reason should now be OPENING
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.OPENING
    )

    # WHEN: Opening_2 closes
    setup_boolean(hass, opening_2, "closed")
    await hass.async_block_till_done()

    # THEN: HVAC action reason stays OPENING (closing_timeout not met)
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.OPENING
    )

    # WHEN: Wait 4 more seconds (past 3s closing_timeout)
    freezer.tick(timedelta(seconds=4))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # THEN: HVAC action reason should revert to TARGET_TEMP_NOT_REACHED
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
    """Test HVAC power level and percent calculations with 5 power levels in cooling mode."""
    # GIVEN: Thermostat with 5 power levels and one opening sensor
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

    # THEN: Initial power levels should be 0
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_LEVEL) == 0
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_PERCENT) == 0

    # WHEN: Current temp 23, target 18 (max cooling needed)
    setup_sensor(hass, 23)
    await hass.async_block_till_done()
    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()

    # THEN: Should be cooling at max power (level 5, 100%)
    assert (
        hass.states.get(common.ENTITY).attributes.get("hvac_action")
        == HVACAction.COOLING
    )
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_LEVEL) == 5
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_PERCENT) == 100

    # WHEN: Opening opens
    setup_boolean(hass, opening_1, STATE_OPEN)
    await hass.async_block_till_done()

    # THEN: Should go idle with zero power
    assert (
        hass.states.get(common.ENTITY).attributes.get("hvac_action") == HVACAction.IDLE
    )
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_LEVEL) == 0
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_PERCENT) == 0

    # WHEN: Opening closes and temp drops to 17 (below target)
    setup_boolean(hass, opening_1, STATE_CLOSED)
    setup_sensor(hass, 17)
    await hass.async_block_till_done()

    # THEN: Cooler should be off with zero power (target reached)
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_LEVEL) == 0
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_PERCENT) == 0

    # WHEN: Temp rises to 18.5 (slightly above target)
    setup_sensor(hass, 18.5)
    await hass.async_block_till_done()

    # THEN: Should cool at medium power (level 2, 50%)
    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_LEVEL) == 2
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_PERCENT) == 50

    # WHEN: HVAC mode set to OFF
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await hass.async_block_till_done()

    # THEN: Cooler should turn off with zero power
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_LEVEL) == 0
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_PERCENT) == 0


async def test_cooler_mode_hvac_power_value_2(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test HVAC power level and percent calculations with 3 power levels in cooling mode."""
    # GIVEN: Thermostat with 3 power levels
    cooler_switch = "input_boolean.test"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"test": None}},
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

    # THEN: Initial power levels should be 0
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_LEVEL) == 0
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_PERCENT) == 0

    # WHEN: Current temp 23, target 18 (max cooling needed)
    setup_sensor(hass, 23)
    await hass.async_block_till_done()
    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()

    # THEN: Should be cooling at max power (level 3, 100%)
    assert (
        hass.states.get(common.ENTITY).attributes.get("hvac_action")
        == HVACAction.COOLING
    )
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_LEVEL) == 3
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_PERCENT) == 100

    # WHEN: Temp drops to 18.5 (medium cooling needed)
    setup_sensor(hass, 18.5)
    await hass.async_block_till_done()

    # THEN: Should cool at medium power (level 2, 50%)
    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_LEVEL) == 2
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_PERCENT) == 50

    # WHEN: Temp drops to 18.3 (low cooling needed)
    setup_sensor(hass, 18.3)
    await hass.async_block_till_done()

    # THEN: Should cool at low power (level 1, 33%)
    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_LEVEL) == 1
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_PERCENT) == 33

    # WHEN: HVAC mode set to OFF
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await hass.async_block_till_done()

    # THEN: Cooler should turn off with zero power
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_LEVEL) == 0
    assert hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_POWER_PERCENT) == 0


############
# OPENINGS #
############


async def test_cooler_mode_opening(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_comp_1  # noqa: F811
) -> None:
    """Test opening sensors with immediate and delayed timeouts pause cooling."""
    # GIVEN: Thermostat with two openings (immediate and with timeouts)
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
                    {
                        "entity_id": opening_2,
                        "timeout": {"seconds": 5},
                        "closing_timeout": {"seconds": 3},
                    },
                ],
            }
        },
    )
    await hass.async_block_till_done()

    # THEN: Cooler should be off initially
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Current temp 23, target 18 (cooling needed)
    setup_sensor(hass, 23)
    await hass.async_block_till_done()
    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()

    # THEN: Cooler should turn on
    assert hass.states.get(cooler_switch).state == STATE_ON

    # WHEN: Opening_1 opens (immediate effect)
    setup_boolean(hass, opening_1, "open")
    await hass.async_block_till_done()

    # THEN: Cooler should turn off immediately
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Opening_1 closes
    setup_boolean(hass, opening_1, "closed")
    await hass.async_block_till_done()

    # THEN: Cooler should turn back on
    assert hass.states.get(cooler_switch).state == STATE_ON

    # WHEN: Opening_2 opens (with 5s timeout)
    setup_boolean(hass, opening_2, "open")
    await hass.async_block_till_done()

    # THEN: Cooler should remain on (timeout not met yet)
    assert hass.states.get(cooler_switch).state == STATE_ON

    # WHEN: Wait 6 seconds (past 5s timeout)
    freezer.tick(timedelta(seconds=6))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # THEN: Cooler should turn off (timeout triggered)
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Opening_2 closes
    setup_boolean(hass, opening_2, "closed")
    await hass.async_block_till_done()

    # THEN: Cooler should remain off (closing_timeout not met)
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Wait 4 more seconds (past 3s closing_timeout)
    freezer.tick(timedelta(seconds=4))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # THEN: Cooler should turn back on (closing_timeout complete)
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
    """Test opening scope configuration limits which HVAC modes are affected."""
    # GIVEN: Thermostat with opening configured with specific scope
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
                "openings": [opening_1],
                "openings_scope": oepning_scope,
            }
        },
    )
    await hass.async_block_till_done()

    # THEN: Cooler should be off initially
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Current temp 23, target 18 (cooling needed)
    setup_sensor(hass, 23)
    await hass.async_block_till_done()
    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()

    # THEN: Cooler state depends on HVAC mode
    assert (
        hass.states.get(cooler_switch).state == STATE_ON
        if hvac_mode == HVACMode.COOL
        else STATE_OFF
    )

    # WHEN: Opening opens
    setup_boolean(hass, opening_1, STATE_OPEN)
    await hass.async_block_till_done()

    # THEN: Cooler state depends on scope (affects COOL mode or not)
    assert hass.states.get(cooler_switch).state == switch_state

    # WHEN: Opening closes
    setup_boolean(hass, opening_1, STATE_CLOSED)
    await hass.async_block_till_done()

    # THEN: Cooler returns to normal state based on HVAC mode
    assert (
        hass.states.get(cooler_switch).state == STATE_ON
        if hvac_mode == HVACMode.COOL
        else STATE_OFF
    )


################################################
# FUNCTIONAL TESTS - TOLERANCE CONFIGURATIONS #
################################################


async def test_legacy_config_cool_mode_behaves_identically(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test legacy config in COOL mode behaves identically.

    This test verifies backward compatibility - configurations using only
    cold_tolerance and hot_tolerance (no cool_tolerance) should work
    correctly in COOL mode.
    """
    # GIVEN: Thermostat with legacy config (cold/hot tolerance, no cool_tolerance)
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

    # Configure with ONLY cold_tolerance=0.5, hot_tolerance=0.5 (NO cool_tolerance)
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
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
            }
        },
    )
    await hass.async_block_till_done()

    # WHEN: Setting target to 22°C
    await common.async_set_temperature(hass, 22)
    await hass.async_block_till_done()

    # WHEN: Current temp is 22.6°C (above target + hot_tolerance)
    setup_sensor(hass, 22.6)
    await hass.async_block_till_done()

    # THEN: Cooler should activate (22.6 >= 22 + 0.5 = 22.5)
    assert hass.states.get(cooler_switch).state == STATE_ON

    # WHEN: Temp drops to 21.4°C (below target - cold_tolerance)
    setup_sensor(hass, 21.4)
    await hass.async_block_till_done()

    # THEN: Cooler should deactivate (21.4 <= 22 - 0.5 = 21.5)
    # Verifies cooling uses legacy tolerances correctly
    assert hass.states.get(cooler_switch).state == STATE_OFF
