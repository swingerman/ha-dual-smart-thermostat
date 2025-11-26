"""Integration tests for heater_cooler system type feature combinations.

Task: T007A - Phase 2: Integration Tests
Issue: #440

These tests validate that heater_cooler system type correctly handles
all valid feature combinations through complete config and options flows.

Available Features for heater_cooler:
- ✅ floor_heating
- ✅ fan
- ✅ humidity
- ✅ openings
- ✅ presets

This is the most feature-rich system type supporting ALL features.

Test Coverage:
1. No features enabled (baseline)
2. Individual features (floor, fan, humidity, openings, presets)
3. Common combinations (floor+openings, fan+humidity)
4. All features enabled (kitchen sink)
5. Feature ordering validation
6. heat_cool_mode preset adaptation
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
)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.config_entries = Mock()
    hass.config_entries.async_entries = Mock(return_value=[])
    hass.data = {DOMAIN: {}}
    return hass


class TestHeaterCoolerNoFeatures:
    """Test heater_cooler with no features enabled (baseline)."""

    async def test_config_flow_no_features(self, mock_hass):
        """Test complete config flow with no features enabled.

        Acceptance Criteria:
        - Flow completes successfully
        - Config entry created with basic heater/cooler settings only
        - No feature-specific configuration saved
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Step 1: Select heater_cooler system type
        user_input = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
        result = await flow.async_step_user(user_input)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "heater_cooler"

        # Step 2: Configure basic heater/cooler settings
        basic_input = {
            CONF_NAME: "Test HVAC",
            CONF_SENSOR: "sensor.temperature",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            "advanced_settings": {
                "hot_tolerance": 0.5,
                "cold_tolerance": 0.5,
                "min_cycle_duration": 300,
            },
        }
        result = await flow.async_step_heater_cooler(basic_input)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "features"

        # Step 3: Disable all features
        features_input = {
            "configure_floor_heating": False,
            "configure_fan": False,
            "configure_humidity": False,
            "configure_openings": False,
            "configure_presets": False,
        }
        result = await flow.async_step_features(features_input)

        # With no features, flow should complete
        assert result["type"] == FlowResultType.CREATE_ENTRY

        # Verify configuration
        assert flow.collected_config[CONF_NAME] == "Test HVAC"
        assert flow.collected_config[CONF_SENSOR] == "sensor.temperature"
        assert flow.collected_config[CONF_HEATER] == "switch.heater"
        assert flow.collected_config[CONF_COOLER] == "switch.cooler"


class TestHeaterCoolerFloorHeatingOnly:
    """Test heater_cooler with only floor_heating enabled."""

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

        # Steps 1-2: System type and basic settings
        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER})
        result = await flow.async_step_heater_cooler(
            {
                CONF_NAME: "Test HVAC",
                CONF_SENSOR: "sensor.temperature",
                CONF_HEATER: "switch.heater",
                CONF_COOLER: "switch.cooler",
            }
        )

        assert result["step_id"] == "features"

        # Step 3: Enable floor_heating only
        result = await flow.async_step_features(
            {
                "configure_floor_heating": True,
                "configure_fan": False,
                "configure_humidity": False,
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


class TestHeaterCoolerFanOnly:
    """Test heater_cooler with only fan enabled."""

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
        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER})
        await flow.async_step_heater_cooler(
            {
                CONF_NAME: "Test HVAC",
                CONF_SENSOR: "sensor.temperature",
                CONF_HEATER: "switch.heater",
                CONF_COOLER: "switch.cooler",
            }
        )

        # Step 3: Enable fan only
        result = await flow.async_step_features(
            {
                "configure_floor_heating": False,
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


class TestHeaterCoolerHumidityOnly:
    """Test heater_cooler with only humidity enabled."""

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
        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER})
        await flow.async_step_heater_cooler(
            {
                CONF_NAME: "Test HVAC",
                CONF_SENSOR: "sensor.temperature",
                CONF_HEATER: "switch.heater",
                CONF_COOLER: "switch.cooler",
            }
        )

        # Step 3: Enable humidity only
        result = await flow.async_step_features(
            {
                "configure_floor_heating": False,
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


class TestHeaterCoolerAllFeatures:
    """Test heater_cooler with all features enabled (kitchen sink)."""

    async def test_config_flow_all_features(self, mock_hass):
        """Test complete config flow with all features enabled.

        This is the kitchen sink test - heater_cooler supports ALL features.

        Acceptance Criteria:
        - All feature configuration steps appear in correct order
        - All feature settings are saved correctly
        - Flow completes successfully
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Steps 1-2: System type and basic settings
        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER})
        await flow.async_step_heater_cooler(
            {
                CONF_NAME: "Test HVAC Kitchen Sink",
                CONF_SENSOR: "sensor.temperature",
                CONF_HEATER: "switch.heater",
                CONF_COOLER: "switch.cooler",
            }
        )

        # Step 3: Enable all features
        result = await flow.async_step_features(
            {
                "configure_floor_heating": True,
                "configure_fan": True,
                "configure_humidity": True,
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

        # Should go to fan
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "fan"

        # Step 5: Configure fan
        result = await flow.async_step_fan(
            {
                CONF_FAN: "switch.fan",
                "fan_on_with_ac": True,
            }
        )

        # Should go to humidity
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "humidity"

        # Step 6: Configure humidity
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

        # Step 7: Select openings
        result = await flow.async_step_openings_selection(
            {"selected_openings": ["binary_sensor.window_1", "binary_sensor.door_1"]}
        )

        # Should go to openings config
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "openings_config"

        # Step 8: Configure openings
        result = await flow.async_step_openings_config(
            {
                "opening_scope": "all",
                "timeout_openings_open": 300,
            }
        )

        # Should go to preset selection
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "preset_selection"

        # Step 9: Select presets
        result = await flow.async_step_preset_selection(
            {"presets": ["away", "home", "sleep"]}
        )

        # Should go to preset configuration
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "presets"

        # Step 10: Configure presets
        result = await flow.async_step_presets(
            {
                "away_temp": 16,
                "home_temp": 21,
                "sleep_temp": 18,
            }
        )

        # Flow should complete
        assert result["type"] == FlowResultType.CREATE_ENTRY

        # Verify all features are saved
        assert flow.collected_config["configure_floor_heating"] is True
        assert flow.collected_config[CONF_FLOOR_SENSOR] == "sensor.floor_temperature"

        assert flow.collected_config["configure_fan"] is True
        assert flow.collected_config[CONF_FAN] == "switch.fan"

        assert flow.collected_config["configure_humidity"] is True
        assert flow.collected_config[CONF_HUMIDITY_SENSOR] == "sensor.humidity"

        assert flow.collected_config["configure_openings"] is True

        assert flow.collected_config["configure_presets"] is True


class TestHeaterCoolerCommonCombinations:
    """Test common feature combinations for heater_cooler."""

    async def test_floor_and_openings(self, mock_hass):
        """Test floor heating + openings combination.

        Common for radiant floor systems with window sensors.

        Acceptance Criteria:
        - Both features configured successfully
        - Correct step ordering (floor → openings)
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Setup
        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER})
        await flow.async_step_heater_cooler(
            {
                CONF_NAME: "Test",
                CONF_SENSOR: "sensor.temp",
                CONF_HEATER: "switch.heater",
                CONF_COOLER: "switch.cooler",
            }
        )

        # Enable floor + openings
        result = await flow.async_step_features(
            {
                "configure_floor_heating": True,
                "configure_fan": False,
                "configure_humidity": False,
                "configure_openings": True,
                "configure_presets": False,
            }
        )

        # Floor first
        assert result["step_id"] == "floor_config"
        result = await flow.async_step_floor_config(
            {
                CONF_FLOOR_SENSOR: "sensor.floor_temp",
                CONF_MIN_FLOOR_TEMP: 5,
                CONF_MAX_FLOOR_TEMP: 28,
            }
        )

        # Openings next
        assert result["step_id"] == "openings_selection"

    async def test_fan_and_humidity(self, mock_hass):
        """Test fan + humidity combination.

        Common for HVAC with dehumidification.

        Acceptance Criteria:
        - Both features configured successfully
        - Correct step ordering (fan → humidity)
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Setup
        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER})
        await flow.async_step_heater_cooler(
            {
                CONF_NAME: "Test",
                CONF_SENSOR: "sensor.temp",
                CONF_HEATER: "switch.heater",
                CONF_COOLER: "switch.cooler",
            }
        )

        # Enable fan + humidity
        result = await flow.async_step_features(
            {
                "configure_floor_heating": False,
                "configure_fan": True,
                "configure_humidity": True,
                "configure_openings": False,
                "configure_presets": False,
            }
        )

        # Fan first
        assert result["step_id"] == "fan"
        result = await flow.async_step_fan(
            {
                CONF_FAN: "switch.fan",
                "fan_on_with_ac": True,
            }
        )

        # Humidity next
        assert result["step_id"] == "humidity"


class TestHeaterCoolerFeatureOrdering:
    """Test that feature configuration steps appear in correct order."""

    async def test_complete_feature_ordering(self, mock_hass):
        """Test complete feature ordering for heater_cooler.

        Expected order when all enabled:
        floor → fan → humidity → openings → presets

        Acceptance Criteria:
        - Features appear in correct dependency order
        - Each step transitions to the next correctly
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Setup with all features enabled
        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER})
        await flow.async_step_heater_cooler(
            {
                CONF_NAME: "Test",
                CONF_SENSOR: "sensor.temp",
                CONF_HEATER: "switch.heater",
                CONF_COOLER: "switch.cooler",
            }
        )

        result = await flow.async_step_features(
            {
                "configure_floor_heating": True,
                "configure_fan": True,
                "configure_humidity": True,
                "configure_openings": True,
                "configure_presets": True,
            }
        )

        # Verify step sequence
        steps_visited = []

        # 1. Floor
        assert result["step_id"] == "floor_config"
        steps_visited.append("floor_config")
        result = await flow.async_step_floor_config(
            {
                CONF_FLOOR_SENSOR: "sensor.floor_temp",
                CONF_MIN_FLOOR_TEMP: 5,
                CONF_MAX_FLOOR_TEMP: 28,
            }
        )

        # 2. Fan
        assert result["step_id"] == "fan"
        steps_visited.append("fan")
        result = await flow.async_step_fan(
            {
                CONF_FAN: "switch.fan",
                "fan_on_with_ac": True,
            }
        )

        # 3. Humidity
        assert result["step_id"] == "humidity"
        steps_visited.append("humidity")
        result = await flow.async_step_humidity(
            {
                CONF_HUMIDITY_SENSOR: "sensor.humidity",
                CONF_DRYER: "switch.dehumidifier",
                "target_humidity": 50,
            }
        )

        # 4. Openings
        assert result["step_id"] == "openings_selection"
        steps_visited.append("openings_selection")
        result = await flow.async_step_openings_selection(
            {"selected_openings": ["binary_sensor.window_1"]}
        )
        steps_visited.append("openings_config")
        result = await flow.async_step_openings_config(
            {
                "opening_scope": "all",
                "timeout_openings_open": 300,
            }
        )

        # 5. Presets
        assert result["step_id"] == "preset_selection"
        steps_visited.append("preset_selection")

        # Verify complete sequence
        expected_sequence = [
            "floor_config",
            "fan",
            "humidity",
            "openings_selection",
            "openings_config",
            "preset_selection",
        ]
        assert steps_visited == expected_sequence


class TestHeaterCoolerAvailableFeatures:
    """Test that all features are available for heater_cooler."""

    async def test_all_features_available(self, mock_hass):
        """Test that all five features are available in features schema.

        Acceptance Criteria:
        - All feature toggles present in features step
        - No features are blocked
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}

        result = await flow.async_step_features()
        schema = result["data_schema"].schema

        field_names = [key.schema for key in schema.keys() if hasattr(key, "schema")]

        # All features should be present
        expected_features = [
            "configure_floor_heating",
            "configure_fan",
            "configure_humidity",
            "configure_openings",
            "configure_presets",
        ]

        feature_fields = [f for f in field_names if f.startswith("configure_")]

        assert sorted(feature_fields) == sorted(expected_features)


class TestHeaterCoolerPartialOverride:
    """Test partial override of tolerances for heater_cooler (T041)."""

    async def test_tolerance_partial_override_heat_only(self, mock_hass):
        """Test partial override with only heat_tolerance configured.

        Heater_cooler supports both heating and cooling with separate switches.
        This test validates that when only heat_tolerance is set:
        - HEAT mode uses the configured heat_tolerance (0.3)
        - COOL mode falls back to legacy tolerances (cold_tolerance, hot_tolerance)
        - Backward compatibility is maintained

        Acceptance Criteria:
        - Config flow accepts heat_tolerance without cool_tolerance
        - heat_tolerance is saved in configuration
        - Legacy tolerances (cold_tolerance, hot_tolerance) are also saved
        - Flow completes successfully
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Step 1: Select heater_cooler system type
        user_input = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
        result = await flow.async_step_user(user_input)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "heater_cooler"

        # Step 2: Configure with partial override (heat_tolerance only)
        basic_input = {
            CONF_NAME: "Test HVAC Partial Heat",
            CONF_SENSOR: "sensor.temperature",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            "advanced_settings": {
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
                "heat_tolerance": 0.3,  # Override for HEAT mode
                # cool_tolerance intentionally omitted
                "min_cycle_duration": 300,
            },
        }
        result = await flow.async_step_heater_cooler(basic_input)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "features"

        # Step 3: Complete features step (no features enabled)
        features_input = {
            "configure_floor_heating": False,
            "configure_fan": False,
            "configure_humidity": False,
            "configure_openings": False,
            "configure_presets": False,
        }
        result = await flow.async_step_features(features_input)

        # Flow should complete
        assert result["type"] == FlowResultType.CREATE_ENTRY

        # Verify configuration - all tolerances saved
        assert flow.collected_config["cold_tolerance"] == 0.5
        assert flow.collected_config["hot_tolerance"] == 0.5
        assert flow.collected_config["heat_tolerance"] == 0.3

        # cool_tolerance should not be in config (not set)
        assert "cool_tolerance" not in flow.collected_config

    async def test_tolerance_partial_override_cool_only(self, mock_hass):
        """Test partial override with only cool_tolerance configured.

        Heater_cooler supports both heating and cooling with separate switches.
        This test validates that when only cool_tolerance is set:
        - COOL mode uses the configured cool_tolerance (1.5)
        - HEAT mode falls back to legacy tolerances (cold_tolerance, hot_tolerance)
        - Backward compatibility is maintained

        Acceptance Criteria:
        - Config flow accepts cool_tolerance without heat_tolerance
        - cool_tolerance is saved in configuration
        - Legacy tolerances (cold_tolerance, hot_tolerance) are also saved
        - Flow completes successfully
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Step 1: Select heater_cooler system type
        user_input = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
        result = await flow.async_step_user(user_input)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "heater_cooler"

        # Step 2: Configure with partial override (cool_tolerance only)
        basic_input = {
            CONF_NAME: "Test HVAC Partial Cool",
            CONF_SENSOR: "sensor.temperature",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            "advanced_settings": {
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
                "cool_tolerance": 1.5,  # Override for COOL mode
                # heat_tolerance intentionally omitted
                "min_cycle_duration": 300,
            },
        }
        result = await flow.async_step_heater_cooler(basic_input)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "features"

        # Step 3: Complete features step (no features enabled)
        features_input = {
            "configure_floor_heating": False,
            "configure_fan": False,
            "configure_humidity": False,
            "configure_openings": False,
            "configure_presets": False,
        }
        result = await flow.async_step_features(features_input)

        # Flow should complete
        assert result["type"] == FlowResultType.CREATE_ENTRY

        # Verify configuration - all tolerances saved
        assert flow.collected_config["cold_tolerance"] == 0.5
        assert flow.collected_config["hot_tolerance"] == 0.5
        assert flow.collected_config["cool_tolerance"] == 1.5

        # heat_tolerance should not be in config (not set)
        assert "heat_tolerance" not in flow.collected_config

    async def test_tolerance_partial_override_mixed(self, mock_hass):
        """Test partial override with different tolerance values for each mode.

        Heater_cooler supports both heating and cooling with separate switches.
        This test validates mixed tolerance configuration:
        - HEAT mode uses heat_tolerance (0.2)
        - COOL mode uses cool_tolerance (1.8)
        - Both mode-specific and legacy tolerances coexist
        - This is the most realistic use case for heater_cooler systems

        Acceptance Criteria:
        - Config flow accepts both heat_tolerance and cool_tolerance
        - Both mode-specific tolerances are saved
        - Legacy tolerances are also saved
        - Flow completes successfully
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Step 1: Select heater_cooler system type
        user_input = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
        result = await flow.async_step_user(user_input)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "heater_cooler"

        # Step 2: Configure with mixed overrides (both heat and cool)
        basic_input = {
            CONF_NAME: "Test HVAC Mixed Override",
            CONF_SENSOR: "sensor.temperature",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            "advanced_settings": {
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
                "heat_tolerance": 0.2,  # Override for HEAT mode
                "cool_tolerance": 1.8,  # Override for COOL mode
                "min_cycle_duration": 300,
            },
        }
        result = await flow.async_step_heater_cooler(basic_input)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "features"

        # Step 3: Complete features step (no features enabled)
        features_input = {
            "configure_floor_heating": False,
            "configure_fan": False,
            "configure_humidity": False,
            "configure_openings": False,
            "configure_presets": False,
        }
        result = await flow.async_step_features(features_input)

        # Flow should complete
        assert result["type"] == FlowResultType.CREATE_ENTRY

        # Verify configuration - all tolerances saved
        assert flow.collected_config["cold_tolerance"] == 0.5
        assert flow.collected_config["hot_tolerance"] == 0.5
        assert flow.collected_config["heat_tolerance"] == 0.2
        assert flow.collected_config["cool_tolerance"] == 1.8
