"""Shared test fixtures and configuration for mode-agnostic tests.

This module provides MODE_CONFIGS that define HVAC mode-specific test parameters,
allowing tests to be parametrized across all supported modes (heater, cooler, heat_pump, fan, dry, dual).
"""

from pathlib import Path

# Import common test utilities
# isort: off
import sys

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
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest

from custom_components.dual_smart_thermostat.const import DOMAIN, PRESET_ANTI_FREEZE

# Add parent directory to path to import from tests package
tests_dir = Path(__file__).parent.parent
if str(tests_dir) not in sys.path:
    sys.path.insert(0, str(tests_dir))

from tests import (  # noqa: E402, F401
    setup_comp_fan_only_config,
    setup_comp_fan_only_config_presets,
    setup_comp_heat,
    setup_comp_heat_ac_cool,
    setup_comp_heat_ac_cool_presets,
    setup_comp_heat_presets,
)

# Import preset setup fixtures from tests module so they're available
from tests import common  # noqa: E402

# isort: on

# Mode-specific configuration for parametrized tests
MODE_CONFIGS = {
    "heater": {
        "name": "heater",
        "hvac_mode": HVACMode.HEAT,
        "hvac_modes": [HVACMode.HEAT, HVACMode.OFF],
        "hvac_action_on": HVACAction.HEATING,
        "hvac_action_off": HVACAction.IDLE,
        "device_entity": common.ENT_SWITCH,
        "device_type": "heater",
        "device_state_on": STATE_ON,
        "device_state_off": STATE_OFF,
        "target_temp": 23,
        "current_temp_below_target": 20,
        "current_temp_above_target": 26,
        "cold_tolerance": 0.5,
        "hot_tolerance": 0.5,
        "preset_temps": {
            PRESET_NONE: 23,
            PRESET_AWAY: 16,
            PRESET_COMFORT: 20,
            PRESET_ECO: 18,
            PRESET_HOME: 19,
            PRESET_SLEEP: 17,
            PRESET_ACTIVITY: 21,
            PRESET_BOOST: 24,
            PRESET_ANTI_FREEZE: 5,
        },
        "config_extra": {},
        "supports_aux": True,
        "supports_floor_temp": True,
    },
    "cooler": {
        "name": "cooler",
        "hvac_mode": HVACMode.COOL,
        "hvac_modes": [HVACMode.COOL, HVACMode.OFF],
        "hvac_action_on": HVACAction.COOLING,
        "hvac_action_off": HVACAction.IDLE,
        "device_entity": common.ENT_SWITCH,
        "device_type": "heater",  # AC mode uses heater param
        "device_state_on": STATE_ON,
        "device_state_off": STATE_OFF,
        "target_temp": 23,
        "current_temp_below_target": 20,
        "current_temp_above_target": 26,
        "cold_tolerance": 0.5,
        "hot_tolerance": 0.5,
        "preset_temps": {
            # Note: setup_comp_heat_ac_cool_presets uses heater-style preset temps
            PRESET_NONE: 23,
            PRESET_AWAY: 16,
            PRESET_COMFORT: 20,
            PRESET_ECO: 18,
            PRESET_HOME: 19,
            PRESET_SLEEP: 17,
            PRESET_ACTIVITY: 21,
            PRESET_BOOST: 10,
            PRESET_ANTI_FREEZE: 5,
        },
        "config_extra": {"ac_mode": True},
        "supports_aux": False,
        "supports_floor_temp": False,
    },
    "heat_pump": {
        "name": "heat_pump",
        "hvac_mode": HVACMode.HEAT_COOL,
        "hvac_modes": [HVACMode.HEAT_COOL, HVACMode.HEAT, HVACMode.COOL, HVACMode.OFF],
        "hvac_action_on": HVACAction.HEATING,  # Can be HEATING or COOLING
        "hvac_action_off": HVACAction.IDLE,
        "device_entity": common.ENT_SWITCH,
        "device_type": "heat_pump",
        "device_state_on": STATE_ON,
        "device_state_off": STATE_OFF,
        "target_temp": 23,
        "current_temp_below_target": 20,
        "current_temp_above_target": 26,
        "cold_tolerance": 0.5,
        "hot_tolerance": 0.5,
        "preset_temps": {
            PRESET_NONE: 23,
            PRESET_AWAY: 16,
            PRESET_COMFORT: 20,
            PRESET_ECO: 18,
            PRESET_HOME: 19,
            PRESET_SLEEP: 17,
            PRESET_ACTIVITY: 21,
            PRESET_BOOST: 24,
            PRESET_ANTI_FREEZE: 5,
        },
        "config_extra": {"heat_pump_cooling": common.ENT_HEAT_PUMP_COOLING},
        "supports_aux": False,
        "supports_floor_temp": False,
    },
    "fan": {
        "name": "fan",
        "hvac_mode": HVACMode.FAN_ONLY,
        "hvac_modes": [HVACMode.FAN_ONLY, HVACMode.OFF],
        "hvac_action_on": HVACAction.FAN,
        "hvac_action_off": HVACAction.IDLE,
        "device_entity": common.ENT_SWITCH,
        "device_type": "heater",  # Fan mode uses heater param
        "device_state_on": STATE_ON,
        "device_state_off": STATE_OFF,
        "target_temp": 23,
        "current_temp_below_target": 20,
        "current_temp_above_target": 26,
        "cold_tolerance": 0.5,
        "hot_tolerance": 0.5,
        "preset_temps": {
            PRESET_NONE: 23,
            PRESET_AWAY: 16,
            PRESET_COMFORT: 20,
            PRESET_ECO: 18,
            PRESET_HOME: 19,
            PRESET_SLEEP: 17,
            PRESET_ACTIVITY: 21,
            PRESET_BOOST: 10,
            PRESET_ANTI_FREEZE: 5,
        },
        "config_extra": {"fan_mode": True},
        "supports_aux": False,
        "supports_floor_temp": False,
    },
    "dry": {
        "name": "dry",
        "hvac_mode": HVACMode.DRY,
        "hvac_modes": [HVACMode.DRY, HVACMode.OFF],
        "hvac_action_on": HVACAction.DRYING,
        "hvac_action_off": HVACAction.IDLE,
        "device_entity": common.ENT_DRYER,
        "device_type": "dryer",
        "device_state_on": STATE_ON,
        "device_state_off": STATE_OFF,
        "target_humidity": 50,
        "current_humidity_below_target": 40,
        "current_humidity_above_target": 60,
        "cold_tolerance": 3,  # humidity tolerance
        "hot_tolerance": 3,  # humidity tolerance
        "preset_temps": {
            PRESET_NONE: 50,
            PRESET_AWAY: 70,
            PRESET_COMFORT: 45,
            PRESET_ECO: 55,
            PRESET_HOME: 48,
            PRESET_SLEEP: 60,
            PRESET_ACTIVITY: 40,
            PRESET_BOOST: 35,
            PRESET_ANTI_FREEZE: 80,
        },
        "config_extra": {
            "dryer": common.ENT_DRYER,
            "humidity_sensor": common.ENT_HUMIDITY_SENSOR,
        },
        "supports_aux": False,
        "supports_floor_temp": False,
        "uses_humidity": True,
    },
    "dual": {
        "name": "dual",
        "hvac_mode": HVACMode.HEAT_COOL,
        "hvac_modes": [HVACMode.HEAT_COOL, HVACMode.HEAT, HVACMode.COOL, HVACMode.OFF],
        "hvac_action_on": HVACAction.HEATING,  # Can be HEATING or COOLING
        "hvac_action_off": HVACAction.IDLE,
        "device_entity": common.ENT_SWITCH,  # heater
        "device_entity_cooler": common.ENT_COOLER,
        "device_type": "heater_cooler",
        "device_state_on": STATE_ON,
        "device_state_off": STATE_OFF,
        "target_temp": 23,
        "target_temp_low": 20,
        "target_temp_high": 26,
        "current_temp_below_target": 18,
        "current_temp_above_target": 28,
        "current_temp_in_range": 23,
        "cold_tolerance": 0.5,
        "hot_tolerance": 0.5,
        "preset_temps": {
            PRESET_NONE: {"target_temp_low": 20, "target_temp_high": 26},
            PRESET_AWAY: {"target_temp_low": 16, "target_temp_high": 30},
            PRESET_COMFORT: {"target_temp_low": 20, "target_temp_high": 27},
            PRESET_ECO: {"target_temp_low": 18, "target_temp_high": 29},
            PRESET_HOME: {"target_temp_low": 19, "target_temp_high": 23},
            PRESET_SLEEP: {"target_temp_low": 17, "target_temp_high": 24},
            PRESET_ACTIVITY: {"target_temp_low": 21, "target_temp_high": 24},
            PRESET_BOOST: {"target_temp_low": 22, "target_temp_high": 25},
            PRESET_ANTI_FREEZE: {"target_temp_low": 5, "target_temp_high": 32},
        },
        "config_extra": {"cooler": common.ENT_COOLER},
        "supports_aux": False,
        "supports_floor_temp": False,
        "uses_range": True,
    },
}


@pytest.fixture
def mode_config(request):
    """Fixture that provides mode-specific configuration for parametrized tests.

    Usage:
        @pytest.mark.parametrize("mode_config", ["heater", "cooler"], indirect=True)
        async def test_something(hass, mode_config):
            # mode_config contains heater or cooler specific config
    """
    mode_name = request.param
    return MODE_CONFIGS[mode_name]


@pytest.fixture
async def setup_component_with_mode(hass: HomeAssistant, mode_config):
    """Set up a climate component with mode-specific configuration.

    This fixture creates a climate entity configured for the specific HVAC mode
    defined in mode_config.
    """
    hass.config.units = METRIC_SYSTEM

    # Build base configuration
    climate_config = {
        "platform": DOMAIN,
        "name": "test",
        "cold_tolerance": mode_config["cold_tolerance"],
        "hot_tolerance": mode_config["hot_tolerance"],
        "target_sensor": common.ENT_SENSOR,
        "initial_hvac_mode": mode_config["hvac_mode"],
    }

    # Add device entity based on type
    if mode_config.get("uses_humidity"):
        # Dry mode uses different config structure
        climate_config["heater"] = mode_config[
            "device_entity"
        ]  # Still needs heater for validation
        climate_config["dryer"] = mode_config["config_extra"]["dryer"]
        climate_config["humidity_sensor"] = mode_config["config_extra"][
            "humidity_sensor"
        ]
    elif mode_config.get("device_type") == "heater_cooler":
        # Dual mode has separate heater/cooler
        climate_config["heater"] = mode_config["device_entity"]
        climate_config["cooler"] = mode_config.get("device_entity_cooler")
    else:
        # Standard modes use heater parameter
        climate_config["heater"] = mode_config["device_entity"]

    # Merge extra config
    climate_config.update(mode_config["config_extra"])

    # Setup component
    assert await async_setup_component(
        hass,
        "climate",
        {"climate": climate_config},
    )
    await hass.async_block_till_done()

    return mode_config


@pytest.fixture
async def setup_component_with_mode_and_presets(hass: HomeAssistant, mode_config):
    """Set up a climate component with mode-specific configuration including presets.

    This fixture creates a climate entity configured for the specific HVAC mode
    with preset temperature configurations.
    """
    hass.config.units = METRIC_SYSTEM

    # Build base configuration
    climate_config = {
        "platform": DOMAIN,
        "name": "test",
        "cold_tolerance": mode_config["cold_tolerance"],
        "hot_tolerance": mode_config["hot_tolerance"],
        "target_sensor": common.ENT_SENSOR,
        "initial_hvac_mode": mode_config["hvac_mode"],
    }

    # Add device entity based on type
    if mode_config.get("uses_humidity"):
        climate_config["heater"] = mode_config[
            "device_entity"
        ]  # Still needs heater for validation
        climate_config["dryer"] = mode_config["config_extra"]["dryer"]
        climate_config["humidity_sensor"] = mode_config["config_extra"][
            "humidity_sensor"
        ]
    elif mode_config.get("device_type") == "heater_cooler":
        climate_config["heater"] = mode_config["device_entity"]
        climate_config["cooler"] = mode_config.get("device_entity_cooler")
    else:
        climate_config["heater"] = mode_config["device_entity"]

    # Merge extra config
    climate_config.update(mode_config["config_extra"])

    # Add preset configurations
    preset_temps = mode_config["preset_temps"]
    for preset, temp_config in preset_temps.items():
        if preset == PRESET_NONE:
            continue
        if mode_config.get("uses_range"):
            # Dual mode uses temp ranges
            climate_config[preset] = temp_config
        elif mode_config.get("uses_humidity"):
            # Dry mode uses humidity
            climate_config[preset] = {"humidity": temp_config}
        else:
            # Standard modes use temperature
            climate_config[preset] = {"temperature": temp_config}

    # Setup component
    assert await async_setup_component(
        hass,
        "climate",
        {"climate": climate_config},
    )
    await hass.async_block_till_done()

    return mode_config
