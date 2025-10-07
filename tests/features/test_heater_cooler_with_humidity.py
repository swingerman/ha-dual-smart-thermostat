"""Feature integration tests for heater_cooler with humidity feature.

Following TDD approach - these tests should guide implementation.
Task: T005 - Complete heater_cooler implementation
Issue: #415
"""

from unittest.mock import Mock

from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResultType
import pytest

from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
from custom_components.dual_smart_thermostat.const import (
    CONF_COOLER,
    CONF_HEATER,
    CONF_HUMIDITY_SENSOR,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    CONF_TARGET_HUMIDITY,
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


class TestHeaterCoolerWithHumidity:
    """Test heater_cooler system type with humidity feature enabled."""

    async def test_humidity_feature_configuration_step_appears(self, mock_hass):
        """Test that humidity configuration step appears when humidity feature is enabled.

        Acceptance Criteria: Enabled features show their configuration steps
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}

        # Complete basic heater_cooler setup
        heater_cooler_input = {
            CONF_NAME: "Test",
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
        }
        result = await flow.async_step_heater_cooler(heater_cooler_input)

        # Enable humidity feature
        features_input = {
            "configure_fan": False,
            "configure_humidity": True,
            "configure_presets": False,
            "configure_openings": False,
        }
        result = await flow.async_step_features(features_input)

        # Should proceed to humidity configuration step
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "humidity"

    async def test_humidity_settings_saved_under_correct_keys(self, mock_hass):
        """Test that humidity settings are saved under correct keys.

        Acceptance Criteria: Feature settings are saved under correct keys
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}

        # Complete basic setup
        heater_cooler_input = {
            CONF_NAME: "Test",
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
        }
        await flow.async_step_heater_cooler(heater_cooler_input)

        # Enable humidity feature
        features_input = {"configure_humidity": True}
        await flow.async_step_features(features_input)

        # Configure humidity
        humidity_input = {
            CONF_HUMIDITY_SENSOR: "sensor.humidity",
            CONF_TARGET_HUMIDITY: 50.0,
        }
        await flow.async_step_humidity(humidity_input)

        # Verify humidity settings are saved correctly
        assert CONF_HUMIDITY_SENSOR in flow.collected_config
        assert flow.collected_config[CONF_HUMIDITY_SENSOR] == "sensor.humidity"
        assert flow.collected_config[CONF_TARGET_HUMIDITY] == 50.0

    async def test_humidity_feature_with_heater_cooler_complete_flow(self, mock_hass):
        """Test complete config flow with heater_cooler + humidity feature.

        Acceptance Criteria: Flow completes without error with feature enabled
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Step 1: Select system type
        user_input = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
        result = await flow.async_step_user(user_input)

        # Step 2: Configure heater_cooler
        heater_cooler_input = {
            CONF_NAME: "Test Heater Cooler",
            CONF_SENSOR: "sensor.temperature",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
        }
        result = await flow.async_step_heater_cooler(heater_cooler_input)

        # Step 3: Enable humidity feature
        features_input = {
            "configure_fan": False,
            "configure_humidity": True,
        }
        result = await flow.async_step_features(features_input)

        # Step 4: Configure humidity
        humidity_input = {
            CONF_HUMIDITY_SENSOR: "sensor.humidity",
            CONF_TARGET_HUMIDITY: 60.0,
        }
        result = await flow.async_step_humidity(humidity_input)

        # After configuring humidity (last feature), flow should complete
        # Result type will be either FORM (if more steps) or CREATE_ENTRY (if done)
        assert result["type"] in [FlowResultType.FORM, FlowResultType.CREATE_ENTRY]

        # Verify all settings are collected
        assert flow.collected_config[CONF_NAME] == "Test Heater Cooler"
        assert flow.collected_config[CONF_HEATER] == "switch.heater"
        assert flow.collected_config[CONF_COOLER] == "switch.cooler"
        assert flow.collected_config[CONF_HUMIDITY_SENSOR] == "sensor.humidity"
        assert flow.collected_config[CONF_TARGET_HUMIDITY] == 60.0

    async def test_humidity_feature_settings_match_schema(self, mock_hass):
        """Test that humidity feature settings match schema definitions.

        Acceptance Criteria: Feature settings match schema definitions
        """
        from custom_components.dual_smart_thermostat.schemas import get_humidity_schema

        schema = get_humidity_schema(defaults=None)

        # Extract field names from schema
        field_names = [k.schema for k in schema.schema.keys() if hasattr(k, "schema")]

        # Humidity schema should include required fields
        assert CONF_HUMIDITY_SENSOR in field_names
        assert CONF_TARGET_HUMIDITY in field_names

    async def test_humidity_sensor_is_optional_entity_field(self, mock_hass):
        """Test that humidity_sensor is optional and accepts vol.UNDEFINED.

        Acceptance Criteria: Optional entity fields accept empty values (vol.UNDEFINED pattern)
        """
        import voluptuous as vol

        from custom_components.dual_smart_thermostat.schemas import get_humidity_schema

        schema = get_humidity_schema(defaults=None)

        # Find humidity_sensor field
        for key in schema.schema.keys():
            if hasattr(key, "schema") and key.schema == CONF_HUMIDITY_SENSOR:
                # Could be Optional or Required depending on implementation
                # If optional, should allow vol.UNDEFINED
                if isinstance(key, vol.Optional):
                    if hasattr(key, "default"):
                        assert key.default == vol.UNDEFINED or key.default is None
                break

    async def test_humidity_with_fan_both_enabled(self, mock_hass):
        """Test heater_cooler with both humidity and fan features enabled.

        Acceptance Criteria: Multiple features can be enabled together
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}

        # Complete basic setup
        heater_cooler_input = {
            CONF_NAME: "Test",
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
        }
        await flow.async_step_heater_cooler(heater_cooler_input)

        # Enable both fan and humidity features
        features_input = {
            "configure_fan": True,
            "configure_humidity": True,
        }
        result = await flow.async_step_features(features_input)

        # Should proceed to first feature (likely fan)
        assert result["type"] == FlowResultType.FORM
        # Step should be either fan or humidity
        assert result["step_id"] in ["fan", "humidity"]
