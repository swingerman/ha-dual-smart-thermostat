#!/usr/bin/env python3
"""Tests for reconfigure flow functionality."""

from unittest.mock import Mock, PropertyMock, patch

from homeassistant.config_entries import SOURCE_RECONFIGURE
from homeassistant.const import CONF_NAME
import pytest

from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
from custom_components.dual_smart_thermostat.const import (
    CONF_HEATER,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    SYSTEM_TYPE_HEAT_PUMP,
    SYSTEM_TYPE_HEATER_COOLER,
    SYSTEM_TYPE_SIMPLE_HEATER,
)


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry for reconfigure testing."""
    entry = Mock()
    entry.entry_id = "test_entry_id"
    entry.data = {
        CONF_NAME: "Test Thermostat",
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER,
        CONF_HEATER: "switch.heater",
        CONF_SENSOR: "sensor.temperature",
    }
    return entry


async def test_reconfigure_entry_point(mock_config_entry):
    """Test reconfigure flow entry point."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    # Mock the source property to return SOURCE_RECONFIGURE
    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        # Mock _get_reconfigure_entry to return our mock entry
        flow._get_reconfigure_entry = Mock(return_value=mock_config_entry)

        # Start reconfigure flow
        result = await flow.async_step_reconfigure()

        # Should show reconfigure_confirm step
        assert result["type"] == "form"
        assert result["step_id"] == "reconfigure_confirm"

        # Should initialize collected_config with current data
        assert flow.collected_config[CONF_NAME] == "Test Thermostat"
        assert flow.collected_config[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_SIMPLE_HEATER
        assert flow.collected_config[CONF_HEATER] == "switch.heater"
        assert flow.collected_config[CONF_SENSOR] == "sensor.temperature"


async def test_reconfigure_preserves_name(mock_config_entry):
    """Test that reconfigure flow preserves the entry name."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=mock_config_entry)

        # Start reconfigure
        await flow.async_step_reconfigure()

        # Original name should be in collected_config
        assert flow.collected_config[CONF_NAME] == "Test Thermostat"

        # The name should persist through reconfiguration
        # (user cannot change name in reconfigure flow)


async def test_reconfigure_system_type_change(mock_config_entry):
    """Test changing system type in reconfigure flow."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=mock_config_entry)

        # Start reconfigure
        await flow.async_step_reconfigure()

        # User changes system type from simple_heater to heat_pump
        result = await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP}
        )

        # Should proceed to heat pump configuration
        assert result["type"] == "form"
        assert result["step_id"] == "heat_pump"

        # System type should be updated
        assert flow.collected_config[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_HEAT_PUMP


async def test_reconfigure_keeps_system_type(mock_config_entry):
    """Test keeping the same system type in reconfigure flow."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=mock_config_entry)

        # Start reconfigure
        await flow.async_step_reconfigure()

        # User keeps same system type
        result = await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER}
        )

        # Should proceed to basic configuration for simple_heater
        assert result["type"] == "form"
        assert result["step_id"] == "basic"

        # System type should remain unchanged
        assert flow.collected_config[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_SIMPLE_HEATER


async def test_reconfigure_updates_entity(mock_config_entry):
    """Test updating entity in reconfigure flow."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=mock_config_entry)

        # Start reconfigure and proceed to basic config
        await flow.async_step_reconfigure()
        await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER}
        )

        # User updates heater entity
        new_heater_input = {
            CONF_NAME: "Test Thermostat",  # Name preserved
            CONF_HEATER: "switch.new_heater",  # Updated entity
            CONF_SENSOR: "sensor.temperature",  # Unchanged
        }

        result = await flow.async_step_basic(new_heater_input)

        # Should continue to next step
        assert result["type"] == "form"
        assert result["step_id"] == "features"

        # Heater should be updated in collected_config
        assert flow.collected_config[CONF_HEATER] == "switch.new_heater"


async def test_reconfigure_uses_update_reload_and_abort():
    """Test that reconfigure flow uses async_update_reload_and_abort."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    mock_entry = Mock()
    mock_entry.data = {
        CONF_NAME: "Test",
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER,
        CONF_HEATER: "switch.heater",
        CONF_SENSOR: "sensor.temp",
    }

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=mock_entry)

        # Initialize collected_config to simulate completed flow
        flow.collected_config = {
            CONF_NAME: "Test",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER,
            CONF_HEATER: "switch.new_heater",
            CONF_SENSOR: "sensor.temp",
        }

        # Mock async_update_reload_and_abort
        flow.async_update_reload_and_abort = Mock(
            return_value={"type": "abort", "reason": "reconfigure_successful"}
        )

        # Call _async_finish_flow which should detect SOURCE_RECONFIGURE
        result = await flow._async_finish_flow()

        # Should call async_update_reload_and_abort
        assert flow.async_update_reload_and_abort.called
        assert result["type"] == "abort"


async def test_config_flow_uses_create_entry():
    """Test that config flow uses async_create_entry (not reconfigure)."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value="user"
    ):
        # Initialize collected_config to simulate completed flow
        flow.collected_config = {
            CONF_NAME: "New Thermostat",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER,
            CONF_HEATER: "switch.heater",
            CONF_SENSOR: "sensor.temp",
        }

        # Mock async_create_entry
        flow.async_create_entry = Mock(
            return_value={"type": "create_entry", "title": "New Thermostat"}
        )

        # Call _async_finish_flow which should detect it's NOT reconfigure
        result = await flow._async_finish_flow()

        # Should call async_create_entry
        assert flow.async_create_entry.called
        assert result["type"] == "create_entry"


async def test_reconfigure_all_system_types():
    """Test reconfigure flow for all system types."""
    system_types_and_steps = [
        (SYSTEM_TYPE_SIMPLE_HEATER, "basic"),
        (SYSTEM_TYPE_HEAT_PUMP, "heat_pump"),
        (SYSTEM_TYPE_HEATER_COOLER, "heater_cooler"),
    ]

    for system_type, expected_step in system_types_and_steps:
        flow = ConfigFlowHandler()
        flow.hass = Mock()

        mock_entry = Mock()
        mock_entry.data = {
            CONF_NAME: "Test",
            CONF_SYSTEM_TYPE: system_type,
            CONF_HEATER: "switch.heater",
            CONF_SENSOR: "sensor.temp",
        }

        with patch.object(
            type(flow),
            "source",
            new_callable=PropertyMock,
            return_value=SOURCE_RECONFIGURE,
        ):
            flow._get_reconfigure_entry = Mock(return_value=mock_entry)

            # Start reconfigure
            await flow.async_step_reconfigure()

            # Confirm with same system type
            result = await flow.async_step_reconfigure_confirm(
                {CONF_SYSTEM_TYPE: system_type}
            )

            # Should proceed to correct step for system type
            assert result["type"] == "form"
            assert result["step_id"] == expected_step, (
                f"Expected step {expected_step} for {system_type}, "
                f"got {result['step_id']}"
            )


async def test_reconfigure_uses_data_parameter_not_data_updates():
    """Test that reconfigure flow uses data parameter to replace all config.

    This test verifies that async_update_reload_and_abort is called with
    the 'data' parameter (which replaces all data) rather than 'data_updates'
    (which merges data). This is critical to prevent duplicate entries.

    The reconfigure flow collects the entire configuration from the user,
    so we should replace all data, not merge with existing data.
    """
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    mock_entry = Mock()
    mock_entry.data = {
        CONF_NAME: "Test",
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER,
        CONF_HEATER: "switch.old_heater",  # This should be replaced
        CONF_SENSOR: "sensor.temp",
    }

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=mock_entry)

        # Initialize collected_config with new complete configuration
        new_config = {
            CONF_NAME: "Test",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER,
            CONF_HEATER: "switch.new_heater",  # Updated heater
            CONF_SENSOR: "sensor.new_temp",  # Updated sensor
        }
        flow.collected_config = new_config

        # Mock async_update_reload_and_abort to capture how it's called
        with patch.object(flow, "async_update_reload_and_abort") as mock_update:
            mock_update.return_value = {
                "type": "abort",
                "reason": "reconfigure_successful",
            }

            # Call _async_finish_flow
            result = await flow._async_finish_flow()

            # Verify async_update_reload_and_abort was called
            assert mock_update.called, "async_update_reload_and_abort should be called"

            # Verify it was called with the entry and data parameter (not data_updates)
            call_args = mock_update.call_args
            assert call_args is not None, "Should have call arguments"

            # Check positional args
            assert (
                len(call_args[0]) >= 1
            ), "Should have at least entry as positional arg"
            assert call_args[0][0] == mock_entry, "First arg should be the config entry"

            # Check keyword args - should have 'data', NOT 'data_updates'
            assert "data" in call_args[1], "Should use 'data' parameter"
            assert (
                "data_updates" not in call_args[1]
            ), "Should NOT use 'data_updates' parameter"

            # Verify the data parameter contains the cleaned config
            # (without transient flags like features_shown, etc.)
            assert call_args[1]["data"] is not None, "data parameter should not be None"

            # Result should be an abort
            assert result["type"] == "abort"
            assert result["reason"] == "reconfigure_successful"


if __name__ == "__main__":
    """Run tests directly."""
    import asyncio
    import sys

    async def run_all_tests():
        """Run all tests manually."""
        print("🧪 Running Reconfigure Flow Tests")
        print("=" * 50)

        mock_entry = Mock()
        mock_entry.entry_id = "test"
        mock_entry.data = {
            CONF_NAME: "Test",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER,
            CONF_HEATER: "switch.heater",
            CONF_SENSOR: "sensor.temp",
        }

        tests = [
            ("Reconfigure entry point", test_reconfigure_entry_point(mock_entry)),
            ("Preserves name", test_reconfigure_preserves_name(mock_entry)),
            ("System type change", test_reconfigure_system_type_change(mock_entry)),
            ("Keeps system type", test_reconfigure_keeps_system_type(mock_entry)),
            ("Updates entity", test_reconfigure_updates_entity(mock_entry)),
            (
                "Uses update_reload_and_abort",
                test_reconfigure_uses_update_reload_and_abort(),
            ),
            ("Config uses create_entry", test_config_flow_uses_create_entry()),
            ("All system types", test_reconfigure_all_system_types()),
            (
                "Uses data not data_updates",
                test_reconfigure_uses_data_parameter_not_data_updates(),
            ),
        ]

        passed = 0
        for test_name, test_coro in tests:
            try:
                await test_coro
                print(f"✅ {test_name}")
                passed += 1
            except Exception as e:
                print(f"❌ {test_name}: {e}")
                import traceback

                traceback.print_exc()

        print(f"\n🎯 Results: {passed}/{len(tests)} tests passed")
        return passed == len(tests)

    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
