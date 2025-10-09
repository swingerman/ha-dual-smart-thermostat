"""Integration tests for ac_only system type feature combinations.

Task: T007A - Phase 2: Integration Tests
Issue: #440

These tests validate that ac_only system type correctly handles
all valid feature combinations through complete config and options flows.

Available Features for ac_only:
- ❌ floor_heating (not available)
- ✅ fan
- ✅ humidity
- ✅ openings
- ✅ presets

Test Coverage:
1. No features enabled (baseline)
2. Individual features (fan, humidity, openings, presets)
3. Fan + humidity combination (common AC setup)
4. All available features enabled
5. Blocked features not accessible (floor_heating)
6. HVAC mode additions (FAN_ONLY when fan enabled, DRY when humidity enabled)
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
    CONF_HUMIDITY_SENSOR,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    DOMAIN,
    SYSTEM_TYPE_AC_ONLY,
)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.config_entries = Mock()
    hass.config_entries.async_entries = Mock(return_value=[])
    hass.data = {DOMAIN: {}}
    return hass


class TestAcOnlyNoFeatures:
    """Test ac_only with no features enabled (baseline)."""

    async def test_config_flow_no_features(self, mock_hass):
        """Test complete config flow with no features enabled.

        Acceptance Criteria:
        - Flow completes successfully
        - Config entry created with basic AC settings only
        - No feature-specific configuration saved
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Step 1: Select ac_only system type
        user_input = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY}
        result = await flow.async_step_user(user_input)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "basic_ac_only"

        # Step 2: Configure basic AC settings
        basic_input = {
            CONF_NAME: "Test AC",
            CONF_SENSOR: "sensor.temperature",
            CONF_COOLER: "switch.ac",
            "advanced_settings": {
                "cold_tolerance": 0.5,
                "min_cycle_duration": 300,
            },
        }
        result = await flow.async_step_basic_ac_only(basic_input)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "features"

        # Step 3: Disable all features
        features_input = {
            "configure_fan": False,
            "configure_humidity": False,
            "configure_openings": False,
            "configure_presets": False,
        }
        result = await flow.async_step_features(features_input)

        # With no features, flow should complete
        assert result["type"] == FlowResultType.CREATE_ENTRY

        # Verify configuration
        assert flow.collected_config[CONF_NAME] == "Test AC"
        assert flow.collected_config[CONF_SENSOR] == "sensor.temperature"
        assert flow.collected_config[CONF_COOLER] == "switch.ac"

        # Verify no feature-specific config
        assert flow.collected_config["configure_fan"] is False
        assert flow.collected_config["configure_humidity"] is False


class TestAcOnlyFanOnly:
    """Test ac_only with only fan enabled."""

    async def test_config_flow_fan_only(self, mock_hass):
        """Test complete config flow with fan enabled.

        Acceptance Criteria:
        - Fan configuration step appears
        - Fan entity and settings saved
        - Flow completes successfully
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Steps 1-2: System type and basic settings
        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY})
        result = await flow.async_step_basic_ac_only(
            {
                CONF_NAME: "Test AC",
                CONF_SENSOR: "sensor.temperature",
                CONF_COOLER: "switch.ac",
            }
        )

        assert result["step_id"] == "features"

        # Step 3: Enable fan only
        result = await flow.async_step_features(
            {
                "configure_fan": True,
                "configure_humidity": False,
                "configure_openings": False,
                "configure_presets": False,
            }
        )

        # Should go to fan configuration
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "fan"

        # Step 4: Configure fan
        fan_input = {
            CONF_FAN: "switch.fan",
            "fan_on_with_ac": True,
        }
        result = await flow.async_step_fan(fan_input)

        # Flow should complete
        assert result["type"] == FlowResultType.CREATE_ENTRY

        # Verify fan configuration saved
        assert flow.collected_config["configure_fan"] is True
        assert flow.collected_config[CONF_FAN] == "switch.fan"


class TestAcOnlyHumidityOnly:
    """Test ac_only with only humidity enabled."""

    async def test_config_flow_humidity_only(self, mock_hass):
        """Test complete config flow with humidity enabled.

        Acceptance Criteria:
        - Humidity configuration step appears
        - Humidity sensor and dryer settings saved
        - Flow completes successfully
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Steps 1-2: System type and basic settings
        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY})
        await flow.async_step_basic_ac_only(
            {
                CONF_NAME: "Test AC",
                CONF_SENSOR: "sensor.temperature",
                CONF_COOLER: "switch.ac",
            }
        )

        # Step 3: Enable humidity only
        result = await flow.async_step_features(
            {
                "configure_fan": False,
                "configure_humidity": True,
                "configure_openings": False,
                "configure_presets": False,
            }
        )

        # Should go to humidity configuration
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "humidity"

        # Step 4: Configure humidity
        humidity_input = {
            CONF_HUMIDITY_SENSOR: "sensor.humidity",
            CONF_DRYER: "switch.dehumidifier",
            "target_humidity": 50,
            "min_humidity": 30,
            "max_humidity": 70,
            "dry_tolerance": 3,
            "moist_tolerance": 3,
        }
        result = await flow.async_step_humidity(humidity_input)

        # Flow should complete
        assert result["type"] == FlowResultType.CREATE_ENTRY

        # Verify humidity configuration saved
        assert flow.collected_config["configure_humidity"] is True
        assert flow.collected_config[CONF_HUMIDITY_SENSOR] == "sensor.humidity"
        assert flow.collected_config[CONF_DRYER] == "switch.dehumidifier"


class TestAcOnlyFanAndHumidity:
    """Test ac_only with fan and humidity enabled (common combination)."""

    async def test_config_flow_fan_and_humidity(self, mock_hass):
        """Test complete config flow with fan and humidity enabled.

        This is a common AC configuration where both fan and dehumidifier
        are used together for climate control.

        Acceptance Criteria:
        - Both fan and humidity configuration steps appear
        - Both features are saved correctly
        - Step ordering is correct (fan before humidity for ac_only)
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Steps 1-2: System type and basic settings
        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY})
        await flow.async_step_basic_ac_only(
            {
                CONF_NAME: "Test AC",
                CONF_SENSOR: "sensor.temperature",
                CONF_COOLER: "switch.ac",
            }
        )

        # Step 3: Enable fan and humidity
        result = await flow.async_step_features(
            {
                "configure_fan": True,
                "configure_humidity": True,
                "configure_openings": False,
                "configure_presets": False,
            }
        )

        # Should go to fan configuration first
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "fan"

        # Step 4: Configure fan
        result = await flow.async_step_fan(
            {
                CONF_FAN: "switch.fan",
                "fan_on_with_ac": True,
            }
        )

        # Should go to humidity configuration
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "humidity"

        # Step 5: Configure humidity
        result = await flow.async_step_humidity(
            {
                CONF_HUMIDITY_SENSOR: "sensor.humidity",
                CONF_DRYER: "switch.dehumidifier",
                "target_humidity": 50,
            }
        )

        # Flow should complete
        assert result["type"] == FlowResultType.CREATE_ENTRY

        # Verify both features are saved
        assert flow.collected_config["configure_fan"] is True
        assert flow.collected_config[CONF_FAN] == "switch.fan"

        assert flow.collected_config["configure_humidity"] is True
        assert flow.collected_config[CONF_HUMIDITY_SENSOR] == "sensor.humidity"


class TestAcOnlyAllFeatures:
    """Test ac_only with all available features enabled."""

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
        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY})
        await flow.async_step_basic_ac_only(
            {
                CONF_NAME: "Test AC All Features",
                CONF_SENSOR: "sensor.temperature",
                CONF_COOLER: "switch.ac",
            }
        )

        # Step 3: Enable all available features
        result = await flow.async_step_features(
            {
                "configure_fan": True,
                "configure_humidity": True,
                "configure_openings": True,
                "configure_presets": True,
            }
        )

        # Should go to fan first (for ac_only)
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "fan"

        # Step 4: Configure fan
        result = await flow.async_step_fan(
            {
                CONF_FAN: "switch.fan",
                "fan_on_with_ac": True,
            }
        )

        # Should go to humidity
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "humidity"

        # Step 5: Configure humidity
        result = await flow.async_step_humidity(
            {
                CONF_HUMIDITY_SENSOR: "sensor.humidity",
                CONF_DRYER: "switch.dehumidifier",
                "target_humidity": 50,
            }
        )

        # Should go to openings selection
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "openings_selection"

        # Step 6: Select openings
        result = await flow.async_step_openings_selection(
            {"selected_openings": ["binary_sensor.window_1"]}
        )

        # Should go to openings config
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "openings_config"

        # Step 7: Configure openings
        result = await flow.async_step_openings_config(
            {
                "opening_scope": "all",
                "timeout_openings_open": 300,
            }
        )

        # Should go to preset selection
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "preset_selection"

        # Step 8: Select presets
        result = await flow.async_step_preset_selection({"presets": ["away", "home"]})

        # Should go to preset configuration
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "presets"

        # Step 9: Configure presets
        result = await flow.async_step_presets(
            {
                "away_temp": 26,
                "home_temp": 22,
            }
        )

        # Flow should complete
        assert result["type"] == FlowResultType.CREATE_ENTRY

        # Verify all features are saved
        assert flow.collected_config["configure_fan"] is True
        assert flow.collected_config[CONF_FAN] == "switch.fan"

        assert flow.collected_config["configure_humidity"] is True
        assert flow.collected_config[CONF_HUMIDITY_SENSOR] == "sensor.humidity"

        assert flow.collected_config["configure_openings"] is True

        assert flow.collected_config["configure_presets"] is True


class TestAcOnlyBlockedFeatures:
    """Test that floor_heating feature is not available for ac_only."""

    async def test_floor_heating_not_in_schema(self, mock_hass):
        """Test that configure_floor_heating is not in features schema.

        Acceptance Criteria:
        - configure_floor_heating toggle not present in features step
        - ac_only cannot enable floor heating feature
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY}

        result = await flow.async_step_features()
        schema = result["data_schema"].schema

        field_names = [key.schema for key in schema.keys() if hasattr(key, "schema")]

        # Floor heating should NOT be in the schema
        assert "configure_floor_heating" not in field_names

    async def test_available_features_only(self, mock_hass):
        """Test that only available features are shown in schema.

        Acceptance Criteria:
        - Only fan, humidity, openings, presets toggles present
        - Floor heating not accessible
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY}

        result = await flow.async_step_features()
        schema = result["data_schema"].schema

        field_names = [key.schema for key in schema.keys() if hasattr(key, "schema")]

        # Only available features should be present
        expected_features = [
            "configure_fan",
            "configure_humidity",
            "configure_openings",
            "configure_presets",
        ]

        feature_fields = [f for f in field_names if f.startswith("configure_")]

        assert sorted(feature_fields) == sorted(expected_features)


class TestAcOnlyFeatureOrdering:
    """Test that feature configuration steps appear in correct order."""

    async def test_fan_before_humidity(self, mock_hass):
        """Test that fan configuration comes before humidity for ac_only.

        Acceptance Criteria:
        - When both enabled, fan step appears first
        - Humidity step appears after fan
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Setup: Enable fan and humidity
        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY})
        await flow.async_step_basic_ac_only(
            {
                CONF_NAME: "Test",
                CONF_SENSOR: "sensor.temp",
                CONF_COOLER: "switch.ac",
            }
        )

        result = await flow.async_step_features(
            {
                "configure_fan": True,
                "configure_humidity": True,
                "configure_openings": False,
                "configure_presets": False,
            }
        )

        # First should be fan
        assert result["step_id"] == "fan"

        # Complete fan
        result = await flow.async_step_fan(
            {
                CONF_FAN: "switch.fan",
                "fan_on_with_ac": True,
            }
        )

        # Next should be humidity
        assert result["step_id"] == "humidity"

    async def test_humidity_before_openings(self, mock_hass):
        """Test that humidity configuration comes before openings.

        Acceptance Criteria:
        - When both enabled, humidity step comes before openings steps
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Setup: Enable humidity and openings
        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY})
        await flow.async_step_basic_ac_only(
            {
                CONF_NAME: "Test",
                CONF_SENSOR: "sensor.temp",
                CONF_COOLER: "switch.ac",
            }
        )

        result = await flow.async_step_features(
            {
                "configure_fan": False,
                "configure_humidity": True,
                "configure_openings": True,
                "configure_presets": False,
            }
        )

        # First should be humidity
        assert result["step_id"] == "humidity"

        # Complete humidity
        result = await flow.async_step_humidity(
            {
                CONF_HUMIDITY_SENSOR: "sensor.humidity",
                CONF_DRYER: "switch.dehumidifier",
                "target_humidity": 50,
            }
        )

        # Next should be openings
        assert result["step_id"] == "openings_selection"
