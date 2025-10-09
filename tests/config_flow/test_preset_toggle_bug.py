"""Test for preset toggle bug in options flow.

Bug Report: When reopening options flow after configuring presets in config flow,
the configure_presets toggle is not checked, even though presets are configured.

Issue: options_flow.py checks for preset keys like "away", "home" directly,
but should check for "presets" list or preset config keys like "away_temp".
"""

from unittest.mock import Mock, PropertyMock

from homeassistant.const import CONF_NAME
import pytest

from custom_components.dual_smart_thermostat.const import (
    CONF_HEATER,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    DOMAIN,
    SYSTEM_TYPE_SIMPLE_HEATER,
)
from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler


@pytest.fixture
def mock_config_entry_with_presets():
    """Create a mock config entry with presets configured."""
    entry = Mock()
    entry.data = {
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER,
        CONF_NAME: "Test Heater",
        CONF_SENSOR: "sensor.temperature",
        CONF_HEATER: "switch.heater",
        # Presets were configured
        "presets": ["away", "sleep"],
        "away_temp": 16,
        "sleep_temp": 18,
        "configure_presets": True,
    }
    entry.options = {}
    entry.entry_id = "test_entry_id"
    return entry


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.config_entries = Mock()
    hass.data = {DOMAIN: {}}
    return hass


class TestPresetToggleBug:
    """Test preset toggle bug in options flow."""

    async def test_preset_toggle_checked_when_presets_configured(
        self, mock_hass, mock_config_entry_with_presets
    ):
        """Test that configure_presets toggle is checked when presets are configured.

        Bug: When reopening options flow, configure_presets should be checked
        if presets were configured in config flow.

        Expected: configure_presets default should be True
        Actual: configure_presets default is False (bug)
        """
        # Create options flow
        flow = OptionsFlowHandler(mock_config_entry_with_presets)
        flow.hass = mock_hass

        # Mock the config_entry property to return our mock
        type(flow).config_entry = PropertyMock(
            return_value=mock_config_entry_with_presets
        )

        # Show features step (this is where the bug manifests)
        result = await flow.async_step_features()

        # Extract the schema to check defaults
        schema = result["data_schema"].schema

        # Find the configure_presets field and its default value
        configure_presets_default = None
        for key in schema.keys():
            if hasattr(key, "schema") and key.schema == "configure_presets":
                default_value = getattr(key, "default", None)
                # Default might be a callable (lambda function)
                if callable(default_value):
                    configure_presets_default = default_value()
                else:
                    configure_presets_default = default_value
                break

        # BUG: This assertion should pass but currently fails
        # The default should be True because presets are configured
        assert (
            configure_presets_default is True
        ), f"configure_presets default should be True when presets are configured, got {configure_presets_default}"
