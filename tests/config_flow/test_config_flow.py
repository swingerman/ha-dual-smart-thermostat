#!/usr/bin/env python3
"""Comprehensive tests for config flow functionality."""

from unittest.mock import Mock, patch

from homeassistant.const import CONF_NAME
import pytest

from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
from custom_components.dual_smart_thermostat.const import (
    CONF_COLD_TOLERANCE,
    CONF_COOLER,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_KEEP_ALIVE,
    CONF_MIN_DUR,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    SYSTEM_TYPE_AC_ONLY,
    SYSTEM_TYPE_HEATER_COOLER,
    SYSTEM_TYPE_SIMPLE_HEATER,
)


@pytest.fixture
def mock_hass():
    """Create a mock hass instance."""
    hass = Mock()
    hass.config_entries = Mock()
    hass.config_entries.async_entries = Mock(return_value=[])
    return hass


async def test_config_flow_system_type_selection():
    """Test initial system type selection in config flow."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    # Test initial step
    result = await flow.async_step_user()
    assert result["type"] == "form"
    assert result["step_id"] == "user"

    # Check that system type options are available
    schema_dict = result["data_schema"].schema
    system_type_field = None
    for key in schema_dict.keys():
        if hasattr(key, "schema") and key.schema == CONF_SYSTEM_TYPE:
            system_type_field = key
            break

    assert system_type_field is not None


async def test_ac_only_config_flow():
    """Test complete AC-only system configuration flow."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()
    flow.collected_config = {}

    # Step 1: User selects AC-only system
    user_input = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY}
    result = await flow.async_step_user(user_input)

    assert result["type"] == "form"
    assert result["step_id"] == "cooling_only"

    # Step 2: Cooling configuration
    cooling_input = {
        CONF_NAME: "AC Thermostat",
        CONF_HEATER: "switch.ac_unit",  # AC-only uses heater field for backward compatibility
        CONF_SENSOR: "sensor.temperature",
        "advanced_settings": {
            CONF_COLD_TOLERANCE: 0.5,
            CONF_HOT_TOLERANCE: 0.5,
            CONF_MIN_DUR: 300,
            CONF_KEEP_ALIVE: 300,
        },
    }
    result = await flow.async_step_cooling_only(cooling_input)

    assert result["type"] == "form"
    assert result["step_id"] == "ac_only_features"

    # Verify that advanced settings were flattened to top level
    assert CONF_COLD_TOLERANCE in flow.collected_config
    assert CONF_HOT_TOLERANCE in flow.collected_config
    assert CONF_MIN_DUR in flow.collected_config
    assert CONF_KEEP_ALIVE in flow.collected_config
    assert flow.collected_config[CONF_COLD_TOLERANCE] == 0.5
    assert flow.collected_config[CONF_HOT_TOLERANCE] == 0.5
    assert flow.collected_config[CONF_MIN_DUR] == 300
    assert flow.collected_config[CONF_KEEP_ALIVE] == 300


async def test_ac_only_config_flow_without_advanced_settings():
    """Test AC-only configuration flow without advanced settings."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()
    flow.collected_config = {}

    # Step 1: User selects AC-only system
    user_input = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY}
    result = await flow.async_step_user(user_input)

    # Step 2: Cooling configuration without advanced settings
    cooling_input = {
        CONF_NAME: "AC Thermostat",
        CONF_HEATER: "switch.ac_unit",
        CONF_SENSOR: "sensor.temperature",
    }
    result = await flow.async_step_cooling_only(cooling_input)

    assert result["type"] == "form"
    assert result["step_id"] == "ac_only_features"

    # Verify that default values are not set when not provided
    assert CONF_COLD_TOLERANCE not in flow.collected_config
    assert CONF_HOT_TOLERANCE not in flow.collected_config
    assert CONF_MIN_DUR not in flow.collected_config
    assert CONF_KEEP_ALIVE not in flow.collected_config


async def test_ac_only_config_flow_with_custom_tolerances():
    """Test AC-only configuration flow with custom tolerance values."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()
    flow.collected_config = {}

    # Step 1: User selects AC-only system
    user_input = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY}
    result = await flow.async_step_user(user_input)

    # Step 2: Cooling configuration with custom tolerance values
    cooling_input = {
        CONF_NAME: "AC Thermostat",
        CONF_HEATER: "switch.ac_unit",
        CONF_SENSOR: "sensor.temperature",
        "advanced_settings": {
            CONF_COLD_TOLERANCE: 1.0,
            CONF_HOT_TOLERANCE: 0.8,
            CONF_MIN_DUR: 600,
            CONF_KEEP_ALIVE: 180,
        },
    }
    result = await flow.async_step_cooling_only(cooling_input)

    assert result["type"] == "form"
    assert result["step_id"] == "ac_only_features"

    # Verify that custom tolerance values are properly set
    assert flow.collected_config[CONF_COLD_TOLERANCE] == 1.0
    assert flow.collected_config[CONF_HOT_TOLERANCE] == 0.8
    assert flow.collected_config[CONF_MIN_DUR] == 600
    assert flow.collected_config[CONF_KEEP_ALIVE] == 180


async def test_ac_only_features_selection():
    """Test AC-only features selection step."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()
    flow.collected_config = {
        "name": "AC Thermostat",
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY,
        CONF_SENSOR: "sensor.temperature",
        CONF_COOLER: "switch.ac_unit",
    }

    # Test features form
    result = await flow.async_step_ac_only_features()
    assert result["type"] == "form"
    assert result["step_id"] == "ac_only_features"

    # Test feature selection
    features_input = {
        "configure_fan": True,
        "configure_humidity": False,
        "configure_openings": True,
        "configure_presets": False,
        "configure_advanced": False,
    }

    # Mock the next step to test the flow
    with patch.object(flow, "_determine_next_step") as mock_next:
        mock_next.return_value = {"type": "form", "step_id": "fan_toggle"}
        result = await flow.async_step_ac_only_features(features_input)

    # Should proceed to next step based on selections
    assert result["type"] == "form"


async def test_simple_heater_config_flow():
    """Test simple heater system configuration flow."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()
    flow.collected_config = {}

    # Step 1: User selects simple heater
    user_input = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER}
    result = await flow.async_step_user(user_input)

    assert result["step_id"] == "basic"

    # Step 2: Basic configuration
    basic_input = {
        "name": "Simple Heater",
        CONF_SENSOR: "sensor.temperature",
        CONF_HEATER: "switch.heater",
        "cold_tolerance": 0.3,
        "hot_tolerance": 0.3,
    }
    result = await flow.async_step_basic(basic_input)

    # Simple heater now shows a combined features selection step first
    assert result["type"] == "form"
    assert result["step_id"] == "simple_heater_features"


async def test_dual_system_config_flow():
    """Test heater+cooler system configuration flow."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()
    flow.collected_config = {}

    # Step 1: User selects heater+cooler
    user_input = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
    result = await flow.async_step_user(user_input)

    assert result["step_id"] == "heater_cooler"

    # Step 2: Basic configuration
    basic_input = {
        "name": "Dual Thermostat",
        CONF_SENSOR: "sensor.temperature",
        "cold_tolerance": 0.3,
        "hot_tolerance": 0.3,
    }
    result = await flow.async_step_basic(basic_input)

    # Should proceed to heater_cooler features selection step
    assert result["step_id"] == "system_features"

    # Step 3: Heater and cooler configuration
    heater_cooler_input = {
        CONF_HEATER: "switch.heater",
        CONF_COOLER: "switch.cooler",
    }
    result = await flow.async_step_heater_cooler(heater_cooler_input)

    # Should continue to additional configuration
    assert result["type"] == "form"


async def test_preset_selection_flow():
    """Test preset selection in config flow."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()
    flow.collected_config = {
        "name": "Test Thermostat",
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY,
        CONF_SENSOR: "sensor.temperature",
        CONF_COOLER: "switch.ac_unit",
    }

    # Test preset selection step
    result = await flow.async_step_preset_selection()
    assert result["type"] == "form"
    assert result["step_id"] == "preset_selection"

    # User selects specific presets
    preset_input = {
        "away": True,
        "comfort": False,
        "eco": True,
        "home": False,
        "sleep": False,
        "anti_freeze": False,
        "activity": False,
        "boost": False,
    }

    result = await flow.async_step_preset_selection(preset_input)

    # Should proceed to preset configuration since some presets were selected
    assert result["type"] == "form"
    assert result["step_id"] == "presets"


async def test_preset_skip_logic():
    """Test that preset configuration is skipped when no presets selected."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()
    flow.collected_config = {
        "name": "Test Thermostat",
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY,
    }

    # User selects no presets
    no_presets_input = {
        "away": False,
        "comfort": False,
        "eco": False,
        "home": False,
        "sleep": False,
        "anti_freeze": False,
        "activity": False,
        "boost": False,
    }

    result = await flow.async_step_preset_selection(no_presets_input)

    # Should skip preset configuration and create entry
    assert result["type"] == "create_entry"


async def test_advanced_options_step():
    """Test advanced options configuration step."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()
    flow.collected_config = {
        "name": "Test Thermostat",
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY,
        "configure_advanced": True,
    }

    # Test advanced options form
    result = await flow.async_step_advanced()
    assert result["type"] == "form"
    assert result["step_id"] == "advanced"

    # Test advanced configuration
    advanced_input = {
        "precision": 0.1,
        "target_temp": 22,
        "min_temp": 15,
        "max_temp": 30,
        "initial_hvac_mode": "cool",
        "target_temp_step": 1,
    }

    # Mock next step determination
    with patch.object(flow, "_determine_next_step") as mock_next:
        mock_next.return_value = {"type": "create_entry", "data": {}}
        result = await flow.async_step_advanced(advanced_input)

    # Advanced options should be stored in collected config
    for key, value in advanced_input.items():
        assert flow.collected_config[key] == value


if __name__ == "__main__":
    """Run tests directly."""
    import asyncio
    import sys

    async def run_all_tests():
        """Run all tests manually."""
        print("🧪 Running Config Flow Tests")
        print("=" * 50)

        tests = [
            ("System type selection", test_config_flow_system_type_selection()),
            ("AC-only config flow", test_ac_only_config_flow()),
            ("AC-only features selection", test_ac_only_features_selection()),
            ("Simple heater flow", test_simple_heater_config_flow()),
            ("Preset selection flow", test_preset_selection_flow()),
            ("Preset skip logic", test_preset_skip_logic()),
            ("Advanced options step", test_advanced_options_step()),
        ]

        passed = 0
        for test_name, test_coro in tests:
            try:
                await test_coro
                print(f"✅ {test_name}")
                passed += 1
            except Exception as e:
                print(f"❌ {test_name}: {e}")

        print(f"\n🎯 Results: {passed}/{len(tests)} tests passed")
        return passed == len(tests)

    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
