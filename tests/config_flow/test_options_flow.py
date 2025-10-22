#!/usr/bin/env python3
"""Comprehensive tests for options flow functionality.

This module consolidates all options flow tests including:
- Basic flow progression and step navigation
- Feature persistence (fan, humidity settings pre-filled)
- Preset detection and configuration
- Openings configuration
- Complete flow integration tests
- System-specific flow variations

The simplified options flow shows runtime tuning parameters first,
then proceeds to configuration steps for already-configured features.
"""

from unittest.mock import AsyncMock, Mock, PropertyMock, patch

import pytest
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResultType

from custom_components.dual_smart_thermostat.const import (
    ATTR_OPENING_TIMEOUT,
    CONF_COLD_TOLERANCE,
    CONF_COOLER,
    CONF_FAN,
    CONF_FAN_HOT_TOLERANCE,
    CONF_FAN_HOT_TOLERANCE_TOGGLE,
    CONF_FLOOR_SENSOR,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_HUMIDITY_SENSOR,
    CONF_MIN_DUR,
    CONF_OPENINGS,
    CONF_OPENINGS_SCOPE,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    CONF_TARGET_HUMIDITY,
    DOMAIN,
    SYSTEM_TYPE_AC_ONLY,
    SYSTEM_TYPE_HEATER_COOLER,
    SYSTEM_TYPE_SIMPLE_HEATER,
)
from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_hass():
    """Create a mock hass instance."""
    hass = Mock()
    hass.config_entries = Mock()
    hass.config_entries.async_update_entry = AsyncMock()
    hass.config_entries.async_entries = Mock(return_value=[])
    hass.data = {DOMAIN: {}}
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
    config_entry.options = {}
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
    config_entry.options = {}
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
    config_entry.options = {}
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
    config_entry.options = {}
    config_entry.entry_id = "test_dual_stage_entry"
    return config_entry


@pytest.fixture
def simple_heater_config_entry():
    """Create a mock config entry for simple heater system."""
    config_entry = Mock()
    config_entry.data = {
        CONF_NAME: "Simple Heater",
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER,
        CONF_SENSOR: "sensor.temp",
        CONF_HEATER: "switch.heater",
    }
    config_entry.options = {}
    config_entry.entry_id = "test_simple_heater_entry"
    return config_entry


@pytest.fixture
def config_entry_with_presets():
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


# ============================================================================
# BASIC FLOW TESTS
# ============================================================================


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


# ============================================================================
# OPENINGS CONFIGURATION TESTS
# ============================================================================


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


# ============================================================================
# SYSTEM-SPECIFIC FEATURE TESTS
# ============================================================================


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


# ============================================================================
# FEATURE PERSISTENCE TESTS - FAN SETTINGS
# ============================================================================


async def test_heater_cooler_fan_settings_prefilled_in_options_flow(mock_hass):
    """Test that fan settings are pre-filled when reopening options flow.

    Scenario:
    1. User configures heater_cooler with fan feature enabled
    2. User saves configuration
    3. User opens options flow
    4. Fan settings should be pre-filled with previous values

    Acceptance: Fan configuration step shows existing values as defaults

    With simplified options flow:
    - Fan feature already configured in entry.data
    - Init step shows runtime tuning
    - Flow proceeds automatically to fan_options step
    """
    # Simulate existing config entry with fan configured
    config_entry = Mock()
    config_entry.data = {
        CONF_NAME: "Test Thermostat",
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
        CONF_SENSOR: "sensor.temp",
        CONF_HEATER: "switch.heater",
        CONF_COOLER: "switch.cooler",
        # Fan feature previously configured
        CONF_FAN: "switch.fan",
        CONF_FAN_HOT_TOLERANCE: 0.7,
        CONF_FAN_HOT_TOLERANCE_TOGGLE: "switch.fan_toggle",
    }
    config_entry.options = {}
    config_entry.entry_id = "test_entry"

    flow = OptionsFlowHandler(config_entry)
    flow.hass = mock_hass

    # Initialize options flow - shows runtime tuning parameters
    result = await flow.async_step_init()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    # Submit runtime parameters (empty dict uses defaults)
    result = await flow.async_step_init({})

    # Flow should proceed to fan_options step since fan is already configured
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "fan_options"

    # Verify defaults are pre-filled from existing config
    schema = result["data_schema"].schema

    fan_field_default = None
    fan_hot_tolerance_default = None
    fan_hot_tolerance_toggle_default = None

    for key in schema.keys():
        if hasattr(key, "schema"):
            field_name = key.schema
            if field_name == CONF_FAN and hasattr(key, "default"):
                fan_field_default = (
                    key.default() if callable(key.default) else key.default
                )
            elif field_name == CONF_FAN_HOT_TOLERANCE and hasattr(key, "default"):
                fan_hot_tolerance_default = (
                    key.default() if callable(key.default) else key.default
                )
            elif field_name == CONF_FAN_HOT_TOLERANCE_TOGGLE and hasattr(
                key, "default"
            ):
                fan_hot_tolerance_toggle_default = (
                    key.default() if callable(key.default) else key.default
                )

    # Assert that existing values are used as defaults
    assert (
        fan_field_default == "switch.fan"
    ), f"Fan field not pre-filled, got: {fan_field_default}"
    assert (
        fan_hot_tolerance_default == 0.7
    ), f"Fan hot tolerance not pre-filled, got: {fan_hot_tolerance_default}"
    assert (
        fan_hot_tolerance_toggle_default == "switch.fan_toggle"
    ), f"Fan toggle not pre-filled, got: {fan_hot_tolerance_toggle_default}"


async def test_simple_heater_fan_settings_prefilled_in_options_flow(mock_hass):
    """Test fan settings persistence for simple_heater system type."""
    config_entry = Mock()
    config_entry.data = {
        CONF_NAME: "Simple Heater",
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER,
        CONF_SENSOR: "sensor.temp",
        CONF_HEATER: "switch.heater",
        CONF_FAN: "switch.fan",
        CONF_FAN_HOT_TOLERANCE: 0.5,
    }
    config_entry.options = {}
    config_entry.entry_id = "test_entry"

    flow = OptionsFlowHandler(config_entry)
    flow.hass = mock_hass

    # Navigate through simplified options flow
    await flow.async_step_init()
    result = await flow.async_step_init({})

    # Should proceed to fan_options since fan is already configured
    assert result["step_id"] == "fan_options"

    # Check defaults
    schema = result["data_schema"].schema
    fan_hot_tolerance_default = None

    for key in schema.keys():
        if hasattr(key, "schema") and key.schema == CONF_FAN_HOT_TOLERANCE:
            if hasattr(key, "default"):
                fan_hot_tolerance_default = (
                    key.default() if callable(key.default) else key.default
                )
                break

    assert (
        fan_hot_tolerance_default == 0.5
    ), "Fan hot tolerance not pre-filled for simple_heater"


async def test_ac_only_fan_settings_prefilled_in_options_flow(mock_hass):
    """Test fan settings persistence for ac_only system type."""
    config_entry = Mock()
    config_entry.data = {
        CONF_NAME: "AC Only",
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY,
        CONF_SENSOR: "sensor.temp",
        CONF_HEATER: "switch.ac",
        CONF_FAN: "switch.fan",
        CONF_FAN_HOT_TOLERANCE: 0.3,
        CONF_FAN_HOT_TOLERANCE_TOGGLE: "switch.ac_fan_toggle",
    }
    config_entry.options = {}
    config_entry.entry_id = "test_entry"

    flow = OptionsFlowHandler(config_entry)
    flow.hass = mock_hass

    await flow.async_step_init()
    result = await flow.async_step_init({})

    # Should proceed to fan_options since fan is already configured
    assert result["step_id"] == "fan_options"

    schema = result["data_schema"].schema
    defaults = {}

    for key in schema.keys():
        if hasattr(key, "schema"):
            field_name = key.schema
            if hasattr(key, "default"):
                defaults[field_name] = (
                    key.default() if callable(key.default) else key.default
                )

    assert defaults.get(CONF_FAN) == "switch.fan"
    assert defaults.get(CONF_FAN_HOT_TOLERANCE) == 0.3
    assert defaults.get(CONF_FAN_HOT_TOLERANCE_TOGGLE) == "switch.ac_fan_toggle"


# ============================================================================
# FEATURE PERSISTENCE TESTS - HUMIDITY SETTINGS
# ============================================================================


async def test_heater_cooler_humidity_settings_prefilled_in_options_flow(mock_hass):
    """Test that humidity settings are pre-filled when reopening options flow."""
    config_entry = Mock()
    config_entry.data = {
        CONF_NAME: "Test Thermostat",
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
        CONF_SENSOR: "sensor.temp",
        CONF_HEATER: "switch.heater",
        CONF_COOLER: "switch.cooler",
        # Humidity feature previously configured
        CONF_HUMIDITY_SENSOR: "sensor.humidity",
        CONF_TARGET_HUMIDITY: 55.0,
    }
    config_entry.options = {}
    config_entry.entry_id = "test_entry"

    flow = OptionsFlowHandler(config_entry)
    flow.hass = mock_hass

    await flow.async_step_init()
    result = await flow.async_step_init({})

    # Should proceed to humidity_options since humidity is already configured
    assert result["step_id"] == "humidity_options"

    schema = result["data_schema"].schema
    defaults = {}

    for key in schema.keys():
        if hasattr(key, "schema"):
            field_name = key.schema
            if hasattr(key, "default"):
                defaults[field_name] = (
                    key.default() if callable(key.default) else key.default
                )

    assert defaults.get(CONF_HUMIDITY_SENSOR) == "sensor.humidity"
    assert defaults.get(CONF_TARGET_HUMIDITY) == 55.0


async def test_simple_heater_humidity_settings_prefilled_in_options_flow(mock_hass):
    """Test humidity settings persistence for simple_heater system type."""
    config_entry = Mock()
    config_entry.data = {
        CONF_NAME: "Simple Heater",
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER,
        CONF_SENSOR: "sensor.temp",
        CONF_HEATER: "switch.heater",
        CONF_HUMIDITY_SENSOR: "sensor.humidity",
        CONF_TARGET_HUMIDITY: 45.0,
    }
    config_entry.options = {}
    config_entry.entry_id = "test_entry"

    flow = OptionsFlowHandler(config_entry)
    flow.hass = mock_hass

    await flow.async_step_init()
    result = await flow.async_step_init({})

    # Should proceed to humidity_options since humidity is already configured
    assert result["step_id"] == "humidity_options"

    schema = result["data_schema"].schema
    target_humidity_default = None

    for key in schema.keys():
        if hasattr(key, "schema") and key.schema == CONF_TARGET_HUMIDITY:
            if hasattr(key, "default"):
                target_humidity_default = (
                    key.default() if callable(key.default) else key.default
                )
                break

    assert (
        target_humidity_default == 45.0
    ), "Target humidity not pre-filled for simple_heater"


# ============================================================================
# FEATURE PERSISTENCE EDGE CASE TESTS
# ============================================================================


async def test_fan_not_configured_skips_fan_step(mock_hass):
    """Test that when fan was never configured, options flow skips fan step.

    With simplified options flow, feature steps only appear for features
    already configured in entry.data. If fan is not configured, the flow
    should complete without showing the fan_options step.
    """
    config_entry = Mock()
    config_entry.data = {
        CONF_NAME: "Test",
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
        CONF_SENSOR: "sensor.temp",
        CONF_HEATER: "switch.heater",
        CONF_COOLER: "switch.cooler",
        # No fan configuration
    }
    config_entry.options = {}
    config_entry.entry_id = "test_entry"

    flow = OptionsFlowHandler(config_entry)
    flow.hass = mock_hass

    await flow.async_step_init()
    result = await flow.async_step_init({})

    # Should complete successfully without showing fan_options
    # Result can be either CREATE_ENTRY or another step, but NOT fan_options
    if result["type"] == FlowResultType.FORM:
        assert result.get("step_id") != "fan_options"
    else:
        # Flow completed - this is expected when no features configured
        assert result["type"] == FlowResultType.CREATE_ENTRY


# ============================================================================
# PRESET DETECTION TESTS
# ============================================================================


async def test_preset_toggle_checked_when_presets_configured(
    mock_hass, config_entry_with_presets
):
    """Test that options flow shows preset_selection step when presets are configured.

    With simplified options flow, there is no features toggle step.
    Instead, the flow automatically navigates through configured features.
    This test verifies that preset_selection appears when presets are configured.
    """
    # Create options flow
    flow = OptionsFlowHandler(config_entry_with_presets)
    flow.hass = mock_hass

    # Mock the config_entry property to return our mock
    type(flow).config_entry = PropertyMock(return_value=config_entry_with_presets)

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


# ============================================================================
# COMPLETE FLOW INTEGRATION TEST
# ============================================================================


@pytest.mark.asyncio
async def test_ac_only_options_flow_with_fan_and_humidity_enabled(mock_hass):
    """Test that AC-only options flow includes both fan and humidity options when enabled.

    This comprehensive test verifies the complete flow progression when multiple
    features are configured.
    """
    # Mock config entry for AC-only system with features already configured
    mock_config_entry = Mock()
    mock_config_entry.data = {
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY,
        CONF_HEATER: "switch.ac_unit",
        CONF_SENSOR: "sensor.temperature",
        CONF_COLD_TOLERANCE: 0.3,
        CONF_HOT_TOLERANCE: 0.3,
        CONF_MIN_DUR: {"minutes": 5},
        # Pre-configure fan and humidity features
        "fan": "switch.fan",
        "humidity_sensor": "sensor.humidity",
        # Pre-configure openings
        "openings": ["binary_sensor.window"],
        # Pre-configure presets
        "presets": ["away", "home"],
        "away_temp": 16,
        "home_temp": 21,
    }
    mock_config_entry.options = {}
    mock_config_entry.entry_id = "test_entry"

    # Create handler
    handler = OptionsFlowHandler(mock_config_entry)
    handler.hass = mock_hass

    # Test flow progression to identify all steps
    steps_visited = []

    # Start with init step (runtime tuning parameters)
    result = await handler.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "init"
    steps_visited.append("init")

    # Submit init step with runtime tuning
    result = await handler.async_step_init(
        {
            CONF_COLD_TOLERANCE: 0.3,
            CONF_HOT_TOLERANCE: 0.3,
        }
    )

    # Continue through the flow to see all steps
    max_iterations = 10  # Prevent infinite loops
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        if result["type"] == "create_entry":
            # We've reached the end
            steps_visited.append("create_entry")
            break
        elif result["type"] == "form":
            current_step = result["step_id"]
            steps_visited.append(current_step)

            # Get the appropriate step method
            step_method = getattr(handler, f"async_step_{current_step}")

            # Call with empty input to see next step
            try:
                result = await step_method({})
            except Exception:
                # Some steps might require specific input, which is okay
                break
        else:
            break

    # Check that we have the key steps - since features are pre-configured,
    # they should appear in the flow for tuning
    expected_steps = [
        "init",  # Runtime tuning
        "fan_options",  # Fan is configured
        "humidity_options",  # Humidity is configured
        "openings_options",  # Openings are configured
        "preset_selection",  # Presets are configured
    ]

    missing_steps = [step for step in expected_steps if step not in steps_visited]

    assert not missing_steps, f"Missing expected steps: {missing_steps}"
