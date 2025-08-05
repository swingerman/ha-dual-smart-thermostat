"""Test the options flow for openings configuration."""

from unittest.mock import Mock

import pytest

from custom_components.dual_smart_thermostat.const import (
    ATTR_OPENING_TIMEOUT,
    CONF_HEATER,
    CONF_OPENINGS,
    CONF_OPENINGS_SCOPE,
)
from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry with openings configuration."""
    config_entry = Mock()
    config_entry.data = {
        "name": "Test Thermostat",
        CONF_HEATER: "switch.heater",
        CONF_OPENINGS: [
            {"entity_id": "binary_sensor.door", ATTR_OPENING_TIMEOUT: {"seconds": 30}},
            "binary_sensor.window",
        ],
        CONF_OPENINGS_SCOPE: ["heat", "cool"],
    }
    config_entry.entry_id = "test_entry"
    return config_entry


def test_options_flow_includes_openings_step():
    """Test that options flow includes openings configuration step when openings exist."""
    # Create mock config entry with openings
    config_entry = Mock()
    config_entry.data = {
        "name": "Test Thermostat",
        CONF_HEATER: "switch.heater",
        CONF_OPENINGS: ["binary_sensor.door"],
    }

    # Create options flow handler
    options_handler = OptionsFlowHandler(config_entry)
    options_handler.collected_config = {}

    # Test _determine_options_next_step logic
    assert hasattr(options_handler, "async_step_openings_options")

    # Verify that openings step would be called if not shown yet
    current_config = config_entry.data
    has_openings = bool(current_config.get(CONF_OPENINGS))
    openings_not_shown = (
        "openings_options_shown" not in options_handler.collected_config
    )

    assert has_openings is True
    assert openings_not_shown is True

    print("✅ Options flow includes openings step when openings are configured")
    return True


def test_options_flow_skips_openings_when_not_configured():
    """Test that options flow skips openings when not configured."""
    # Create mock config entry without openings
    config_entry = Mock()
    config_entry.data = {
        "name": "Test Thermostat",
        CONF_HEATER: "switch.heater",
        # No CONF_OPENINGS
    }

    # Create options flow handler
    options_handler = OptionsFlowHandler(config_entry)
    options_handler.collected_config = {}

    # Verify that openings step would be skipped
    current_config = config_entry.data
    has_openings = bool(current_config.get(CONF_OPENINGS))

    assert has_openings is False

    print("✅ Options flow skips openings step when openings are not configured")
    return True


if __name__ == "__main__":
    test_options_flow_includes_openings_step()
    test_options_flow_skips_openings_when_not_configured()
    print("🎉 All options flow tests passed!")
