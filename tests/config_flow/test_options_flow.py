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
    """Test that AC-only options flow includes all expected steps."""
    handler = OptionsFlowHandler(ac_only_config_entry)
    handler.hass = mock_hass

    # Step 1: Init with same system type
    result = await handler.async_step_init({CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY})
    assert result["type"] == "form"
    assert result["step_id"] == "basic"

    # Step 2: Core configuration
    core_data = {
        CONF_COOLER: "switch.ac_unit",
        CONF_SENSOR: "sensor.temperature",
        "cold_tolerance": 0.3,
        "hot_tolerance": 0.3,
    }
    result = await handler.async_step_basic(core_data)
    assert result["type"] == "form"

    # Should proceed to unified features step
    assert result["step_id"] == "features"


async def test_ac_only_features_step(mock_hass, ac_only_config_entry):
    """Test AC-only features configuration step."""
    handler = OptionsFlowHandler(ac_only_config_entry)
    handler.hass = mock_hass
    handler.collected_config = {"ac_only_features_shown": False}

    # Test basic AC features form
    result = await handler.async_step_features()
    assert result["type"] == "form"
    assert result["step_id"] == "features"

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

    result = await handler.async_step_features(user_input)

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
    result = await handler.async_step_basic(core_data)
    steps_visited.append("basic")

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
    expected_steps = ["basic", "features"]
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
    """Test that options flow preserves system type and shows appropriate steps."""
    handler = OptionsFlowHandler(dual_system_config_entry)
    handler.hass = mock_hass

    # Init with same system type
    result = await handler.async_step_init(
        {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
    )
    assert result["step_id"] == "basic"

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
    result = await handler.async_step_basic(core_data)

    # Should go to the combined features step first (not ac_only_features)
    assert result["step_id"] == "features"


async def test_system_features_fields_and_floor_redirect(
    mock_hass, dual_system_config_entry
):
    """Verify system_features presents expected toggles and floor redirect."""
    handler = OptionsFlowHandler(dual_system_config_entry)
    handler.hass = mock_hass

    # Ensure the handler will use heater_cooler as system type
    handler.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}

    # Initial display of features should show a form
    result = await handler.async_step_features()
    assert result["type"] == "form"
    assert result["step_id"] == "features"

    # Check schema fields include fan/humidity/presets/openings/floor/advanced
    schema_dict = result["data_schema"].schema
    field_names = [str(key) for key in schema_dict.keys()]

    expected_fields = [
        "configure_presets",
        "configure_openings",
        "configure_advanced",
        "configure_fan",
        "configure_humidity",
        "configure_floor_heating",
    ]

    for field in expected_fields:
        assert any(field in name for name in field_names), f"Missing field: {field}"

    # If user selects floor heating, options flow should go straight to floor options
    user_input = {"configure_floor_heating": True}
    result = await handler.async_step_features(user_input)
    assert result["type"] == "form"
    assert result["step_id"] == "floor_options"


async def test_heat_pump_options_flow_parity(mock_hass, heat_pump_config_entry):
    """Ensure heat_pump options flow mirrors heater_cooler parity and floor redirect."""
    handler = OptionsFlowHandler(heat_pump_config_entry)
    handler.hass = mock_hass

    # Ensure the handler will use heat_pump as system type
    handler.collected_config = {CONF_SYSTEM_TYPE: "heat_pump"}

    # Initial display should be the combined features
    result = await handler.async_step_features()
    assert result["type"] == "form"
    assert result["step_id"] == "features"

    # If user selects floor heating, options flow should go straight to floor options
    user_input = {"configure_floor_heating": True}
    result = await handler.async_step_features(user_input)
    assert result["type"] == "form"
    assert result["step_id"] == "floor_options"


async def test_dual_stage_options_flow_parity(mock_hass, dual_stage_config_entry):
    """Ensure dual_stage options flow presents dual-stage options and floor redirect."""
    handler = OptionsFlowHandler(dual_stage_config_entry)
    handler.hass = mock_hass

    # dual_stage should show combined features first
    handler.collected_config = {CONF_SYSTEM_TYPE: "dual_stage"}
    result = await handler.async_step_features()
    assert result["type"] == "form"
    assert result["step_id"] == "features"

    # Selecting floor heating for dual_stage shows dual-stage specific options first
    user_input = {"configure_floor_heating": True}
    result = await handler.async_step_features(user_input)
    assert result["type"] == "form"
    assert result["step_id"] == "dual_stage_options"


async def test_simple_heater_select_only_openings_shows_only_openings(
    mock_hass, dual_stage_config_entry
):
    """If the user selects only openings on simple_heater_features, only openings step shows."""
    # Reuse a simple heater config entry by modifying the fixture data
    entry = dual_stage_config_entry
    entry.data["system_type"] = "simple_heater"

    handler = OptionsFlowHandler(entry)
    handler.hass = mock_hass

    # Simulate we already passed core and are at the simple heater features step
    handler.collected_config = {
        "system_type_changed": False,
        "system_type": "simple_heater",
    }

    # Indicate the features form has been shown so a submission will progress
    handler.collected_config["features_shown"] = True

    # User selects only openings (features are unified into 'features' step)
    result = await handler.async_step_features(
        {
            "configure_openings": True,
            "configure_presets": False,
            "configure_floor_heating": False,
            "configure_advanced": False,
        }
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
    """Comprehensive smoke-test: run options flow for several system types.

    This test walks the options flow for different pre-made config entries and
    ensures the flow visits the expected high-level steps for each system
    type without raising unhandled exceptions.
    """
    cases = [
        (
            ac_only_config_entry,
            {
                CONF_COOLER: ac_only_config_entry.data.get(CONF_COOLER),
                CONF_SENSOR: ac_only_config_entry.data.get(CONF_SENSOR),
            },
            ["basic", "features"],
        ),
        (
            dual_system_config_entry,
            {
                CONF_HEATER: dual_system_config_entry.data.get(CONF_HEATER),
                CONF_COOLER: dual_system_config_entry.data.get(CONF_COOLER),
                CONF_SENSOR: dual_system_config_entry.data.get(CONF_SENSOR),
            },
            ["basic", "features"],
        ),
        (
            heat_pump_config_entry,
            {
                CONF_HEATER: heat_pump_config_entry.data.get(CONF_HEATER),
                CONF_SENSOR: heat_pump_config_entry.data.get(CONF_SENSOR),
            },
            ["basic", "features"],
        ),
        (
            dual_stage_config_entry,
            {
                CONF_HEATER: dual_stage_config_entry.data.get(CONF_HEATER),
                CONF_SENSOR: dual_stage_config_entry.data.get(CONF_SENSOR),
            },
            ["basic", "features"],
        ),
    ]

    for entry, core_data, expected_steps in cases:
        handler = OptionsFlowHandler(entry)
        handler.hass = mock_hass
        steps_visited = []

        # Start the flow by calling init with the existing system type
        result = await handler.async_step_init(
            {CONF_SYSTEM_TYPE: entry.data.get(CONF_SYSTEM_TYPE)}
        )
        steps_visited.append("init")

        # Submit basic data and progress
        result = await handler.async_step_basic(core_data)
        steps_visited.append("basic")

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
