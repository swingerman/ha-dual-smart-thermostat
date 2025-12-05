"""The tests for the dual_smart_thermostat."""

import datetime
from datetime import timedelta
import logging
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
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
    SERVICE_CLOSE_VALVE,
    SERVICE_OPEN_VALVE,
    SERVICE_RELOAD,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_CLOSED,
    STATE_OFF,
    STATE_ON,
    STATE_OPEN,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import DOMAIN as HASS_DOMAIN, CoreState, HomeAssistant, State
from homeassistant.exceptions import ServiceValidationError
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
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
from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason_internal import (
    HVACActionReasonInternal,
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
    setup_comp_heat_safety_delay,
    setup_comp_heat_valve,
    setup_floor_sensor,
    setup_sensor,
    setup_switch,
    setup_valve,
)

COLD_TOLERANCE = 0.5
HOT_TOLERANCE = 0.5

_LOGGER = logging.getLogger(__name__)

###################
# COMMON FEATURES #
###################


async def test_default_setup_params(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test the setup with default parameters."""
    # GIVEN - Component is set up with default configuration (via fixture)

    # WHEN - Entity state is retrieved
    state = hass.states.get(common.ENTITY)

    # THEN - Default parameters are correctly set
    assert state.attributes.get("min_temp") == 7
    assert state.attributes.get("max_temp") == 35
    assert state.attributes.get("temperature") == 7
    assert state.attributes.get("target_temp_step") == 0.1


@pytest.mark.parametrize(
    "hvac_mode",
    [HVACMode.OFF, HVACMode.HEAT],
)
async def test_restore_state(hass: HomeAssistant, hvac_mode) -> None:
    """Ensure states are restored on startup."""
    # GIVEN - Previous state cached with temperature 20 and away preset
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

    # WHEN - Component is set up on startup
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

    # THEN - Previous state is restored
    state = hass.states.get("climate.test_thermostat")
    assert state.attributes[ATTR_TEMPERATURE] == 20
    assert state.attributes[ATTR_PRESET_MODE] == PRESET_AWAY
    assert state.state == hvac_mode


async def test_no_restore_state(hass: HomeAssistant) -> None:
    """Ensure states are restored on startup if they exist.

    Allows for graceful reboot.
    """
    # GIVEN - Previous state cached with old temperature and preset
    common.mock_restore_cache(
        hass,
        (
            State(
                "climate.test_thermostat",
                HVACMode.OFF,
                {
                    ATTR_TEMPERATURE: "20",
                    ATTR_PRESET_MODE: PRESET_AWAY,
                },
            ),
        ),
    )
    hass.set_state(CoreState.starting)

    # WHEN - Component is set up with explicit target_temp
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

    # THEN - Configuration target_temp overrides cached state
    state = hass.states.get("climate.test_thermostat")
    assert state.attributes[ATTR_TEMPERATURE] == 22
    assert state.state == HVACMode.OFF


async def test_reload(hass: HomeAssistant) -> None:
    """Test we can reload."""
    # GIVEN - Component is set up with initial configuration
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

    # WHEN - Reload service is called with new configuration
    yaml_path = common.get_fixture_path("configuration.yaml", DOMAIN)
    with patch.object(hass_config, "YAML_CONFIG_FILE", yaml_path):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_RELOAD,
            {},
            blocking=True,
        )
        await hass.async_block_till_done()

    # THEN - Old entity is removed and new entity from YAML is loaded
    assert len(hass.states.async_all()) == 1
    assert hass.states.get("climate.test") is None
    assert hass.states.get("climate.reload")


async def test_custom_setup_params(hass: HomeAssistant) -> None:
    """Test the setup with custom parameters."""
    # GIVEN - Component configured with custom parameters
    # WHEN - Component is set up
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

    # THEN - Custom parameters are correctly set
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
    # GIVEN - Component set up with valid sensor reading
    state = hass.states.get(common.ENTITY)
    temp = state.attributes.get("current_temperature")

    # WHEN - Sensor reports None
    setup_sensor(hass, None)
    await hass.async_block_till_done()
    # THEN - Temperature remains unchanged
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("current_temperature") == temp

    # WHEN - Sensor reports invalid 'inf' value
    setup_sensor(hass, "inf")
    await hass.async_block_till_done()
    # THEN - Temperature remains unchanged
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("current_temperature") == temp

    # WHEN - Sensor reports invalid 'nan' value
    setup_sensor(hass, "nan")
    await hass.async_block_till_done()
    # THEN - Temperature remains unchanged
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("current_temperature") == temp


async def test_sensor_unknown(hass: HomeAssistant) -> None:  # noqa: F811
    """Test when target sensor is Unknown."""
    # GIVEN - Sensor in unknown state
    hass.states.async_set("sensor.unknown", STATE_UNKNOWN)

    # WHEN - Component is set up with unknown sensor
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

    # THEN - Current temperature is None
    state = hass.states.get("climate.unknown")
    assert state.attributes.get("current_temperature") is None


async def test_sensor_unavailable(hass: HomeAssistant) -> None:  # noqa: F811
    """Test when target sensor is unavailable."""
    # GIVEN - Sensor in unavailable state
    hass.states.async_set("sensor.unknown", STATE_UNAVAILABLE)

    # WHEN - Component is set up with unavailable sensor
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

    # THEN - Current temperature is None
    state = hass.states.get("climate.unavailable")
    assert state.attributes.get("current_temperature") is None


async def test_floor_sensor_bad_value(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test floor sensor that have None as state."""
    # GIVEN - Component set up with valid floor sensor reading
    state = hass.states.get(common.ENTITY)
    temp = state.attributes.get("current_floor_temperature")

    # WHEN - Floor sensor reports None
    setup_floor_sensor(hass, None)
    await hass.async_block_till_done()
    # THEN - Floor temperature remains unchanged
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("current_floor_temperature") == temp

    # WHEN - Floor sensor reports invalid 'inf' value
    setup_floor_sensor(hass, "inf")
    await hass.async_block_till_done()
    # THEN - Floor temperature remains unchanged
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("current_floor_temperature") == temp

    # WHEN - Floor sensor reports invalid 'nan' value
    setup_floor_sensor(hass, "nan")
    await hass.async_block_till_done()
    # THEN - Floor temperature remains unchanged
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("current_floor_temperature") == temp


async def test_floor_sensor_unknown(hass: HomeAssistant) -> None:  # noqa: F811
    """Test when floor sensor is Unknown."""
    # GIVEN - Both sensors in unknown state
    hass.states.async_set("sensor.unknown", STATE_UNKNOWN)
    hass.states.async_set("sensor.floor_unknown", STATE_UNKNOWN)

    # WHEN - Component is set up with unknown sensors
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

    # THEN - Both temperatures are None
    state = hass.states.get("climate.unknown")
    assert state.attributes.get("current_temperature") is None
    assert state.attributes.get("current_floor_temperature") is None


async def test_floor_sensor_unavailable(hass: HomeAssistant) -> None:  # noqa: F811
    """Test when floor sensor is unavailable."""
    # GIVEN - Both sensors in unavailable state
    hass.states.async_set("sensor.unknown", STATE_UNAVAILABLE)
    hass.states.async_set("sensor.floor_unknown", STATE_UNAVAILABLE)

    # WHEN - Component is set up with unavailable sensors
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

    # THEN - Both temperatures are None
    state = hass.states.get("climate.unavailable")
    assert state.attributes.get("current_temperature") is None
    assert state.attributes.get("current_floor_temperature") is None


async def test_heater_unknown_to_available(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:  # noqa: F811
    """Test when heater turns on after been Unknown and then becomes available."""
    heater_switch = "input_boolean.test"
    # hass.states.async_set(heater_switch, STATE_UNKNOWN)

    # Given
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
                "heater": heater_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT,
            }
        },
    )
    await hass.async_block_till_done()

    # When
    setup_sensor(hass, 19)
    await hass.async_block_till_done()
    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()

    # Then
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert (
        hass.states.get(common.ENTITY).attributes.get("hvac_action") == HVACAction.IDLE
    )

    # When
    # heater is in unknown state and target temperature is set
    hass.states.async_set(heater_switch, STATE_UNKNOWN)
    await hass.async_block_till_done()
    await common.async_set_temperature(hass, 21)
    await hass.async_block_till_done()

    # Then
    assert hass.states.get(heater_switch).state == STATE_UNKNOWN
    assert (
        hass.states.get(common.ENTITY).attributes.get("hvac_action") == HVACAction.IDLE
    )

    # When
    # heater becomes available again
    calls = setup_switch(hass, False, heater_switch)
    await hass.async_block_till_done()

    # await asyncio.sleep(1)
    freezer.tick(timedelta(seconds=1))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # Then
    assert len(calls) == 1
    assert calls[0].data.get("entity_id") == heater_switch


###################
# CHANGE SETTINGS #
###################


async def test_get_hvac_modes(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test that the operation list returns the correct modes."""
    # GIVEN - Component set up in heat mode (via fixture)

    # WHEN - Entity state is retrieved
    state = hass.states.get(common.ENTITY)
    modes = state.attributes.get("hvac_modes")

    # THEN - Available modes include HEAT and OFF
    assert modes == [HVACMode.HEAT, HVACMode.OFF]


async def test_set_target_temp(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test the setting of the target temperature."""
    # GIVEN - Component set up in heat mode (via fixture)

    # WHEN - Target temperature is set to 30
    await common.async_set_temperature(hass, 30)

    # THEN - Temperature is updated correctly
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 30.0

    # WHEN - Attempting to set None as temperature
    with pytest.raises(vol.Invalid):
        await common.async_set_temperature(hass, None)

    # THEN - Temperature remains unchanged
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 30.0


async def test_set_target_temp_and_hvac_mode(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test the setting of the target temperature and HVAC mode together."""

    # Given
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await hass.async_block_till_done()
    state = hass.states.get(common.ENTITY)
    assert state.state == HVACMode.OFF

    # When
    await common.async_set_temperature(hass, temperature=30, hvac_mode=HVACMode.HEAT)
    await hass.async_block_till_done()

    # Then
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 30.0
    assert state.state == HVACMode.HEAT


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
    # GIVEN - Component set up with preset modes and target temperature of 23
    await common.async_set_temperature(hass, 23)

    # WHEN - Preset mode is set
    await common.async_set_preset_mode(hass, preset)

    # THEN - Temperature changes to preset temperature
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
    # GIVEN - Component set up with preset modes and target temperature of 23
    await common.async_set_temperature(hass, 23)

    # WHEN - Preset mode is set
    await common.async_set_preset_mode(hass, preset)

    # THEN - Temperature changes to preset temperature
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == temp

    # WHEN - Preset mode is set back to NONE
    await common.async_set_preset_mode(hass, PRESET_NONE)

    # THEN - Original temperature is restored
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
async def test_set_preset_mode_twice_and_restore_prev_temp(
    hass: HomeAssistant, setup_comp_heat_presets, preset, temp  # noqa: F811
) -> None:
    """Test the setting preset mode twice in a row.

    Verify original temperature is restored.
    """
    # GIVEN - Component set up with preset modes and target temperature of 23
    await common.async_set_temperature(hass, 23)

    # WHEN - Preset mode is set twice in a row
    await common.async_set_preset_mode(hass, preset)
    await common.async_set_preset_mode(hass, preset)

    # THEN - Temperature is set to preset temperature
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == temp

    # WHEN - Preset mode is set back to NONE
    await common.async_set_preset_mode(hass, PRESET_NONE)

    # THEN - Original temperature is restored
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 23


async def test_set_preset_mode_invalid(
    hass: HomeAssistant, setup_comp_heat_presets  # noqa: F811
) -> None:
    """Test an invalid mode raises an error and ignore case when checking modes."""
    # GIVEN - Component set up with preset modes and target temperature of 23
    await common.async_set_temperature(hass, 23)

    # WHEN - Lowercase preset mode is set
    await common.async_set_preset_mode(hass, "away")

    # THEN - Preset mode is accepted
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == "away"

    # WHEN - Lowercase "none" preset mode is set
    await common.async_set_preset_mode(hass, "none")

    # THEN - Preset mode is accepted
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == "none"

    # WHEN - Invalid capitalized preset mode is set
    with pytest.raises(ServiceValidationError):
        await common.async_set_preset_mode(hass, "Sleep")

    # THEN - Preset mode remains unchanged
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
    # GIVEN - Component set up with preset modes and target temperature of 23
    target_temp = 32
    await common.async_set_temperature(hass, 23)

    # WHEN - Preset mode is set
    await common.async_set_preset_mode(hass, preset)

    # THEN - Temperature changes to preset temperature
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == temp

    # WHEN - Target temperature is manually set while in preset mode
    await common.async_set_temperature(hass, target_temp)
    assert state.attributes.get("supported_features") == 401

    # THEN - Temperature is updated but preset mode is preserved
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == target_temp
    assert state.attributes.get("preset_mode") == preset
    assert state.attributes.get("supported_features") == 401

    # WHEN - Preset mode is set back to NONE
    await common.async_set_preset_mode(hass, PRESET_NONE)

    # THEN - Appropriate temperature is restored based on preset type
    state = hass.states.get(common.ENTITY)
    if preset == PRESET_NONE:
        assert state.attributes.get("temperature") == target_temp
    else:
        assert state.attributes.get("temperature") == 23


@pytest.mark.parametrize(
    ("preset", "temp"),
    [
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
async def test_set_same_preset_mode_restores_preset_temp_from_modified(
    hass: HomeAssistant, setup_comp_heat_presets, preset, temp  # noqa: F811
) -> None:
    """Test the setting preset mode again after modifying temperature.

    Verify preset mode called twice restores preset temperatures.
    """
    # GIVEN - Component set up with preset modes and target temperature of 23
    target_temp = 32
    await common.async_set_temperature(hass, 23)

    # WHEN - Preset mode is set
    await common.async_set_preset_mode(hass, preset)

    # THEN - Temperature changes to preset temperature
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == temp

    # WHEN - Target temperature is manually modified
    await common.async_set_temperature(hass, target_temp)

    # THEN - Temperature is updated while preset mode is maintained
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == target_temp
    assert state.attributes.get("preset_mode") == preset

    # WHEN - Same preset mode is set again
    await common.async_set_preset_mode(hass, preset)

    # THEN - Original preset temperature is restored
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == temp

    # WHEN - Preset mode is set back to NONE
    await common.async_set_preset_mode(hass, PRESET_NONE)

    # THEN - Original non-preset temperature is restored
    state = hass.states.get(common.ENTITY)
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
    """Test change mode from OFF to HEAT.

    Switch turns on when temp below setpoint and mode changes.
    """
    # GIVEN - Component set up with initial HVAC mode
    await common.async_set_hvac_mode(hass, from_hvac_mode)

    # WHEN - Toggle is called
    await common.async_toggle(hass)
    await hass.async_block_till_done()

    # THEN - HVAC mode changes to opposite mode
    state = hass.states.get(common.ENTITY)
    assert state.state == to_hvac_mode

    # WHEN - Toggle is called again
    await common.async_toggle(hass)
    await hass.async_block_till_done()

    # THEN - HVAC mode returns to original mode
    state = hass.states.get(common.ENTITY)
    assert state.state == from_hvac_mode


async def test_sensor_change_dont_control_heater_when_off(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test if temperature change doesn't turn heater on when off."""
    # GIVEN - HVAC mode is OFF with high target temperature and sensor at 25
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await common.async_set_temperature(hass, 30)
    await hass.async_block_till_done()
    calls = setup_switch(hass, True)

    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    assert len(calls) == 0

    # WHEN - Temperature drops below target
    setup_sensor(hass, 24)
    await hass.async_block_till_done()

    # THEN - Heater remains off because HVAC mode is OFF
    assert len(calls) == 0


async def test_set_target_temp_heater_on(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test if target temperature turn heater on."""
    # GIVEN - Heater is off and current temperature is 25
    calls = setup_switch(hass, False)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()

    # WHEN - Target temperature is set above current temperature
    await common.async_set_temperature(hass, 30)

    # THEN - Heater turns on
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_set_target_temp_heater_off(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test if target temperature turn heater off."""
    # GIVEN - Heater is on and current temperature is 30
    calls = setup_switch(hass, True)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()

    # WHEN - Target temperature is set below current temperature
    await common.async_set_temperature(hass, 25)

    # THEN - Heater turns off
    assert len(calls) == 2
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_set_target_temp_heater_valve_open(
    hass: HomeAssistant, setup_comp_heat_valve  # noqa: F811
) -> None:
    """Test if target temperature turn heater on."""
    # GIVEN - Valve is closed and current temperature is 25
    calls = setup_valve(hass, False)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()

    # WHEN - Target temperature is set above current temperature
    await common.async_set_temperature(hass, 30)

    # THEN - Valve opens
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_OPEN_VALVE
    assert call.data["entity_id"] == common.ENT_VALVE


async def test_set_target_temp_heater_valve_close(
    hass: HomeAssistant, setup_comp_heat_valve  # noqa: F811
) -> None:
    """Test if target temperature turn heater off."""
    # GIVEN - Valve is open and current temperature is 30
    calls = setup_valve(hass, True)
    setup_sensor(hass, 30)
    await hass.async_block_till_done()

    # WHEN - Target temperature is set below current temperature
    await common.async_set_temperature(hass, 25)

    # THEN - Valve closes
    assert len(calls) == 2
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_CLOSE_VALVE
    assert call.data["entity_id"] == common.ENT_VALVE


async def test_temp_change_heater_on_within_tolerance(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test if temperature change doesn't turn on within tolerance."""
    # GIVEN - Heater is off with target temperature of 30
    calls = setup_switch(hass, False)
    await common.async_set_temperature(hass, 30)

    # WHEN - Temperature is within cold tolerance (29 vs 30)
    setup_sensor(hass, 29)
    await hass.async_block_till_done()

    # THEN - Heater remains off
    assert len(calls) == 0


async def test_temp_change_heater_on_outside_tolerance(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test if temperature change turn heater on outside cold tolerance."""
    # GIVEN - Heater is off with target temperature of 30
    calls = setup_switch(hass, False)
    await common.async_set_temperature(hass, 30)

    # WHEN - Temperature drops outside cold tolerance (27 vs 30)
    setup_sensor(hass, 27)
    await hass.async_block_till_done()

    # THEN - Heater turns on
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_temp_change_heater_off_within_tolerance(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test if temperature change doesn't turn off within tolerance."""
    # GIVEN - Heater is on with target temperature of 30
    calls = setup_switch(hass, True)
    await common.async_set_temperature(hass, 30)

    # WHEN - Temperature is within hot tolerance (33 vs 30)
    setup_sensor(hass, 33)
    await hass.async_block_till_done()

    # THEN - Heater remains on
    assert len(calls) == 0


async def test_temp_change_heater_off_outside_tolerance(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test if temperature change turn heater off outside hot tolerance."""
    # GIVEN - Heater is on with target temperature of 30
    calls = setup_switch(hass, True)
    await common.async_set_temperature(hass, 30)

    # WHEN - Temperature rises outside hot tolerance (35 vs 30)
    setup_sensor(hass, 35)
    await hass.async_block_till_done()

    # THEN - Heater turns off
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


@pytest.mark.parametrize(
    "sensor_state",
    [18, STATE_UNAVAILABLE, STATE_UNKNOWN],
)
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_sensor_unknown_secure_heater_off_outside_stale_duration(
    hass: HomeAssistant, sensor_state, setup_comp_heat_safety_delay  # noqa: F811
) -> None:
    """Test if sensor unavailable for defined delay turns off heater."""
    # GIVEN - Heater is on with sensor reading 18 and target temperature 30
    setup_sensor(hass, 18)
    await common.async_set_temperature(hass, 30)
    calls = setup_switch(hass, True)

    # WHEN - Sensor enters the desired state (unavailable/unknown/stale)
    hass.states.async_set(common.ENT_SENSOR, sensor_state)
    await hass.async_block_till_done()

    # WHEN - Wait 3 minutes for safety delay
    common.async_fire_time_changed(
        hass, dt_util.utcnow() + datetime.timedelta(minutes=3)
    )
    await hass.async_block_till_done()

    # THEN - Heater turns off for safety
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH

    # WHEN - Sensor is restored with valid reading
    calls = setup_switch(hass, False)
    setup_sensor(hass, 19)
    await hass.async_block_till_done()

    # THEN - Heater turns back on
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


@pytest.mark.parametrize(
    "sensor_state",
    [18, STATE_UNAVAILABLE, STATE_UNKNOWN],
)
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_sensor_unknown_secure_heater_off_outside_stale_duration_reason(
    hass: HomeAssistant, sensor_state, setup_comp_heat_safety_delay  # noqa: F811
) -> None:
    """Test if sensor unavailable for defined delay turns off heater."""
    # GIVEN - Heater is on with sensor reading 28 and target temperature 30
    setup_sensor(hass, 28)
    await common.async_set_temperature(hass, 30)
    calls = setup_switch(hass, True)  # noqa: F841
    await hass.async_block_till_done()

    # WHEN - Sensor enters the desired state (unavailable/unknown/stale)
    hass.states.async_set(common.ENT_SENSOR, sensor_state)
    await hass.async_block_till_done()

    # WHEN - Wait 3 minutes for safety delay
    common.async_fire_time_changed(
        hass, dt_util.utcnow() + datetime.timedelta(minutes=3)
    )
    await hass.async_block_till_done()

    # THEN - HVAC action reason indicates sensor stalled
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReasonInternal.TEMPERATURE_SENSOR_STALLED
    )


@pytest.mark.parametrize(
    "sensor_state",
    [18, STATE_UNAVAILABLE, STATE_UNKNOWN],
)
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_sensor_restores_after_state_changes(
    hass: HomeAssistant, sensor_state, setup_comp_heat_safety_delay  # noqa: F811
) -> None:
    """Test if sensor unavailable for defined delay turns off heater."""
    # GIVEN - Heater is on with sensor reading 28 and target temperature 30
    setup_sensor(hass, 28)
    await common.async_set_temperature(hass, 30)
    calls = setup_switch(hass, True)  # noqa: F841
    await hass.async_block_till_done()

    # WHEN - Sensor enters the desired state (unavailable/unknown/stale)
    hass.states.async_set(common.ENT_SENSOR, sensor_state)
    await hass.async_block_till_done()

    # WHEN - Wait 3 minutes for safety delay
    common.async_fire_time_changed(
        hass, dt_util.utcnow() + datetime.timedelta(minutes=3)
    )
    await hass.async_block_till_done()

    # THEN - HVAC action reason indicates sensor stalled
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReasonInternal.TEMPERATURE_SENSOR_STALLED
    )

    # WHEN - Sensor state changes to valid reading
    hass.states.async_set(common.ENT_SENSOR, 31)
    await hass.async_block_till_done()

    # THEN - HVAC action reason is cleared
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.NONE
    )


async def test_running_when_hvac_mode_is_off(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test that the switch turns off when enabled is set False."""
    # GIVEN - Heater is on with target temperature set
    calls = setup_switch(hass, True)
    await common.async_set_temperature(hass, 30)

    # WHEN - HVAC mode is set to OFF
    await common.async_set_hvac_mode(hass, HVACMode.OFF)

    # THEN - Heater turns off
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_no_state_change_when_hvac_mode_off(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test that the switch doesn't turn on when enabled is False."""
    # GIVEN - Heater is off with HVAC mode OFF and target temperature 30
    calls = setup_switch(hass, False)
    await common.async_set_temperature(hass, 30)
    await common.async_set_hvac_mode(hass, HVACMode.OFF)

    # WHEN - Temperature drops below target
    setup_sensor(hass, 25)
    await hass.async_block_till_done()

    # THEN - Heater remains off because HVAC mode is OFF
    assert len(calls) == 0


async def test_hvac_mode_heat(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test change mode from OFF to HEAT.

    Switch turns on when temp below setpoint and mode changes.
    """
    # GIVEN - HVAC mode is OFF with temperature below target (25 vs 30)
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await common.async_set_temperature(hass, 30)
    setup_sensor(hass, 25)
    await hass.async_block_till_done()
    calls = setup_switch(hass, False)

    # WHEN - HVAC mode is changed to HEAT
    await common.async_set_hvac_mode(hass, HVACMode.HEAT)

    # THEN - Heater turns on
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


##
@pytest.mark.parametrize("sw_on", [True, False])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_temp_change_heater_trigger_long_enough_xx(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    sw_on,
    setup_comp_heat_cycle,  # noqa: F811
) -> None:
    """Test if temperature change turn heater on or off."""
    # GIVEN - Heater with cycle time, target temp 18, switch state sw_on
    calls = setup_switch(hass, sw_on)
    await common.async_set_temperature(hass, 18)
    setup_sensor(hass, 16 if sw_on else 22)
    await hass.async_block_till_done()

    # WHEN - Time passes and temperature changes to trigger point
    freezer.tick(timedelta(minutes=6))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    setup_sensor(hass, 22 if sw_on else 16)
    await hass.async_block_till_done()

    # THEN - No call yet, not enough time elapsed for cycle
    assert len(calls) == 0

    # WHEN - Temperature moves back and cycle time elapses
    setup_sensor(hass, 16 if sw_on else 22)
    await hass.async_block_till_done()

    freezer.tick(timedelta(minutes=6))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # THEN - Still no call, switch not needed
    assert len(calls) == 0

    # WHEN - Temperature changes to trigger point again
    setup_sensor(hass, 22 if sw_on else 16)
    await hass.async_block_till_done()

    # THEN - Call triggered, cycle time elapsed and temperature reached
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF if sw_on else SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


@pytest.mark.parametrize("sw_on", [True, False])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_time_change_heater_trigger_long_enough(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    sw_on,
    setup_comp_heat_cycle,  # noqa: F811
) -> None:
    """Test if temperature change turn heater on or off when cycle time is past."""
    # GIVEN - Heater with cycle time, target temp 18, switch state sw_on
    calls = setup_switch(hass, sw_on)
    await common.async_set_temperature(hass, 18)
    setup_sensor(hass, 16 if sw_on else 22)
    await hass.async_block_till_done()

    # WHEN - Time passes and temperature changes to trigger point
    freezer.tick(timedelta(minutes=6))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    setup_sensor(hass, 22 if sw_on else 16)
    await hass.async_block_till_done()

    # THEN - No call yet, not enough time elapsed
    assert len(calls) == 0

    # WHEN - Cycle time completes
    freezer.tick(timedelta(minutes=5))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # THEN - Call triggered, cycle time is sufficient
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF if sw_on else SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


@pytest.mark.parametrize("sw_on", [True, False])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_mode_change_heater_trigger_not_long_enough(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    sw_on,
    setup_comp_heat_cycle,  # noqa: F811
) -> None:
    """Test if mode change turns heater off or on despite minimum cycle."""
    # GIVEN - Heater with cycle time, target temp 18, switch state sw_on
    calls = setup_switch(hass, sw_on)
    await common.async_set_temperature(hass, 18)
    setup_sensor(hass, 16 if sw_on else 22)
    await hass.async_block_till_done()

    # WHEN - Time passes and temperature changes to trigger point
    freezer.tick(timedelta(minutes=6))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    setup_sensor(hass, 22 if sw_on else 16)
    await hass.async_block_till_done()

    # THEN - No call yet, not enough time elapsed
    assert len(calls) == 0

    # WHEN - HVAC mode is changed (bypasses cycle time constraint)
    await common.async_set_hvac_mode(hass, HVACMode.OFF if sw_on else HVACMode.HEAT)

    # THEN - Call triggered immediately despite cycle time
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF if sw_on else SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


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
    # GIVEN - Switch is on and sensor reads 16 (below target)
    calls = setup_switch(hass, True)
    assert hass.states.get(common.ENT_SWITCH).state == STATE_ON
    setup_sensor(hass, 16)

    # WHEN - Component is set up with initial_hvac_mode OFF
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

    # THEN - HVAC mode is OFF and heater is turned off despite low temperature
    state = hass.states.get("climate.test_thermostat")
    assert state.state == HVACMode.OFF
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_restore_will_turn_off_(hass: HomeAssistant) -> None:
    """Ensure that restored state is coherent with real situation.

    Thermostat status must trigger heater event if temp raises the target .
    """
    # GIVEN - Previous state with HEAT mode, target temp 18, and switch on
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

    # WHEN - Component is set up with current temperature 22 (above target)
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

    # THEN - State is restored but heater remains on (legacy behavior)
    state = hass.states.get("climate.test_thermostat")
    assert state.attributes[ATTR_TEMPERATURE] == 20
    assert state.state == HVACMode.HEAT
    assert hass.states.get(heater_switch).state == STATE_ON


# async def test_restore_will_turn_off_when_loaded_second(hass: HomeAssistant) -> None:
#     """Ensure that restored state is coherent with real situation.

#     Switch is not available until after component is loaded
#     """
#     heater_switch = "input_boolean.test"
#     common.mock_restore_cache(
#         hass,
#         (
#             State(
#                 "climate.test_thermostat",
#                 HVACMode.HEAT,
#                 {ATTR_TEMPERATURE: "18", ATTR_PRESET_MODE: PRESET_NONE},
#             ),
#             State(heater_switch, STATE_ON, {}),
#         ),
#     )

#     hass.set_state(CoreState.starting)

#     await hass.async_block_till_done()
#     assert hass.states.get(heater_switch) is None

#     setup_sensor(hass, 16)

#     await async_setup_component(
#         hass,
#         CLIMATE,
#         {
#             "climate": {
#                 "platform": DOMAIN,
#                 "name": "test_thermostat",
#                 "heater": heater_switch,
#                 "target_sensor": common.ENT_SENSOR,
#                 "target_temp": 20,
#                 "initial_hvac_mode": HVACMode.OFF,
#             }
#         },
#     )
#     await hass.async_block_till_done()
#     state = hass.states.get("climate.test_thermostat")
#     assert state.attributes[ATTR_TEMPERATURE] == 20
#     assert state.state == HVACMode.OFF

#     calls_on = common.async_mock_service(hass, HASS_DOMAIN, SERVICE_TURN_ON)
#     calls_off = common.async_mock_service(hass, HASS_DOMAIN, SERVICE_TURN_OFF)

#     assert await async_setup_component(
#         hass, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
#     )
#     await hass.async_block_till_done()
#     # heater must be switched off
#     assert len(calls_on) == 0
#     assert len(calls_off) == 1
#     call = calls_off[0]
#     assert call.domain == HASS_DOMAIN
#     assert call.service == SERVICE_TURN_OFF
#     assert call.data["entity_id"] == "input_boolean.test"


async def test_restore_state_inconsistency_case(hass: HomeAssistant) -> None:
    """Test restore from a strange state.

    - Turn the generic thermostat off
    - Restart HA and restore state from DB
    """
    # GIVEN - Previous state cached with temperature 20
    _mock_restore_cache(hass, temperature=20)
    calls = setup_switch(hass, False)
    setup_sensor(hass, 15)

    # WHEN - Component is set up with ac_mode configuration
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

    # THEN - Temperature restored but HVAC mode is OFF with no switch calls
    state = hass.states.get(common.ENTITY)
    assert state.attributes[ATTR_TEMPERATURE] == 20
    assert state.state == HVACMode.OFF
    assert len(calls) == 0

    # WHEN - Switch state refreshed
    calls = setup_switch(hass, False)
    await hass.async_block_till_done()

    # THEN - HVAC mode remains OFF
    state = hass.states.get(common.ENTITY)
    assert state.state == HVACMode.OFF


async def test_heater_mode_from_off_to_idle(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat switch state if HVAC mode changes."""
    # GIVEN - Component set up in OFF mode with temperature above target (26 vs 25)
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

    # THEN - Heater is off and HVAC action is OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).attributes["hvac_action"] == HVACAction.OFF

    # WHEN - HVAC mode is changed to HEAT
    await common.async_set_hvac_mode(hass, HVACMode.HEAT)

    # THEN - Heater remains off but HVAC action changes to IDLE (temperature above target)
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
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat secondary heater switch in heating mode."""

    secondary_heater_timeout = 10
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
                "secondary_heater_timeout": {"seconds": secondary_heater_timeout},
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
    # await asyncio.sleep(secondary_heater_timeout - 4)
    freezer.tick(timedelta(seconds=secondary_heater_timeout - 4))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(secondary_heater_switch).state == STATE_OFF

    # after secondary heater timeout secondary heater should be on
    # await asyncio.sleep(secondary_heater_timeout + 5)
    freezer.tick(timedelta(seconds=secondary_heater_timeout + 5))
    common.async_fire_time_changed(hass)
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
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat secondary heater switch in heating mode."""

    secondary_heater_timeout = 10
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
                "secondary_heater_timeout": {"seconds": secondary_heater_timeout},
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
    # await asyncio.sleep(secondary_heater_timeout - 4)
    freezer.tick(timedelta(seconds=secondary_heater_timeout - 4))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(secondary_heater_switch).state == STATE_OFF

    # after secondary heater timeout secondary heater should be on
    # await asyncio.sleep(secondary_heater_timeout + 3)
    freezer.tick(timedelta(seconds=secondary_heater_timeout + 3))
    common.async_fire_time_changed(hass)
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


async def test_heater_mode_floor_temp_presets(
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

    # Given
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
                "away": {"temperature": 30, "min_floor_temp": 10, "max_floor_temp": 25},
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF

    # When
    # Temperature is below target
    # Floor temperature is above min_floor_temp
    setup_sensor(hass, 18.6)
    setup_floor_sensor(hass, 10)
    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()

    # Then
    # Heater should be off
    assert hass.states.get(heater_switch).state == STATE_OFF

    # When
    # Temperature is below target
    setup_sensor(hass, 17)
    await hass.async_block_till_done()

    # Then
    # Heater should be on
    assert hass.states.get(heater_switch).state == STATE_ON

    # When
    # Floor temperature reaches max_floor_temp
    setup_floor_sensor(hass, 28)
    await hass.async_block_till_done()

    # Then
    # Heater should be off
    assert hass.states.get(heater_switch).state == STATE_OFF

    # When
    # Floor temperature is below max_floor_temp
    setup_floor_sensor(hass, 26)
    await hass.async_block_till_done()

    # Then
    # Heater should be on
    assert hass.states.get(heater_switch).state == STATE_ON

    # When
    # Temperature reaches target
    setup_sensor(hass, 22)
    await hass.async_block_till_done()

    # Then
    # Heater should be off
    assert hass.states.get(heater_switch).state == STATE_OFF

    # When
    # Floor temperature is below min_floor_temp
    setup_floor_sensor(hass, 4)
    await hass.async_block_till_done()

    # Then
    # Heater should be on
    assert hass.states.get(heater_switch).state == STATE_ON

    # When
    # Floor temperature is below min_floor_temp
    setup_floor_sensor(hass, 3)
    await hass.async_block_till_done()

    # Then
    # Heater should be on
    assert hass.states.get(heater_switch).state == STATE_ON

    # When
    # Floor temperature reaches min_floor_temp
    setup_floor_sensor(hass, 10)
    await hass.async_block_till_done()

    # Then
    assert hass.states.get(heater_switch).state == STATE_OFF

    # away mode
    # When
    # Temperature is below target from preset away
    await common.async_set_preset_mode(hass, "away")
    await hass.async_block_till_done()

    # Then
    # Heater should be on
    assert hass.states.get(heater_switch).state == STATE_ON

    # When
    # Floor temperature is above max_floor_temp from preset away
    setup_floor_sensor(hass, 26)
    await hass.async_block_till_done()

    # Then
    # Heater should be off
    assert hass.states.get(heater_switch).state == STATE_OFF

    # When
    # Floor temperature is within range from preset away
    setup_floor_sensor(hass, 20)
    await hass.async_block_till_done()

    # Then
    # Heater should be on
    assert hass.states.get(heater_switch).state == STATE_ON

    # When
    # Floor temperature reaches max_floor_temp from preset away
    setup_floor_sensor(hass, 25)
    await hass.async_block_till_done()

    # Then
    # Heater should be off
    assert hass.states.get(heater_switch).state == STATE_OFF

    # When
    # Floor temperature is within range from preset away
    setup_floor_sensor(hass, 20)
    await hass.async_block_till_done()

    # Then
    # Heater should be on
    assert hass.states.get(heater_switch).state == STATE_ON

    # When
    # No preset mode
    await common.async_set_preset_mode(hass, "none")
    # Temperature is below target
    # Floor temperature is above min_floor_temp
    setup_sensor(hass, 18.6)
    setup_floor_sensor(hass, 10)
    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()

    # Then
    # Heater should be off
    assert hass.states.get(heater_switch).state == STATE_OFF

    # When
    # Temperature is below target
    setup_sensor(hass, 17)
    await hass.async_block_till_done()

    # Then
    # Heater should be on
    assert hass.states.get(heater_switch).state == STATE_ON

    # When
    # Floor temperature reaches max_floor_temp
    setup_floor_sensor(hass, 28)
    await hass.async_block_till_done()

    # Then
    # Heater should be off
    assert hass.states.get(heater_switch).state == STATE_OFF

    # When
    # Floor temperature is below max_floor_temp
    setup_floor_sensor(hass, 26)
    await hass.async_block_till_done()

    # Then
    # Heater should be on
    assert hass.states.get(heater_switch).state == STATE_ON

    # When
    # Temperature reaches target
    setup_sensor(hass, 22)
    await hass.async_block_till_done()

    # Then
    # Heater should be off
    assert hass.states.get(heater_switch).state == STATE_OFF

    # When
    # Floor temperature is below min_floor_temp
    setup_floor_sensor(hass, 4)
    await hass.async_block_till_done()

    # Then
    # Heater should be on
    assert hass.states.get(heater_switch).state == STATE_ON

    # When
    # Floor temperature is below min_floor_temp
    setup_floor_sensor(hass, 3)
    await hass.async_block_till_done()

    # Then
    # Heater should be on
    assert hass.states.get(heater_switch).state == STATE_ON

    # When
    # Floor temperature reaches min_floor_temp
    setup_floor_sensor(hass, 10)
    await hass.async_block_till_done()

    # Then
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
        == HVACActionReason.TARGET_TEMP_REACHED
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
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_comp_1  # noqa: F811
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

    # wait 5 seconds
    freezer.tick(timedelta(seconds=6))
    common.async_fire_time_changed(hass)
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

    # wait openings
    freezer.tick(timedelta(seconds=4))
    common.async_fire_time_changed(hass)
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
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_heater_mode_cycle(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    duration,
    result_state,
    setup_comp_1,  # noqa: F811
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

    await common.async_set_temperature(hass, 23)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON

    freezer.tick(duration)
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    setup_sensor(hass, 24)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == result_state


async def test_heater_mode_opening(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_comp_1  # noqa: F811
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

    # wait 5 seconds
    freezer.tick(timedelta(seconds=6))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF

    setup_boolean(hass, opening_2, "closed")
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF

    # wait openings
    freezer.tick(timedelta(seconds=4))
    common.async_fire_time_changed(hass)
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


@pytest.mark.parametrize(
    ["hvac_mode", "opening_scope", "switch_state"],
    [
        ([HVACMode.HEAT, ["all"], STATE_OFF]),
        ([HVACMode.HEAT, [HVACMode.HEAT], STATE_OFF]),
        ([HVACMode.HEAT, [HVACMode.FAN_ONLY], STATE_ON]),
    ],
)
async def test_heater_mode_opening_scope(
    hass: HomeAssistant,
    hvac_mode,
    opening_scope,
    switch_state,
    setup_comp_1,  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode."""
    heater_switch = "input_boolean.test"

    opening_1 = "input_boolean.opening_1"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {
            "input_boolean": {
                "test": None,
                "opening_1": None,
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
                "heater": heater_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": hvac_mode,
                "openings": [
                    opening_1,
                ],
                "openings_scope": opening_scope,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 24)
    await hass.async_block_till_done()
    assert (
        hass.states.get(heater_switch).state == STATE_ON
        if hvac_mode == HVACMode.HEAT
        else STATE_OFF
    )

    setup_boolean(hass, opening_1, STATE_OPEN)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == switch_state

    setup_boolean(hass, opening_1, STATE_CLOSED)
    await hass.async_block_till_done()

    assert (
        hass.states.get(heater_switch).state == STATE_ON
        if hvac_mode == HVACMode.HEAT
        else STATE_OFF
    )


################################################
# FUNCTIONAL TESTS - TOLERANCE CONFIGURATIONS #
################################################


async def test_legacy_config_heat_mode_behaves_identically(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test legacy config in HEAT mode behaves identically.

    This test verifies backward compatibility - configurations using only
    cold_tolerance and hot_tolerance (no heat_tolerance) should work
    correctly in HEAT mode.
    """
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

    # Configure with ONLY cold_tolerance=0.5, hot_tolerance=0.5 (NO heat_tolerance)
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
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
            }
        },
    )
    await hass.async_block_till_done()

    # Set target to 20°C
    await common.async_set_temperature(hass, 20)
    await hass.async_block_till_done()

    # Set current to 19.4°C
    # Should activate heater (19.4 <= 20 - 0.5 = 19.5)
    setup_sensor(hass, 19.4)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON

    # Verify heating uses legacy tolerances
    # At 20.6°C, heater should deactivate (20.6 >= 20 + 0.5 = 20.5)
    setup_sensor(hass, 20.6)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
