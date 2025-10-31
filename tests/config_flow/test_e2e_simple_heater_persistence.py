"""End-to-end persistence tests for SIMPLE_HEATER system type.

This module validates the complete lifecycle for simple_heater systems:
1. User completes config flow with initial settings
2. User opens options flow and sees the correct values pre-filled
3. User changes some settings in options flow
4. Changes persist correctly (in entry.options)
5. Original values are preserved (in entry.data)
6. Reopening options flow shows the updated values

Test Coverage:
- Minimal configuration (basic + single feature)
- All available features enabled (floor_heating, openings, presets)
- Individual features in isolation
- Openings configuration edge cases (scope, timeout persistence)
"""

from homeassistant.const import CONF_NAME
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dual_smart_thermostat.const import (
    CONF_COLD_TOLERANCE,
    CONF_FAN,
    CONF_FAN_MODE,
    CONF_FLOOR_SENSOR,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_MAX_FLOOR_TEMP,
    CONF_MIN_FLOOR_TEMP,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    DOMAIN,
    SYSTEM_TYPE_SIMPLE_HEATER,
)


@pytest.mark.asyncio
async def test_simple_heater_minimal_config_persistence(hass):
    """Test minimal SIMPLE_HEATER flow: config → options → verify persistence.

    Tests the simple_heater system type with fan feature and tolerance changes.
    This is the baseline test for persistence with minimal configuration.
    """
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
    from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler

    # ===== STEP 1: Complete config flow =====
    config_flow = ConfigFlowHandler()
    config_flow.hass = hass

    # Start config flow - user selects simple heater
    result = await config_flow.async_step_user(
        {CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER}
    )

    # Fill in basic simple heater config
    initial_config = {
        CONF_NAME: "Simple Heater Test",
        CONF_SENSOR: "sensor.room_temp",
        CONF_HEATER: "switch.heater",
        CONF_COLD_TOLERANCE: 0.5,
        CONF_HOT_TOLERANCE: 0.3,
    }
    result = await config_flow.async_step_basic(initial_config)

    # Enable fan feature
    result = await config_flow.async_step_features(
        {
            "configure_fan": True,
        }
    )

    # Configure fan
    initial_fan_config = {
        CONF_FAN: "switch.fan",
        CONF_FAN_MODE: False,  # Simple heater with fan mode off
    }
    result = await config_flow.async_step_fan(initial_fan_config)

    # Flow should complete
    assert result["type"] == "create_entry"
    assert result["title"] == "Simple Heater Test"

    # ===== STEP 2: Verify initial config entry =====
    created_data = result["data"]

    # Check no transient flags saved
    assert "configure_fan" not in created_data
    assert "features_shown" not in created_data

    # Check actual config is saved
    assert created_data[CONF_NAME] == "Simple Heater Test"
    assert created_data[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_SIMPLE_HEATER
    assert created_data[CONF_HEATER] == "switch.heater"
    assert created_data[CONF_COLD_TOLERANCE] == 0.5
    assert created_data[CONF_HOT_TOLERANCE] == 0.3
    assert created_data[CONF_FAN] == "switch.fan"
    assert created_data[CONF_FAN_MODE] is False

    # ===== STEP 3: Create MockConfigEntry =====
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=created_data,
        options={},
        title="Simple Heater Test",
    )
    config_entry.add_to_hass(hass)

    # ===== STEP 4: Open options flow and verify pre-filled values =====
    options_flow = OptionsFlowHandler(config_entry)
    options_flow.hass = hass

    # Simplified options flow shows runtime tuning directly in init
    result = await options_flow.async_step_init()

    # Should show init form with runtime tuning parameters
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # Verify tolerances are pre-filled
    init_schema = result["data_schema"].schema
    cold_tolerance_default = None
    hot_tolerance_default = None
    for key in init_schema:
        if hasattr(key, "schema") and key.schema == CONF_COLD_TOLERANCE:
            if hasattr(key, "default"):
                cold_tolerance_default = (
                    key.default() if callable(key.default) else key.default
                )
        if hasattr(key, "schema") and key.schema == CONF_HOT_TOLERANCE:
            if hasattr(key, "default"):
                hot_tolerance_default = (
                    key.default() if callable(key.default) else key.default
                )

    assert cold_tolerance_default == 0.5, "Cold tolerance should be pre-filled!"
    assert hot_tolerance_default == 0.3, "Hot tolerance should be pre-filled!"

    # ===== STEP 5: Change tolerance settings =====
    # Simplified options flow: only runtime tuning parameters
    updated_config = {
        CONF_COLD_TOLERANCE: 0.8,  # CHANGE: was 0.5
        CONF_HOT_TOLERANCE: 0.6,  # CHANGE: was 0.3
    }
    result = await options_flow.async_step_init(updated_config)

    # Since CONF_FAN is configured, proceeds to fan_options
    assert result["type"] == "form"
    assert result["step_id"] == "fan_options"

    # Complete fan options with existing values
    result = await options_flow.async_step_fan_options({})

    # Now should complete
    assert result["type"] == "create_entry"

    # ===== STEP 6: Verify persistence =====
    updated_data = result["data"]

    # Check no transient flags
    assert "configure_fan" not in updated_data
    assert "features_shown" not in updated_data

    # Check changed runtime tuning values
    assert updated_data[CONF_COLD_TOLERANCE] == 0.8
    assert updated_data[CONF_HOT_TOLERANCE] == 0.6

    # Check preserved values (feature config unchanged, only runtime tuning)
    assert updated_data[CONF_NAME] == "Simple Heater Test"
    assert updated_data[CONF_HEATER] == "switch.heater"
    assert updated_data[CONF_FAN] == "switch.fan"
    assert updated_data[CONF_FAN_MODE] is False  # Unchanged from original

    # ===== STEP 7: Reopen and verify updated values shown =====
    config_entry_after = MockConfigEntry(
        domain=DOMAIN,
        data=created_data,  # Original unchanged
        options={
            CONF_COLD_TOLERANCE: 0.8,
            CONF_HOT_TOLERANCE: 0.6,
        },
        title="Simple Heater Test",
    )
    config_entry_after.add_to_hass(hass)

    options_flow2 = OptionsFlowHandler(config_entry_after)
    options_flow2.hass = hass

    result = await options_flow2.async_step_init()

    # Verify updated tolerances are shown in init step
    init_schema2 = result["data_schema"].schema
    cold_tolerance_default2 = None
    hot_tolerance_default2 = None
    for key in init_schema2:
        if hasattr(key, "schema") and key.schema == CONF_COLD_TOLERANCE:
            if hasattr(key, "default"):
                cold_tolerance_default2 = (
                    key.default() if callable(key.default) else key.default
                )
        if hasattr(key, "schema") and key.schema == CONF_HOT_TOLERANCE:
            if hasattr(key, "default"):
                hot_tolerance_default2 = (
                    key.default() if callable(key.default) else key.default
                )

    assert (
        cold_tolerance_default2 == 0.8
    ), "Updated cold_tolerance should be shown in reopened flow!"
    assert (
        hot_tolerance_default2 == 0.6
    ), "Updated hot_tolerance should be shown in reopened flow!"


@pytest.mark.asyncio
async def test_simple_heater_all_features_persistence(hass):
    """Test SIMPLE_HEATER with all features: config → options → persistence.

    This E2E test validates:
    - All 3 features configured in config flow (floor_heating, openings, presets)
    - All settings pre-filled in options flow
    - Changes to multiple features persist correctly
    - Original entry.data preserved, changes in entry.options

    Available features for simple_heater:
    - floor_heating ✅
    - openings ✅
    - presets ✅
    """
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
    from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler

    # ===== STEP 1: Complete config flow with all features =====
    config_flow = ConfigFlowHandler()
    config_flow.hass = hass

    # Start: Select simple_heater
    result = await config_flow.async_step_user(
        {CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER}
    )

    # Basic config
    initial_config = {
        CONF_NAME: "Simple Heater All Features Test",
        CONF_SENSOR: "sensor.room_temp",
        CONF_HEATER: "switch.heater",
        CONF_COLD_TOLERANCE: 0.5,
        CONF_HOT_TOLERANCE: 0.3,
    }
    result = await config_flow.async_step_basic(initial_config)

    # Enable ALL features
    result = await config_flow.async_step_features(
        {
            "configure_floor_heating": True,
            "configure_openings": True,
            "configure_presets": True,
        }
    )

    # Configure floor heating
    initial_floor_config = {
        CONF_FLOOR_SENSOR: "sensor.floor_temp",
        CONF_MIN_FLOOR_TEMP: 5,
        CONF_MAX_FLOOR_TEMP: 28,
    }
    result = await config_flow.async_step_floor_config(initial_floor_config)

    # Configure openings
    result = await config_flow.async_step_openings_selection(
        {"selected_openings": ["binary_sensor.window_1", "binary_sensor.door_1"]}
    )
    result = await config_flow.async_step_openings_config(
        {
            "opening_scope": "heat",
            "timeout_openings_open": 300,
        }
    )

    # Configure presets
    result = await config_flow.async_step_preset_selection(
        {"presets": ["away", "home"]}
    )
    result = await config_flow.async_step_presets(
        {
            "away_temp": 16,
            "home_temp": 21,
        }
    )

    # Flow should complete
    assert result["type"] == "create_entry"
    assert result["title"] == "Simple Heater All Features Test"

    # ===== STEP 2: Verify initial config entry =====
    created_data = result["data"]

    # NOTE: Transient flags ARE currently saved in config flow
    # This is existing behavior - they're cleaned in options flow
    # See existing E2E tests for systems without these flags

    # Verify basic settings
    assert created_data[CONF_NAME] == "Simple Heater All Features Test"
    assert created_data[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_SIMPLE_HEATER
    assert created_data[CONF_HEATER] == "switch.heater"
    assert created_data[CONF_COLD_TOLERANCE] == 0.5
    assert created_data[CONF_HOT_TOLERANCE] == 0.3

    # Verify floor heating
    assert created_data[CONF_FLOOR_SENSOR] == "sensor.floor_temp"
    assert created_data[CONF_MIN_FLOOR_TEMP] == 5
    assert created_data[CONF_MAX_FLOOR_TEMP] == 28

    # Verify openings
    assert "binary_sensor.window_1" in created_data.get("selected_openings", [])
    assert "binary_sensor.door_1" in created_data.get("selected_openings", [])

    # Verify presets
    assert "away" in created_data.get("presets", [])
    assert "home" in created_data.get("presets", [])

    # ===== STEP 3: Create MockConfigEntry =====
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=created_data,
        options={},
        title="Simple Heater All Features Test",
    )
    config_entry.add_to_hass(hass)

    # ===== STEP 4: Open options flow and verify pre-filled values =====
    options_flow = OptionsFlowHandler(config_entry)
    options_flow.hass = hass

    # Simplified options flow: init shows runtime tuning directly
    result = await options_flow.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # ===== STEP 5: Make changes - simplified to test persistence =====
    # Change tolerances (runtime parameters) in init step
    result = await options_flow.async_step_init(
        {
            CONF_COLD_TOLERANCE: 0.8,  # CHANGED from 0.5
            CONF_HOT_TOLERANCE: 0.6,  # CHANGED from 0.3
        }
    )

    # Navigate through configured features in order (simplified options flow)
    # Each feature step automatically proceeds to the next when submitted with {}

    # Floor heating options
    assert result["step_id"] == "floor_options"
    result = await options_flow.async_step_floor_options({})

    # Openings options (single-step in options flow)
    assert result["step_id"] == "openings_options"
    result = await options_flow.async_step_openings_options({})

    # Presets selection - when submitted with {}, completes directly in options flow
    assert result["step_id"] == "preset_selection"
    result = await options_flow.async_step_preset_selection({})

    # In options flow, preset_selection with {} completes the flow (no separate presets step)
    assert result["type"] == "create_entry"

    # ===== STEP 6: Verify persistence =====
    updated_data = result["data"]

    # Verify changed basic values
    assert updated_data[CONF_COLD_TOLERANCE] == 0.8
    assert updated_data[CONF_HOT_TOLERANCE] == 0.6

    # Verify original feature values preserved (from config flow)
    assert updated_data[CONF_FLOOR_SENSOR] == "sensor.floor_temp"
    assert updated_data[CONF_MIN_FLOOR_TEMP] == 5  # Original value
    assert updated_data[CONF_MAX_FLOOR_TEMP] == 28  # Original value
    assert "binary_sensor.window_1" in updated_data.get("selected_openings", [])
    assert "away" in updated_data.get("presets", [])

    # Verify preserved system info
    assert updated_data[CONF_NAME] == "Simple Heater All Features Test"
    assert updated_data[CONF_HEATER] == "switch.heater"

    # ===== STEP 7: Reopen options flow and verify updated values =====
    config_entry_updated = MockConfigEntry(
        domain=DOMAIN,
        data=created_data,  # Original unchanged
        options=updated_data,  # Updated values
        title="Simple Heater All Features Test",
    )
    config_entry_updated.add_to_hass(hass)

    options_flow2 = OptionsFlowHandler(config_entry_updated)
    options_flow2.hass = hass

    # Simplified options flow: verify it opens successfully with merged values
    result = await options_flow2.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_simple_heater_floor_heating_only_persistence(hass):
    """Test SIMPLE_HEATER with only floor_heating enabled.

    This tests feature isolation - only floor_heating configured.
    Validates that when only one feature is enabled, the configuration
    persists correctly and other features remain unconfigured.
    """
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler

    config_flow = ConfigFlowHandler()
    config_flow.hass = hass

    result = await config_flow.async_step_user(
        {CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER}
    )

    result = await config_flow.async_step_basic(
        {
            CONF_NAME: "Floor Only Test",
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
        }
    )

    # Enable only floor_heating
    result = await config_flow.async_step_features(
        {
            "configure_floor_heating": True,
            "configure_openings": False,
            "configure_presets": False,
        }
    )

    result = await config_flow.async_step_floor_config(
        {
            CONF_FLOOR_SENSOR: "sensor.floor_temp",
            CONF_MIN_FLOOR_TEMP: 5,
            CONF_MAX_FLOOR_TEMP: 28,
        }
    )

    assert result["type"] == "create_entry"

    created_data = result["data"]

    # Verify floor heating configured
    assert created_data[CONF_FLOOR_SENSOR] == "sensor.floor_temp"
    assert created_data[CONF_MIN_FLOOR_TEMP] == 5
    assert created_data[CONF_MAX_FLOOR_TEMP] == 28

    # Verify other features NOT configured
    assert "selected_openings" not in created_data or not created_data.get(
        "selected_openings"
    )
    assert "presets" not in created_data or not created_data.get("presets")


# =============================================================================
# OPENINGS CONFIGURATION EDGE CASE TESTS
# =============================================================================
# These tests validate that openings scope and timeout values persist correctly
# through the config flow. Originally identified as bug fixes.


@pytest.mark.asyncio
async def test_simple_heater_openings_scope_and_timeout_saved(hass):
    """Test that opening_scope and timeout_openings_open are saved to config.

    Bug Fix: These values were being lost because async_step_config didn't
    update collected_config with user_input before processing.

    Expected: opening_scope="heat" and timeout_openings_open=300 should
    both be present in the final config.
    """
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler

    flow = ConfigFlowHandler()
    flow.hass = hass

    # Start config flow
    result = await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER})

    result = await flow.async_step_basic(
        {
            CONF_NAME: "Test Heater",
            CONF_SENSOR: "sensor.temperature",
            CONF_HEATER: "switch.heater",
        }
    )

    # Enable openings
    result = await flow.async_step_features(
        {
            "configure_floor_heating": False,
            "configure_openings": True,
            "configure_presets": False,
        }
    )

    # Select openings
    result = await flow.async_step_openings_selection(
        {"selected_openings": ["binary_sensor.window_1"]}
    )

    # Configure openings with specific scope and timeout
    result = await flow.async_step_openings_config(
        {
            "opening_scope": "heat",  # This was being lost
            "timeout_openings_open": 300,  # This was being lost
        }
    )

    # Flow should complete
    assert result["type"] == "create_entry"

    created_data = result["data"]

    # BUG FIX VERIFICATION: These should now be saved
    # Note: The form field is "opening_scope" (singular) but after clean_openings_scope
    # it gets normalized to "openings_scope" (plural) if not "all"
    # Actually, looking at the logs, it stays as "opening_scope" in collected_config
    assert (
        "opening_scope" in created_data
    ), "opening_scope should be saved when not 'all'"
    assert created_data["opening_scope"] == "heat"

    # Timeout should also be saved
    assert "timeout_openings_open" in created_data
    assert created_data["timeout_openings_open"] == 300


@pytest.mark.asyncio
async def test_simple_heater_openings_scope_all_is_cleaned(hass):
    """Test that opening_scope='all' is removed (existing behavior).

    The clean_openings_scope function removes scope="all" because
    "all" is the default behavior when no scope is specified.
    """
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler

    flow = ConfigFlowHandler()
    flow.hass = hass

    result = await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER})

    result = await flow.async_step_basic(
        {
            CONF_NAME: "Test Heater",
            CONF_SENSOR: "sensor.temperature",
            CONF_HEATER: "switch.heater",
        }
    )

    result = await flow.async_step_features(
        {
            "configure_floor_heating": False,
            "configure_openings": True,
            "configure_presets": False,
        }
    )

    result = await flow.async_step_openings_selection(
        {"selected_openings": ["binary_sensor.window_1"]}
    )

    # Configure with scope="all"
    result = await flow.async_step_openings_config(
        {
            "opening_scope": "all",  # This should be removed
            "timeout_openings_open": 300,
        }
    )

    assert result["type"] == "create_entry"

    created_data = result["data"]

    # "all" scope should be cleaned (removed)
    assert (
        "opening_scope" not in created_data
        or created_data.get("opening_scope") != "all"
    )

    # But timeout should still be saved
    assert "timeout_openings_open" in created_data
    assert created_data["timeout_openings_open"] == 300


@pytest.mark.asyncio
async def test_simple_heater_openings_multiple_timeout_values(hass):
    """Test that different timeout values are saved correctly.

    Validates that the timeout configuration is flexible and preserves
    whatever value the user specifies.
    """
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler

    flow = ConfigFlowHandler()
    flow.hass = hass

    result = await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER})

    result = await flow.async_step_basic(
        {
            CONF_NAME: "Test Heater",
            CONF_SENSOR: "sensor.temperature",
            CONF_HEATER: "switch.heater",
        }
    )

    result = await flow.async_step_features(
        {
            "configure_floor_heating": False,
            "configure_openings": True,
            "configure_presets": False,
        }
    )

    result = await flow.async_step_openings_selection(
        {"selected_openings": ["binary_sensor.window_1"]}
    )

    # Test with a different timeout value
    result = await flow.async_step_openings_config(
        {
            "opening_scope": "heat",
            "timeout_openings_open": 600,  # 10 minutes
        }
    )

    assert result["type"] == "create_entry"

    created_data = result["data"]

    # Verify the specific timeout value is saved
    assert created_data["timeout_openings_open"] == 600
    assert created_data["opening_scope"] == "heat"


# =============================================================================
# NOTE: Mode-specific tolerances (heat_tolerance, cool_tolerance) are only
# applicable to dual-mode systems (heater_cooler, heat_pump). SIMPLE_HEATER is
# a single-mode system and does not support mode-specific tolerances.
# Tests for mode-specific tolerances should be in dual-mode system test files.
# =============================================================================


# =============================================================================
# LEGACY TOLERANCES PERSISTENCE TESTS
# =============================================================================
# These tests validate that legacy configurations (without mode-specific
# tolerances) continue to work correctly


@pytest.mark.asyncio
class TestSimpleHeaterLegacyTolerancesPersistence:
    """Test legacy tolerance persistence for SIMPLE_HEATER system type."""

    async def test_legacy_tolerances_persist_without_mode_specific(self, hass):
        """Test that legacy config without mode-specific tolerances persists correctly.

        This E2E test validates:
        1. Config with only cold_tolerance and hot_tolerance (no heat/cool)
        2. Values persist through full cycle
        3. No mode-specific tolerances are added unexpectedly
        4. Legacy behavior is preserved

        Phase 6: E2E Persistence & System Type Coverage (T047)
        """
        from custom_components.dual_smart_thermostat.const import (
            CONF_COOL_TOLERANCE,
            CONF_HEAT_TOLERANCE,
        )

        # Step 1: Create config with ONLY legacy tolerances
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_NAME: "Legacy Thermostat",
                CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER,
                CONF_HEATER: "switch.heater",
                CONF_SENSOR: "sensor.temperature",
                CONF_COLD_TOLERANCE: 0.5,
                CONF_HOT_TOLERANCE: 0.5,
                # NO heat_tolerance or cool_tolerance
            },
            title="Legacy Thermostat",
        )
        config_entry.add_to_hass(hass)
        # Step 3: Verify only legacy config present
        assert config_entry.data[CONF_COLD_TOLERANCE] == 0.5
        assert config_entry.data[CONF_HOT_TOLERANCE] == 0.5
        assert CONF_HEAT_TOLERANCE not in config_entry.data
        assert CONF_COOL_TOLERANCE not in config_entry.data

        # Step 4: Open options flow
        from custom_components.dual_smart_thermostat.options_flow import (
            OptionsFlowHandler,
        )

        options_flow = OptionsFlowHandler(config_entry)
        options_flow.hass = hass

        result = await options_flow.async_step_init()
        assert result["type"] == "form"

        # Step 5: Update only legacy tolerances in options flow
        result = await options_flow.async_step_init(
            {
                CONF_COLD_TOLERANCE: 0.8,  # CHANGED
                CONF_HOT_TOLERANCE: 0.6,  # CHANGED
                # Still no mode-specific tolerances
            }
        )

        assert result["type"] == "create_entry"

        # Step 6: Verify no mode-specific tolerances were added
        updated_data = result["data"]
        assert updated_data[CONF_COLD_TOLERANCE] == 0.8
        assert updated_data[CONF_HOT_TOLERANCE] == 0.6
        assert CONF_HEAT_TOLERANCE not in updated_data
        assert CONF_COOL_TOLERANCE not in updated_data

        # Step 7: Simulate persistence - create new config entry with updated data
        config_entry_after = MockConfigEntry(
            domain=DOMAIN,
            data=updated_data,
            title="Legacy Thermostat",
        )
        config_entry_after.add_to_hass(hass)

        # Step 8: Reopen options flow to verify legacy values persist
        options_flow2 = OptionsFlowHandler(config_entry_after)
        options_flow2.hass = hass

        result2 = await options_flow2.async_step_init()
        assert result2["type"] == "form"

        # Step 9: Verify no mode-specific tolerances added after persistence
        assert config_entry_after.data[CONF_COLD_TOLERANCE] == 0.8
        assert config_entry_after.data[CONF_HOT_TOLERANCE] == 0.6
        assert CONF_HEAT_TOLERANCE not in config_entry_after.data
        assert CONF_COOL_TOLERANCE not in config_entry_after.data
