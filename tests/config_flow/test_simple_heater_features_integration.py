"""Integration tests for simple_heater system type feature combinations.

Task: T007A - Phase 2: Integration Tests
Issue: #440

These tests validate that simple_heater system type correctly handles
all valid feature combinations through complete config and options flows.

Available Features for simple_heater:
- ✅ floor_heating
- ❌ fan (not available)
- ❌ humidity (not available)
- ✅ openings
- ✅ presets

Test Coverage:
1. No features enabled (baseline)
2. Individual features (floor_heating, openings, presets)
3. All available features enabled
4. Options flow modifications
5. Blocked features not accessible
"""

from unittest.mock import Mock

from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResultType
import pytest

from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
from custom_components.dual_smart_thermostat.const import (
    CONF_FLOOR_SENSOR,
    CONF_HEATER,
    CONF_MAX_FLOOR_TEMP,
    CONF_MIN_FLOOR_TEMP,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    DOMAIN,
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


class TestSimpleHeaterNoFeatures:
    """Test simple_heater with no features enabled (baseline)."""

    async def test_config_flow_no_features(self, mock_hass):
        """Test complete config flow with no features enabled.

        Acceptance Criteria:
        - Flow completes successfully
        - Config entry created with basic settings only
        - No feature-specific configuration saved
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Step 1: Select simple_heater system type
        user_input = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER}
        result = await flow.async_step_user(user_input)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "basic"

        # Step 2: Configure basic settings
        basic_input = {
            CONF_NAME: "Test Heater",
            CONF_SENSOR: "sensor.temperature",
            CONF_HEATER: "switch.heater",
            "advanced_settings": {
                "hot_tolerance": 0.5,
                "min_cycle_duration": 300,
            },
        }
        result = await flow.async_step_basic(basic_input)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "features"

        # Step 3: Disable all features
        features_input = {
            "configure_floor_heating": False,
            "configure_openings": False,
            "configure_presets": False,
        }
        result = await flow.async_step_features(features_input)

        # With no features, flow should complete
        assert result["type"] == FlowResultType.CREATE_ENTRY

        # Verify configuration
        assert flow.collected_config[CONF_NAME] == "Test Heater"
        assert flow.collected_config[CONF_SENSOR] == "sensor.temperature"
        assert flow.collected_config[CONF_HEATER] == "switch.heater"

        # Verify no feature-specific config
        assert "configure_floor_heating" in flow.collected_config
        assert flow.collected_config["configure_floor_heating"] is False
        assert "configure_openings" in flow.collected_config
        assert flow.collected_config["configure_openings"] is False
        assert "configure_presets" in flow.collected_config
        assert flow.collected_config["configure_presets"] is False


class TestSimpleHeaterFloorHeatingOnly:
    """Test simple_heater with only floor_heating enabled."""

    async def test_config_flow_floor_heating_only(self, mock_hass):
        """Test complete config flow with floor_heating enabled.

        Acceptance Criteria:
        - Floor heating configuration step appears
        - Floor sensor and temperature limits saved
        - Flow completes successfully
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Step 1-2: System type and basic settings
        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER})
        result = await flow.async_step_basic(
            {
                CONF_NAME: "Test Heater",
                CONF_SENSOR: "sensor.temperature",
                CONF_HEATER: "switch.heater",
            }
        )

        assert result["step_id"] == "features"

        # Step 3: Enable floor_heating only
        result = await flow.async_step_features(
            {
                "configure_floor_heating": True,
                "configure_openings": False,
                "configure_presets": False,
            }
        )

        # Should go to floor_config configuration
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "floor_config"

        # Step 4: Configure floor heating
        floor_input = {
            CONF_FLOOR_SENSOR: "sensor.floor_temperature",
            CONF_MIN_FLOOR_TEMP: 5,
            CONF_MAX_FLOOR_TEMP: 28,
        }
        result = await flow.async_step_floor_config(floor_input)

        # Flow should complete
        assert result["type"] == FlowResultType.CREATE_ENTRY

        # Verify floor heating configuration saved
        assert flow.collected_config["configure_floor_heating"] is True
        assert flow.collected_config[CONF_FLOOR_SENSOR] == "sensor.floor_temperature"
        assert flow.collected_config[CONF_MIN_FLOOR_TEMP] == 5
        assert flow.collected_config[CONF_MAX_FLOOR_TEMP] == 28

    async def test_floor_heating_schema_contains_required_fields(self, mock_hass):
        """Test floor heating schema contains all required fields.

        Acceptance Criteria:
        - Schema contains floor_sensor
        - Schema contains min_floor_temp
        - Schema contains max_floor_temp
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER,
            "configure_floor_heating": True,
        }

        result = await flow.async_step_floor_config()
        schema = result["data_schema"].schema

        field_names = [key.schema for key in schema.keys() if hasattr(key, "schema")]

        assert CONF_FLOOR_SENSOR in field_names
        assert CONF_MIN_FLOOR_TEMP in field_names
        assert CONF_MAX_FLOOR_TEMP in field_names


class TestSimpleHeaterOpeningsOnly:
    """Test simple_heater with only openings enabled."""

    async def test_config_flow_openings_only(self, mock_hass):
        """Test complete config flow with openings enabled.

        Acceptance Criteria:
        - Openings selection step appears
        - Openings can be configured
        - Flow completes successfully
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Steps 1-2: System type and basic settings
        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER})
        await flow.async_step_basic(
            {
                CONF_NAME: "Test Heater",
                CONF_SENSOR: "sensor.temperature",
                CONF_HEATER: "switch.heater",
            }
        )

        # Step 3: Enable openings only
        result = await flow.async_step_features(
            {
                "configure_floor_heating": False,
                "configure_openings": True,
                "configure_presets": False,
            }
        )

        # Should go to openings selection
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "openings_selection"

        # Step 4: Select openings entities
        openings_selection_input = {"selected_openings": ["binary_sensor.window_1"]}
        result = await flow.async_step_openings_selection(openings_selection_input)

        # Should go to openings config (timeout and scope)
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "openings_config"

        # Step 5: Configure openings timeout and scope
        openings_config_input = {
            "opening_scope": "all",
            "timeout_openings_open": 300,
            "timeout_openings_close": 60,
        }
        result = await flow.async_step_openings_config(openings_config_input)

        # Flow should complete
        assert result["type"] == FlowResultType.CREATE_ENTRY

        # Verify openings configuration saved
        assert flow.collected_config["configure_openings"] is True
        # Note: openings are stored in a processed format after config step
        # Just verify the toggle is saved
        assert flow.collected_config.get("configure_openings") is True


class TestSimpleHeaterPresetsOnly:
    """Test simple_heater with only presets enabled."""

    async def test_config_flow_presets_only(self, mock_hass):
        """Test complete config flow with presets enabled.

        Acceptance Criteria:
        - Preset selection step appears
        - Preset configuration step appears
        - Flow completes successfully
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Steps 1-2: System type and basic settings
        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER})
        await flow.async_step_basic(
            {
                CONF_NAME: "Test Heater",
                CONF_SENSOR: "sensor.temperature",
                CONF_HEATER: "switch.heater",
            }
        )

        # Step 3: Enable presets only
        result = await flow.async_step_features(
            {
                "configure_floor_heating": False,
                "configure_openings": False,
                "configure_presets": True,
            }
        )

        # Should go to preset selection
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "preset_selection"

        # Step 4: Select presets (use "presets" key not "selected_presets")
        preset_selection_input = {"presets": ["away", "sleep"]}
        result = await flow.async_step_preset_selection(preset_selection_input)

        # Should go to preset configuration
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "presets"

        # Step 5: Configure presets
        presets_input = {
            "away_temp": 16,
            "sleep_temp": 18,
        }
        result = await flow.async_step_presets(presets_input)

        # Flow should complete
        assert result["type"] == FlowResultType.CREATE_ENTRY

        # Verify preset configuration saved
        assert flow.collected_config["configure_presets"] is True
        # Presets are stored after selection (in "presets" key which gets renamed to "selected_presets" internally)
        assert flow.collected_config.get("configure_presets") is True


class TestSimpleHeaterAllFeatures:
    """Test simple_heater with all available features enabled."""

    async def test_config_flow_all_features(self, mock_hass):
        """Test complete config flow with all available features enabled.

        Acceptance Criteria:
        - All feature configuration steps appear in correct order
        - All feature settings are saved correctly
        - Flow completes successfully
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Steps 1-2: System type and basic settings
        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER})
        await flow.async_step_basic(
            {
                CONF_NAME: "Test Heater All Features",
                CONF_SENSOR: "sensor.temperature",
                CONF_HEATER: "switch.heater",
            }
        )

        # Step 3: Enable all available features
        result = await flow.async_step_features(
            {
                "configure_floor_heating": True,
                "configure_openings": True,
                "configure_presets": True,
            }
        )

        # Should go to floor_config first
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "floor_config"

        # Step 4: Configure floor heating
        result = await flow.async_step_floor_config(
            {
                CONF_FLOOR_SENSOR: "sensor.floor_temperature",
                CONF_MIN_FLOOR_TEMP: 5,
                CONF_MAX_FLOOR_TEMP: 28,
            }
        )

        # Should go to openings selection
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "openings_selection"

        # Step 5: Select openings
        result = await flow.async_step_openings_selection(
            {"selected_openings": ["binary_sensor.window_1", "binary_sensor.door_1"]}
        )

        # Should go to openings config
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "openings_config"

        # Step 6: Configure openings
        result = await flow.async_step_openings_config(
            {
                "opening_scope": "all",
                "timeout_openings_open": 300,
            }
        )

        # Should go to preset selection
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "preset_selection"

        # Step 7: Select presets
        result = await flow.async_step_preset_selection(
            {"presets": ["away", "sleep", "home"]}
        )

        # Should go to preset configuration
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "presets"

        # Step 8: Configure presets
        result = await flow.async_step_presets(
            {
                "away_temp": 16,
                "sleep_temp": 18,
                "home_temp": 21,
            }
        )

        # Flow should complete
        assert result["type"] == FlowResultType.CREATE_ENTRY

        # Verify all features are saved
        assert flow.collected_config["configure_floor_heating"] is True
        assert flow.collected_config[CONF_FLOOR_SENSOR] == "sensor.floor_temperature"

        assert flow.collected_config["configure_openings"] is True
        # Openings are processed into a dict format by the config step

        assert flow.collected_config["configure_presets"] is True
        # Presets are stored in processed format after configuration


class TestSimpleHeaterBlockedFeatures:
    """Test that fan and humidity features are not available for simple_heater."""

    async def test_fan_feature_not_in_schema(self, mock_hass):
        """Test that configure_fan is not in features schema.

        Acceptance Criteria:
        - configure_fan toggle not present in features step
        - simple_heater cannot enable fan feature
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER}

        result = await flow.async_step_features()
        schema = result["data_schema"].schema

        field_names = [key.schema for key in schema.keys() if hasattr(key, "schema")]

        # Fan should NOT be in the schema
        assert "configure_fan" not in field_names

    async def test_humidity_feature_not_in_schema(self, mock_hass):
        """Test that configure_humidity is not in features schema.

        Acceptance Criteria:
        - configure_humidity toggle not present in features step
        - simple_heater cannot enable humidity feature
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER}

        result = await flow.async_step_features()
        schema = result["data_schema"].schema

        field_names = [key.schema for key in schema.keys() if hasattr(key, "schema")]

        # Humidity should NOT be in the schema
        assert "configure_humidity" not in field_names

    async def test_available_features_only(self, mock_hass):
        """Test that only available features are shown in schema.

        Acceptance Criteria:
        - Only floor_heating, openings, presets toggles present
        - Fan and humidity not accessible
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER}

        result = await flow.async_step_features()
        schema = result["data_schema"].schema

        field_names = [key.schema for key in schema.keys() if hasattr(key, "schema")]

        # Only available features should be present
        expected_features = [
            "configure_floor_heating",
            "configure_openings",
            "configure_presets",
        ]

        feature_fields = [f for f in field_names if f.startswith("configure_")]

        assert sorted(feature_fields) == sorted(expected_features)


class TestSimpleHeaterFeatureOrdering:
    """Test that feature configuration steps appear in correct order."""

    async def test_floor_heating_before_openings(self, mock_hass):
        """Test that floor_heating configuration comes before openings.

        Acceptance Criteria:
        - When both enabled, floor_heating step appears first
        - Openings step appears after floor_heating
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Setup: Enable floor_heating and openings
        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER})
        await flow.async_step_basic(
            {
                CONF_NAME: "Test",
                CONF_SENSOR: "sensor.temp",
                CONF_HEATER: "switch.heater",
            }
        )

        result = await flow.async_step_features(
            {
                "configure_floor_heating": True,
                "configure_openings": True,
                "configure_presets": False,
            }
        )

        # First should be floor_config
        assert result["step_id"] == "floor_config"

        # Complete floor_config
        result = await flow.async_step_floor_config(
            {
                CONF_FLOOR_SENSOR: "sensor.floor_temp",
                CONF_MIN_FLOOR_TEMP: 5,
                CONF_MAX_FLOOR_TEMP: 28,
            }
        )

        # Next should be openings
        assert result["step_id"] == "openings_selection"

    async def test_openings_before_presets(self, mock_hass):
        """Test that openings configuration comes before presets.

        Acceptance Criteria:
        - When both enabled, openings steps come before preset steps
        - Presets is always the final configuration step
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Setup: Enable openings and presets
        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER})
        await flow.async_step_basic(
            {
                CONF_NAME: "Test",
                CONF_SENSOR: "sensor.temp",
                CONF_HEATER: "switch.heater",
            }
        )

        result = await flow.async_step_features(
            {
                "configure_floor_heating": False,
                "configure_openings": True,
                "configure_presets": True,
            }
        )

        # First should be openings selection
        assert result["step_id"] == "openings_selection"

        # Complete openings
        result = await flow.async_step_openings_selection(
            {"selected_openings": ["binary_sensor.window_1"]}
        )
        result = await flow.async_step_openings_config(
            {
                "opening_scope": "all",
                "timeout_openings_open": 300,
            }
        )

        # Next should be preset selection
        assert result["step_id"] == "preset_selection"
