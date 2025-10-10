"""Tests for config validation integration with config_flow and options_flow."""

from unittest.mock import MagicMock, patch

from homeassistant.const import CONF_NAME
import pytest

from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
from custom_components.dual_smart_thermostat.const import CONF_HEATER, CONF_SENSOR


@pytest.fixture
def mock_hass():
    """Mock Home Assistant instance."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    return hass


class TestConfigFlowValidation:
    """Test config flow validation using models."""

    @pytest.mark.asyncio
    async def test_config_flow_validates_on_create_entry(self, mock_hass):
        """Test that config flow validates configuration before creating entry."""
        flow = ConfigFlowHandler()
        flow.hass = mock_hass

        # Setup minimal valid configuration
        flow.collected_config = {
            CONF_NAME: "Test Thermostat",
            CONF_SENSOR: "sensor.test_temp",
            CONF_HEATER: "switch.test_heater",
            "system_type": "simple_heater",
        }

        with patch(
            "custom_components.dual_smart_thermostat.config_flow.validate_config_with_models"
        ) as mock_validate:
            mock_validate.return_value = True

            # Simulate finishing preset selection without presets
            await flow.async_step_preset_selection(user_input={})

            # Validation should have been called
            mock_validate.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_flow_logs_warning_on_invalid_config(self, mock_hass):
        """Test that config flow logs warning when validation fails."""
        flow = ConfigFlowHandler()
        flow.hass = mock_hass

        # Setup invalid configuration (missing required fields)
        flow.collected_config = {
            CONF_NAME: "Test Thermostat",
            # Missing CONF_SENSOR - invalid
            "system_type": "simple_heater",
        }

        with patch(
            "custom_components.dual_smart_thermostat.config_flow.validate_config_with_models"
        ) as mock_validate:
            with patch(
                "custom_components.dual_smart_thermostat.config_flow._LOGGER"
            ) as mock_logger:
                mock_validate.return_value = False

                # Simulate finishing preset selection without presets
                await flow.async_step_preset_selection(user_input={})

                # Validation should have failed and logged warning
                mock_validate.assert_called_once()
                mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_flow_import_validates_config(self, mock_hass):
        """Test that config import step validates configuration."""
        flow = ConfigFlowHandler()
        flow.hass = mock_hass

        import_config = {
            CONF_NAME: "Imported Thermostat",
            CONF_SENSOR: "sensor.imported_temp",
            CONF_HEATER: "switch.imported_heater",
            "system_type": "simple_heater",
        }

        with patch(
            "custom_components.dual_smart_thermostat.config_flow.validate_config_with_models"
        ) as mock_validate:
            mock_validate.return_value = True

            await flow.async_step_import(import_config)

            # Validation should have been called
            mock_validate.assert_called_once_with(import_config)


class TestOptionsFlowValidation:
    """Test options flow validation using models."""

    @pytest.mark.asyncio
    async def test_options_flow_validates_config(self):
        """Test that options flow validation is called when needed."""
        # Simple test to verify validate_config_with_models can be called
        from custom_components.dual_smart_thermostat.config_validation import (
            validate_config_with_models,
        )

        valid_config = {
            CONF_NAME: "Test Thermostat",
            CONF_SENSOR: "sensor.test_temp",
            CONF_HEATER: "switch.test_heater",
            "system_type": "simple_heater",
        }

        # Should validate successfully
        assert validate_config_with_models(valid_config) is True

        # Missing required field should fail
        invalid_config = {
            CONF_NAME: "Test Thermostat",
            # Missing CONF_SENSOR
            "system_type": "simple_heater",
        }

        assert validate_config_with_models(invalid_config) is False
