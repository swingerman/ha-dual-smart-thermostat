"""The tests for the dual_smart_thermostat."""

import asyncio
import datetime
from datetime import timedelta
import logging
from unittest.mock import patch

from freezegun import freeze_time
from homeassistant import config as hass_config
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
from homeassistant.components.climate.const import ATTR_PRESET_MODE, DOMAIN as CLIMATE
from homeassistant.const import (
    ATTR_TEMPERATURE,
    SERVICE_RELOAD,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import DOMAIN as HASS_DOMAIN, CoreState, HomeAssistant, State
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt, dt as dt_util
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest
import voluptuous as vol

from custom_components.dual_smart_thermostat.const import (
    ATTR_HVAC_ACTION_REASON,
    DOMAIN,
    PRESET_ANTI_FREEZE,
)
from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason import (
    SET_HVAC_ACTION_REASON_SIGNAL,
    HVACActionReason,
    HVACActionReasonExternal,
)

from . import (  # noqa: F401
    common,
    setup_boolean,
    setup_comp_1,
    setup_comp_heat,
    setup_comp_heat_cycle,
    setup_comp_heat_cycle_precision,
    setup_comp_heat_floor_opening_sensor,
    setup_comp_heat_presets,
    setup_floor_sensor,
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
            }
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get(common.ENTITY).state == HVACMode.OFF


async def test_setup_gets_current_temp_from_sensor(
    hass: HomeAssistant,
) -> None:
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
            }
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get(common.ENTITY).attributes["current_temperature"] == 18


async def test_default_setup_params(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test the setup with default parameters."""
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("min_temp") == 7
    assert state.attributes.get("max_temp") == 35
    assert state.attributes.get("temperature") == 7
    assert state.attributes.get("target_temp_step") == 0.1


@pytest.mark.parametrize("hvac_mode", [HVACMode.OFF, HVACMode.HEAT])
async def test_restore_state(hass: HomeAssistant, hvac_mode) -> None:
    """Ensure states are restored on startup."""
    common.mock_restore_cache(
        hass,
        (
            State(
                "climate.test_thermostat",
                hvac_mode,
                {ATTR_TEMPERATURE: "20", ATTR_PRESET_MODE: PRESET_AWAY},
            ),
        ),
    )

    hass.set_state(CoreState.starting)

    await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test_thermostat",
                "heater": common.ENT_SWITCH,
                "target_sensor": common.ENT_SENSOR,
                "away": {"temperature": 14},
            }
        },
    )
    await hass.async_block_till_done()
    state = hass.states.get("climate.test_thermostat")
    assert state.attributes[ATTR_TEMPERATURE] == 20
    assert state.attributes[ATTR_PRESET_MODE] == PRESET_AWAY
    assert state.state == hvac_mode


async def test_no_restore_state(hass: HomeAssistant) -> None:
    """Ensure states are restored on startup if they exist.

    Allows for graceful reboot.
    """
    common.mock_restore_cache(
        hass,
        (
            State(
                "climate.test_thermostat",
                HVACMode.OFF,
                {
                    ATTR_TEMPERATURE: "20",
                    ATTR_PRESET_MODE: PRESET_AWAY,
                    ATTR_HVAC_ACTION_REASON: HVACActionReason.TARGET_TEMP_NOT_REACHED,
                },
            ),
        ),
    )

    hass.set_state(CoreState.starting)

    await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test_thermostat",
                "heater": common.ENT_SWITCH,
                "target_sensor": common.ENT_SENSOR,
                "target_temp": 22,
            }
        },
    )
    await hass.async_block_till_done()
    state = hass.states.get("climate.test_thermostat")
    assert state.attributes[ATTR_TEMPERATURE] == 22
    assert state.state == HVACMode.OFF
    assert (
        state.attributes[ATTR_HVAC_ACTION_REASON]
        == HVACActionReason.TARGET_TEMP_NOT_REACHED
    )


async def test_reload(hass: HomeAssistant) -> None:
    """Test we can reload."""

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "heater": "switch.any",
                "target_sensor": "sensor.any",
            }
        },
    )

    await hass.async_block_till_done()
    assert len(hass.states.async_all()) == 1
    assert hass.states.get(common.ENTITY) is not None

    yaml_path = common.get_fixture_path("configuration.yaml", DOMAIN)
    with patch.object(hass_config, "YAML_CONFIG_FILE", yaml_path):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_RELOAD,
            {},
            blocking=True,
        )
        await hass.async_block_till_done()

    assert len(hass.states.async_all()) == 1
    assert hass.states.get("climate.test") is None
    assert hass.states.get("climate.reload")


async def test_custom_setup_params(hass: HomeAssistant) -> None:
    """Test the setup with custom parameters."""
    result = await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "heater": common.ENT_SWITCH,
                "target_sensor": common.ENT_SENSOR,
                "min_temp": common.MIN_TEMP,
                "max_temp": common.MAX_TEMP,
                "target_temp": common.TARGET_TEMP,
                "target_temp_step": 0.5,
            }
        },
    )
    assert result
    await hass.async_block_till_done()
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("min_temp") == common.MIN_TEMP
    assert state.attributes.get("max_temp") == common.MAX_TEMP
    assert state.attributes.get("temperature") == common.TARGET_TEMP
    assert state.attributes.get("target_temp_step") == common.TARGET_TEMP_STEP


###########
# SENSORS #
###########


async def test_sensor_bad_value(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test sensor that have None as state."""
    state = hass.states.get(common.ENTITY)
    temp = state.attributes.get("current_temperature")

    setup_sensor(hass, None)
    await hass.async_block_till_done()
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("current_temperature") == temp

    setup_sensor(hass, "inf")
    await hass.async_block_till_done()
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("current_temperature") == temp

    setup_sensor(hass, "nan")
    await hass.async_block_till_done()
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("current_temperature") == temp


async def test_sensor_unknown(hass: HomeAssistant) -> None:  # noqa: F811
    """Test when target sensor is Unknown."""
    hass.states.async_set("sensor.unknown", STATE_UNKNOWN)
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "unknown",
                "heater": common.ENT_HEATER,
                "target_sensor": "sensor.unknown",
            }
        },
    )
    await hass.async_block_till_done()
    state = hass.states.get("climate.unknown")
    assert state.attributes.get("current_temperature") is None


async def test_sensor_unavailable(hass: HomeAssistant) -> None:  # noqa: F811
    """Test when target sensor is Unknown."""
    hass.states.async_set("sensor.unknown", STATE_UNAVAILABLE)
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "unavailable",
                "heater": common.ENT_HEATER,
                "target_sensor": "sensor.unavailable",
            }
        },
    )
    await hass.async_block_till_done()
    state = hass.states.get("climate.unavailable")
    assert state.attributes.get("current_temperature") is None


async def test_floor_sensor_bad_value(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test sensor that have None as state."""
    state = hass.states.get(common.ENTITY)
    temp = state.attributes.get("current_floor_temperature")

    setup_floor_sensor(hass, None)
    await hass.async_block_till_done()
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("current_floor_temperature") == temp

    setup_floor_sensor(hass, "inf")
    await hass.async_block_till_done()
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("current_floor_temperature") == temp

    setup_floor_sensor(hass, "nan")
    await hass.async_block_till_done()
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("current_floor_temperature") == temp


async def test_floor_sensor_unknown(hass: HomeAssistant) -> None:  # noqa: F811
    """Test when target sensor is Unknown."""
    hass.states.async_set("sensor.unknown", STATE_UNKNOWN)
    hass.states.async_set("sensor.floor_unknown", STATE_UNKNOWN)
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "unknown",
                "heater": common.ENT_HEATER,
                "target_sensor": "sensor.unknown",
                "floor_sensor": "sensor.floor_unknown",
            }
        },
    )
    await hass.async_block_till_done()
    state = hass.states.get("climate.unknown")
    assert state.attributes.get("current_temperature") is None
    assert state.attributes.get("current_floor_temperature") is None


async def test_floor_sensor_unavailable(hass: HomeAssistant) -> None:  # noqa: F811
    """Test when target sensor is Unknown."""
    hass.states.async_set("sensor.unknown", STATE_UNAVAILABLE)
    hass.states.async_set("sensor.floor_unknown", STATE_UNAVAILABLE)
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "unavailable",
                "heater": common.ENT_HEATER,
                "target_sensor": "sensor.unavailable",
                "floor_sensor": "sensor.floor_unknown",
            }
        },
    )
    await hass.async_block_till_done()
    state = hass.states.get("climate.unavailable")
    assert state.attributes.get("current_temperature") is None
    assert state.attributes.get("current_floor_temperature") is None


###################
# CHANGE SETTINGS #
###################


async def test_get_hvac_modes(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test that the operation list returns the correct modes."""
    state = hass.states.get(common.ENTITY)
    modes = state.attributes.get("hvac_modes")
    assert modes == [HVACMode.HEAT, HVACMode.OFF]


async def test_set_target_temp(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test the setting of the target temperature."""
    await common.async_set_temperature(hass, 30)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 30.0
    with pytest.raises(vol.Invalid):
        await common.async_set_temperature(hass, None)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 30.0


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
        (PRESET_BOOST, 24),
        (PRESET_ANTI_FREEZE, 5),
    ],
)
async def test_set_preset_mode(
    hass: HomeAssistant, setup_comp_heat_presets, preset, temp  # noqa: F811
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
        (PRESET_BOOST, 24),
        (PRESET_ANTI_FREEZE, 5),
    ],
)
async def test_set_preset_mode_and_restore_prev_temp(
    hass: HomeAssistant, setup_comp_heat_presets, preset, temp  # noqa: F811
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
        (PRESET_BOOST, 24),
        (PRESET_ACTIVITY, 21),
        (PRESET_ANTI_FREEZE, 5),
    ],
)
async def test_set_preset_modet_twice_and_restore_prev_temp(
    hass: HomeAssistant, setup_comp_heat_presets, preset, temp  # noqa: F811
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
    hass: HomeAssistant, setup_comp_heat_presets  # noqa: F811
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
        (PRESET_BOOST, 24),
        (PRESET_ACTIVITY, 21),
        (PRESET_ANTI_FREEZE, 5),
    ],
)
async def test_set_preset_mode_set_temp_keeps_preset_mode(
    hass: HomeAssistant, setup_comp_heat_presets, preset, temp  # noqa: F811
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


###################
# HVAC OPERATIONS #
###################


@pytest.mark.parametrize(
    ["from_hvac_mode", "to_hvac_mode"],
    [
        [HVACMode.OFF, HVACMode.HEAT],
        [HVACMode.HEAT, HVACMode.OFF],
    ],
)
async def test_toggle(
    hass: HomeAssistant, from_hvac_mode, to_hvac_mode, setup_comp_heat  # noqa: F811
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


async def test_set_target_temp_heater_on(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test if target temperature turn heater on."""
    calls = setup_switch(hass, False)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    await common.async_set_temperature(hass, 30)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_set_target_temp_heater_off(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test if target temperature turn heater off."""
    calls = setup_switch(hass, True)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    await common.async_set_temperature(hass, 25)
    assert len(calls) == 2
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_temp_change_heater_on_within_tolerance(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test if temperature change doesn't turn on within tolerance."""
    calls = setup_switch(hass, False)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 29)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_heater_on_outside_tolerance(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test if temperature change turn heater on outside cold tolerance."""
    calls = setup_switch(hass, False)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 27)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_temp_change_heater_off_within_tolerance(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test if temperature change doesn't turn off within tolerance."""
    calls = setup_switch(hass, True)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 33)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_heater_off_outside_tolerance(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test if temperature change turn heater off outside hot tolerance."""
    calls = setup_switch(hass, True)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 35)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_running_when_hvac_mode_is_off(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
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


async def test_no_state_change_when_hvac_mode_off(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test that the switch doesn't turn on when enabled is False."""
    calls = setup_switch(hass, False)
    await common.async_set_temperature(hass, 30)
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_hvac_mode_heat(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test change mode from OFF to HEAT.

    Switch turns on when temp below setpoint and mode changes.
    """
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    calls = setup_switch(hass, False)
    await common.async_set_hvac_mode(hass, HVACMode.HEAT)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_temp_change_heater_trigger_off_not_long_enough(
    hass: HomeAssistant, setup_comp_heat_cycle  # noqa: F811
) -> None:
    """Test if temp change doesn't turn heater off because of time."""
    calls = setup_switch(hass, True)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_heater_trigger_on_not_long_enough(
    hass: HomeAssistant, setup_comp_heat_cycle  # noqa: F811
) -> None:
    """Test if temp change doesn't turn heater on because of time."""
    calls = setup_switch(hass, False)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_heater_trigger_on_long_enough(
    hass: HomeAssistant, setup_comp_heat_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn heater on after min cycle."""
    fake_changed = datetime.datetime(1970, 11, 11, 11, 11, 11, tzinfo=dt_util.UTC)
    with freeze_time(fake_changed):
        calls = setup_switch(hass, False)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_temp_change_heater_trigger_off_long_enough(
    hass: HomeAssistant, setup_comp_heat_cycle  # noqa: F811
) -> None:
    """Test if temperature change turn heater off after min cycle."""
    fake_changed = datetime.datetime(1970, 11, 11, 11, 11, 11, tzinfo=dt_util.UTC)
    with freeze_time(fake_changed):
        calls = setup_switch(hass, True)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_mode_change_heater_trigger_off_not_long_enough(
    hass: HomeAssistant, setup_comp_heat_cycle  # noqa: F811
) -> None:
    """Test if mode change turns heater off despite minimum cycle."""
    calls = setup_switch(hass, True)
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()
    assert len(calls) == 0
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == "homeassistant"
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_mode_change_heater_trigger_on_not_long_enough(
    hass: HomeAssistant, setup_comp_heat_cycle  # noqa: F811
) -> None:
    """Test if mode change turns heater on despite minimum cycle."""
    calls = setup_switch(hass, False)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    assert len(calls) == 0
    await common.async_set_hvac_mode(hass, HVACMode.HEAT)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == "homeassistant"
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


# async def test_temp_change_ac_trigger_on_long_enough_3(
#     hass: HomeAssistant, setup_comp_heat_ac_cool_cycle_kepp_alive  # noqa: F811
# ) -> None:
#     """Test if turn on signal is sent at keep-alive intervals."""
#     calls = setup_switch(hass, True)
#     await hass.async_block_till_done()
#     setup_sensor(hass, 30)
#     await hass.async_block_till_done()
#     await common.async_set_temperature(hass, 25)
#     test_time = datetime.datetime.now(dt_util.UTC)
#     common.async_fire_time_changed(hass, test_time)
#     await hass.async_block_till_done()
#     assert len(calls) == 0
#     common.async_fire_time_changed(hass, test_time + datetime.timedelta(minutes=5))
#     await hass.async_block_till_done()
#     assert len(calls) == 0
#     common.async_fire_time_changed(hass, test_time + datetime.timedelta(minutes=10))
#     await hass.async_block_till_done()
#     assert len(calls) == 1
#     call = calls[0]
#     assert call.domain == HASS_DOMAIN
#     assert call.service == SERVICE_TURN_ON
#     assert call.data["entity_id"] == common.ENT_SWITCH


# async def test_precision(
#     hass: HomeAssistant, setup_comp_heat_cycle_precision  # noqa: F811
# ) -> None:
#     """Test that setting precision to tenths works as intended."""
#     hass.config.units = US_CUSTOMARY_SYSTEM
#     await common.async_set_temperature(hass, 23.27)
#     state = hass.states.get(common.ENTITY)
#     assert state.attributes.get("temperature") == 23.3
#     # check that target_temp_step defaults to precision
#     assert state.attributes.get("target_temp_step") == 0.1


async def test_initial_hvac_off_force_heater_off(hass: HomeAssistant) -> None:
    """Ensure that restored state is coherent with real situation.

    'initial_hvac_mode: off' will force HVAC status, but we must be sure
    that heater don't keep on.
    """
    # switch is on
    calls = setup_switch(hass, True)
    assert hass.states.get(common.ENT_SWITCH).state == STATE_ON

    setup_sensor(hass, 16)

    await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test_thermostat",
                "heater": common.ENT_SWITCH,
                "target_sensor": common.ENT_SENSOR,
                "target_temp": 20,
                "initial_hvac_mode": HVACMode.OFF,
            }
        },
    )
    await hass.async_block_till_done()
    state = hass.states.get("climate.test_thermostat")
    # 'initial_hvac_mode' will force state but must prevent heather keep working
    assert state.state == HVACMode.OFF
    # heater must be switched off
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_restore_will_turn_off_(hass: HomeAssistant) -> None:
    """Ensure that restored state is coherent with real situation.

    Thermostat status must trigger heater event if temp raises the target .
    """
    heater_switch = "input_boolean.test"
    common.mock_restore_cache(
        hass,
        (
            State(
                "climate.test_thermostat",
                HVACMode.HEAT,
                {ATTR_TEMPERATURE: "18", ATTR_PRESET_MODE: PRESET_NONE},
            ),
            State(heater_switch, STATE_ON, {}),
        ),
    )

    hass.set_state(CoreState.starting)

    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
    )
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON

    setup_sensor(hass, 22)

    await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test_thermostat",
                "heater": heater_switch,
                "target_sensor": common.ENT_SENSOR,
                "target_temp": 20,
            }
        },
    )
    await hass.async_block_till_done()
    state = hass.states.get("climate.test_thermostat")
    assert state.attributes[ATTR_TEMPERATURE] == 20
    assert state.state == HVACMode.HEAT
    assert hass.states.get(heater_switch).state == STATE_ON


async def test_restore_will_turn_off_when_loaded_second(hass: HomeAssistant) -> None:
    """Ensure that restored state is coherent with real situation.

    Switch is not available until after component is loaded
    """
    heater_switch = "input_boolean.test"
    common.mock_restore_cache(
        hass,
        (
            State(
                "climate.test_thermostat",
                HVACMode.HEAT,
                {ATTR_TEMPERATURE: "18", ATTR_PRESET_MODE: PRESET_NONE},
            ),
            State(heater_switch, STATE_ON, {}),
        ),
    )

    hass.set_state(CoreState.starting)

    await hass.async_block_till_done()
    assert hass.states.get(heater_switch) is None

    setup_sensor(hass, 16)

    await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test_thermostat",
                "heater": heater_switch,
                "target_sensor": common.ENT_SENSOR,
                "target_temp": 20,
                "initial_hvac_mode": HVACMode.OFF,
            }
        },
    )
    await hass.async_block_till_done()
    state = hass.states.get("climate.test_thermostat")
    assert state.attributes[ATTR_TEMPERATURE] == 20
    assert state.state == HVACMode.OFF

    calls_on = common.async_mock_service(hass, HASS_DOMAIN, SERVICE_TURN_ON)
    calls_off = common.async_mock_service(hass, HASS_DOMAIN, SERVICE_TURN_OFF)

    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
    )
    await hass.async_block_till_done()
    # heater must be switched off
    assert len(calls_on) == 0
    assert len(calls_off) == 1
    call = calls_off[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == "input_boolean.test"


async def test_restore_state_uncoherence_case(hass: HomeAssistant) -> None:
    """Test restore from a strange state.

    - Turn the generic thermostat off
    - Restart HA and restore state from DB
    """
    _mock_restore_cache(hass, temperature=20)

    calls = setup_switch(hass, False)
    setup_sensor(hass, 15)

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cold_tolerance": 2,
                "hot_tolerance": 4,
                "away_temp": 30,
                "heater": common.ENT_SWITCH,
                "target_sensor": common.ENT_SENSOR,
                "ac_mode": True,
            }
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.attributes[ATTR_TEMPERATURE] == 20
    assert state.state == HVACMode.OFF
    assert len(calls) == 0

    calls = setup_switch(hass, False)
    await hass.async_block_till_done()
    state = hass.states.get(common.ENTITY)
    assert state.state == HVACMode.OFF


async def test_heater_mode_from_off_to_idle(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat switch state if HVAC mode changes."""
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
                "initial_hvac_mode": HVACMode.OFF,
                "target_temp": 25,
            }
        },
    )
    await hass.async_block_till_done()

    setup_sensor(hass, 26)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).attributes["hvac_action"] == HVACAction.OFF

    await common.async_set_hvac_mode(hass, HVACMode.HEAT)

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).attributes["hvac_action"] == HVACAction.IDLE


async def test_cooler_mode_off_switch_change_keeps_off(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat switch state if HVAC mode changes."""
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
                "initial_hvac_mode": HVACMode.OFF,
                "target_temp": 25,
            }
        },
    )
    await hass.async_block_till_done()

    setup_sensor(hass, 26)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).attributes["hvac_action"] == HVACAction.OFF

    hass.states.async_set(heater_switch, STATE_ON)

    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(common.ENTITY).attributes["hvac_action"] == HVACAction.OFF


async def test_heater_mode_aux_heater(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat secondary heater switch in heating mode."""

    secondaty_heater_timeout = 10
    heater_switch = "input_boolean.heater_switch"
    secondary_heater_switch = "input_boolean.secondary_heater_switch"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater_switch": None, "secondary_heater_switch": None}},
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
                "secondary_heater": secondary_heater_switch,
                "secondary_heater_timeout": {"seconds": secondaty_heater_timeout},
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("supported_features") == 385

    setup_sensor(hass, 18)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 23)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(secondary_heater_switch).state == STATE_OFF

    # until secondary heater timeout everything should be the same
    await asyncio.sleep(secondaty_heater_timeout - 4)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(secondary_heater_switch).state == STATE_OFF

    # after secondary heater timeout secondary heater should be on
    await asyncio.sleep(secondaty_heater_timeout + 5)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(secondary_heater_switch).state == STATE_ON

    # triggers reaching target temp should turn off secondary heater
    setup_sensor(hass, 24)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(secondary_heater_switch).state == STATE_OFF

    # if temp is below target temp secondary heater should be on again for the same day
    setup_sensor(hass, 18)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(secondary_heater_switch).state == STATE_ON


async def test_heater_mode_aux_heater_keep_primary_heater_on(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat secondary heater switch in heating mode."""

    secondaty_heater_timeout = 10
    heater_switch = "input_boolean.heater_switch"
    secondary_heater_switch = "input_boolean.secondary_heater_switch"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater_switch": None, "secondary_heater_switch": None}},
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
                "secondary_heater": secondary_heater_switch,
                "secondary_heater_timeout": {"seconds": secondaty_heater_timeout},
                "secondary_heater_dual_mode": True,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("supported_features") == 385

    setup_sensor(hass, 18)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 23)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(secondary_heater_switch).state == STATE_OFF

    # until secondary heater timeout everything should be the same
    await asyncio.sleep(secondaty_heater_timeout - 4)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(secondary_heater_switch).state == STATE_OFF

    # after secondary heater timeout secondary heater should be on
    await asyncio.sleep(secondaty_heater_timeout + 3)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(secondary_heater_switch).state == STATE_ON

    # triggers reaching target temp should turn off secondary heater
    setup_sensor(hass, 24)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(secondary_heater_switch).state == STATE_OFF

    # if temp is below target temp secondary heater should be on again for the same day
    setup_sensor(hass, 18)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(secondary_heater_switch).state == STATE_ON


async def test_heater_mode_tolerance(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat heater switch in heating mode."""
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
                "cold_tolerance": COLD_TOLERANCE,
                "hot_tolerance": HOT_TOLERANCE,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF

    setup_sensor(hass, 18.6)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 19)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF

    setup_sensor(hass, 18.5)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON

    setup_sensor(hass, 19)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON

    setup_sensor(hass, 19.4)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON

    setup_sensor(hass, 19.5)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF


async def test_heater_mode_floor_temp(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat heater switch with floor temp in heating mode."""
    heater_switch = "input_boolean.test"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
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
                "heater": heater_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT,
                "floor_sensor": common.ENT_FLOOR_SENSOR,
                "min_floor_temp": 5,
                "max_floor_temp": 28,
                "cold_tolerance": COLD_TOLERANCE,
                "hot_tolerance": HOT_TOLERANCE,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF

    setup_sensor(hass, 18.6)
    setup_floor_sensor(hass, 10)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF

    setup_sensor(hass, 17)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON

    setup_floor_sensor(hass, 28)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF

    setup_floor_sensor(hass, 26)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON

    setup_sensor(hass, 22)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF

    setup_floor_sensor(hass, 4)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON

    setup_floor_sensor(hass, 3)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON

    setup_floor_sensor(hass, 10)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF


######################
# HVAC ACTION REASON #
######################


async def test_hvac_action_reason_default(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test if action reason is set."""
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_HVAC_ACTION_REASON) == HVACActionReason.NONE


async def test_hvac_action_reason_service(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_HVAC_ACTION_REASON) == HVACActionReason.NONE

    signal_output_call = common.async_mock_signal(
        hass, SET_HVAC_ACTION_REASON_SIGNAL.format(common.ENTITY)
    )

    await common.async_set_hvac_action_reason(
        hass, common.ENTITY, HVACActionReason.SCHEDULE
    )
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert len(signal_output_call) == 1
    assert (
        state.attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReasonExternal.SCHEDULE
    )


async def test_heater_mode_floor_temp_hvac_action_reason(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat heater switch with floor temp in heating mode."""
    heater_switch = "input_boolean.test"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
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
                "heater": heater_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT,
                "floor_sensor": common.ENT_FLOOR_SENSOR,
                "min_floor_temp": 5,
                "max_floor_temp": 28,
                "cold_tolerance": COLD_TOLERANCE,
                "hot_tolerance": HOT_TOLERANCE,
            }
        },
    )
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.NONE
    )

    setup_sensor(hass, 18.6)
    setup_floor_sensor(hass, 10)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.NONE
    )

    setup_sensor(hass, 17)
    await hass.async_block_till_done()
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_TEMP_NOT_REACHED
    )

    setup_floor_sensor(hass, 28)
    await hass.async_block_till_done()
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.OVERHEAT
    )

    setup_floor_sensor(hass, 26)
    await hass.async_block_till_done()
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_TEMP_NOT_REACHED
    )

    setup_sensor(hass, 22)
    await hass.async_block_till_done()
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_TEMP_REACHED
    )

    setup_floor_sensor(hass, 4)
    await hass.async_block_till_done()
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.LIMIT
    )

    setup_floor_sensor(hass, 3)
    await hass.async_block_till_done()
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.LIMIT
    )

    setup_floor_sensor(hass, 10)
    await hass.async_block_till_done()
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_TEMP_REACHED
    )


async def test_heater_mode_opening_hvac_action_reason(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode."""
    heater_switch = "input_boolean.test"
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
                "heater": heater_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT,
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

    setup_sensor(hass, 18)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 23)
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


@pytest.mark.parametrize(
    ["duration", "result_state"],
    [
        (timedelta(seconds=10), STATE_ON),
        (timedelta(seconds=30), STATE_OFF),
    ],
)
async def test_heater_mode_cycle(
    hass: HomeAssistant, duration, result_state, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat heater switch in heating mode with min_cycle_duration."""
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
                "min_cycle_duration": timedelta(seconds=15),
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF

    setup_sensor(hass, 18)
    await hass.async_block_till_done()

    fake_changed = dt.utcnow() - duration
    with freeze_time(fake_changed):
        await common.async_set_temperature(hass, 23)
        await hass.async_block_till_done()
        assert hass.states.get(heater_switch).state == STATE_ON

    setup_sensor(hass, 24)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == result_state


async def test_heater_mode_opening(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode."""
    heater_switch = "input_boolean.test"
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
                "heater": heater_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT,
                "openings": [
                    opening_1,
                    {"entity_id": opening_2, "timeout": {"seconds": 10}},
                ],
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF

    setup_sensor(hass, 18)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 23)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON

    setup_boolean(hass, opening_1, "open")
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF

    setup_boolean(hass, opening_1, "closed")
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON

    setup_boolean(hass, opening_2, "open")
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON

    # wait 10 seconds, actually 133 due to the other tests run time seems to affect this
    # needs to separate the tests
    await asyncio.sleep(13)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF

    setup_boolean(hass, opening_2, "closed")
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON


def _mock_restore_cache(hass, temperature=20, hvac_mode=HVACMode.OFF):
    common.mock_restore_cache(
        hass,
        (
            State(
                common.ENTITY,
                hvac_mode,
                {ATTR_TEMPERATURE: str(temperature), ATTR_PRESET_MODE: PRESET_AWAY},
            ),
        ),
    )
