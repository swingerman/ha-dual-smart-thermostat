"""The tests for the dual_smart_thermostat."""

import datetime
from datetime import timedelta
import logging

from freezegun.api import FrozenDateTimeFactory
from homeassistant.components import input_boolean, input_number
from homeassistant.components.climate import (
    PRESET_ACTIVITY,
    PRESET_AWAY,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_HOME,
    PRESET_NONE,
    PRESET_SLEEP,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.components.climate.const import (
    ATTR_PRESET_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    DOMAIN as CLIMATE,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    ENTITY_MATCH_ALL,
    SERVICE_TURN_OFF,
    STATE_CLOSED,
    STATE_OFF,
    STATE_ON,
    STATE_OPEN,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import DOMAIN as HASS_DOMAIN, CoreState, HomeAssistant, State
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest
import voluptuous as vol

from custom_components.dual_smart_thermostat.const import (
    ATTR_HVAC_ACTION_REASON,
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
    setup_comp_dual,
    setup_comp_dual_fan_config,
    setup_comp_heat_cool_1,
    setup_comp_heat_cool_2,
    setup_comp_heat_cool_fan_config,
    setup_comp_heat_cool_fan_config_2,
    setup_comp_heat_cool_fan_presets,
    setup_comp_heat_cool_presets,
    setup_comp_heat_cool_presets_range_only,
    setup_comp_heat_cool_safety_delay,
    setup_floor_sensor,
    setup_humidity_sensor,
    setup_outside_sensor,
    setup_sensor,
    setup_switch_dual,
    setup_switch_heat_cool_fan,
)
from . import setup_comp_dual_presets  # noqa: F401, F811

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
    # GIVEN: Climate entity configured with a unique ID in heat_cool mode
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

    # WHEN: Checking the entity registry for the created entity
    entry = entity_registry.async_get(common.ENTITY)

    # THEN: Entity should have the configured unique ID
    assert entry
    assert entry.unique_id == unique_id


async def test_setup_defaults_to_unknown(hass: HomeAssistant) -> None:  # noqa: F811
    """Test the setting of defaults to unknown."""
    # GIVEN: Climate entity configured without initial HVAC mode
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

    # THEN: Thermostat should default to OFF state
    assert hass.states.get(common.ENTITY).state == HVACMode.OFF


async def test_setup_gets_current_temp_from_sensor(
    hass: HomeAssistant,
) -> None:  # noqa: F811
    """Test that current temperature is updated on entity addition."""
    # GIVEN: Temperature sensor reporting 18°C
    hass.config.units = METRIC_SYSTEM
    setup_sensor(hass, 18)
    await hass.async_block_till_done()

    # WHEN: Setting up thermostat with temperature sensor
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

    # THEN: Current temperature should be read from sensor
    assert hass.states.get(common.ENTITY).attributes["current_temperature"] == 18


async def test_restore_state_while_off(hass: HomeAssistant) -> None:
    """Ensure states are restored on startup."""
    # GIVEN: Cached state with OFF mode and temperature 20
    common.mock_restore_cache(
        hass,
        (
            State(
                "climate.test",
                HVACMode.OFF,
                {ATTR_TEMPERATURE: "20"},
            ),
        ),
    )

    hass.set_state(CoreState.starting)

    # WHEN: Setting up climate entity with target_temp 19.5
    await async_setup_component(
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
                "target_temp": 19.5,
            }
        },
    )

    await hass.async_block_till_done()

    # THEN: Cached temperature 20 is restored despite config having 19.5
    state = hass.states.get("climate.test")
    _LOGGER.debug("Attributes: %s", state.attributes)
    assert state.attributes[ATTR_TEMPERATURE] == 20
    assert state.state == HVACMode.OFF


# issue 80
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_presets_use_case_80(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test that current temperature is updated on entity addition."""
    # GIVEN: Heat cool mode setup with away preset
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
                "heater": common.ENT_HEATER,
                "cooler": common.ENT_COOLER,
                "target_sensor": common.ENT_SENSOR,
                "min_cycle_duration": timedelta(seconds=60),
                "precision": 0.5,
                "min_temp": 20,
                "max_temp": 25,
                "heat_cool_mode": True,
                PRESET_AWAY: {
                    "target_temp_low": 0,
                    "target_temp_high": 50,
                },
            }
        },
    )
    await hass.async_block_till_done()

    # THEN: Entity supports presets and has away mode available
    state = hass.states.get(common.ENTITY)
    assert state.attributes["supported_features"] == 402
    assert set(state.attributes["preset_modes"]) == set([PRESET_NONE, PRESET_AWAY])

    # WHEN: Setting preset to away
    await common.async_set_preset_mode(hass, PRESET_AWAY)

    # THEN: Away preset is active
    state = hass.states.get(common.ENTITY)
    assert state.attributes[ATTR_PRESET_MODE] == PRESET_AWAY


# issue 150
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_presets_use_case_150(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:  # noqa: F811
    """Test that current temperature is updated on entity addition."""
    # GIVEN: Sensor at 18 degrees
    hass.config.units = METRIC_SYSTEM
    setup_sensor(hass, 18)
    await hass.async_block_till_done()

    # WHEN: Setting up dual climate entity with precision 1.0 and tolerances
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "heater": common.ENT_HEATER,
                "cooler": common.ENT_COOLER,
                "target_sensor": common.ENT_SENSOR,
                "min_cycle_duration": timedelta(seconds=60),
                "precision": 1.0,
                "min_temp": 58,
                "max_temp": 80,
                "cold_tolerance": 1.0,
                "hot_tolerance": 1.0,
            }
        },
    )
    await hass.async_block_till_done()

    # THEN: Entity configured with correct supported features
    state = hass.states.get(common.ENTITY)
    assert state.attributes["supported_features"] == 385


async def test_presets_use_case_150_2(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:  # noqa: F811
    """Test that current temperature is updated on entity addition."""
    # GIVEN: Heat cool mode setup starting in OFF mode
    hass.config.units = METRIC_SYSTEM

    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None}},
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
                # "min_cycle_duration": min_cycle_duration,
                # "keep_alive": timedelta(seconds=3),
                "precision": 1.0,
                "min_temp": 16,
                "max_temp": 32,
                "target_temp": 26.5,
                "target_temp_low": 23,
                "target_temp_high": 26.5,
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
                "initial_hvac_mode": HVACMode.OFF,
            }
        },
    )
    await hass.async_block_till_done()

    # THEN: Entity configured with correct features and modes
    state = hass.states.get(common.ENTITY)
    assert state.attributes["supported_features"] == 386

    modes = state.attributes.get("hvac_modes")
    assert set(modes) == set(
        [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.HEAT_COOL]
    )

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).attributes["hvac_action"] == HVACAction.OFF

    # WHEN: Sensor at 23, switching to HEAT_COOL mode with range 16-18
    setup_sensor(hass, 23)
    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await common.async_set_temperature_range(hass, ENTITY_MATCH_ALL, 18, 16)
    await hass.async_block_till_done()

    # THEN: Cooler activates since temp is above range
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    assert (
        hass.states.get(common.ENTITY).attributes["hvac_action"] == HVACAction.COOLING
    )

    # WHEN: Sensor drops to 1 degree (far below target range)
    setup_sensor(hass, 1)
    await hass.async_block_till_done()

    # THEN: Both switches off and system idle
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).attributes["hvac_action"] == HVACAction.IDLE


async def test_dual_default_setup_params(
    hass: HomeAssistant, setup_comp_dual  # noqa: F811
) -> None:
    """Test the setup with default parameters."""
    # GIVEN: Dual mode setup complete
    # WHEN: Reading entity state
    state = hass.states.get(common.ENTITY)

    # THEN: Default temperature parameters are set correctly
    assert state.attributes.get("min_temp") == 7
    assert state.attributes.get("max_temp") == 35
    assert state.attributes.get("temperature") == 7


async def test_heat_cool_default_setup_params(
    hass: HomeAssistant, setup_comp_heat_cool_1  # noqa: F811
) -> None:
    """Test the setup with default parameters."""
    # GIVEN: Heat cool mode setup complete
    # WHEN: Reading entity state
    state = hass.states.get(common.ENTITY)

    # THEN: Default temperature range parameters are set correctly
    assert state.attributes.get("min_temp") == 7
    assert state.attributes.get("max_temp") == 35
    assert state.attributes.get("target_temp_low") == 7
    assert state.attributes.get("target_temp_high") == 35
    assert state.attributes.get("target_temp_step") == 0.1


###################
# CHANGE SETTINGS #
###################


async def test_get_hvac_modes_dual(
    hass: HomeAssistant, setup_comp_dual  # noqa: F811
) -> None:
    """Test that the operation list returns the correct modes."""
    # GIVEN: Dual mode setup complete
    # WHEN: Reading available HVAC modes
    state = hass.states.get(common.ENTITY)
    modes = state.attributes.get("hvac_modes")

    # THEN: OFF, HEAT, and COOL modes are available (no HEAT_COOL)
    assert set(modes) == set([HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL])


async def test_get_hvac_modes_heat_cool(
    hass: HomeAssistant, setup_comp_heat_cool_1  # noqa: F811
) -> None:
    """Test that the operation list returns the correct modes."""
    # GIVEN: Heat cool mode setup complete
    # WHEN: Reading available HVAC modes
    state = hass.states.get(common.ENTITY)
    modes = state.attributes.get("hvac_modes")

    # THEN: All modes including HEAT_COOL are available
    assert set(modes) == set(
        [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.HEAT_COOL]
    )


async def test_get_hvac_modes_heat_cool_2(
    hass: HomeAssistant, setup_comp_heat_cool_2  # noqa: F811
) -> None:
    """Test that the operation list returns the correct modes."""
    # GIVEN: Heat cool mode setup complete (variant 2)
    # WHEN: Reading available HVAC modes
    state = hass.states.get(common.ENTITY)
    modes = state.attributes.get("hvac_modes")

    # THEN: All modes including HEAT_COOL are available
    assert set(modes) == set(
        [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.HEAT_COOL]
    )


# async def test_get_hvac_modes_heat_cool_if_heat_cool_mode_off(
#     hass: HomeAssistant, setup_comp_heat_cool_3  # noqa: F811
# ) -> None:
#     """Test that the operation list returns the correct modes."""
#     await async_setup_component(
#         hass,
#         CLIMATE,
#         {
#             "climate": {
#                 "platform": DOMAIN,
#                 "name": "test",
#                 "cold_tolerance": 2,
#                 "hot_tolerance": 4,
#                 "heater": common.ENT_HEATER,
#                 "cooler": common.ENT_COOLER,
#                 "target_sensor": common.ENT_SENSOR,
#                 "initial_hvac_mode": HVACMode.OFF,
#                 "target_temp": 21,
#                 "heat_cool_mode": False,
#                 PRESET_AWAY: {
#                     "temperature": 16,
#                 },
#             }
#         },
#     )
#     await hass.async_block_till_done()

#     common.mock_restore_cache(
#         hass,
#         (
#             State(
#                 common.ENTITY,
#                 {
#                     ATTR_PREV_TARGET_HIGH: "21",
#                     ATTR_PREV_TARGET_LOW: "19",
#                 },
#             ),
#         ),
#     )

#     hass.set_state(CoreState.starting)
#     await hass.async_block_till_done()

#     state = hass.states.get(common.ENTITY)
#     assert state.attributes.get("supported_features") == 401
#     modes = state.attributes.get("hvac_modes")
#     assert set(modes) == set([HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL])


async def test_dual_get_hvac_modes_fan_configured(
    hass: HomeAssistant, setup_comp_dual_fan_config  # noqa: F811
) -> None:
    """Test that the operation list returns the correct modes."""
    # GIVEN: Dual mode with fan configured
    # WHEN: Reading available HVAC modes
    state = hass.states.get(common.ENTITY)
    modes = state.attributes.get("hvac_modes")

    # THEN: FAN_ONLY mode is available in addition to standard modes
    assert set(modes) == set(
        [
            HVACMode.OFF,
            HVACMode.HEAT,
            HVACMode.COOL,
            HVACMode.FAN_ONLY,
        ]
    )


async def test_heat_cool_get_hvac_modes_fan_configured(
    hass: HomeAssistant, setup_comp_heat_cool_fan_config  # noqa: F811
) -> None:
    """Test that the operation list returns the correct modes."""
    # GIVEN: Heat cool mode with fan configured
    # WHEN: Reading available HVAC modes
    state = hass.states.get(common.ENTITY)
    modes = state.attributes.get("hvac_modes")

    # THEN: FAN_ONLY mode available along with all heat/cool modes
    assert set(modes) == set(
        [
            HVACMode.OFF,
            HVACMode.HEAT,
            HVACMode.COOL,
            HVACMode.HEAT_COOL,
            HVACMode.FAN_ONLY,
        ]
    )


async def test_set_hvac_mode_chnage_trarget_temp(
    hass: HomeAssistant, setup_comp_dual  # noqa: F811
) -> None:
    """Test the changing of the hvac mode avoid invalid target temp."""
    # GIVEN: Temperature set to 30
    await common.async_set_temperature(hass, 30)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 30

    # WHEN: Switching to COOL mode
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    await hass.async_block_till_done()

    # THEN: Temperature is preserved
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 30

    # WHEN: Switching to HEAT mode
    await common.async_set_hvac_mode(hass, HVACMode.HEAT)
    await hass.async_block_till_done()

    # THEN: Temperature is still preserved
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 30


async def test_set_target_temp_dual(
    hass: HomeAssistant, setup_comp_dual  # noqa: F811
) -> None:
    """Test the setting of the target temperature."""
    # GIVEN: Dual mode setup
    # WHEN: Setting temperature to 30
    await common.async_set_temperature(hass, 30)

    # THEN: Temperature is set correctly
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 30

    # WHEN: Attempting to set None temperature
    # THEN: Raises validation error and temperature unchanged
    with pytest.raises(vol.Invalid):
        await common.async_set_temperature(hass, None)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 30


async def test_set_target_temp_heat_cool(
    hass: HomeAssistant, setup_comp_heat_cool_1  # noqa: F811
) -> None:
    """Test the setting of the target temperature."""
    # GIVEN: Heat cool mode setup
    # WHEN: Setting temperature range to 22-25
    await common.async_set_temperature_range(hass, common.ENTITY, 25, 22)

    # THEN: Temperature range is set correctly
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_high") == 25.0
    assert state.attributes.get("target_temp_low") == 22.0

    # WHEN: Attempting to set None temperature
    # THEN: Raises validation error and range unchanged
    with pytest.raises(vol.Invalid):
        await common.async_set_temperature(hass, None)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_high") == 25.0
    assert state.attributes.get("target_temp_low") == 22.0


@pytest.mark.parametrize(
    ("preset", "temperature"),
    [
        (PRESET_NONE, 23),
        (PRESET_AWAY, 16),
        (PRESET_COMFORT, 20),
        (PRESET_ECO, 18),
        (PRESET_HOME, 19),
        (PRESET_SLEEP, 17),
        (PRESET_ACTIVITY, 21),
        (PRESET_ANTI_FREEZE, 5),
    ],
)
async def test_dual_set_preset_mode(
    hass: HomeAssistant,
    setup_comp_dual_presets,  # noqa: F811
    preset,
    temperature,
) -> None:
    """Test the setting preset mode."""
    # GIVEN: Temperature set to 23
    await common.async_set_temperature(hass, 23)

    # WHEN: Setting preset mode
    await common.async_set_preset_mode(hass, preset)

    # THEN: Temperature matches preset's configured value
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == temperature


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
async def test_heat_cool_set_preset_mode(
    hass: HomeAssistant,
    setup_comp_heat_cool_presets,  # noqa: F811
    preset,
    temp_low,
    temp_high,
) -> None:
    """Test the setting preset mode."""
    # GIVEN: Temperature range set to 18-22
    await common.async_set_temperature_range(hass, common.ENTITY, 22, 18)

    # WHEN: Setting preset mode
    await common.async_set_preset_mode(hass, preset)

    # THEN: Temperature range matches preset's configured values
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == temp_low
    assert state.attributes.get("target_temp_high") == temp_high


@pytest.mark.parametrize(
    ("preset", "temperature"),
    [
        (PRESET_NONE, 23),
        (PRESET_AWAY, 16),
        (PRESET_COMFORT, 20),
        (PRESET_ECO, 18),
        (PRESET_HOME, 19),
        (PRESET_SLEEP, 17),
        (PRESET_ACTIVITY, 21),
        (PRESET_ANTI_FREEZE, 5),
    ],
)
async def test_dual_set_preset_mode_and_restore_prev_temp(
    hass: HomeAssistant, setup_comp_dual_presets, preset, temperature  # noqa: F811
) -> None:
    """Test the setting preset mode.

    Verify original temperature is restored.
    """
    # GIVEN: Temperature set to 23
    await common.async_set_temperature(hass, 23)

    # WHEN: Setting preset mode
    await common.async_set_preset_mode(hass, preset)

    # THEN: Temperature matches preset value
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == temperature

    # WHEN: Returning to PRESET_NONE
    await common.async_set_preset_mode(hass, PRESET_NONE)

    # THEN: Original temperature is restored
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 23


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
async def test_set_heat_cool_preset_mode_and_restore_prev_temp(
    hass: HomeAssistant,
    setup_comp_heat_cool_presets,  # noqa: F811
    preset,
    temp_low,
    temp_high,
) -> None:
    """Test the setting preset mode.

    Verify original temperature is restored.
    """
    # GIVEN: Temperature range set to 18-22
    await common.async_set_temperature_range(hass, common.ENTITY, 22, 18)

    # WHEN: Setting preset mode
    await common.async_set_preset_mode(hass, preset)

    # THEN: Temperature range matches preset values
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == temp_low
    assert state.attributes.get("target_temp_high") == temp_high

    # WHEN: Returning to PRESET_NONE
    await common.async_set_preset_mode(hass, PRESET_NONE)

    # THEN: Original temperature range is restored
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == 18
    assert state.attributes.get("target_temp_high") == 22


@pytest.mark.parametrize(
    ("preset", "temp_low", "temp_high"),
    [
        (PRESET_AWAY, 16, 30),
        (PRESET_COMFORT, 20, 27),
        (PRESET_ECO, 18, 29),
        (PRESET_HOME, 19, 23),
        (PRESET_SLEEP, 17, 24),
        (PRESET_ACTIVITY, 21, 28),
        (PRESET_ANTI_FREEZE, 5, 32),
    ],
)
async def test_set_heat_cool_preset_mode_and_restore_prev_temp_2(
    hass: HomeAssistant,
    setup_comp_heat_cool_presets,  # noqa: F811
    preset,
    temp_low,
    temp_high,
) -> None:
    """Test the setting preset mode.

    Verify original temperature is restored.
    And verifies that if the preset set again it's temps are match the preset
    """
    # GIVEN: Temperature range set to 18-22
    await common.async_set_temperature_range(hass, common.ENTITY, 22, 18)

    # WHEN: Setting preset mode
    await common.async_set_preset_mode(hass, preset)

    # THEN: Temperature range matches preset values
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TARGET_TEMP_LOW) == temp_low
    assert state.attributes.get(ATTR_TARGET_TEMP_HIGH) == temp_high

    # WHEN: Manually setting temperature range updates targets while keeping preset
    await common.async_set_temperature_range(hass, common.ENTITY, 24, 17)
    await hass.async_block_till_done()

    # THEN: Targets updated but preset mode preserved
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TARGET_TEMP_LOW) == 17
    assert state.attributes.get(ATTR_TARGET_TEMP_HIGH) == 24
    assert state.attributes.get(ATTR_PRESET_MODE) == preset

    # WHEN: Setting preset mode again
    await common.async_set_preset_mode(hass, preset)

    # THEN: Temps reset to preset values
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TARGET_TEMP_LOW) == temp_low
    assert state.attributes.get(ATTR_TARGET_TEMP_HIGH) == temp_high

    # WHEN: Returning to PRESET_NONE
    await common.async_set_preset_mode(hass, PRESET_NONE)

    # THEN: Original temps are restored
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TARGET_TEMP_LOW) == 18
    assert state.attributes.get(ATTR_TARGET_TEMP_HIGH) == 22

    # WHEN: Setting preset mode again after PRESET_NONE
    await common.async_set_preset_mode(hass, preset)

    # THEN: Temps match preset values again
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TARGET_TEMP_LOW) == temp_low
    assert state.attributes.get(ATTR_TARGET_TEMP_HIGH) == temp_high


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
async def test_set_heat_cool_fan_preset_mode_and_restore_prev_temp(
    hass: HomeAssistant,
    setup_comp_heat_cool_fan_presets,  # noqa: F811
    preset,
    temp_low,
    temp_high,
) -> None:
    """Test the setting preset mode.

    Verify original temperature is restored.
    """
    # GIVEN: Temperature range set to 18-22 with fan configured
    await common.async_set_temperature_range(hass, common.ENTITY, 22, 18)

    # WHEN: Setting preset mode
    await common.async_set_preset_mode(hass, preset)

    # THEN: Temperature range matches preset values
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == temp_low
    assert state.attributes.get("target_temp_high") == temp_high

    # WHEN: Returning to PRESET_NONE
    await common.async_set_preset_mode(hass, PRESET_NONE)

    # THEN: Original temperature range is restored
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == 18
    assert state.attributes.get("target_temp_high") == 22


@pytest.mark.parametrize(
    "preset",
    [PRESET_NONE, PRESET_AWAY],
)
async def test_set_heat_cool_fan_restore_state(
    hass: HomeAssistant, preset  # noqa: F811
) -> None:
    # GIVEN: Cached state with HEAT_COOL mode, temps 19-21, and preset
    common.mock_restore_cache(
        hass,
        (
            State(
                "climate.test_thermostat",
                HVACMode.HEAT_COOL,
                {
                    ATTR_TARGET_TEMP_HIGH: "21",
                    ATTR_TARGET_TEMP_LOW: "19",
                    ATTR_PRESET_MODE: preset,
                },
            ),
        ),
    )

    hass.set_state(CoreState.starting)

    # WHEN: Setting up climate entity with fan and away preset configured
    await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test_thermostat",
                "heater": common.ENT_SWITCH,
                "cooler": common.ENT_COOLER,
                "fan": common.ENT_FAN,
                "heat_cool_mode": True,
                "target_sensor": common.ENT_SENSOR,
                PRESET_AWAY: {
                    "temperature": 14,
                    "target_temp_high": 20,
                    "target_temp_low": 18,
                },
            }
        },
    )
    await hass.async_block_till_done()

    # THEN: Cached state is restored correctly
    state = hass.states.get("climate.test_thermostat")
    assert state.attributes[ATTR_TARGET_TEMP_HIGH] == 21
    assert state.attributes[ATTR_TARGET_TEMP_LOW] == 19
    assert state.attributes[ATTR_PRESET_MODE] == preset
    assert state.state == HVACMode.HEAT_COOL


# async def test_set_heat_cool_fan_restore_state_check_reason(
#     hass: HomeAssistant,  # noqa: F811
# ) -> None:
#     common.mock_restore_cache(
#         hass,
#         (
#             State(
#                 "climate.test_thermostat",
#                 HVACMode.HEAT_COOL,
#                 {
#                     ATTR_TARGET_TEMP_HIGH: "21",
#                     ATTR_TARGET_TEMP_LOW: "19",
#                 },
#             ),
#         ),
#     )

#     hass.set_state(CoreState.starting)

#     await async_setup_component(
#         hass,
#         CLIMATE,
#         {
#             "climate": {
#                 "platform": DOMAIN,
#                 "name": "test_thermostat",
#                 "heater": common.ENT_SWITCH,
#                 "cooler": common.ENT_COOLER,
#                 "fan": common.ENT_FAN,
#                 "heat_cool_mode": True,
#                 "target_sensor": common.ENT_SENSOR,
#                 PRESET_AWAY: {
#                     "temperature": 14,
#                     "target_temp_high": 20,
#                     "target_temp_low": 18,
#                 },
#             }
#         },
#     )
#     await hass.async_block_till_done()
#     setup_sensor(hass, 23)
#     state = hass.states.get("climate.test_thermostat")
#     assert state.attributes[ATTR_TARGET_TEMP_HIGH] == 21
#     assert state.attributes[ATTR_TARGET_TEMP_LOW] == 19
#     assert state.state == HVACMode.HEAT_COOL
#     assert (
#         state.attributes[ATTR_HVAC_ACTION_REASON]
#         == HVACActionReasonInternal.TARGET_TEMP_NOT_REACHED
#     )

#     # simulate a restart with old state
#     common.mock_restore_cache(
#         hass,
#         (
#             State(
#                 "climate.test_thermostat",
#                 HVACMode.HEAT_COOL,
#                 {
#                     ATTR_TARGET_TEMP_HIGH: "21",
#                     ATTR_TARGET_TEMP_LOW: "19",
#                     ATTR_HVAC_ACTION_REASON: HVACActionReasonInternal.TARGET_TEMP_NOT_REACHED,
#                 },
#             ),
#         ),
#     )

#     hass.set_state(CoreState.starting)

#     setup_sensor(hass, 25)
#     await hass.async_block_till_done()

#     state = hass.states.get("climate.test_thermostat")
#     # assert state.attributes[ATTR_HVAC_ACTION] == HVACAction.COOLING
#     # assert (
#     #     state.attributes[ATTR_HVAC_ACTION_REASON]
#     #     == HVACActionReasonInternal.TARGET_TEMP_NOT_REACHED
#     # )
#     assert state.attributes[ATTR_HVAC_ACTION_REASON] != ""


@pytest.mark.parametrize(
    ["preset", "hvac_mode"],
    [
        [PRESET_NONE, HVACMode.HEAT],
        [PRESET_AWAY, HVACMode.HEAT],
        [PRESET_NONE, HVACMode.COOL],
        [PRESET_AWAY, HVACMode.COOL],
    ],
)
async def test_set_heat_cool_fan_restore_state_2(
    hass: HomeAssistant, preset, hvac_mode  # noqa: F811
) -> None:
    # GIVEN: Cached state with HEAT or COOL mode, temp 20, and preset
    common.mock_restore_cache(
        hass,
        (
            State(
                "climate.test_thermostat",
                hvac_mode,
                {
                    ATTR_TEMPERATURE: "20",
                    ATTR_PRESET_MODE: preset,
                },
            ),
        ),
    )

    hass.set_state(CoreState.starting)

    # WHEN: Setting up heat cool fan entity with away preset
    await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test_thermostat",
                "heater": common.ENT_SWITCH,
                "cooler": common.ENT_COOLER,
                "fan": common.ENT_FAN,
                "heat_cool_mode": True,
                "target_sensor": common.ENT_SENSOR,
                PRESET_AWAY: {
                    "temperature": 14,
                    "target_temp_high": 20,
                    "target_temp_low": 18,
                },
            }
        },
    )
    await hass.async_block_till_done()

    # THEN: Cached state is restored correctly
    state = hass.states.get("climate.test_thermostat")
    assert state.attributes[ATTR_TEMPERATURE] == 20
    assert state.attributes[ATTR_PRESET_MODE] == preset
    assert state.state == hvac_mode


@pytest.mark.parametrize(
    ("preset", "temperature"),
    [
        (PRESET_NONE, 23),
        (PRESET_AWAY, 16),
        (PRESET_COMFORT, 20),
        (PRESET_ECO, 18),
        (PRESET_HOME, 19),
        (PRESET_SLEEP, 17),
        (PRESET_ACTIVITY, 21),
        (PRESET_ANTI_FREEZE, 5),
    ],
)
async def test_set_dual_preset_mode_twice_and_restore_prev_temp(
    hass: HomeAssistant, setup_comp_dual_presets, preset, temperature  # noqa: F811
) -> None:
    """Test the setting preset mode twice in a row.

    Verify original temperature is restored.
    """
    # GIVEN: Temperature set to 23
    await common.async_set_temperature(hass, 23)

    # WHEN: Setting same preset mode twice in a row
    await common.async_set_preset_mode(hass, preset)
    await common.async_set_preset_mode(hass, preset)

    # THEN: Temperature matches preset value
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == temperature

    # WHEN: Returning to PRESET_NONE
    await common.async_set_preset_mode(hass, PRESET_NONE)

    # THEN: Original temperature is restored
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 23


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
async def test_set_heat_cool_preset_mode_twice_and_restore_prev_temp(
    hass: HomeAssistant,
    setup_comp_heat_cool_presets,  # noqa: F811
    preset,
    temp_low,
    temp_high,
) -> None:
    """Test the setting preset mode twice in a row.

    Verify original temperature is restored.
    """
    # GIVEN: Temperature range set to 18-22
    await common.async_set_temperature_range(hass, common.ENTITY, 22, 18)

    # WHEN: Setting same preset mode twice in a row
    await common.async_set_preset_mode(hass, preset)
    await common.async_set_preset_mode(hass, preset)

    # THEN: Temperature range matches preset values
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == temp_low
    assert state.attributes.get("target_temp_high") == temp_high

    # WHEN: Returning to PRESET_NONE
    await common.async_set_preset_mode(hass, PRESET_NONE)

    # THEN: Original temperature range is restored
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
async def test_set_heat_cool_preset_mode_and_restore_prev_temp_apply_preset_again(
    hass: HomeAssistant,
    setup_comp_heat_cool_presets,  # noqa: F811
    preset,
    temp_low,
    temp_high,
) -> None:
    """Test the setting preset mode twice in a row.

    Verify original temperature is restored.
    """
    # GIVEN: Temperature range set to 18-22
    await common.async_set_temperature_range(hass, common.ENTITY, 22, 18)

    # WHEN: Setting preset mode
    await common.async_set_preset_mode(hass, preset)

    # THEN: Targets match preset values
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == temp_low
    assert state.attributes.get("target_temp_high") == temp_high

    # WHEN: Returning to PRESET_NONE
    await common.async_set_preset_mode(hass, PRESET_NONE)

    # THEN: Targets match previous settings
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == 18
    assert state.attributes.get("target_temp_high") == 22

    # WHEN: Reapplying preset
    await common.async_set_preset_mode(hass, preset)

    # THEN: Targets match preset again
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == temp_low
    assert state.attributes.get("target_temp_high") == temp_high

    # WHEN: Simulating restore state
    common.mock_restore_cache(
        hass,
        (
            State(
                "climate.test_thermostat",
                {ATTR_PRESET_MODE: {preset}},
            ),
        ),
    )

    hass.set_state(CoreState.starting)

    # THEN: Targets match preset again after restart
    # await common.async_set_preset_mode(hass, preset)
    assert state.attributes.get("target_temp_low") == temp_low
    assert state.attributes.get("target_temp_high") == temp_high


async def test_set_dual_preset_mode_invalid(
    hass: HomeAssistant, setup_comp_dual_presets  # noqa: F811
) -> None:
    """Test an invalid mode raises an error and ignore case when checking modes."""
    # GIVEN: Temperature set to 23
    await common.async_set_temperature(hass, 23)

    # WHEN: Setting lowercase away preset
    await common.async_set_preset_mode(hass, "away")

    # THEN: Away preset is active
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == "away"

    # WHEN: Setting lowercase none preset
    await common.async_set_preset_mode(hass, "none")

    # THEN: None preset is active
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == "none"

    # WHEN: Attempting to set invalid capitalized preset
    # THEN: Raises validation error and preset unchanged
    with pytest.raises(ServiceValidationError):
        await common.async_set_preset_mode(hass, "Sleep")
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == "none"


async def test_set_heat_cool_preset_mode_invalid(
    hass: HomeAssistant, setup_comp_heat_cool_presets  # noqa: F811
) -> None:
    """Test an invalid mode raises an error and ignore case when checking modes."""
    # GIVEN: Temperature range set to 18-22
    await common.async_set_temperature_range(hass, common.ENTITY, 22, 18)

    # WHEN: Setting lowercase away preset
    await common.async_set_preset_mode(hass, "away")

    # THEN: Away preset is active
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == "away"

    # WHEN: Setting lowercase none preset
    await common.async_set_preset_mode(hass, "none")

    # THEN: None preset is active
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == "none"

    # WHEN: Attempting to set invalid capitalized preset
    # THEN: Raises validation error and preset unchanged
    with pytest.raises(ServiceValidationError):
        await common.async_set_preset_mode(hass, "Sleep")
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == "none"


@pytest.mark.parametrize(
    "sensor_state",
    [STATE_UNAVAILABLE, STATE_UNKNOWN],
)
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_sensor_unknown_secure_heat_cool_off_outside_stale_duration_cooler(
    hass: HomeAssistant, sensor_state, setup_comp_heat_cool_safety_delay  # noqa: F811
) -> None:
    # GIVEN: Sensor at 28, HEAT_COOL mode with range 22-25, cooler ON
    setup_sensor(hass, 28)
    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await common.async_set_temperature_range(hass, common.ENTITY, 25, 22)
    calls = setup_switch_dual(hass, common.ENT_COOLER, False, True)

    # WHEN: Sensor becomes unavailable/unknown and 3 minutes pass
    hass.states.async_set(common.ENT_SENSOR, sensor_state)
    await hass.async_block_till_done()

    common.async_fire_time_changed(
        hass, dt_util.utcnow() + datetime.timedelta(minutes=3)
    )
    await hass.async_block_till_done()

    # THEN: Cooler is turned off for safety
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_COOLER


@pytest.mark.parametrize(
    "sensor_state",
    [STATE_UNAVAILABLE, STATE_UNKNOWN],
)
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_sensor_unknown_secure_heat_cool_off_outside_stale_duration_heater(
    hass: HomeAssistant, sensor_state, setup_comp_heat_cool_safety_delay  # noqa: F811
) -> None:
    # GIVEN: Sensor at 18, HEAT_COOL mode with range 22-25, heater ON
    setup_sensor(hass, 18)
    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await common.async_set_temperature_range(hass, common.ENTITY, 25, 22)
    calls = setup_switch_dual(hass, common.ENT_COOLER, True, False)
    await hass.async_block_till_done()

    # WHEN: Sensor becomes unavailable/unknown and 3 minutes pass
    hass.states.async_set(common.ENT_SENSOR, sensor_state)
    await hass.async_block_till_done()

    common.async_fire_time_changed(
        hass, dt_util.utcnow() + datetime.timedelta(minutes=3)
    )
    await hass.async_block_till_done()

    # THEN: Heater is turned off for safety
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


@pytest.mark.parametrize(
    ["sensor_state", "sensor_value", "affected_switch"],
    [
        (STATE_UNAVAILABLE, 28, common.ENT_COOLER),
        (STATE_UNKNOWN, 28, common.ENT_COOLER),
        (28, 28, common.ENT_COOLER),
        (STATE_UNKNOWN, 18, common.ENT_SWITCH),
        (STATE_UNKNOWN, 18, common.ENT_SWITCH),
        (18, 18, common.ENT_SWITCH),
    ],
)
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_sensor_unknown_secure_heat_cool_off_outside_stale_duration(
    hass: HomeAssistant,
    sensor_state,
    sensor_value,
    affected_switch,
    setup_comp_heat_cool_safety_delay,  # noqa: F811
) -> None:
    # GIVEN: Sensor at specific value, HEAT_COOL mode with range 22-25
    temp_high = 25
    temp_low = 22

    setup_sensor(hass, sensor_value)
    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await common.async_set_temperature_range(hass, common.ENTITY, temp_high, temp_low)
    calls = setup_switch_dual(
        hass, common.ENT_COOLER, sensor_value < temp_low, sensor_value > temp_high
    )
    await hass.async_block_till_done()

    # WHEN: Sensor becomes unavailable/unknown and 3 minutes pass
    hass.states.async_set(common.ENT_SENSOR, sensor_state)
    await hass.async_block_till_done()

    common.async_fire_time_changed(
        hass, dt_util.utcnow() + datetime.timedelta(minutes=3)
    )
    await hass.async_block_till_done()

    # THEN: Appropriate switch is turned off for safety
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == affected_switch


@pytest.mark.parametrize(
    ["sensor_state", "sensor_value"],
    [
        (STATE_UNAVAILABLE, 28),
        (STATE_UNKNOWN, 28),
        (28, 28),
        (STATE_UNKNOWN, 18),
        (STATE_UNKNOWN, 18),
        (18, 18),
    ],
)
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_sensor_unknown_secure_heat_cool_off_outside_stale_duration_reason(
    hass: HomeAssistant,
    sensor_state,
    sensor_value,
    setup_comp_heat_cool_safety_delay,  # noqa: F811
) -> None:
    # GIVEN: Sensor at specific value, HEAT_COOL mode with range 22-25
    temp_high = 25
    temp_low = 22

    setup_sensor(hass, sensor_value)
    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await common.async_set_temperature_range(hass, common.ENTITY, temp_high, temp_low)
    calls = setup_switch_dual(  # noqa: F841
        hass, common.ENT_COOLER, sensor_value < temp_low, sensor_value > temp_high
    )
    await hass.async_block_till_done()

    hass.states.async_set(common.ENT_SENSOR, sensor_state)
    await hass.async_block_till_done()

    # WHEN: Sensor unavailable/unknown for 3 minutes
    common.async_fire_time_changed(
        hass, dt_util.utcnow() + datetime.timedelta(minutes=3)
    )
    await hass.async_block_till_done()

    # THEN: HVAC action reason shows sensor stalled
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReasonInternal.TEMPERATURE_SENSOR_STALLED
    )


@pytest.mark.parametrize(
    ["sensor_state", "sensor_value"],
    [
        (STATE_UNAVAILABLE, 28),
        (STATE_UNKNOWN, 28),
        (28, 28),
        (STATE_UNAVAILABLE, 18),
        (STATE_UNKNOWN, 18),
        (18, 18),
    ],
)
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_sensor_restores_after_state_changes(
    hass: HomeAssistant,
    sensor_state,
    sensor_value,
    setup_comp_heat_cool_safety_delay,  # noqa: F811
) -> None:
    # GIVEN: Sensor at specific value, HEAT_COOL mode with range 22-25
    temp_high = 25
    temp_low = 22

    setup_sensor(hass, sensor_value)
    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await common.async_set_temperature_range(hass, common.ENTITY, temp_high, temp_low)
    calls = setup_switch_dual(  # noqa: F841
        hass, common.ENT_COOLER, sensor_value < temp_low, sensor_value > temp_high
    )
    await hass.async_block_till_done()

    hass.states.async_set(common.ENT_SENSOR, sensor_state)
    await hass.async_block_till_done()

    # WHEN: Sensor unavailable/unknown for 3 minutes
    common.async_fire_time_changed(
        hass, dt_util.utcnow() + datetime.timedelta(minutes=3)
    )
    await hass.async_block_till_done()

    # THEN: HVAC action reason shows sensor stalled
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReasonInternal.TEMPERATURE_SENSOR_STALLED
    )

    # WHEN: Sensor state changes to valid value
    hass.states.async_set(common.ENT_SENSOR, 31)
    await hass.async_block_till_done()

    # THEN: Sensor stalled reason is cleared
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        is not HVACActionReason.TEMPERATURE_SENSOR_STALLED
    )


@pytest.mark.parametrize(
    ("preset", "temperature"),
    [
        (PRESET_NONE, 23),
        (PRESET_AWAY, 16),
        (PRESET_COMFORT, 20),
        (PRESET_ECO, 18),
        (PRESET_HOME, 19),
        (PRESET_SLEEP, 17),
        (PRESET_ACTIVITY, 21),
        (PRESET_ANTI_FREEZE, 5),
    ],
)
async def test_dual_set_preset_mode_set_temp_keeps_preset_mode(
    hass: HomeAssistant, setup_comp_dual_presets, preset, temperature  # noqa: F811
) -> None:
    """Test the setting preset mode then set temperature.

    Verify preset mode preserved while temperature updated.
    """
    # GIVEN: Temperature at 23
    test_target_temp = 33
    await common.async_set_temperature(hass, 23)

    # WHEN: Setting preset mode
    await common.async_set_preset_mode(hass, preset)
    await hass.async_block_till_done()

    # THEN: Temperature matches preset value
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == temperature

    # WHEN: Manually setting temperature to 33
    await common.async_set_temperature(
        hass,
        test_target_temp,
    )

    # THEN: Temperature updated but preset mode preserved
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == test_target_temp
    assert state.attributes.get("preset_mode") == preset
    assert state.attributes.get("supported_features") == 401

    # WHEN: Returning to PRESET_NONE
    await common.async_set_preset_mode(hass, PRESET_NONE)

    # THEN: Original or manually set temperature is restored
    state = hass.states.get(common.ENTITY)
    if preset == PRESET_NONE:
        assert state.attributes.get("temperature") == test_target_temp
    else:
        assert state.attributes.get("temperature") == 23


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
async def test_heat_cool_set_preset_mode_set_temp_keeps_preset_mode(
    hass: HomeAssistant,
    setup_comp_heat_cool_presets,  # noqa: F811
    preset,
    temp_low,
    temp_high,
) -> None:
    """Test the setting preset mode then set temperature.

    Verify preset mode preserved while temperature updated.
    """
    # GIVEN: Temperature range set to 18-22
    test_target_temp_low = 7
    test_target_temp_high = 33
    await common.async_set_temperature_range(hass, common.ENTITY, 22, 18)
    await hass.async_block_till_done()

    # WHEN: Setting preset mode
    await common.async_set_preset_mode(hass, preset)

    # THEN: Temperature range matches preset values
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == temp_low
    assert state.attributes.get("target_temp_high") == temp_high

    # WHEN: Manually setting temperature range to 7-33
    await common.async_set_temperature_range(
        hass,
        common.ENTITY,
        test_target_temp_high,
        test_target_temp_low,
    )

    # THEN: Range updated but preset mode preserved
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == test_target_temp_low
    assert state.attributes.get("target_temp_high") == test_target_temp_high
    assert state.attributes.get("preset_mode") == preset
    assert state.attributes.get("supported_features") == 402

    # WHEN: Returning to PRESET_NONE
    await common.async_set_preset_mode(hass, PRESET_NONE)

    # THEN: Original or manually set range is restored
    state = hass.states.get(common.ENTITY)
    if preset == PRESET_NONE:
        assert state.attributes.get("target_temp_low") == test_target_temp_low
        assert state.attributes.get("target_temp_high") == test_target_temp_high
    else:
        assert state.attributes.get("target_temp_low") == 18
        assert state.attributes.get("target_temp_high") == 22


@pytest.mark.parametrize(
    ("preset", "hvac_mode", "temp"),
    [
        (PRESET_AWAY, HVACMode.HEAT, 16),
        (PRESET_AWAY, HVACMode.COOL, 30),
        (PRESET_COMFORT, HVACMode.HEAT, 20),
        (PRESET_COMFORT, HVACMode.COOL, 27),
        (PRESET_ECO, HVACMode.HEAT, 18),
        (PRESET_ECO, HVACMode.COOL, 29),
        (PRESET_HOME, HVACMode.HEAT, 19),
        (PRESET_HOME, HVACMode.COOL, 23),
        (PRESET_SLEEP, HVACMode.HEAT, 17),
        (PRESET_SLEEP, HVACMode.COOL, 24),
        (PRESET_ACTIVITY, HVACMode.HEAT, 21),
        (PRESET_ACTIVITY, HVACMode.COOL, 28),
        (PRESET_ANTI_FREEZE, HVACMode.HEAT, 5),
        (PRESET_ANTI_FREEZE, HVACMode.COOL, 32),
    ],
)
async def test_heat_cool_set_preset_mode_in_non_range_mode(
    hass: HomeAssistant,
    setup_comp_heat_cool_presets_range_only,  # noqa: F811
    preset,
    hvac_mode,
    temp,
) -> None:
    """Test the setting range preset mode while in target hvac mode"""
    # GIVEN: Heat cool setup with range-only presets

    # WHEN: Setting HVAC mode and applying preset
    await common.async_set_hvac_mode(hass, hvac_mode)
    await hass.async_block_till_done()

    await common.async_set_preset_mode(hass, preset)
    await hass.async_block_till_done()

    # THEN: Preset is applied with correct single temperature for the HVAC mode
    state = hass.states.get(common.ENTITY)
    assert state.state == hvac_mode
    assert state.attributes.get("preset_mode") == preset
    assert state.attributes.get("temperature") == temp


@pytest.mark.parametrize(
    ("preset", "temp_low", "temp_high"),
    [
        (PRESET_NONE, 7, 35),
        (PRESET_AWAY, 16, 30),
        (PRESET_COMFORT, 20, 27),
        (PRESET_ECO, 18, 29),
        (PRESET_HOME, 19, 23),
        (PRESET_SLEEP, 17, 24),
        (PRESET_ACTIVITY, 21, 28),
        (PRESET_ANTI_FREEZE, 5, 32),
    ],
)
async def test_heat_cool_set_preset_mode_auto_target_temps_if_range_only_presets(
    hass: HomeAssistant,
    setup_comp_heat_cool_presets_range_only,  # noqa: F811
    preset,
    temp_low,
    temp_high,
) -> None:
    """Test the setting preset mode across hvac_modes using range-only preset values.

    Verify preset target temperatures are pcked up while switching hvac_modes.
    """
    # GIVEN: Heat cool setup with range-only presets

    # WHEN: Setting HEAT_COOL mode and applying preset
    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await common.async_set_preset_mode(hass, preset)
    await hass.async_block_till_done()

    # THEN: Preset temperatures are applied as range
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == temp_low
    assert state.attributes.get("target_temp_high") == temp_high

    # WHEN: Switching to HEAT mode
    await common.async_set_hvac_mode(hass, HVACMode.HEAT)
    await hass.async_block_till_done()

    # THEN: Low target is used as single temperature
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == temp_low

    # WHEN: Switching to COOL mode
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    await hass.async_block_till_done()

    # THEN: High target is used as single temperature
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == temp_high

    # WHEN: Switching back to HEAT_COOL mode
    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await hass.async_block_till_done()

    # THEN: Range temperatures are restored
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
async def test_heat_cool_fan_set_preset_mode_set_temp_keeps_preset_mode(
    hass: HomeAssistant,
    setup_comp_heat_cool_fan_presets,  # noqa: F811
    preset,
    temp_low,
    temp_high,
) -> None:
    """Test the setting preset mode then set temperature.

    Verify preset mode preserved while temperature updated.
    """
    # GIVEN: Heat cool fan setup with presets
    test_target_temp_low = 7
    test_target_temp_high = 33

    # WHEN: Setting initial temperature range and applying preset
    await common.async_set_temperature_range(hass, common.ENTITY, 22, 18)
    await common.async_set_preset_mode(hass, preset)

    # THEN: Preset temperatures are applied
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == temp_low
    assert state.attributes.get("target_temp_high") == temp_high

    # WHEN: Manually setting new temperature range while preset is active
    await common.async_set_temperature_range(
        hass,
        common.ENTITY,
        test_target_temp_high,
        test_target_temp_low,
    )

    # THEN: Temperature is updated but preset mode is preserved
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == test_target_temp_low
    assert state.attributes.get("target_temp_high") == test_target_temp_high
    assert state.attributes.get("preset_mode") == preset
    assert state.attributes.get("supported_features") == 402

    # WHEN: Switching back to PRESET_NONE
    await common.async_set_preset_mode(hass, PRESET_NONE)

    # THEN: Behavior depends on whether we were already in PRESET_NONE
    state = hass.states.get(common.ENTITY)
    if preset == PRESET_NONE:
        assert state.attributes.get("target_temp_low") == test_target_temp_low
        assert state.attributes.get("target_temp_high") == test_target_temp_high
    else:
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
async def test_heat_cool_fan_set_preset_mode_change_hvac_mode(
    hass: HomeAssistant,
    setup_comp_heat_cool_fan_presets,  # noqa: F811
    preset,
    temp_low,
    temp_high,
) -> None:
    """Test the setting preset mode then set temperature.

    Verify preset mode preserved while temperature updated.
    """
    # GIVEN: Heat cool fan setup with presets

    # WHEN: Setting temperature range and applying preset
    await common.async_set_temperature_range(hass, common.ENTITY, 22, 18)
    await common.async_set_preset_mode(hass, preset)

    # THEN: Preset temperatures are applied as range
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TARGET_TEMP_LOW) == temp_low
    assert state.attributes.get(ATTR_TARGET_TEMP_HIGH) == temp_high

    # WHEN: Switching to HEAT mode
    await common.async_set_hvac_mode(hass, HVACMode.HEAT)
    await hass.async_block_till_done()

    # THEN: Preset is preserved and low temperature is used
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_PRESET_MODE) == preset
    assert state.attributes.get(ATTR_TEMPERATURE) == temp_low
    assert state.attributes.get(ATTR_TARGET_TEMP_LOW) is None
    assert state.attributes.get(ATTR_TARGET_TEMP_HIGH) is None

    # WHEN: Switching to COOL mode
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    await hass.async_block_till_done()

    # THEN: Preset is preserved and high temperature is used
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_PRESET_MODE) == preset
    assert state.attributes.get(ATTR_TEMPERATURE) == temp_high
    assert state.attributes.get(ATTR_TARGET_TEMP_LOW) is None
    assert state.attributes.get(ATTR_TARGET_TEMP_HIGH) is None

    # WHEN: Switching to FAN_ONLY mode
    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
    await hass.async_block_till_done()

    # THEN: Preset is preserved and last temperature is retained
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_PRESET_MODE) == preset
    assert state.attributes.get(ATTR_TEMPERATURE) == temp_high
    assert state.attributes.get(ATTR_TARGET_TEMP_LOW) is None
    assert state.attributes.get(ATTR_TARGET_TEMP_HIGH) is None


###################
# HVAC OPERATIONS #
###################


@pytest.mark.parametrize(
    ["from_hvac_mode", "to_hvac_mode"],
    [
        [HVACMode.OFF, HVACMode.HEAT],
        [HVACMode.COOL, HVACMode.OFF],
        [HVACMode.HEAT, HVACMode.OFF],
    ],
)
async def test_dual_toggle(
    hass: HomeAssistant, from_hvac_mode, to_hvac_mode, setup_comp_dual  # noqa: F811
) -> None:
    """Test change mode toggle."""
    # GIVEN: Dual mode setup with initial HVAC mode
    await common.async_set_hvac_mode(hass, from_hvac_mode)

    # WHEN: Toggling the thermostat
    await common.async_toggle(hass)
    await hass.async_block_till_done()

    # THEN: Mode changes to target mode
    state = hass.states.get(common.ENTITY)
    assert state.state == to_hvac_mode

    # WHEN: Toggling again
    await common.async_toggle(hass)
    await hass.async_block_till_done()

    # THEN: Mode returns to original
    state = hass.states.get(common.ENTITY)
    assert state.state == from_hvac_mode


@pytest.mark.parametrize(
    ["from_hvac_mode", "to_hvac_mode"],
    [
        [HVACMode.OFF, HVACMode.HEAT_COOL],
        [HVACMode.COOL, HVACMode.OFF],
        [HVACMode.HEAT, HVACMode.OFF],
    ],
)
async def test_heat_cool_toggle(
    hass: HomeAssistant,
    from_hvac_mode,
    to_hvac_mode,
    setup_comp_heat_cool_1,  # noqa: F811
) -> None:
    """Test change mode from OFF to COOL.

    Switch turns on when temp below setpoint and mode changes.
    """
    # GIVEN: Heat cool mode setup with initial HVAC mode
    await common.async_set_hvac_mode(hass, from_hvac_mode)

    # WHEN: Toggling the thermostat
    await common.async_toggle(hass)
    await hass.async_block_till_done()

    # THEN: Mode changes to target mode
    state = hass.states.get(common.ENTITY)
    assert state.state == to_hvac_mode

    # WHEN: Toggling again
    await common.async_toggle(hass)
    await hass.async_block_till_done()

    # THEN: Mode returns to original
    state = hass.states.get(common.ENTITY)
    assert state.state == from_hvac_mode


@pytest.mark.parametrize(
    ["from_hvac_mode", "to_hvac_mode"],
    [
        [HVACMode.OFF, HVACMode.COOL],
        [HVACMode.COOL, HVACMode.OFF],
        [HVACMode.FAN_ONLY, HVACMode.OFF],
        [HVACMode.HEAT, HVACMode.OFF],
    ],
)
async def test_dual_toggle_with_fan(
    hass: HomeAssistant,
    from_hvac_mode,
    to_hvac_mode,
    setup_comp_dual_fan_config,  # noqa: F811
) -> None:
    """Test change mode from OFF to COOL.

    Switch turns on when temp below setpoint and mode changes.
    """
    # GIVEN: Dual mode with fan configured and initial HVAC mode
    await common.async_set_hvac_mode(hass, from_hvac_mode)

    # WHEN: Toggling the thermostat
    await common.async_toggle(hass)
    await hass.async_block_till_done()

    # THEN: Mode changes to target mode
    state = hass.states.get(common.ENTITY)
    assert state.state == to_hvac_mode

    # WHEN: Toggling again
    await common.async_toggle(hass)
    await hass.async_block_till_done()

    # THEN: Mode returns to original
    state = hass.states.get(common.ENTITY)
    assert state.state == from_hvac_mode


@pytest.mark.parametrize(
    ["from_hvac_mode", "to_hvac_mode"],
    [
        [HVACMode.OFF, HVACMode.HEAT_COOL],
        [HVACMode.HEAT_COOL, HVACMode.OFF],
        [HVACMode.COOL, HVACMode.OFF],
        [HVACMode.FAN_ONLY, HVACMode.OFF],
        [HVACMode.HEAT, HVACMode.OFF],
    ],
)
async def test_heat_cool_toggle_with_fan(
    hass: HomeAssistant,
    from_hvac_mode,
    to_hvac_mode,
    setup_comp_heat_cool_fan_config,  # noqa: F811
) -> None:
    """Test change mode from OFF to COOL.

    Switch turns on when temp below setpoint and mode changes.
    """
    # GIVEN: Heat cool mode with fan configured and initial HVAC mode
    await common.async_set_hvac_mode(hass, from_hvac_mode)

    # WHEN: Toggling the thermostat
    await common.async_toggle(hass)
    await hass.async_block_till_done()

    # THEN: Mode changes to target mode
    state = hass.states.get(common.ENTITY)
    assert state.state == to_hvac_mode

    # WHEN: Toggling again
    await common.async_toggle(hass)
    await hass.async_block_till_done()

    # THEN: Mode returns to original
    state = hass.states.get(common.ENTITY)
    assert state.state == from_hvac_mode


async def test_hvac_mode_mode_heat_cool(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler switch in heat/cool mode."""
    # GIVEN: Heat cool mode setup with heater and cooler switches
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

    # THEN: All HVAC modes are available
    hvac_modes = hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_MODES)
    assert HVACMode.HEAT in hvac_modes
    assert HVACMode.COOL in hvac_modes
    assert HVACMode.HEAT_COOL in hvac_modes
    assert HVACMode.OFF in hvac_modes

    state = hass.states.get(common.ENTITY)
    assert state.attributes["supported_features"] == 386

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Setting HEAT_COOL mode with temp range 22-25 and temp at 26
    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await common.async_set_temperature_range(hass, ENTITY_MATCH_ALL, 25, 22)
    setup_sensor(hass, 26)
    await hass.async_block_till_done()

    # THEN: Cooler activates because temp is above range
    state = hass.states.get(common.ENTITY)
    assert state.attributes["supported_features"] == 386

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    # WHEN: Temperature drops to 24 (within range)
    setup_sensor(hass, 24)
    await hass.async_block_till_done()

    # THEN: Both heater and cooler are off
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Temperature drops to 18 (below range)
    setup_sensor(hass, 18)
    await hass.async_block_till_done()

    # THEN: Heater activates
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Switching to HEAT mode with target temp 25
    await common.async_set_hvac_mode(hass, HVACMode.HEAT)
    await common.async_set_temperature(hass, 25, ENTITY_MATCH_ALL)
    await hass.async_block_till_done()

    # THEN: Supported features change for single temp mode
    state = hass.states.get(common.ENTITY)
    assert state.attributes["supported_features"] == 385

    # WHEN: Temperature is at 20 (below target)
    setup_sensor(hass, 20)
    await hass.async_block_till_done()

    # THEN: Heater is on
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Temperature rises to 26 (above target)
    setup_sensor(hass, 26)
    await hass.async_block_till_done()

    # THEN: Heater is off
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Temperature drops back to 20
    setup_sensor(hass, 20)
    await hass.async_block_till_done()

    # THEN: Heater activates again
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Switching to COOL mode
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    await hass.async_block_till_done()

    # THEN: Heater turns off and features are for single temp mode
    assert hass.states.get(heater_switch).state == STATE_OFF
    state = hass.states.get(common.ENTITY)
    assert state.attributes["supported_features"] == 385

    # WHEN: Switching back to HEAT_COOL mode
    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await hass.async_block_till_done()

    # THEN: Features change back to range mode
    state = hass.states.get(common.ENTITY)
    assert state.attributes["supported_features"] == 386


@pytest.mark.parametrize(
    "hvac_mode",
    [
        HVACMode.HEAT_COOL,
        HVACMode.COOL,
    ],
)
async def test_hvac_mode_mode_heat_cool_fan_tolerance(
    hass: HomeAssistant, hvac_mode, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler switch in heat/cool mode."""
    # GIVEN: Setup with fan and separate tolerances (hot: 0.2, fan_hot: 0.5)
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    fan_switch = "input_boolean.fan"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None, "fan": None}},
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
                "fan": fan_switch,
                "hot_tolerance": 0.2,
                "cold_tolerance": 0.2,
                "fan_hot_tolerance": 0.5,
                "heat_cool_mode": True,
                "target_sensor": common.ENT_SENSOR,
            }
        },
    )
    await hass.async_block_till_done()

    # WHEN: Setting HVAC mode and target temperature
    await common.async_set_hvac_mode(hass, hvac_mode)
    state = hass.states.get(common.ENTITY)
    supports_temperature_range = (
        state.attributes.get("supported_features")
        & ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
    )

    if supports_temperature_range:
        await common.async_set_temperature_range(hass, ENTITY_MATCH_ALL, 20, 18)
    else:
        await common.async_set_temperature(hass, 20, ENTITY_MATCH_ALL)

    setup_sensor(hass, 20)
    await hass.async_block_till_done()

    # THEN: At target temp, all devices are off
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    # WHEN: Temperature rises past hot tolerance (20.2)
    setup_sensor(hass, 20.2)
    await hass.async_block_till_done()

    # THEN: Fan activates first (within fan_hot_tolerance)
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_ON

    # WHEN: Temperature rises further (20.5, still within fan zone)
    setup_sensor(hass, 20.5)
    await hass.async_block_till_done()

    # THEN: Only fan remains on
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_ON

    # WHEN: Temperature at 20.7 (still within fan zone)
    setup_sensor(hass, 20.7)
    await hass.async_block_till_done()

    # THEN: Only fan remains on
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_ON

    # WHEN: Temperature exceeds fan_hot_tolerance (20.8)
    setup_sensor(hass, 20.8)
    await hass.async_block_till_done()

    # THEN: Cooler activates and fan turns off
    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF


@pytest.mark.parametrize(
    "hvac_mode",
    [
        HVACMode.HEAT_COOL,
        HVACMode.COOL,
    ],
)
async def test_hvac_mode_mode_heat_cool_ignore_fan_tolerance(
    hass: HomeAssistant, hvac_mode, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler switch in heat/cool mode."""
    # GIVEN: Setup with fan, fan_air_outside enabled, outside temp warmer than inside
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    fan_switch = "input_boolean.fan"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None, "fan": None}},
    )

    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1},
                "outside_temp": {
                    "name": "test",
                    "initial": 10,
                    "min": 0,
                    "max": 40,
                    "step": 1,
                },
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
                "fan": fan_switch,
                "hot_tolerance": 0.2,
                "cold_tolerance": 0.2,
                "fan_hot_tolerance": 0.5,
                "fan_air_outside": True,
                "heat_cool_mode": True,
                "target_sensor": common.ENT_SENSOR,
                "outside_sensor": common.ENT_OUTSIDE_SENSOR,
            }
        },
    )
    await hass.async_block_till_done()

    # WHEN: Setting HVAC mode and target temperature with outside warmer
    await common.async_set_hvac_mode(hass, hvac_mode)

    supports_temperature_range = (
        hass.states.get(common.ENTITY).attributes.get("supported_features")
        & ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
    )
    if supports_temperature_range:
        await common.async_set_temperature_range(hass, ENTITY_MATCH_ALL, 20, 18)
    else:
        await common.async_set_temperature(hass, 20, ENTITY_MATCH_ALL)

    setup_sensor(hass, 20)
    setup_outside_sensor(hass, 21)
    await hass.async_block_till_done()

    # THEN: At target temp, all devices are off
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    # WHEN: Temperature rises past hot_tolerance (20.2)
    setup_sensor(hass, 20.2)
    await hass.async_block_till_done()

    # THEN: Cooler activates immediately (fan ignored because outside is warmer)
    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    # WHEN: Temperature rises to 20.5
    setup_sensor(hass, 20.5)
    await hass.async_block_till_done()

    # THEN: Cooler remains on
    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    # WHEN: Temperature rises to 20.7
    setup_sensor(hass, 20.7)
    await hass.async_block_till_done()

    # THEN: Cooler remains on
    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    # WHEN: Temperature rises to 20.8
    setup_sensor(hass, 20.8)
    await hass.async_block_till_done()

    # THEN: Cooler remains on
    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF


@pytest.mark.parametrize(
    "hvac_mode",
    [
        HVACMode.HEAT_COOL,
        HVACMode.COOL,
    ],
)
async def test_hvac_mode_mode_heat_cool_dont_ignore_fan_tolerance(
    hass: HomeAssistant, hvac_mode, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler switch in heat/cool mode."""
    # GIVEN: Setup with fan, fan_air_outside enabled, outside temp cooler than inside
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    fan_switch = "input_boolean.fan"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None, "fan": None}},
    )

    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1},
                "outside_temp": {
                    "name": "test",
                    "initial": 10,
                    "min": 0,
                    "max": 40,
                    "step": 1,
                },
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
                "fan": fan_switch,
                "hot_tolerance": 0.2,
                "cold_tolerance": 0.2,
                "fan_hot_tolerance": 0.5,
                "fan_air_outside": True,
                "heat_cool_mode": True,
                "target_sensor": common.ENT_SENSOR,
                "outside_sensor": common.ENT_OUTSIDE_SENSOR,
            }
        },
    )
    await hass.async_block_till_done()

    # WHEN: Setting HVAC mode and target temperature with outside cooler
    await common.async_set_hvac_mode(hass, hvac_mode)

    supports_temperature_range = (
        hass.states.get(common.ENTITY).attributes.get("supported_features")
        & ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
    )
    if supports_temperature_range:
        await common.async_set_temperature_range(hass, ENTITY_MATCH_ALL, 20, 18)
    else:
        await common.async_set_temperature(hass, 20, ENTITY_MATCH_ALL)

    setup_sensor(hass, 20)
    setup_outside_sensor(hass, 18)
    await hass.async_block_till_done()

    # THEN: At target temp, all devices are off
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    # WHEN: Temperature rises past hot_tolerance (20.2)
    setup_sensor(hass, 20.2)
    await hass.async_block_till_done()

    # THEN: Fan activates (outside air is cooler, fan can help)
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_ON

    # WHEN: Temperature rises to 20.5
    setup_sensor(hass, 20.5)
    await hass.async_block_till_done()

    # THEN: Fan remains on
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_ON

    # WHEN: Temperature rises to 20.7
    setup_sensor(hass, 20.7)
    await hass.async_block_till_done()

    # THEN: Fan remains on
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_ON

    # WHEN: Temperature exceeds fan_hot_tolerance (20.8)
    setup_sensor(hass, 20.8)
    await hass.async_block_till_done()

    # THEN: Cooler activates and fan turns off
    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF


@pytest.mark.parametrize(
    "hvac_mode",
    [
        HVACMode.HEAT_COOL,
        # HVACMode.COOL,
    ],
)
async def test_hvac_mode_mode_heat_cool_fan_tolerance_with_floor_sensor(
    hass: HomeAssistant, hvac_mode, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler switch in heat/cool mode."""
    # GIVEN: Setup with fan, floor sensor, and floor temp above max (27 > 26)
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    fan_switch = "input_boolean.fan"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None, "fan": None}},
    )

    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1},
                "floor_temp": {
                    "name": "floor_temp",
                    "initial": 10,
                    "min": 10,
                    "max": 40,
                    "step": 1,
                },
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
                "fan": fan_switch,
                "hot_tolerance": 0.2,
                "cold_tolerance": 0.2,
                "fan_hot_tolerance": 0.5,
                "heat_cool_mode": True,
                "target_sensor": common.ENT_SENSOR,
                "floor_sensor": common.ENT_FLOOR_SENSOR,
                "max_floor_temp": 26,
                "min_floor_temp": 9,
            }
        },
    )
    await hass.async_block_till_done()

    # WHEN: Setting HVAC mode with floor temp above max
    await common.async_set_hvac_mode(hass, hvac_mode)
    await common.async_set_temperature_range(hass, ENTITY_MATCH_ALL, 20, 18)
    setup_sensor(hass, 20)
    setup_floor_sensor(hass, 27)
    await hass.async_block_till_done()

    # THEN: At target temp, all devices are off (floor temp high but within tolerance)
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    # WHEN: Temperature rises past hot_tolerance (20.2)
    setup_sensor(hass, 20.2)
    await hass.async_block_till_done()

    # THEN: Fan activates first
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_ON

    # WHEN: Temperature rises to 20.5
    setup_sensor(hass, 20.5)
    await hass.async_block_till_done()

    # THEN: Fan remains on
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_ON

    # WHEN: Temperature rises to 20.7
    setup_sensor(hass, 20.7)
    await hass.async_block_till_done()

    # THEN: Fan remains on
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_ON

    # WHEN: Temperature exceeds fan_hot_tolerance (20.8)
    setup_sensor(hass, 20.8)
    await hass.async_block_till_done()

    # THEN: Cooler activates and fan turns off
    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF


async def test_hvac_mode_mode_heat_cool_hvac_modes_temps(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler switch in heat/cool mode."""
    # GIVEN: Heat cool mode setup
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

    # THEN: Initial state is set up correctly
    state = hass.states.get(common.ENTITY)
    assert state.attributes["supported_features"] == 386

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Setting HEAT_COOL mode with temp range 22-25
    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await common.async_set_temperature_range(hass, ENTITY_MATCH_ALL, 25, 22)
    await hass.async_block_till_done()

    # THEN: Temperature range is set, no single temperature
    state = hass.states.get(common.ENTITY)
    assert state.attributes["target_temp_low"] == 22
    assert state.attributes["target_temp_high"] == 25
    assert state.attributes.get("temperature") is None

    # WHEN: Switching to HEAT mode with single temp 24
    await common.async_set_hvac_mode(hass, HVACMode.HEAT)
    await common.async_set_temperature(hass, 24)
    await hass.async_block_till_done()

    # THEN: Single temperature is set, no range
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") is None
    assert state.attributes.get("target_temp_high") is None
    assert state.attributes.get("temperature") == 24

    # WHEN: Switching to COOL mode with single temp 26
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    await common.async_set_temperature(hass, 26)
    await hass.async_block_till_done()

    # THEN: Single temperature is set, no range
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") is None
    assert state.attributes.get("target_temp_high") is None
    assert state.attributes.get("temperature") == 26

    # WHEN: Switching back to HEAT_COOL mode
    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await hass.async_block_till_done()

    # THEN: Range is reconstructed from individual mode temperatures
    state = hass.states.get(common.ENTITY)
    assert state.attributes["target_temp_low"] == 24
    assert state.attributes["target_temp_high"] == 26
    assert state.attributes.get("temperature") is None


async def test_hvac_mode_mode_heat_cool_hvac_modes_temps_avoid_unrealism(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler switch in heat/cool mode."""
    # GIVEN: Heat cool mode setup
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

    # THEN: Initial state is set up correctly
    state = hass.states.get(common.ENTITY)
    assert state.attributes["supported_features"] == 386

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Setting HEAT_COOL mode with temp range 22-25
    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await common.async_set_temperature_range(hass, ENTITY_MATCH_ALL, 25, 22)
    await hass.async_block_till_done()

    # THEN: Temperature range is set
    state = hass.states.get(common.ENTITY)
    assert state.attributes["target_temp_low"] == 22
    assert state.attributes["target_temp_high"] == 25
    assert state.attributes.get("temperature") is None

    # WHEN: Switching to HEAT mode with temp 26 (higher than cool temp)
    await common.async_set_hvac_mode(hass, HVACMode.HEAT)
    await common.async_set_temperature(hass, 26)
    await hass.async_block_till_done()

    # THEN: Temperature is set
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 26

    # WHEN: Switching to COOL mode with temp 21 (lower than heat temp - unrealistic)
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    await common.async_set_temperature(hass, 21)
    await hass.async_block_till_done()

    # THEN: Temperature is set
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 21

    # WHEN: Switching back to HEAT_COOL mode with inverted temps
    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await hass.async_block_till_done()

    # THEN: Range is adjusted to avoid unrealistic values (cool > heat)
    state = hass.states.get(common.ENTITY)
    assert state.attributes["target_temp_low"] == 20  # temp_high - precision
    assert state.attributes["target_temp_high"] == 21  # temp_low + precision


async def test_hvac_mode_mode_heat_cool_hvac_modes_temps_picks_range_values(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
):
    """Test thermostat target tempreratures get from range mode

    when switched from heat-cool mode to heat or cool mode"""
    # GIVEN: Heat cool mode setup
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

    # THEN: Initial state is set up correctly
    state = hass.states.get(common.ENTITY)
    assert state.attributes["supported_features"] == 386

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Setting HEAT_COOL mode with temp range 22-25
    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await common.async_set_temperature_range(hass, ENTITY_MATCH_ALL, 25, 22)
    await hass.async_block_till_done()

    # THEN: Temperature range is set
    state = hass.states.get(common.ENTITY)
    assert state.attributes["target_temp_low"] == 22
    assert state.attributes["target_temp_high"] == 25
    assert state.attributes.get("temperature") is None

    # WHEN: Switching to HEAT mode without setting temp
    await common.async_set_hvac_mode(hass, HVACMode.HEAT)
    await hass.async_block_till_done()

    # THEN: Temperature is picked from low range value
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 22

    # WHEN: Switching to COOL mode without setting temp
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    await hass.async_block_till_done()

    # THEN: Temperature is picked from high range value
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 25


async def test_hvac_mode_heat_cool_floor_temp(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler switch in heat/cool mode. with floor temp caps"""
    # GIVEN: Heat cool mode setup with floor sensor (min: 5, max: 28)
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

    # THEN: All HVAC modes are available
    hvac_modes = hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_MODES)
    assert HVACMode.HEAT in hvac_modes
    assert HVACMode.COOL in hvac_modes
    assert HVACMode.HEAT_COOL in hvac_modes
    assert HVACMode.OFF in hvac_modes

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Setting HEAT_COOL mode with temp 26 (above range), floor 10 (within limits)
    setup_sensor(hass, 26)
    setup_floor_sensor(hass, 10)
    await hass.async_block_till_done()

    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await common.async_set_temperature_range(hass, ENTITY_MATCH_ALL, 25, 22)
    await hass.async_block_till_done()

    # THEN: Cooler activates due to high temp
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    # WHEN: Temperature drops to within range (24)
    setup_sensor(hass, 24)
    await hass.async_block_till_done()

    # THEN: Both devices are off
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Floor temp drops below min (4 < 5)
    setup_floor_sensor(hass, 4)
    await hass.async_block_till_done()

    # THEN: Heater activates to protect floor
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Floor temp rises above min (10 > 5)
    setup_floor_sensor(hass, 10)
    setup_sensor(hass, 24)
    await hass.async_block_till_done()

    # THEN: Heater turns off
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Room temp drops below range (18 < 22)
    setup_sensor(hass, 18)
    await hass.async_block_till_done()

    # THEN: Heater activates
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Room temp rises back to within range
    setup_sensor(hass, 24)
    await hass.async_block_till_done()

    # THEN: Heater turns off
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_hvac_mode_mode_heat_cool_aux_heat(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler switch in heat/cool mode."""
    # GIVEN: Heat cool mode setup with aux heater (timeout: 10s)
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    secondary_heater_switch = "input_boolean.aux_heater"
    secondaty_heater_timeout = 10
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "aux_heater": None, "cooler": None}},
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
                "secondary_heater": secondary_heater_switch,
                "secondary_heater_timeout": {"seconds": secondaty_heater_timeout},
                "heat_cool_mode": True,
                "target_sensor": common.ENT_SENSOR,
            }
        },
    )
    await hass.async_block_till_done()

    # THEN: All HVAC modes are available
    hvac_modes = hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_MODES)
    assert HVACMode.HEAT in hvac_modes
    assert HVACMode.COOL in hvac_modes
    assert HVACMode.HEAT_COOL in hvac_modes
    assert HVACMode.OFF in hvac_modes

    state = hass.states.get(common.ENTITY)
    assert state.attributes["supported_features"] == 386

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(secondary_heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Setting HEAT_COOL mode with temp above range (26 > 25)
    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await common.async_set_temperature_range(hass, ENTITY_MATCH_ALL, 25, 22)
    setup_sensor(hass, 26)
    await hass.async_block_till_done()

    # THEN: Cooler activates
    state = hass.states.get(common.ENTITY)
    assert state.attributes["supported_features"] == 386

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(secondary_heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    # WHEN: Temperature drops to within range
    setup_sensor(hass, 24)
    await hass.async_block_till_done()

    # THEN: All devices are off
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(secondary_heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Temperature drops below range (18 < 22)
    setup_sensor(hass, 18)
    await hass.async_block_till_done()

    # THEN: Primary heater activates
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(secondary_heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Switching to HEAT mode with target 25
    await common.async_set_hvac_mode(hass, HVACMode.HEAT)
    await common.async_set_temperature(hass, 25, ENTITY_MATCH_ALL)
    await hass.async_block_till_done()

    # THEN: Supported features change
    state = hass.states.get(common.ENTITY)
    assert state.attributes["supported_features"] == 385

    # WHEN: Temperature is at 20 (below target)
    setup_sensor(hass, 20)
    await hass.async_block_till_done()

    # THEN: Heater is on
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Temperature reaches target
    setup_sensor(hass, 26)
    await hass.async_block_till_done()

    # THEN: Heater turns off
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Temperature drops again and heater runs
    setup_sensor(hass, 20)
    await hass.async_block_till_done()

    # THEN: Heater is on
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Time passes but less than aux timeout (6s < 10s)
    freezer.tick(timedelta(seconds=secondaty_heater_timeout - 4))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # THEN: Only primary heater is still on
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(secondary_heater_switch).state == STATE_OFF

    # WHEN: Time exceeds aux heater timeout (15s > 10s)
    freezer.tick(timedelta(seconds=secondaty_heater_timeout + 5))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # THEN: Aux heater activates, primary turns off
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(secondary_heater_switch).state == STATE_ON

    # WHEN: Temperature reaches target
    setup_sensor(hass, 26)
    await hass.async_block_till_done()

    # THEN: Aux heater turns off
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(secondary_heater_switch).state == STATE_OFF

    # WHEN: Switching to COOL mode
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    await hass.async_block_till_done()

    # THEN: Heaters are off, features change
    assert hass.states.get(heater_switch).state == STATE_OFF
    state = hass.states.get(common.ENTITY)
    assert state.attributes["supported_features"] == 385

    # WHEN: Switching back to HEAT_COOL
    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await hass.async_block_till_done()

    # THEN: Features change back
    state = hass.states.get(common.ENTITY)
    assert state.attributes["supported_features"] == 386


# TODO: test handling setting only target temp without low and high


async def test_hvac_mode_cool(hass: HomeAssistant, setup_comp_1):  # noqa: F811
    """Test thermostat cooler switch in cooling mode."""
    # GIVEN: Heat cool mode setup starting in COOL mode
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
                "heat_cool_mode": True,
            }
        },
    )
    await hass.async_block_till_done()

    # THEN: Initially both devices are off
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Temperature is 23 and target is set to 18
    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()

    # THEN: Cooler activates (23 > 18)
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    # WHEN: Temperature drops to 17 (below target)
    setup_sensor(hass, 17)
    await hass.async_block_till_done()

    # THEN: Cooler turns off
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Temperature rises back to 23
    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    # THEN: Cooler activates again
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON


async def test_hvac_mode_cool_hvac_action_reason(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
):  # noqa: F811
    """Test thermostat sets hvac action reason after startup in cool mode."""
    # GIVEN: A thermostat with restored state in COOL mode with target temp 20°C and current temp 10°C
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

    common.mock_restore_cache(
        hass,
        (
            State(
                "climate.test",
                HVACMode.COOL,
                {ATTR_TEMPERATURE: "20"},
            ),
        ),
    )

    hass.set_state(CoreState.starting)

    # WHEN: Thermostat is set up and starts in COOL mode
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "heater": heater_switch,
                "cooler": cooler_switch,
                "target_sensor": "input_number.temp",
                "initial_hvac_mode": HVACMode.COOL,
                "heat_cool_mode": True,
            }
        },
    )
    await hass.async_block_till_done()

    # THEN: Both switches are off, mode is COOL, action is IDLE with TARGET_TEMP_REACHED reason
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).state == HVACMode.COOL
    assert (
        hass.states.get(common.ENTITY).attributes.get("hvac_action") == HVACAction.IDLE
    )
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReasonInternal.TARGET_TEMP_REACHED
    )


async def test_hvac_mode_heat_hvac_action_reason(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
):
    """Test thermostat sets hvac action reason after startup in heat mode."""
    # GIVEN: A thermostat with restored state in COOL mode with target temp 20°C and current temp 22°C
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
                "temp": {"name": "test", "initial": 22, "min": 0, "max": 40, "step": 1}
            }
        },
    )

    common.mock_restore_cache(
        hass,
        (
            State(
                "climate.test",
                HVACMode.COOL,
                {ATTR_TEMPERATURE: "20"},
            ),
        ),
    )

    hass.set_state(CoreState.starting)

    # WHEN: Thermostat is set up and starts in HEAT mode
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "heater": heater_switch,
                "cooler": cooler_switch,
                "target_sensor": "input_number.temp",
                "initial_hvac_mode": HVACMode.HEAT,
                "heat_cool_mode": True,
            }
        },
    )
    await hass.async_block_till_done()

    # THEN: Both switches are off, mode is HEAT, action is IDLE with TARGET_TEMP_REACHED reason
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).state == HVACMode.HEAT
    assert (
        hass.states.get(common.ENTITY).attributes.get("hvac_action") == HVACAction.IDLE
    )
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReasonInternal.TARGET_TEMP_REACHED
    )


@pytest.mark.parametrize(
    ["duration", "result_state"],
    [
        (timedelta(seconds=10), STATE_ON),
        (timedelta(seconds=30), STATE_OFF),
    ],
)
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_hvac_mode_cool_cycle(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    duration,
    result_state,
    setup_comp_1,  # noqa: F811
):
    """Test thermostat cooler switch in cooling mode with cycle duration."""
    # GIVEN: A thermostat in COOL mode with 15s min_cycle_duration, temp at 23°C, target at 18°C
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
                "heat_cool_mode": True,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    # WHEN: Temperature is set to 18°C triggering cooler ON
    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    # WHEN: Time advances by duration and temperature drops to 17°C
    freezer.tick(duration)
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    setup_sensor(hass, 17)
    await hass.async_block_till_done()

    # THEN: Cooler state depends on whether min_cycle_duration was met
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == result_state


@pytest.mark.parametrize(
    ["duration", "result_state"],
    [
        (timedelta(seconds=10), STATE_ON),
        (timedelta(seconds=30), STATE_OFF),
    ],
)
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_hvac_mode_heat_cycle(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    duration,
    result_state,
    setup_comp_1,  # noqa: F811
):
    """Test thermostat heater and cooler switch in heat mode with min_cycle_duration."""
    # GIVEN: A thermostat in HEAT_COOL mode with 15s min_cycle_duration, temp at 20°C, target range 22-25°C
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

    # WHEN: Temperature range is set to 22-25°C triggering heater ON
    await common.async_set_temperature(hass, None, ENTITY_MATCH_ALL, 25, 22)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Time advances by duration and temperature rises to 24°C
    freezer.tick(duration)
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    setup_sensor(hass, 24)
    await hass.async_block_till_done()

    # THEN: Heater state depends on whether min_cycle_duration was met
    assert hass.states.get(heater_switch).state == result_state
    assert hass.states.get(cooler_switch).state == STATE_OFF


@pytest.mark.parametrize(
    ["duration", "result_state"],
    [
        (timedelta(seconds=10), STATE_ON),
        (timedelta(seconds=30), STATE_OFF),
    ],
)
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_hvac_mode_heat_cool_cycle(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    duration,
    result_state,
    setup_comp_1,  # noqa: F811
):
    """Test thermostat heater and cooler switch in cool mode with min_cycle_duration."""
    # GIVEN: A thermostat in HEAT_COOL mode with 15s min_cycle_duration, temp at 26°C, target range 22-25°C
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

    # WHEN: Temperature range is set to 22-25°C triggering cooler ON
    await common.async_set_temperature(hass, None, ENTITY_MATCH_ALL, 25, 22)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    # WHEN: Time advances by duration and temperature drops to 24°C
    freezer.tick(duration)
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    setup_sensor(hass, 24)
    await hass.async_block_till_done()

    # THEN: Cooler state depends on whether min_cycle_duration was met
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == result_state


async def test_hvac_mode_heat_cool_switch_preset_modes(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler switch to heater only mode."""
    # GIVEN: A thermostat in HEAT_COOL mode with AWAY and HOME presets configured
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

    # THEN: Both switches should be off initially
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


async def test_hvac_mode_heat_cool_dry_mode(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
):
    """Test thermostat heatre, cooler and dryer mode"""
    # GIVEN: A thermostat with heater, cooler, and dryer in HEAT_COOL mode with humidity sensor
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    dryer_switch = "input_boolean.dryer"
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {
            "input_boolean": {"heater": None, "cooler": None, "dryer": None},
        },
    )

    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1},
                "humidity": {
                    "name": "test_humidity",
                    "initial": 50,
                    "min": 10,
                    "max": 99,
                    "step": 1,
                },
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
                "dryer": dryer_switch,
                "target_sensor": common.ENT_SENSOR,
                "humidity_sensor": common.ENT_HUMIDITY_SENSOR,
                "heat_cool_mode": True,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(dryer_switch).state == STATE_OFF

    setup_sensor(hass, 24)
    setup_humidity_sensor(hass, 60)
    await hass.async_block_till_done()

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    # WHEN: Temperature range is set to 10-18°C with temp at 23°C
    await common.async_set_temperature_range(hass, ENTITY_MATCH_ALL, 18, 10)
    await hass.async_block_till_done()

    # THEN: Cooler turns on to lower temperature
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    # WHEN: Temperature drops to 17°C (below range)
    setup_sensor(hass, 17)
    await hass.async_block_till_done()

    # THEN: Cooler turns off as temperature is now below target
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(dryer_switch).state == STATE_OFF

    # WHEN: Temperature rises back to 23°C
    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    # THEN: Cooler turns back on
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(dryer_switch).state == STATE_OFF

    # WHEN: Mode switched to DRY with target humidity 55% and current humidity 60%
    await common.async_set_hvac_mode(hass, HVACMode.DRY)
    await common.async_set_humidity(hass, 55)
    await hass.async_block_till_done()

    # THEN: Dryer turns on to reduce humidity
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(dryer_switch).state == STATE_ON
    assert (
        hass.states.get(common.ENTITY).attributes.get("hvac_action")
        == HVACAction.DRYING
    )

    # WHEN: Mode switched back to HEAT_COOL
    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await hass.async_block_till_done()

    # THEN: Dryer turns off and cooler resumes
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(dryer_switch).state == STATE_OFF


async def test_hvac_mode_heat_cool_tolerances(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler mode tolerances."""
    # GIVEN: A thermostat in HEAT_COOL mode with hot_tolerance=0.3, cold_tolerance=0.3, target range 22-25°C
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
    await common.async_set_temperature_range(hass, ENTITY_MATCH_ALL, 25, 22)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Temperature drops to 21.7°C (below 22°C - 0.3 cold_tolerance)
    setup_sensor(hass, 21.7)
    await hass.async_block_till_done()

    # THEN: Heater turns on
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Temperature rises to 22.1°C (still within heater hysteresis)
    setup_sensor(hass, 22.1)
    await hass.async_block_till_done()

    # THEN: Heater remains on
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Temperature rises to 22.3°C (above 22°C + 0.3 cold_tolerance)
    setup_sensor(hass, 22.3)
    await hass.async_block_till_done()

    # THEN: Heater turns off
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Temperature rises to 24.7°C (below 25°C + 0.3 hot_tolerance)
    # since both heater and cooler are off, we expect the cooler not
    # to turn on until the temperature is 0.3 degrees above the target
    setup_sensor(hass, 24.7)
    await hass.async_block_till_done()

    # THEN: Both remain off
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Temperature rises to 25.0°C (at target but below hot_tolerance threshold)
    setup_sensor(hass, 25.0)
    await hass.async_block_till_done()

    # THEN: Both remain off
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN: Temperature rises to 25.3°C (above 25°C + 0.3 hot_tolerance)
    setup_sensor(hass, 25.3)
    await hass.async_block_till_done()

    # THEN: Cooler turns on
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    # WHEN: Temperature drops to 25.0°C (still within cooler hysteresis)
    # since cooler is on we expect it keep on until reaches 0.3 degrees
    # below the target
    setup_sensor(hass, 25.0)
    await hass.async_block_till_done()

    # THEN: Cooler remains on
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    # WHEN: Temperature drops to 24.7°C (below 25°C - 0.3 hot_tolerance)
    setup_sensor(hass, 24.7)
    await hass.async_block_till_done()

    # THEN: Cooler turns off
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF


######################
# HVAC ACTION REASON #
######################


async def test_hvac_mode_heat_cool_floor_temp_hvac_action_reason(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler switch in heat/cool mode. with floor temp caps"""
    # GIVEN: A thermostat in HEAT_COOL mode with floor sensor and min_floor_temp=5, max_floor_temp=28
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

    # THEN: Initial HVAC action reason should be NONE
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.NONE
    )

    setup_sensor(hass, 26)
    setup_floor_sensor(hass, 10)
    await hass.async_block_till_done()

    # WHEN: Mode set to HEAT_COOL with target range 22-25°C and temp at 26°C
    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await common.async_set_temperature(hass, None, ENTITY_MATCH_ALL, 25, 22)
    await hass.async_block_till_done()

    # THEN: HVAC action reason should be TARGET_TEMP_NOT_REACHED (cooling needed)
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_TEMP_NOT_REACHED
    )

    # WHEN: Temperature drops to 24°C (within target range)
    setup_sensor(hass, 24)
    await hass.async_block_till_done()

    # THEN: HVAC action reason should be TARGET_TEMP_REACHED
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_TEMP_REACHED
    )

    # WHEN: Floor temp drops to 4°C (below min_floor_temp=5)
    setup_floor_sensor(hass, 4)
    await hass.async_block_till_done()

    # THEN: HVAC action reason should be LIMIT (floor protection activated)
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.LIMIT
    )

    # WHEN: Floor temp rises to 10°C (above min_floor_temp) and room temp at 24°C
    setup_floor_sensor(hass, 10)
    setup_sensor(hass, 24)
    await hass.async_block_till_done()

    # THEN: HVAC action reason should be TARGET_TEMP_REACHED (floor protection cleared)
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_TEMP_REACHED
    )

    setup_sensor(hass, 18)
    await hass.async_block_till_done()
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_TEMP_NOT_REACHED
    )


############
# OPENINGS #
############


@pytest.mark.parametrize(
    ["hvac_mode", "taget_temp", "oepning_scope", "switch_state", "cooler_state"],
    [
        ([HVACMode.HEAT, 24, ["all"], STATE_OFF, STATE_OFF]),
        ([HVACMode.HEAT, 24, [HVACMode.HEAT], STATE_OFF, STATE_OFF]),
        ([HVACMode.HEAT, 24, [HVACMode.COOL], STATE_ON, STATE_OFF]),
        ([HVACMode.COOL, 18, ["all"], STATE_OFF, STATE_OFF]),
        ([HVACMode.COOL, 18, [HVACMode.COOL], STATE_OFF, STATE_OFF]),
        ([HVACMode.COOL, 18, [HVACMode.HEAT], STATE_OFF, STATE_ON]),
    ],
)
async def test_heat_cool_mode_opening_scope(
    hass: HomeAssistant,
    hvac_mode,
    taget_temp,
    oepning_scope,
    switch_state,
    cooler_state,
    setup_comp_1,  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode."""
    # GIVEN: A thermostat with opening sensor and configurable opening_scope
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    opening_1 = "input_boolean.opening_1"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None, "opening_1": None}},
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
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cooler": cooler_switch,
                "heater": heater_switch,
                "heat_cool_mode": True,
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

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    # WHEN: Target temperature is set triggering appropriate switch
    await common.async_set_temperature(hass, taget_temp)
    await hass.async_block_till_done()

    # THEN: Appropriate switch turns on based on HVAC mode
    assert (
        hass.states.get(heater_switch).state == STATE_ON
        if hvac_mode == HVACMode.HEAT
        else STATE_OFF
    )

    assert (
        hass.states.get(cooler_switch).state == STATE_ON
        if hvac_mode == HVACMode.COOL
        else STATE_OFF
    )

    # WHEN: Opening is opened
    setup_boolean(hass, opening_1, STATE_OPEN)
    await hass.async_block_till_done()

    # THEN: Switch states depend on opening_scope configuration
    assert hass.states.get(heater_switch).state == switch_state
    assert hass.states.get(cooler_switch).state == cooler_state

    # WHEN: Opening is closed
    setup_boolean(hass, opening_1, STATE_CLOSED)
    await hass.async_block_till_done()

    # THEN: Switches return to normal operation
    assert (
        hass.states.get(heater_switch).state == STATE_ON
        if hvac_mode == HVACMode.HEAT
        else STATE_OFF
    )

    assert (
        hass.states.get(cooler_switch).state == STATE_ON
        if hvac_mode == HVACMode.COOL
        else STATE_OFF
    )


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_heat_cool_mode_opening_timeout(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    setup_comp_1,  # noqa: F811
) -> None:
    """Test thermostat reacting to opening with timeout."""
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    opening_1 = "input_boolean.opening_1"
    opening_2 = "input_boolean.opening_2"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {
            "input_boolean": {
                "heater": None,
                "cooler": None,
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
                "temp": {"name": "temp", "initial": 10, "min": 0, "max": 40, "step": 1},
                "outside_temp": {
                    "name": "test",
                    "initial": 10,
                    "min": 0,
                    "max": 40,
                    "step": 1,
                },
                "humidity": {
                    "name": "humididty",
                    "initial": 50,
                    "min": 20,
                    "max": 99,
                    "step": 1,
                },
            }
        },
    )

    # GIVEN:
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
                "outside_sensor": common.ENT_OUTSIDE_SENSOR,
                "humidity_sensor": common.ENT_HUMIDITY_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
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

    assert hass.states.get(common.ENTITY).state == HVACMode.HEAT_COOL
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN:
    setup_sensor(hass, 23)
    setup_outside_sensor(hass, 21)

    await common.async_set_temperature_range(hass, "all", 28, 24)
    await hass.async_block_till_done()

    # THEN:
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN:
    # opening_1 is open
    setup_boolean(hass, opening_1, STATE_OPEN)
    await hass.async_block_till_done()

    # THEN:
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN:
    # opening_1 is closed
    setup_boolean(hass, opening_1, STATE_CLOSED)
    await hass.async_block_till_done()

    # THEN:
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN:
    # opening_2 is open within timeout
    setup_boolean(hass, opening_2, STATE_OPEN)
    await hass.async_block_till_done()

    # THEN:
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN:
    # within of timeout
    freezer.tick(timedelta(seconds=3))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # THEN:
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN:
    # outside of timeout
    freezer.tick(timedelta(seconds=3))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # THEN:
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.OPENING
    )

    # WHEN:
    setup_boolean(hass, opening_2, STATE_CLOSED)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # wait openings
    freezer.tick(timedelta(seconds=4))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # THEN:
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # Cooling
    # WHEN:
    setup_sensor(hass, 25)
    await hass.async_block_till_done()

    # THEN:
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # WHEN:
    setup_sensor(hass, 30)
    await hass.async_block_till_done()

    # THEN:
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    # WHEN:
    # opening_2 is open within timeout
    setup_boolean(hass, opening_2, STATE_OPEN)
    await hass.async_block_till_done()

    # THEN:
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    # WHEN:
    # within of timeout
    freezer.tick(timedelta(seconds=3))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # THEN:
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    # WHEN:
    # outside of timeout
    freezer.tick(timedelta(seconds=3))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # THEN:
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.OPENING
    )

    # WHEN:
    setup_boolean(hass, opening_2, STATE_CLOSED)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # wait openings
    freezer.tick(timedelta(seconds=6))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # THEN:
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON
