"""Interaction tests for presets feature with all other features.

Task: T007A - Phase 3: Interaction Tests
Issue: #440

These tests validate that presets can be configured alongside other features
and that preset configuration is the final step in the flow (as required).

Preset Types Available:
- away - Lower temperature when away
- home - Comfort temperature when home
- sleep - Sleep temperature
- activity - Active temperature
- comfort - Maximum comfort
- eco - Energy saving
- boost - Maximum heating/cooling

Test Coverage:
1. Presets with no other features (baseline)
2. Presets with floor heating
3. Presets with fan
4. Presets with humidity
5. Presets with openings
6. Presets with all features combined
7. Preset step ordering validation (must be last)
"""

from unittest.mock import Mock

from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResultType
import pytest

from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
from custom_components.dual_smart_thermostat.const import (
    CONF_COOLER,
    CONF_DRYER,
    CONF_FAN,
    CONF_FLOOR_SENSOR,
    CONF_HEATER,
    CONF_HUMIDITY_SENSOR,
    CONF_MAX_FLOOR_TEMP,
    CONF_MIN_FLOOR_TEMP,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    DOMAIN,
    SYSTEM_TYPE_HEATER_COOLER,
    SYSTEM_TYPE_SIMPLE_HEATER,
)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.config_entries = Mock()
    hass.config_entries.async_entries = Mock(return_value=[])
    hass.data = {DOMAIN: {}}
    return hass


class TestPresetsBaseline:
    """Test presets with no other features enabled."""

    async def test_presets_only_simple_heater(self, mock_hass):
        """Test presets on simple_heater with no other features.

        Acceptance Criteria:
        - Flow completes successfully
        - Preset selection step appears
        - Preset configuration step appears
        - Selected presets saved to config
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER})
        await flow.async_step_basic(
            {
                CONF_NAME: "Test Heater",
                CONF_SENSOR: "sensor.temperature",
                CONF_HEATER: "switch.heater",
            }
        )

        # Enable only presets
        result = await flow.async_step_features(
            {
                "configure_floor_heating": False,
                "configure_openings": False,
                "configure_presets": True,
            }
        )

        # Should go to preset selection
        assert result["step_id"] == "preset_selection"

        # Select presets
        result = await flow.async_step_preset_selection({"presets": ["away", "home"]})

        # Should go to preset configuration
        assert result["step_id"] == "presets"

        # Configure presets
        result = await flow.async_step_presets(
            {
                "away_temp": 16,
                "home_temp": 21,
            }
        )

        # Flow should complete
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert flow.collected_config["configure_presets"] is True


class TestPresetsWithFloorHeating:
    """Test presets combined with floor heating feature."""

    async def test_presets_after_floor_heating(self, mock_hass):
        """Test that presets configuration comes after floor heating.

        Acceptance Criteria:
        - Floor heating configured first
        - Presets configured last
        - Both features saved to config
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER})
        await flow.async_step_basic(
            {
                CONF_NAME: "Test Heater",
                CONF_SENSOR: "sensor.temperature",
                CONF_HEATER: "switch.heater",
            }
        )

        # Enable floor heating and presets
        result = await flow.async_step_features(
            {
                "configure_floor_heating": True,
                "configure_openings": False,
                "configure_presets": True,
            }
        )

        # Should go to floor_config first
        assert result["step_id"] == "floor_config"

        # Configure floor heating
        result = await flow.async_step_floor_config(
            {
                CONF_FLOOR_SENSOR: "sensor.floor_temperature",
                CONF_MIN_FLOOR_TEMP: 5,
                CONF_MAX_FLOOR_TEMP: 28,
            }
        )

        # Should go to preset selection
        assert result["step_id"] == "preset_selection"

        # Select and configure presets
        result = await flow.async_step_preset_selection({"presets": ["away", "sleep"]})
        result = await flow.async_step_presets(
            {
                "away_temp": 16,
                "sleep_temp": 18,
            }
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert flow.collected_config["configure_floor_heating"] is True
        assert flow.collected_config["configure_presets"] is True


class TestPresetsWithOpenings:
    """Test presets combined with openings feature."""

    async def test_presets_after_openings(self, mock_hass):
        """Test that presets configuration comes after openings.

        Acceptance Criteria:
        - Openings configured first
        - Presets configured last
        - Both features saved to config
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER})
        await flow.async_step_basic(
            {
                CONF_NAME: "Test Heater",
                CONF_SENSOR: "sensor.temperature",
                CONF_HEATER: "switch.heater",
            }
        )

        # Enable openings and presets
        result = await flow.async_step_features(
            {
                "configure_floor_heating": False,
                "configure_openings": True,
                "configure_presets": True,
            }
        )

        # Should go to openings selection first
        assert result["step_id"] == "openings_selection"

        # Configure openings
        result = await flow.async_step_openings_selection(
            {"selected_openings": ["binary_sensor.window_1"]}
        )
        result = await flow.async_step_openings_config(
            {
                "opening_scope": "heat",
                "timeout_openings_open": 300,
            }
        )

        # Should go to preset selection
        assert result["step_id"] == "preset_selection"

        # Configure presets
        result = await flow.async_step_preset_selection({"presets": ["away", "home"]})
        result = await flow.async_step_presets(
            {
                "away_temp": 16,
                "home_temp": 21,
            }
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert flow.collected_config["configure_openings"] is True
        assert flow.collected_config["configure_presets"] is True


class TestPresetsWithFanAndHumidity:
    """Test presets combined with fan and humidity features."""

    async def test_presets_after_fan_and_humidity(self, mock_hass):
        """Test that presets configuration comes after fan and humidity.

        Acceptance Criteria:
        - Fan and humidity configured first
        - Presets configured last
        - All features saved to config
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER})
        await flow.async_step_heater_cooler(
            {
                CONF_NAME: "Test HVAC",
                CONF_SENSOR: "sensor.temperature",
                CONF_HEATER: "switch.heater",
                CONF_COOLER: "switch.cooler",
            }
        )

        # Enable fan, humidity, and presets
        result = await flow.async_step_features(
            {
                "configure_floor_heating": False,
                "configure_fan": True,
                "configure_humidity": True,
                "configure_openings": False,
                "configure_presets": True,
            }
        )

        # Should go to fan first
        assert result["step_id"] == "fan"
        result = await flow.async_step_fan(
            {
                CONF_FAN: "switch.fan",
                "fan_on_with_ac": True,
            }
        )

        # Then humidity
        assert result["step_id"] == "humidity"
        result = await flow.async_step_humidity(
            {
                CONF_HUMIDITY_SENSOR: "sensor.humidity",
                CONF_DRYER: "switch.dehumidifier",
                "target_humidity": 50,
            }
        )

        # Finally presets
        assert result["step_id"] == "preset_selection"
        result = await flow.async_step_preset_selection(
            {"presets": ["away", "home", "sleep"]}
        )
        result = await flow.async_step_presets(
            {
                "away_temp": 16,
                "home_temp": 21,
                "sleep_temp": 18,
            }
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert flow.collected_config["configure_fan"] is True
        assert flow.collected_config["configure_humidity"] is True
        assert flow.collected_config["configure_presets"] is True


class TestPresetsWithAllFeatures:
    """Test presets combined with all available features."""

    async def test_presets_last_with_all_features(self, mock_hass):
        """Test that presets is always the last configuration step.

        When all features are enabled, presets must come last because
        it depends on all previously configured features.

        Acceptance Criteria:
        - All features configured in correct order
        - Presets is the final step before CREATE_ENTRY
        - All features saved to config
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER})
        await flow.async_step_heater_cooler(
            {
                CONF_NAME: "Test HVAC All Features",
                CONF_SENSOR: "sensor.temperature",
                CONF_HEATER: "switch.heater",
                CONF_COOLER: "switch.cooler",
            }
        )

        # Enable ALL features
        result = await flow.async_step_features(
            {
                "configure_floor_heating": True,
                "configure_fan": True,
                "configure_humidity": True,
                "configure_openings": True,
                "configure_presets": True,
            }
        )

        # Expected order: floor → fan → humidity → openings → presets

        # 1. Floor heating
        assert result["step_id"] == "floor_config"
        result = await flow.async_step_floor_config(
            {
                CONF_FLOOR_SENSOR: "sensor.floor_temperature",
                CONF_MIN_FLOOR_TEMP: 5,
                CONF_MAX_FLOOR_TEMP: 28,
            }
        )

        # 2. Fan
        assert result["step_id"] == "fan"
        result = await flow.async_step_fan(
            {
                CONF_FAN: "switch.fan",
                "fan_on_with_ac": True,
            }
        )

        # 3. Humidity
        assert result["step_id"] == "humidity"
        result = await flow.async_step_humidity(
            {
                CONF_HUMIDITY_SENSOR: "sensor.humidity",
                CONF_DRYER: "switch.dehumidifier",
                "target_humidity": 50,
            }
        )

        # 4. Openings
        assert result["step_id"] == "openings_selection"
        result = await flow.async_step_openings_selection(
            {"selected_openings": ["binary_sensor.window_1"]}
        )
        result = await flow.async_step_openings_config(
            {
                "opening_scope": "all",
                "timeout_openings_open": 300,
            }
        )

        # 5. Presets (LAST)
        assert result["step_id"] == "preset_selection"
        result = await flow.async_step_preset_selection(
            {"presets": ["away", "home", "sleep", "comfort"]}
        )

        assert result["step_id"] == "presets"
        result = await flow.async_step_presets(
            {
                "away_temp": 16,
                "home_temp": 21,
                "sleep_temp": 18,
                "comfort_temp": 23,
            }
        )

        # Flow completes after presets
        assert result["type"] == FlowResultType.CREATE_ENTRY

        # Verify all features configured
        assert flow.collected_config["configure_floor_heating"] is True
        assert flow.collected_config["configure_fan"] is True
        assert flow.collected_config["configure_humidity"] is True
        assert flow.collected_config["configure_openings"] is True
        assert flow.collected_config["configure_presets"] is True


class TestPresetSelection:
    """Test preset selection variations."""

    async def test_multiple_presets_selected(self, mock_hass):
        """Test selecting multiple presets.

        Acceptance Criteria:
        - Multiple presets can be selected
        - Configuration step shows fields for all selected presets
        - Flow completes successfully
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER})
        await flow.async_step_basic(
            {
                CONF_NAME: "Test Heater",
                CONF_SENSOR: "sensor.temperature",
                CONF_HEATER: "switch.heater",
            }
        )

        result = await flow.async_step_features(
            {
                "configure_floor_heating": False,
                "configure_openings": False,
                "configure_presets": True,
            }
        )

        # Select 5 different presets
        result = await flow.async_step_preset_selection(
            {"presets": ["away", "home", "sleep", "eco", "boost"]}
        )

        assert result["step_id"] == "presets"

        # Configure all 5 presets
        result = await flow.async_step_presets(
            {
                "away_temp": 15,
                "home_temp": 21,
                "sleep_temp": 18,
                "eco_temp": 19,
                "boost_temp": 24,
            }
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert flow.collected_config["configure_presets"] is True

    async def test_single_preset_selected(self, mock_hass):
        """Test selecting just one preset.

        Acceptance Criteria:
        - Single preset can be selected
        - Flow completes successfully
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER})
        await flow.async_step_basic(
            {
                CONF_NAME: "Test Heater",
                CONF_SENSOR: "sensor.temperature",
                CONF_HEATER: "switch.heater",
            }
        )

        result = await flow.async_step_features(
            {
                "configure_floor_heating": False,
                "configure_openings": False,
                "configure_presets": True,
            }
        )

        # Select only 'away' preset
        result = await flow.async_step_preset_selection({"presets": ["away"]})

        assert result["step_id"] == "presets"

        result = await flow.async_step_presets({"away_temp": 16})

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert flow.collected_config["configure_presets"] is True


class TestPresetStepOrdering:
    """Test that preset step ordering is enforced correctly."""

    async def test_presets_always_last_before_create_entry(self, mock_hass):
        """Test that presets step immediately precedes CREATE_ENTRY.

        No other configuration steps should come after presets.

        Acceptance Criteria:
        - After presets configuration, result type is CREATE_ENTRY
        - No additional steps appear after presets
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER})
        await flow.async_step_basic(
            {
                CONF_NAME: "Test Heater",
                CONF_SENSOR: "sensor.temperature",
                CONF_HEATER: "switch.heater",
            }
        )

        # Enable all available features for simple_heater
        result = await flow.async_step_features(
            {
                "configure_floor_heating": True,
                "configure_openings": True,
                "configure_presets": True,
            }
        )

        # Floor heating first
        result = await flow.async_step_floor_config(
            {
                CONF_FLOOR_SENSOR: "sensor.floor_temperature",
                CONF_MIN_FLOOR_TEMP: 5,
                CONF_MAX_FLOOR_TEMP: 28,
            }
        )

        # Openings next
        result = await flow.async_step_openings_selection(
            {"selected_openings": ["binary_sensor.window_1"]}
        )
        result = await flow.async_step_openings_config(
            {
                "opening_scope": "heat",
                "timeout_openings_open": 300,
            }
        )

        # Presets last
        result = await flow.async_step_preset_selection({"presets": ["away"]})
        result = await flow.async_step_presets({"away_temp": 16})

        # After presets, flow must complete - no more steps
        assert result["type"] == FlowResultType.CREATE_ENTRY
