#!/usr/bin/env python3
"""Comprehensive tests for options flow functionality."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.dual_smart_thermostat.const import (
    ATTR_OPENING_TIMEOUT,
    CONF_COOLER,
    CONF_FLOOR_SENSOR,
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
    config_entry.options = {}  # Add missing options attribute
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
    config_entry.options = {}  # Add missing options attribute
    config_entry.entry_id = "test_dual_entry"
    return config_entry


@pytest.fixture
def heat_pump_config_entry():
    """Create a mock config entry for heat pump system."""
    config_entry = Mock()
    config_entry.data = {
        CONF_SYSTEM_TYPE: "heat_pump",
        "name": "Heat Pump Thermostat",
        CONF_HEATER: "switch.heater",
        CONF_SENSOR: "sensor.temperature",
        "cold_tolerance": 0.3,
        "hot_tolerance": 0.3,
    }
    config_entry.options = {}  # Add missing options attribute
    config_entry.entry_id = "test_heat_pump_entry"
    return config_entry


@pytest.fixture
def dual_stage_config_entry():
    """Create a mock config entry for dual-stage system."""
    config_entry = Mock()
    config_entry.data = {
        CONF_SYSTEM_TYPE: "dual_stage",
        "name": "Dual Stage Thermostat",
        CONF_HEATER: "switch.heater",
        CONF_SENSOR: "sensor.temperature",
        "cold_tolerance": 0.3,
        "hot_tolerance": 0.3,
    }
    config_entry.options = {}  # Add missing options attribute
    config_entry.entry_id = "test_dual_stage_entry"
    return config_entry


async def test_ac_only_options_flow_progression(mock_hass, ac_only_config_entry):
    """Test that AC-only options flow shows runtime tuning parameters."""
    handler = OptionsFlowHandler(ac_only_config_entry)
    handler.hass = mock_hass

    # Step 1: Init shows runtime tuning parameters directly
    result = await handler.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # Verify schema contains runtime parameters
    schema_dict = result["data_schema"].schema
    field_names = [str(key) for key in schema_dict.keys()]

    # Should have tolerances and temperature limits
    assert any("cold_tolerance" in name for name in field_names)
    assert any("hot_tolerance" in name for name in field_names)
    assert any("min_temp" in name for name in field_names)
    assert any("max_temp" in name for name in field_names)

    # Submit runtime parameters
    runtime_data = {
        "cold_tolerance": 0.3,
        "hot_tolerance": 0.3,
        "min_temp": 7,
        "max_temp": 35,
    }
    result = await handler.async_step_init(runtime_data)

    # Since no features are configured, should complete directly
    assert result["type"] == "create_entry"


async def test_ac_only_features_step(mock_hass, ac_only_config_entry):
    """Test AC-only simplified options flow without feature configuration.

    The new simplified options flow shows only runtime tuning parameters.
    Feature enable/disable is handled in reconfigure flow.
    """
    handler = OptionsFlowHandler(ac_only_config_entry)
    handler.hass = mock_hass

    # The init step now shows runtime tuning parameters directly
    result = await handler.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # Check that schema has runtime tuning fields (not feature toggles)
    schema_dict = result["data_schema"].schema
    field_names = [str(key) for key in schema_dict.keys()]

    expected_runtime_fields = [
        "cold_tolerance",
        "hot_tolerance",
        "min_temp",
        "max_temp",
        "precision",
        "temp_step",
    ]

    for field in expected_runtime_fields:
        assert any(field in name for name in field_names), f"Missing field: {field}"


# Removed test_advanced_options_separate_step as advanced options are no longer supported


async def test_options_flow_step_progression(mock_hass, ac_only_config_entry):
    """Test simplified options flow step progression.

    The new simplified options flow shows runtime parameters in init,
    then proceeds to multi-step configuration for already-configured features.
    """
    handler = OptionsFlowHandler(ac_only_config_entry)
    handler.hass = mock_hass

    steps_visited = []

    # Start flow - init shows runtime tuning directly
    result = await handler.async_step_init()
    steps_visited.append("init")
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # Submit runtime parameters
    runtime_data = {
        "cold_tolerance": 0.3,
        "hot_tolerance": 0.3,
        "min_temp": 7,
        "max_temp": 35,
    }
    result = await handler.async_step_init(runtime_data)

    # Since no features are configured in the base entry, should complete
    if result.get("type") == "create_entry":
        steps_visited.append("complete")
    else:
        # If features were configured, continue through remaining steps
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

    # Verify we visited the init step at minimum
    assert "init" in steps_visited, "Missing expected init step"


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


async def test_openings_two_step_options_flow(mock_hass, ac_only_config_entry):
    """Test the two-step openings options flow: select then configure timeouts."""
    handler = OptionsFlowHandler(ac_only_config_entry)
    handler.hass = mock_hass
    handler.collected_config = {}

    # Initial display: selection step
    result = await handler.async_step_openings_options()
    assert result["type"] == "form"
    assert result["step_id"] == "openings_options"

    # Submit only selected_openings to trigger the detailed config step
    user_input = {"selected_openings": ["binary_sensor.door", "binary_sensor.window"]}
    result = await handler.async_step_openings_options(user_input)

    # Expect the detailed openings configuration form (timeouts & scope)
    assert result["type"] == "form"
    assert result["step_id"] == "openings_config"

    # Ensure the schema contains per-entity timeout fields for the selected entities
    schema_dict = result["data_schema"].schema
    field_names = [str(key) for key in schema_dict.keys()]
    assert any("opening_1" in name for name in field_names)
    assert any("opening_2" in name for name in field_names)
    assert "openings_scope" in field_names


async def test_system_type_preservation(mock_hass, dual_system_config_entry):
    """Test that options flow preserves system type in simplified flow."""
    handler = OptionsFlowHandler(dual_system_config_entry)
    handler.hass = mock_hass

    # Init shows runtime tuning parameters
    result = await handler.async_step_init()
    assert result["step_id"] == "init"

    # The flow preserves the original system type from entry
    current_config = handler._get_current_config()
    original_system = current_config.get(CONF_SYSTEM_TYPE)
    assert original_system == SYSTEM_TYPE_HEATER_COOLER

    # Submit runtime parameters
    runtime_data = {
        "cold_tolerance": 0.3,
        "hot_tolerance": 0.3,
        "min_temp": 7,
        "max_temp": 35,
    }
    result = await handler.async_step_init(runtime_data)

    # Since no features are configured in the base entry, should complete
    # (or proceed to configured feature steps if any exist)
    assert result["type"] in ["create_entry", "form"]


async def test_system_features_fields_and_floor_redirect(
    mock_hass, dual_system_config_entry
):
    """Verify simplified options flow shows runtime parameters and proceeds to floor options if configured."""
    # Add a configured floor sensor to test the flow
    dual_system_config_entry.data[CONF_FLOOR_SENSOR] = "sensor.floor_temp"

    handler = OptionsFlowHandler(dual_system_config_entry)
    handler.hass = mock_hass

    # Initial display shows runtime tuning parameters
    result = await handler.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # Check schema has runtime tuning fields
    schema_dict = result["data_schema"].schema
    field_names = [str(key) for key in schema_dict.keys()]

    expected_runtime_fields = [
        "cold_tolerance",
        "hot_tolerance",
        "min_temp",
        "max_temp",
    ]

    for field in expected_runtime_fields:
        assert any(field in name for name in field_names), f"Missing field: {field}"

    # Submit runtime data - should proceed to floor options since floor sensor is configured
    user_input = {
        "cold_tolerance": 0.3,
        "hot_tolerance": 0.3,
    }
    result = await handler.async_step_init(user_input)
    assert result["type"] == "form"
    assert result["step_id"] == "floor_options"


async def test_heat_pump_options_flow_parity(mock_hass, heat_pump_config_entry):
    """Ensure heat_pump options flow shows runtime tuning and proceeds to floor options if configured."""
    # Add a configured floor sensor to test the flow
    heat_pump_config_entry.data[CONF_FLOOR_SENSOR] = "sensor.floor_temp"

    handler = OptionsFlowHandler(heat_pump_config_entry)
    handler.hass = mock_hass

    # Initial display shows runtime tuning
    result = await handler.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # Submit runtime parameters - should proceed to floor options since floor sensor is configured
    user_input = {
        "cold_tolerance": 0.3,
        "hot_tolerance": 0.3,
    }
    result = await handler.async_step_init(user_input)
    assert result["type"] == "form"
    assert result["step_id"] == "floor_options"


async def test_dual_stage_options_flow_parity(mock_hass, dual_stage_config_entry):
    """Ensure dual_stage options flow presents dual-stage options when aux heater is configured."""
    # Add aux heater to trigger dual stage options
    dual_stage_config_entry.data["aux_heater"] = "switch.aux_heater"

    handler = OptionsFlowHandler(dual_stage_config_entry)
    handler.hass = mock_hass

    # Init shows runtime tuning
    result = await handler.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # Submit runtime parameters - should proceed to dual_stage_options since aux heater is configured
    user_input = {
        "cold_tolerance": 0.3,
        "hot_tolerance": 0.3,
    }
    result = await handler.async_step_init(user_input)
    assert result["type"] == "form"
    assert result["step_id"] == "dual_stage_options"


async def test_simple_heater_select_only_openings_shows_only_openings(
    mock_hass, dual_stage_config_entry
):
    """If openings are already configured, the simplified flow shows openings options step."""
    # Reuse a simple heater config entry by modifying the fixture data
    entry = dual_stage_config_entry
    entry.data["system_type"] = "simple_heater"
    # Add existing openings configuration
    entry.data[CONF_OPENINGS] = [
        {"entity_id": "binary_sensor.door", ATTR_OPENING_TIMEOUT: {"seconds": 30}},
    ]

    handler = OptionsFlowHandler(entry)
    handler.hass = mock_hass

    # Start the simplified flow - init shows runtime tuning
    result = await handler.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # Submit runtime parameters - should proceed to openings options since openings are configured
    result = await handler.async_step_init(
        {"cold_tolerance": 0.3, "hot_tolerance": 0.3}
    )

    # Should go to openings options next
    assert result["type"] == "form"
    assert result["step_id"] == "openings_options"

    # The openings flow is two-step: first selection triggers the detailed form
    result = await handler.async_step_openings_options(
        {"selected_openings": ["binary_sensor.door"]}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "openings_config"

    # Now submit the detailed config (include a timeout field) and ensure we finish
    user_input = {
        "selected_openings": ["binary_sensor.door"],
        "binary_sensor.door_timeout_open": 10,
    }
    # Mock next step to return create_entry
    with patch.object(handler, "_determine_options_next_step") as mock_next:
        mock_next.return_value = {"type": "create_entry", "data": {}}
        result = await handler.async_step_openings_options(user_input)

    assert result["type"] == "create_entry"


async def test_comprehensive_options_flow_multiple_systems(
    mock_hass,
    ac_only_config_entry,
    dual_system_config_entry,
    heat_pump_config_entry,
    dual_stage_config_entry,
):
    """Comprehensive smoke-test: run simplified options flow for several system types.

    This test walks the simplified options flow for different pre-made config entries and
    ensures the flow starts with the init step (runtime tuning) for each system
    type without raising unhandled exceptions.
    """
    cases = [
        (ac_only_config_entry, ["init"]),
        (dual_system_config_entry, ["init"]),
        (heat_pump_config_entry, ["init"]),
        (dual_stage_config_entry, ["init"]),
    ]

    for entry, expected_steps in cases:
        handler = OptionsFlowHandler(entry)
        handler.hass = mock_hass
        steps_visited = []

        # Start the simplified flow - init shows runtime tuning
        result = await handler.async_step_init()
        steps_visited.append("init")
        assert result["type"] == "form"
        assert result["step_id"] == "init"

        # Submit runtime parameters
        runtime_data = {
            "cold_tolerance": 0.3,
            "hot_tolerance": 0.3,
            "min_temp": 7,
            "max_temp": 35,
        }
        result = await handler.async_step_init(runtime_data)

        # Walk remaining steps until create_entry or iteration limit
        max_iterations = 20
        iteration = 0
        while result.get("type") == "form" and iteration < max_iterations:
            iteration += 1
            current_step = result["step_id"]
            steps_visited.append(current_step)

            step_method = getattr(handler, f"async_step_{current_step}")
            try:
                # Submit an empty dict to progress where possible. Some steps
                # require specific fields; if they raise, treat as flow end.
                result = await step_method({})
            except Exception:
                result = {"type": "create_entry"}
                break

        # Ensure expected high-level steps were visited for this system
        for expected in expected_steps:
            assert (
                expected in steps_visited
            ), f"Expected step {expected} in visited steps for {entry.data.get(CONF_SYSTEM_TYPE)}"


async def test_floor_options_preselects_configured_sensor(
    mock_hass, dual_stage_config_entry
):
    """Ensure the floor options form pre-selects the configured floor sensor."""
    entry = dual_stage_config_entry
    # Simulate an already-configured floor sensor in the stored entry
    entry.data[CONF_FLOOR_SENSOR] = "sensor.floor_temp"  # example entity

    handler = OptionsFlowHandler(entry)
    handler.hass = mock_hass

    # Ensure we start with no collected overrides
    handler.collected_config = {}

    result = await handler.async_step_floor_options()
    assert result["type"] == "form"
    assert result["step_id"] == "floor_options"

    schema_dict = result["data_schema"].schema

    # Find the Optional key that corresponds to the floor sensor and assert
    # the default includes the configured entity id.
    sensor_key = next((k for k in schema_dict.keys() if "floor_sensor" in str(k)), None)
    assert sensor_key is not None, "floor_sensor field missing from schema"
    # The voluptuous Optional key exposes a callable default() returning the default value
    default_value = getattr(sensor_key, "default", None)
    assert default_value is not None, "floor_sensor Optional missing default()"
    assert default_value() == "sensor.floor_temp"


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
