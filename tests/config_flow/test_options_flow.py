#!/usr/bin/env python3
"""Comprehensive tests for options flow functionality."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.dual_smart_thermostat.const import (
    ATTR_OPENING_TIMEOUT,
    CONF_COOLER,
    CONF_HEATER,
    CONF_OPENINGS,
    CONF_OPENINGS_SCOPE,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    SYSTEM_TYPE_AC_ONLY,
    SYSTEM_TYPE_HEATER_COOLER,
)
from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler


@pytest.fixture
def mock_hass():
    """Create a mock hass instance."""
    hass = Mock()
    hass.config_entries = Mock()
    hass.config_entries.async_update_entry = AsyncMock()
    return hass


@pytest.fixture
def ac_only_config_entry():
    """Create a mock config entry for AC-only system."""
    config_entry = Mock()
    config_entry.data = {
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY,
        "name": "AC Thermostat",
        CONF_COOLER: "switch.ac_unit",
        CONF_SENSOR: "sensor.temperature",
        "cold_tolerance": 0.3,
        "hot_tolerance": 0.3,
    }
    config_entry.entry_id = "test_ac_entry"
    return config_entry


@pytest.fixture
def dual_system_config_entry():
    """Create a mock config entry for heater+cooler system."""
    config_entry = Mock()
    config_entry.data = {
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
        "name": "Dual Thermostat",
        CONF_HEATER: "switch.heater",
        CONF_COOLER: "switch.cooler",
        CONF_SENSOR: "sensor.temperature",
        "cold_tolerance": 0.3,
        "hot_tolerance": 0.3,
    }
    config_entry.entry_id = "test_dual_entry"
    return config_entry


async def test_ac_only_options_flow_progression(mock_hass, ac_only_config_entry):
    """Test that AC-only options flow includes all expected steps."""
    handler = OptionsFlowHandler(ac_only_config_entry)
    handler.hass = mock_hass

    # Step 1: Init with same system type
    result = await handler.async_step_init({CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY})
    assert result["type"] == "form"
    assert result["step_id"] == "core"

    # Step 2: Core configuration
    core_data = {
        CONF_COOLER: "switch.ac_unit",
        CONF_SENSOR: "sensor.temperature",
        "cold_tolerance": 0.3,
        "hot_tolerance": 0.3,
    }
    result = await handler.async_step_core(core_data)
    assert result["type"] == "form"

    # Should proceed to AC-only features
    assert result["step_id"] == "ac_only_features"


async def test_ac_only_features_step(mock_hass, ac_only_config_entry):
    """Test AC-only features configuration step."""
    handler = OptionsFlowHandler(ac_only_config_entry)
    handler.hass = mock_hass
    handler.collected_config = {"ac_only_features_shown": False}

    # Test basic AC features form
    result = await handler.async_step_ac_only_features()
    assert result["type"] == "form"
    assert result["step_id"] == "ac_only_features"

    # Check that schema has the expected fields
    schema_dict = result["data_schema"].schema
    field_names = [str(key) for key in schema_dict.keys()]

    expected_fields = [
        "configure_fan",
        "configure_humidity",
        "configure_openings",
        "configure_presets",
        "configure_advanced",
    ]

    for field in expected_fields:
        assert any(field in name for name in field_names), f"Missing field: {field}"


async def test_advanced_options_separate_step(mock_hass, ac_only_config_entry):
    """Test that advanced options appear as separate step when requested."""
    handler = OptionsFlowHandler(ac_only_config_entry)
    handler.hass = mock_hass

    # User enables advanced configuration
    user_input = {
        "configure_fan": False,
        "configure_humidity": False,
        "configure_openings": False,
        "configure_presets": False,
        "configure_advanced": True,
    }

    result = await handler.async_step_ac_only_features(user_input)

    # Should redirect to advanced options step
    assert result["type"] == "form"
    assert result["step_id"] == "advanced_options"


async def test_options_flow_step_progression(mock_hass, ac_only_config_entry):
    """Test complete options flow step progression."""
    handler = OptionsFlowHandler(ac_only_config_entry)
    handler.hass = mock_hass

    steps_visited = []

    # Start flow
    result = await handler.async_step_init({CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY})
    steps_visited.append("init")

    # Core step
    core_data = {
        CONF_COOLER: "switch.ac_unit",
        CONF_SENSOR: "sensor.temperature",
        "cold_tolerance": 0.3,
        "hot_tolerance": 0.3,
    }
    result = await handler.async_step_core(core_data)
    steps_visited.append("core")

    # Continue through remaining steps with minimal configuration
    max_iterations = 10
    iteration = 0

    while result.get("type") == "form" and iteration < max_iterations:
        iteration += 1
        current_step = result["step_id"]
        steps_visited.append(current_step)

        # Get step method and call with empty input
        step_method = getattr(handler, f"async_step_{current_step}")
        try:
            result = await step_method({})
        except Exception:
            # Some steps might require specific input
            result = {"type": "create_entry"}
            break

    # Verify we visited expected steps for AC-only system
    expected_steps = ["core", "ac_only_features"]
    for step in expected_steps:
        assert step in steps_visited, f"Missing expected step: {step}"


async def test_openings_configuration_in_options(mock_hass, ac_only_config_entry):
    """Test openings configuration through options flow."""
    # Add existing openings to config entry
    ac_only_config_entry.data[CONF_OPENINGS] = [
        {"entity_id": "binary_sensor.door", ATTR_OPENING_TIMEOUT: {"seconds": 30}},
        "binary_sensor.window",
    ]
    ac_only_config_entry.data[CONF_OPENINGS_SCOPE] = ["heat", "cool"]

    handler = OptionsFlowHandler(ac_only_config_entry)
    handler.hass = mock_hass
    handler.collected_config = {"openings_options_shown": False}

    # Test openings options step
    result = await handler.async_step_openings_options()
    assert result["type"] == "form"
    assert result["step_id"] == "openings_options"

    # Test modifying openings configuration
    user_input = {
        "selected_openings": ["binary_sensor.door", "binary_sensor.new_window"],
        CONF_OPENINGS_SCOPE: ["heat"],
        "binary_sensor.door_opening_timeout": {"seconds": 45},
        "binary_sensor.new_window_closing_timeout": {"seconds": 15},
    }

    # Mock the next step to avoid going through entire flow
    with patch.object(handler, "_determine_options_next_step") as mock_next:
        mock_next.return_value = {"type": "create_entry", "data": {}}
        result = await handler.async_step_openings_options(user_input)

    # Verify openings data was processed correctly
    assert "selected_openings" in handler.collected_config
    assert handler.collected_config["selected_openings"] == [
        "binary_sensor.door",
        "binary_sensor.new_window",
    ]

    # Check openings list structure
    openings_list = handler.collected_config.get(CONF_OPENINGS, [])
    assert len(openings_list) == 2

    # Find door config
    door_config = next(
        (o for o in openings_list if o.get("entity_id") == "binary_sensor.door"), None
    )
    assert door_config is not None
    assert door_config[ATTR_OPENING_TIMEOUT] == {"seconds": 45}


async def test_system_type_preservation(mock_hass, dual_system_config_entry):
    """Test that options flow preserves system type and shows appropriate steps."""
    handler = OptionsFlowHandler(dual_system_config_entry)
    handler.hass = mock_hass

    # Init with same system type
    result = await handler.async_step_init(
        {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
    )
    assert result["step_id"] == "core"

    # The flow should determine steps based on original system type
    original_system = handler.config_entry.data.get(CONF_SYSTEM_TYPE)
    assert original_system == SYSTEM_TYPE_HEATER_COOLER

    # For heater_cooler system, should show fan toggle (not AC-only features)
    core_data = {
        CONF_HEATER: "switch.heater",
        CONF_COOLER: "switch.cooler",
        CONF_SENSOR: "sensor.temperature",
        "cold_tolerance": 0.3,
        "hot_tolerance": 0.3,
    }
    result = await handler.async_step_core(core_data)

    # Should go to fan_toggle, not ac_only_features
    assert result["step_id"] == "fan_toggle"


if __name__ == "__main__":
    """Run tests directly."""
    import sys

    async def run_all_tests():
        """Run all tests manually."""
        print("🧪 Running Options Flow Tests")
        print("=" * 50)

        # Create mock fixtures
        mock_hass = Mock()
        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_update_entry = AsyncMock()

        ac_config = Mock()
        ac_config.data = {
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY,
            "name": "AC Thermostat",
            CONF_COOLER: "switch.ac_unit",
            CONF_SENSOR: "sensor.temperature",
        }
        ac_config.entry_id = "test_ac"

        tests = [
            (
                "AC-only flow progression",
                test_ac_only_options_flow_progression(mock_hass, ac_config),
            ),
            ("AC-only features step", test_ac_only_features_step(mock_hass, ac_config)),
            (
                "Advanced options separate step",
                test_advanced_options_separate_step(mock_hass, ac_config),
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

        print(f"\n🎯 Results: {passed}/{len(tests)} tests passed")
        return passed == len(tests)

    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
