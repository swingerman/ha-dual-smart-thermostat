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
        """Test that options flow shows preset_selection step when presets are configured.

        With simplified options flow, there is no features toggle step.
        Instead, the flow automatically navigates through configured features.
        This test verifies that preset_selection appears when presets are configured.
        """
        # Create options flow
        flow = OptionsFlowHandler(mock_config_entry_with_presets)
        flow.hass = mock_hass

        # Mock the config_entry property to return our mock
        type(flow).config_entry = PropertyMock(
            return_value=mock_config_entry_with_presets
        )

        # Simplified options flow: init shows runtime tuning
        result = await flow.async_step_init()
        assert result["type"] == "form"
        assert result["step_id"] == "init"

        # Submit init step (no runtime changes)
        result = await flow.async_step_init({})

        # Since presets are configured, flow should proceed to preset_selection
        # (after navigating through any other configured features)
        # In this mock config, only presets are configured
        assert result["type"] == "form"
        assert result["step_id"] == "preset_selection"

        # Test passes: presets are properly detected and preset_selection step appears
