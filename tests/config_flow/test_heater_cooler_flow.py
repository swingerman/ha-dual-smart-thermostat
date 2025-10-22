"""Tests for heater_cooler system type config and simplified options flows.

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
    CONF_COLD_TOLERANCE,
    CONF_COOLER,
    CONF_HEAT_COOL_MODE,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_MIN_DUR,
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


class TestHeaterCoolerConfigFlow:
    """Test heater_cooler config flow - Core Requirements."""

    async def test_config_flow_completes_without_error(self, mock_hass):
        """Test that heater_cooler config flow completes successfully.

        Acceptance Criteria: Flow completes without error - all steps navigate successfully
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Step 1: Select heater_cooler system type
        user_input = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
        result = await flow.async_step_user(user_input)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "heater_cooler"

        # Step 2: Configure heater_cooler basic settings
        heater_cooler_input = {
            CONF_NAME: "Test Heater Cooler",
            CONF_SENSOR: "sensor.temperature",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            CONF_HEAT_COOL_MODE: False,
            "advanced_settings": {
                CONF_COLD_TOLERANCE: 0.5,
                CONF_HOT_TOLERANCE: 0.5,
                CONF_MIN_DUR: 300,
            },
        }
        result = await flow.async_step_heater_cooler(heater_cooler_input)

        # Should proceed to features step
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "features"

    async def test_valid_configuration_created(self, mock_hass):
        """Test that valid configuration is created matching data-model.md.

        Acceptance Criteria: Valid configuration created - config entry data matches data-model.md
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}

        heater_cooler_input = {
            CONF_NAME: "Test Heater Cooler",
            CONF_SENSOR: "sensor.temperature",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            CONF_HEAT_COOL_MODE: True,
            "advanced_settings": {
                CONF_COLD_TOLERANCE: 0.3,
                CONF_HOT_TOLERANCE: 0.3,
                CONF_MIN_DUR: 600,
            },
        }

        await flow.async_step_heater_cooler(heater_cooler_input)

        # Verify configuration structure
        assert CONF_NAME in flow.collected_config
        assert CONF_SENSOR in flow.collected_config
        assert CONF_HEATER in flow.collected_config
        assert CONF_COOLER in flow.collected_config
        assert CONF_HEAT_COOL_MODE in flow.collected_config

        # Verify advanced settings are flattened to top level
        assert CONF_COLD_TOLERANCE in flow.collected_config
        assert CONF_HOT_TOLERANCE in flow.collected_config
        assert CONF_MIN_DUR in flow.collected_config

        # Verify values
        assert flow.collected_config[CONF_NAME] == "Test Heater Cooler"
        assert flow.collected_config[CONF_HEATER] == "switch.heater"
        assert flow.collected_config[CONF_COOLER] == "switch.cooler"
        assert flow.collected_config[CONF_HEAT_COOL_MODE] is True
        assert flow.collected_config[CONF_COLD_TOLERANCE] == 0.3

    async def test_all_required_fields_present(self, mock_hass):
        """Test that all required fields from schema are present in saved config.

        Acceptance Criteria: All required fields from schema present in saved config
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}

        # Get the schema
        result = await flow.async_step_heater_cooler()
        schema = result["data_schema"].schema

        # Verify required fields in schema
        required_fields = []
        for key in schema.keys():
            if hasattr(key, "schema"):
                field_name = key.schema
                # Check if field is required (not Optional)
                if not hasattr(key, "default") or key.default is None:
                    required_fields.append(field_name)

        # Required fields should include name, sensor, heater, cooler
        assert CONF_NAME in [k for k in schema.keys() if hasattr(k, "schema")]
        assert CONF_SENSOR in [k.schema for k in schema.keys() if hasattr(k, "schema")]
        assert CONF_HEATER in [k.schema for k in schema.keys() if hasattr(k, "schema")]
        assert CONF_COOLER in [k.schema for k in schema.keys() if hasattr(k, "schema")]

    async def test_advanced_settings_flattened_correctly(self, mock_hass):
        """Test that advanced settings are extracted and flattened to top level.

        Acceptance Criteria: Advanced settings flattened to top level (tolerances, min_cycle_duration)
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}

        heater_cooler_input = {
            CONF_NAME: "Test",
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            "advanced_settings": {
                CONF_COLD_TOLERANCE: 1.0,
                CONF_HOT_TOLERANCE: 2.0,
                CONF_MIN_DUR: 900,
            },
        }

        await flow.async_step_heater_cooler(heater_cooler_input)

        # Verify advanced_settings key is removed
        assert "advanced_settings" not in flow.collected_config

        # Verify settings are flattened to top level
        assert flow.collected_config[CONF_COLD_TOLERANCE] == 1.0
        assert flow.collected_config[CONF_HOT_TOLERANCE] == 2.0
        assert flow.collected_config[CONF_MIN_DUR] == 900

    async def test_validation_same_heater_cooler_entity(self, mock_hass):
        """Test validation error when heater and cooler are the same entity.

        Acceptance Criteria: Validation - same heater/cooler entity produces error
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}

        heater_cooler_input = {
            CONF_NAME: "Test",
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.same_device",
            CONF_COOLER: "switch.same_device",  # Same as heater - should error
        }

        result = await flow.async_step_heater_cooler(heater_cooler_input)

        # Should show error
        assert result["type"] == FlowResultType.FORM
        assert "errors" in result
        assert "base" in result["errors"] or CONF_COOLER in result["errors"]

    async def test_validation_same_heater_sensor_entity(self, mock_hass):
        """Test validation error when heater and sensor are the same entity.

        Acceptance Criteria: Validation - same heater/sensor entity produces error
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}

        heater_cooler_input = {
            CONF_NAME: "Test",
            CONF_SENSOR: "switch.heater",  # Wrong domain, same as heater
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
        }

        result = await flow.async_step_heater_cooler(heater_cooler_input)

        # Should show error
        assert result["type"] == FlowResultType.FORM
        assert "errors" in result


class TestHeaterCoolerOptionsFlow:
    """Test heater_cooler simplified options flow - Core Requirements."""

    async def test_options_flow_omits_name_field(self, mock_hass):
        """Test that simplified options flow does NOT include name field.

        Acceptance Criteria: name field is omitted in options flow
        """
        from custom_components.dual_smart_thermostat.options_flow import (
            OptionsFlowHandler,
        )

        # Create a mock config entry
        config_entry = Mock()
        config_entry.data = {
            CONF_NAME: "Existing Name",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
        }
        config_entry.options = {}

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass

        # Get options schema from simplified init step
        result = await flow.async_step_init()

        # Verify name field is NOT in schema
        schema_fields = [
            k.schema
            for k in result["data_schema"].schema.keys()
            if hasattr(k, "schema")
        ]
        assert CONF_NAME not in schema_fields

    async def test_options_flow_prefills_all_fields(self, mock_hass):
        """Test that simplified options flow pre-fills runtime tuning parameters from existing config.

        Acceptance Criteria: Options flow pre-fills runtime tuning parameters from existing config
        """
        from custom_components.dual_smart_thermostat.options_flow import (
            OptionsFlowHandler,
        )

        config_entry = Mock()
        config_entry.data = {
            CONF_NAME: "Existing",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
            CONF_SENSOR: "sensor.existing_temp",
            CONF_HEATER: "switch.existing_heater",
            CONF_COOLER: "switch.existing_cooler",
            CONF_HEAT_COOL_MODE: True,
            CONF_COLD_TOLERANCE: 0.7,
            CONF_HOT_TOLERANCE: 0.8,
            CONF_MIN_DUR: 450,
        }
        config_entry.options = {}

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass

        # Get simplified init step showing runtime tuning
        result = await flow.async_step_init()
        schema = result["data_schema"].schema

        # Verify runtime parameter defaults are pre-filled from existing config
        runtime_params = [CONF_COLD_TOLERANCE, CONF_HOT_TOLERANCE]
        for key in schema.keys():
            if hasattr(key, "schema"):
                field_name = key.schema
                if field_name in runtime_params and field_name in config_entry.data:
                    # Check that default matches existing value
                    if hasattr(key, "default"):
                        expected_value = config_entry.data[field_name]
                        # Note: default might be callable or direct value
                        if callable(key.default):
                            assert key.default() == expected_value
                        else:
                            assert key.default == expected_value

    async def test_options_flow_preserves_unmodified_fields(self, mock_hass):
        """Test that simplified options flow preserves fields from existing config.

        Acceptance Criteria: All existing config fields are preserved when updating runtime parameters
        """
        from custom_components.dual_smart_thermostat.options_flow import (
            OptionsFlowHandler,
        )

        config_entry = Mock()
        config_entry.data = {
            CONF_NAME: "Original Name",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
            CONF_SENSOR: "sensor.original",
            CONF_HEATER: "switch.original_heater",
            CONF_COOLER: "switch.original_cooler",
            CONF_COLD_TOLERANCE: 0.5,
            CONF_HOT_TOLERANCE: 0.5,
            CONF_MIN_DUR: 300,
        }
        config_entry.options = {}

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass

        # Only change tolerance, leave others unchanged
        options_input = {
            CONF_COLD_TOLERANCE: 0.7,
            # Other fields not provided - should use existing values
        }

        await flow.async_step_init(options_input)

        # Verify all existing fields are in collected config (merged from entry.data)
        assert flow.collected_config.get(CONF_HEATER) == "switch.original_heater"
        assert flow.collected_config.get(CONF_COOLER) == "switch.original_cooler"
        assert flow.collected_config.get(CONF_SENSOR) == "sensor.original"
        # Updated field should have new value
        assert flow.collected_config.get(CONF_COLD_TOLERANCE) == 0.7

    async def test_options_flow_system_type_display_non_editable(self, mock_hass):
        """Test that system type is preserved but not shown in simplified options flow.

        Acceptance Criteria: System type is preserved in the config entry (not editable in options flow)
        """
        from custom_components.dual_smart_thermostat.options_flow import (
            OptionsFlowHandler,
        )

        config_entry = Mock()
        config_entry.data = {
            CONF_NAME: "Test",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
        }
        config_entry.options = {}

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass

        # Initialize simplified options flow
        result = await flow.async_step_init()

        # System type should NOT be in the form (not editable)
        assert result["type"] == FlowResultType.FORM

        # The simplified form shows runtime tuning only, not system type
        schema = result["data_schema"].schema
        schema_field_names = [str(k) for k in schema.keys()]

        # Verify system type is NOT in schema (use reconfigure flow to change it)
        assert not any(CONF_SYSTEM_TYPE in name for name in schema_field_names)

        # But it should be preserved in the config
        current_config = flow._get_current_config()
        assert current_config[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_HEATER_COOLER

    async def test_options_flow_completes_without_error(self, mock_hass):
        """Test that simplified options flow completes without error.

        Acceptance Criteria: Flow completes without error - all steps navigate successfully
        """
        from custom_components.dual_smart_thermostat.options_flow import (
            OptionsFlowHandler,
        )

        config_entry = Mock()
        config_entry.data = {
            CONF_NAME: "Test",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
        }
        config_entry.options = {}

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass

        # Start simplified flow
        result = await flow.async_step_init()

        # Should show form without errors
        assert result["type"] == FlowResultType.FORM
        assert "errors" not in result or not result["errors"]

    async def test_options_flow_updated_config_matches_data_model(self, mock_hass):
        """Test that updated runtime tuning parameters are collected correctly.

        Acceptance Criteria: Updated runtime tuning parameters are collected correctly
        """
        from custom_components.dual_smart_thermostat.options_flow import (
            OptionsFlowHandler,
        )

        config_entry = Mock()
        config_entry.data = {
            CONF_NAME: "Test",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
            CONF_SENSOR: "sensor.old_temp",
            CONF_HEATER: "switch.old_heater",
            CONF_COOLER: "switch.old_cooler",
            CONF_COLD_TOLERANCE: 0.3,
            CONF_HOT_TOLERANCE: 0.3,
            CONF_MIN_DUR: 300,
        }
        config_entry.options = {}

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass

        # Update runtime tuning parameters only (entities are in reconfigure flow)
        options_input = {
            CONF_COLD_TOLERANCE: 0.5,
            CONF_HOT_TOLERANCE: 0.5,
        }

        await flow.async_step_init(options_input)

        # Verify all existing config is preserved
        assert CONF_SENSOR in flow.collected_config
        assert CONF_HEATER in flow.collected_config
        assert CONF_COOLER in flow.collected_config
        assert CONF_COLD_TOLERANCE in flow.collected_config
        assert CONF_HOT_TOLERANCE in flow.collected_config

        # Verify existing values are preserved
        assert flow.collected_config[CONF_SENSOR] == "sensor.old_temp"
        assert flow.collected_config[CONF_HEATER] == "switch.old_heater"
        assert flow.collected_config[CONF_COOLER] == "switch.old_cooler"

        # Verify updated runtime parameters
        assert flow.collected_config[CONF_COLD_TOLERANCE] == 0.5
        assert flow.collected_config[CONF_HOT_TOLERANCE] == 0.5
