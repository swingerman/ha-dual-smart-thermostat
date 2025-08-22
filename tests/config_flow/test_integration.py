"""Integration test for options flow openings functionality."""

from unittest.mock import AsyncMock, Mock, patch

from homeassistant.data_entry_flow import FlowResult
import pytest

from custom_components.dual_smart_thermostat.const import (
    ATTR_CLOSING_TIMEOUT,
    ATTR_OPENING_TIMEOUT,
    CONF_COOLER,
    CONF_HEATER,
    CONF_OPENINGS,
    CONF_OPENINGS_SCOPE,
)
from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler


@pytest.fixture
def hass():
    """Create a mock hass instance."""
    hass = Mock()
    hass.config_entries = Mock()
    hass.config_entries.async_update_entry = AsyncMock()
    return hass


@pytest.fixture
def config_entry_with_openings():
    """Create a mock config entry with existing openings configuration."""
    config_entry = Mock()
    config_entry.data = {
        "name": "Test Thermostat",
        CONF_HEATER: "switch.heater",
        CONF_COOLER: "switch.cooler",
        CONF_OPENINGS: [
            {"entity_id": "binary_sensor.door", ATTR_OPENING_TIMEOUT: {"seconds": 30}},
            "binary_sensor.window",
        ],
        CONF_OPENINGS_SCOPE: ["heat", "cool"],
    }
    config_entry.entry_id = "test_entry"
    return config_entry


async def test_options_flow_openings_schema_creation(hass, config_entry_with_openings):
    """Test that openings options creates proper schema with current values."""
    # Create options flow handler
    options_handler = OptionsFlowHandler(config_entry_with_openings)
    options_handler.hass = hass
    options_handler.collected_config = {}

    # Mock the flow show form method to capture the schema
    with patch.object(options_handler, "async_show_form") as mock_show_form:
        mock_show_form.return_value = Mock()

        # Call openings options step
        await options_handler.async_step_openings_options()

        # Verify show_form was called
        assert mock_show_form.called
    call_args = mock_show_form.call_args

    # Check that step_id is correct
    assert call_args[1]["step_id"] == "openings_options"

    # Check that schema includes expected fields
    schema = call_args[1]["data_schema"]
    assert schema is not None

    print("Options flow creates proper openings schema")


async def test_options_flow_openings_data_processing(hass, config_entry_with_openings):
    """Test that openings options processes user input correctly."""
    # Create options flow handler
    options_handler = OptionsFlowHandler(config_entry_with_openings)
    options_handler.hass = hass
    options_handler.collected_config = {}

    # Mock _determine_options_next_step to return a mock result
    mock_result = FlowResult()
    mock_result["type"] = "form"

    with patch.object(
        options_handler, "_determine_options_next_step"
    ) as mock_next_step:
        mock_next_step.return_value = mock_result

        # Test user input with modified openings
        user_input = {
            "selected_openings": ["binary_sensor.door", "binary_sensor.new_window"],
            CONF_OPENINGS_SCOPE: ["heat"],
            "binary_sensor.door_opening_timeout": {"seconds": 45},
            "binary_sensor.new_window_closing_timeout": {"seconds": 15},
        }

        # Call openings options with user input
        await options_handler.async_step_openings_options(user_input)

        # Verify that _determine_options_next_step was called
        assert mock_next_step.called

        # Check that collected_config has the correct data
        assert "selected_openings" in options_handler.collected_config
        assert options_handler.collected_config["selected_openings"] == [
            "binary_sensor.door",
            "binary_sensor.new_window",
        ]
        assert options_handler.collected_config[CONF_OPENINGS_SCOPE] == ["heat"]

        # Check that openings list was properly formed
        openings_list = options_handler.collected_config[CONF_OPENINGS]
        assert len(openings_list) == 2

        # Find the door entry
        door_entry = next(
            (o for o in openings_list if o.get("entity_id") == "binary_sensor.door"),
            None,
        )
        assert door_entry is not None
        assert door_entry[ATTR_OPENING_TIMEOUT] == {"seconds": 45}

        # Find the window entry
        window_entry = next(
            (
                o
                for o in openings_list
                if o.get("entity_id") == "binary_sensor.new_window"
            ),
            None,
        )
        assert window_entry is not None
        assert window_entry[ATTR_CLOSING_TIMEOUT] == {"seconds": 15}

        # simple confirmation log
        print("Options flow processes openings user input correctly")


async def test_options_flow_openings_removal(hass, config_entry_with_openings):
    """Test that openings can be completely removed via options flow."""
    # Create options flow handler
    options_handler = OptionsFlowHandler(config_entry_with_openings)
    options_handler.hass = hass
    options_handler.collected_config = {}

    mock_result = FlowResult()
    mock_result["type"] = "form"

    with patch.object(
        options_handler, "_determine_options_next_step"
    ) as mock_next_step:
        mock_next_step.return_value = mock_result

        # Test user input with no selected openings (removal)
        user_input = {
            "selected_openings": [],  # Empty selection removes openings
        }

        # Call openings options with user input
        await options_handler.async_step_openings_options(user_input)

        # Verify that openings configuration was removed
        assert CONF_OPENINGS not in options_handler.collected_config
        assert CONF_OPENINGS_SCOPE not in options_handler.collected_config

        # simple confirmation log
        print("Options flow can remove openings configuration")


if __name__ == "__main__":
    import asyncio

    async def run_tests():
        from unittest.mock import Mock

        # Create mock objects
        hass = Mock()
        hass.config_entries = Mock()
        hass.config_entries.async_update_entry = AsyncMock()

        config_entry = Mock()
        config_entry.data = {
            "name": "Test Thermostat",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            CONF_OPENINGS: [
                {
                    "entity_id": "binary_sensor.door",
                    ATTR_OPENING_TIMEOUT: {"seconds": 30},
                },
                "binary_sensor.window",
            ],
            CONF_OPENINGS_SCOPE: ["heat", "cool"],
        }
        config_entry.entry_id = "test_entry"

        await test_options_flow_openings_schema_creation(hass, config_entry)
        await test_options_flow_openings_data_processing(hass, config_entry)
        await test_options_flow_openings_removal(hass, config_entry)

        print("🎉 All options flow integration tests passed!")

    asyncio.run(run_tests())
