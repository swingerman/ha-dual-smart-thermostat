"""Test that AC-only systems have consistent advanced settings in config and options flows."""

from unittest.mock import Mock

from homeassistant.config_entries import ConfigEntry
import pytest

from custom_components.dual_smart_thermostat.const import (
    CONF_COLD_TOLERANCE,
    CONF_HOT_TOLERANCE,
    CONF_KEEP_ALIVE,
    CONF_MIN_DUR,
    CONF_SYSTEM_TYPE,
    SYSTEM_TYPE_AC_ONLY,
)
from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler


class TestACOnlyAdvancedSettings:
    """Test AC-only advanced settings consistency between flows."""

    def test_config_flow_ac_only_has_advanced_section(self):
        """Test that config flow AC-only system has advanced settings section."""
        from custom_components.dual_smart_thermostat.schemas import get_basic_ac_schema

        schema = get_basic_ac_schema(defaults=None, include_name=True)
        schema_dict = schema.schema

        # Check that advanced_settings section exists
        advanced_field_found = False
        for key in schema_dict.keys():
            if hasattr(key, "schema") and "advanced_settings" in str(key.schema):
                advanced_field_found = True
                break

        assert (
            advanced_field_found
        ), "Advanced settings section not found in AC-only config schema"

    def test_options_flow_ac_only_has_advanced_section(self):
        """Test that options flow AC-only system has advanced settings section."""
        from custom_components.dual_smart_thermostat.schemas import get_basic_ac_schema

        mock_data = {
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY,
            "heater": "switch.ac",
            "sensor": "sensor.temp",
            "name": "Test Thermostat",
            CONF_COLD_TOLERANCE: 0.3,
            CONF_HOT_TOLERANCE: 0.3,
            CONF_MIN_DUR: 300,
            CONF_KEEP_ALIVE: 300,
        }

        schema = get_basic_ac_schema(defaults=mock_data, include_name=False)
        schema_dict = schema.schema

        # Check that advanced_settings section exists
        advanced_field_found = False
        for key in schema_dict.keys():
            if hasattr(key, "schema") and "advanced_settings" in str(key.schema):
                advanced_field_found = True
                break

        assert (
            advanced_field_found
        ), "Advanced settings section not found in AC-only options schema"

    @pytest.mark.asyncio
    async def test_options_flow_init_step_ac_only(self):
        """Test that options flow init step correctly handles AC-only system."""
        # Mock config entry
        mock_entry = Mock(spec=ConfigEntry)
        mock_entry.data = {
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY,
            "heater": "switch.ac",
            "sensor": "sensor.temp",
            "name": "Test Thermostat",
            CONF_COLD_TOLERANCE: 0.3,
            CONF_HOT_TOLERANCE: 0.3,
            CONF_KEEP_ALIVE: 300,  # Add this so advanced_settings appears
        }
        mock_entry.options = {}

        flow = OptionsFlowHandler(mock_entry)
        flow.hass = Mock()
        flow.collected_config = {}

        # Mock the _get_entry method
        flow._get_entry = Mock(return_value=mock_entry)

        # Mock the _determine_options_next_step method
        async def mock_next_step():
            return {"type": "form", "step_id": "next"}

        flow._determine_options_next_step = mock_next_step

        # Test the init step with no user input (should show form)
        result = await flow.async_step_init(None)

        assert result["type"] == "form"
        assert result["step_id"] == "init"

        # Check that the schema has advanced settings section
        schema_dict = result["data_schema"].schema
        advanced_field_found = False
        for key in schema_dict.keys():
            if hasattr(key, "schema") and "advanced_settings" in str(key.schema):
                advanced_field_found = True
                break

        assert (
            advanced_field_found
        ), "Advanced settings section not found in options flow AC-only init step"


if __name__ == "__main__":
    pytest.main([__file__])
