"""Feature integration tests for heater_cooler with fan feature.

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
    CONF_FAN,
    CONF_FAN_HOT_TOLERANCE,
    CONF_FAN_HOT_TOLERANCE_TOGGLE,
    CONF_HEATER,
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


class TestHeaterCoolerWithFan:
    """Test heater_cooler system type with fan feature enabled."""

    async def test_fan_feature_configuration_step_appears(self, mock_hass):
        """Test that fan configuration step appears when fan feature is enabled.

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

        # Enable fan feature
        features_input = {
            "configure_fan": True,
            "configure_humidity": False,
            "configure_presets": False,
            "configure_openings": False,
        }
        result = await flow.async_step_features(features_input)

        # Should proceed to fan configuration step
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "fan"

    async def test_fan_settings_saved_under_correct_keys(self, mock_hass):
        """Test that fan settings are saved under correct keys.

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

        # Enable fan feature
        features_input = {"configure_fan": True}
        await flow.async_step_features(features_input)

        # Configure fan
        fan_input = {
            CONF_FAN: "switch.fan",
            CONF_FAN_HOT_TOLERANCE: 0.5,
            CONF_FAN_HOT_TOLERANCE_TOGGLE: "switch.fan_toggle",
        }
        await flow.async_step_fan(fan_input)

        # Verify fan settings are saved correctly
        assert CONF_FAN in flow.collected_config
        assert flow.collected_config[CONF_FAN] == "switch.fan"
        assert flow.collected_config[CONF_FAN_HOT_TOLERANCE] == 0.5
        assert (
            flow.collected_config[CONF_FAN_HOT_TOLERANCE_TOGGLE] == "switch.fan_toggle"
        )

    async def test_fan_hot_tolerance_has_default_value(self, mock_hass):
        """Test that fan_hot_tolerance has default value of 0.5.

        Acceptance Criteria: Numeric fields have correct defaults when not provided
        Bug fix: fan_hot_tolerance field was missing (2025-01-06)
        """
        from custom_components.dual_smart_thermostat.schemas import get_fan_schema

        schema = get_fan_schema(defaults=None)

        # Find fan_hot_tolerance field
        fan_hot_tolerance_found = False
        for key in schema.schema.keys():
            if hasattr(key, "schema") and key.schema == CONF_FAN_HOT_TOLERANCE:
                fan_hot_tolerance_found = True
                # Check it has default of 0.5
                if hasattr(key, "default"):
                    if callable(key.default):
                        assert key.default() == 0.5
                    else:
                        assert key.default == 0.5
                break

        assert fan_hot_tolerance_found, "fan_hot_tolerance must be in schema"

    async def test_fan_hot_tolerance_toggle_is_optional(self, mock_hass):
        """Test that fan_hot_tolerance_toggle accepts empty values (vol.UNDEFINED).

        Acceptance Criteria: Optional entity fields accept empty values (vol.UNDEFINED pattern)
        Bug fix: fan_hot_tolerance_toggle validation error (2025-01-06)
        """
        import voluptuous as vol

        from custom_components.dual_smart_thermostat.schemas import get_fan_schema

        schema = get_fan_schema(defaults=None)

        # Find fan_hot_tolerance_toggle field
        toggle_found = False
        for key in schema.schema.keys():
            if hasattr(key, "schema") and key.schema == CONF_FAN_HOT_TOLERANCE_TOGGLE:
                toggle_found = True
                # Should be Optional, not Required
                assert isinstance(key, vol.Optional)
                # Should allow vol.UNDEFINED
                if hasattr(key, "default"):
                    assert key.default == vol.UNDEFINED
                break

        assert toggle_found, "fan_hot_tolerance_toggle must be in schema"

    async def test_fan_feature_with_heater_cooler_complete_flow(self, mock_hass):
        """Test complete config flow with heater_cooler + fan feature.

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

        # Step 3: Enable fan feature
        features_input = {
            "configure_fan": True,
            "configure_humidity": False,
        }
        result = await flow.async_step_features(features_input)

        # Step 4: Configure fan
        fan_input = {
            CONF_FAN: "switch.fan",
            CONF_FAN_HOT_TOLERANCE: 0.3,
        }
        result = await flow.async_step_fan(fan_input)

        # After configuring fan (last feature), flow should complete
        # Result type will be either FORM (if more steps) or CREATE_ENTRY (if done)
        assert result["type"] in [FlowResultType.FORM, FlowResultType.CREATE_ENTRY]

        # Verify all settings are collected
        assert flow.collected_config[CONF_NAME] == "Test Heater Cooler"
        assert flow.collected_config[CONF_HEATER] == "switch.heater"
        assert flow.collected_config[CONF_COOLER] == "switch.cooler"
        assert flow.collected_config[CONF_FAN] == "switch.fan"
        assert flow.collected_config[CONF_FAN_HOT_TOLERANCE] == 0.3

    async def test_fan_feature_settings_match_schema(self, mock_hass):
        """Test that fan feature settings match schema definitions.

        Acceptance Criteria: Feature settings match schema definitions
        """
        from custom_components.dual_smart_thermostat.schemas import get_fan_schema

        schema = get_fan_schema(defaults=None)

        # Extract field names from schema
        field_names = [k.schema for k in schema.schema.keys() if hasattr(k, "schema")]

        # Fan schema should include required fields
        assert CONF_FAN in field_names
        assert CONF_FAN_HOT_TOLERANCE in field_names
        assert CONF_FAN_HOT_TOLERANCE_TOGGLE in field_names
