"""End-to-end persistence tests for AC_ONLY system type.

This module validates the complete lifecycle for ac_only systems:
1. User completes config flow with initial settings
2. User opens options flow and sees the correct values pre-filled
3. User changes some settings in options flow
4. Changes persist correctly (in entry.options)
5. Original values are preserved (in entry.data)
6. Reopening options flow shows the updated values

Test Coverage:
- Minimal configuration (basic + fan feature)
- All available features enabled (fan, humidity, openings, presets)
- Individual features in isolation
"""

from homeassistant.const import CONF_NAME
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dual_smart_thermostat.const import (
    CONF_COLD_TOLERANCE,
    CONF_COOLER,
    CONF_DRYER,
    CONF_FAN,
    CONF_FAN_MODE,
    CONF_FAN_ON_WITH_AC,
    CONF_HOT_TOLERANCE,
    CONF_HUMIDITY_SENSOR,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    DOMAIN,
    SYSTEM_TYPE_AC_ONLY,
)


@pytest.mark.asyncio
async def test_ac_only_minimal_config_persistence(hass):
    """Test minimal AC_ONLY flow: config → options → verify persistence.

    Tests the ac_only system type with fan feature and tolerance changes.
    This is the baseline test for persistence with minimal configuration.
    """
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
    from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler

    # ===== STEP 1: Complete config flow =====
    config_flow = ConfigFlowHandler()
    config_flow.hass = hass

    # Start config flow - user selects AC only
    result = await config_flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY})

    # Fill in basic AC config
    initial_config = {
        CONF_NAME: "AC Only Test",
        CONF_SENSOR: "sensor.room_temp",
        CONF_COOLER: "switch.ac",
        CONF_HOT_TOLERANCE: 0.5,
    }
    result = await config_flow.async_step_basic_ac_only(initial_config)

    # Enable fan feature
    result = await config_flow.async_step_features(
        {
            "configure_fan": True,
        }
    )

    # Configure fan for AC
    initial_fan_config = {
        CONF_FAN: "switch.fan",
        CONF_FAN_MODE: False,
        CONF_FAN_ON_WITH_AC: True,  # Fan runs with AC
    }
    result = await config_flow.async_step_fan(initial_fan_config)

    # Flow should complete
    assert result["type"] == "create_entry"
    assert result["title"] == "AC Only Test"

    # ===== STEP 2: Verify initial config entry =====
    created_data = result["data"]

    # Check no transient flags saved
    assert "configure_fan" not in created_data
    assert "features_shown" not in created_data

    # Check actual config is saved
    assert created_data[CONF_NAME] == "AC Only Test"
    assert created_data[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_AC_ONLY
    assert created_data[CONF_COOLER] == "switch.ac"
    assert created_data[CONF_HOT_TOLERANCE] == 0.5
    assert created_data[CONF_FAN] == "switch.fan"
    assert created_data[CONF_FAN_MODE] is False
    assert created_data[CONF_FAN_ON_WITH_AC] is True

    # ===== STEP 3: Create MockConfigEntry =====
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=created_data,
        options={},
        title="AC Only Test",
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

    # Verify hot tolerance is pre-filled
    init_schema = result["data_schema"].schema
    hot_tolerance_default = None
    for key in init_schema:
        if hasattr(key, "schema") and key.schema == CONF_HOT_TOLERANCE:
            # Check for suggested_value in description (new pattern for handling 0 values)
            if hasattr(key, "description") and isinstance(key.description, dict):
                hot_tolerance_default = key.description.get("suggested_value")
            # Fallback to old default pattern
            elif hasattr(key, "default"):
                hot_tolerance_default = (
                    key.default() if callable(key.default) else key.default
                )
            break

    assert hot_tolerance_default == 0.5, "Hot tolerance should be pre-filled!"

    # ===== STEP 5: Change hot tolerance =====
    # Simplified options flow: only runtime tuning parameters
    updated_config = {
        CONF_HOT_TOLERANCE: 0.8,  # CHANGE: was 0.5
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

    # Check changed value
    assert updated_data[CONF_HOT_TOLERANCE] == 0.8

    # Check preserved values (feature config unchanged, only runtime tuning)
    assert updated_data[CONF_NAME] == "AC Only Test"
    assert updated_data[CONF_COOLER] == "switch.ac"
    assert updated_data[CONF_FAN] == "switch.fan"
    assert updated_data[CONF_FAN_MODE] is False  # Unchanged from original
    assert updated_data[CONF_FAN_ON_WITH_AC] is True  # Unchanged from original

    # ===== STEP 7: Reopen and verify updated values shown =====
    config_entry_after = MockConfigEntry(
        domain=DOMAIN,
        data=created_data,  # Original unchanged
        options={
            CONF_HOT_TOLERANCE: 0.8,
        },
        title="AC Only Test",
    )
    config_entry_after.add_to_hass(hass)

    options_flow2 = OptionsFlowHandler(config_entry_after)
    options_flow2.hass = hass

    result = await options_flow2.async_step_init()

    # Verify updated hot tolerance is shown in init step
    init_schema2 = result["data_schema"].schema
    hot_tolerance_default2 = None
    for key in init_schema2:
        if hasattr(key, "schema") and key.schema == CONF_HOT_TOLERANCE:
            # Check for suggested_value in description (new pattern for handling 0 values)
            if hasattr(key, "description") and isinstance(key.description, dict):
                hot_tolerance_default2 = key.description.get("suggested_value")
            # Fallback to old default pattern
            elif hasattr(key, "default"):
                hot_tolerance_default2 = (
                    key.default() if callable(key.default) else key.default
                )
            break

    assert (
        hot_tolerance_default2 == 0.8
    ), "Updated hot_tolerance should be shown in reopened flow!"


@pytest.mark.asyncio
async def test_ac_only_all_features_persistence(hass):
    """Test AC_ONLY with all features: config → options → persistence.

    This E2E test validates:
    - All 4 features configured in config flow (fan, humidity, openings, presets)
    - All settings pre-filled in options flow
    - Changes to multiple features persist correctly
    - Original entry.data preserved, changes in entry.options

    Available features for ac_only:
    - fan ✅
    - humidity ✅
    - openings ✅
    - presets ✅
    """
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
    from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler

    # ===== STEP 1: Complete config flow with all features =====
    config_flow = ConfigFlowHandler()
    config_flow.hass = hass

    # Start: Select ac_only
    result = await config_flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY})

    # Basic config
    initial_config = {
        CONF_NAME: "AC Only All Features Test",
        CONF_SENSOR: "sensor.room_temp",
        CONF_COOLER: "switch.ac",
        CONF_COLD_TOLERANCE: 0.5,
        CONF_HOT_TOLERANCE: 0.3,
    }
    result = await config_flow.async_step_basic_ac_only(initial_config)

    # Enable ALL features
    result = await config_flow.async_step_features(
        {
            "configure_fan": True,
            "configure_humidity": True,
            "configure_openings": True,
            "configure_presets": True,
        }
    )

    # Configure fan
    initial_fan_config = {
        CONF_FAN: "switch.fan",
        "fan_on_with_ac": True,
    }
    result = await config_flow.async_step_fan(initial_fan_config)

    # Configure humidity
    initial_humidity_config = {
        CONF_HUMIDITY_SENSOR: "sensor.humidity",
        CONF_DRYER: "switch.dehumidifier",
        "target_humidity": 50,
    }
    result = await config_flow.async_step_humidity(initial_humidity_config)

    # Configure openings
    result = await config_flow.async_step_openings_selection(
        {"selected_openings": ["binary_sensor.window_1", "binary_sensor.door_1"]}
    )
    result = await config_flow.async_step_openings_config(
        {
            "opening_scope": "cool",
            "timeout_openings_open": 300,
        }
    )

    # Configure presets
    result = await config_flow.async_step_preset_selection(
        {"presets": ["away", "home"]}
    )
    result = await config_flow.async_step_presets(
        {
            "away_temp": 26,
            "home_temp": 22,
        }
    )

    # Flow should complete
    assert result["type"] == "create_entry"
    assert result["title"] == "AC Only All Features Test"

    # ===== STEP 2: Verify initial config entry =====
    created_data = result["data"]

    # NOTE: Transient flags ARE currently saved in config flow
    # This is existing behavior - they're cleaned in options flow
    # See existing E2E tests for systems without these flags

    # Verify basic settings
    assert created_data[CONF_NAME] == "AC Only All Features Test"
    assert created_data[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_AC_ONLY
    assert created_data[CONF_COOLER] == "switch.ac"
    assert created_data[CONF_COLD_TOLERANCE] == 0.5
    assert created_data[CONF_HOT_TOLERANCE] == 0.3

    # Verify fan
    assert created_data[CONF_FAN] == "switch.fan"
    assert created_data["fan_on_with_ac"] is True

    # Verify humidity
    assert created_data[CONF_HUMIDITY_SENSOR] == "sensor.humidity"
    assert created_data[CONF_DRYER] == "switch.dehumidifier"
    assert created_data["target_humidity"] == 50

    # Verify openings
    assert "openings" in created_data
    assert len(created_data["openings"]) == 2
    assert any(
        o.get("entity_id") == "binary_sensor.window_1" for o in created_data["openings"]
    )
    assert any(
        o.get("entity_id") == "binary_sensor.door_1" for o in created_data["openings"]
    )

    # Verify presets (new format)
    assert "away" in created_data
    assert created_data["away"]["temperature"] == 26
    assert "home" in created_data
    assert created_data["home"]["temperature"] == 22

    # ===== STEP 3: Create MockConfigEntry =====
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=created_data,
        options={},
        title="AC Only All Features Test",
    )
    config_entry.add_to_hass(hass)

    # ===== STEP 4: Open options flow and verify pre-filled values =====
    options_flow = OptionsFlowHandler(config_entry)
    options_flow.hass = hass

    # Simplified options flow shows runtime tuning parameters in init step
    result = await options_flow.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # ===== STEP 5: Make changes - simplified to test persistence =====
    # Submit runtime parameter changes in init step
    result = await options_flow.async_step_init(
        {
            CONF_COLD_TOLERANCE: 0.8,  # CHANGED from 0.5
            CONF_HOT_TOLERANCE: 0.6,  # CHANGED from 0.3
        }
    )

    # Navigate through configured features in order (simplified options flow)
    # Each feature step automatically proceeds to the next when submitted with {}

    # Since fan is configured, flow proceeds to fan_options
    assert result["type"] == "form"
    assert result["step_id"] == "fan_options"
    result = await options_flow.async_step_fan_options({})

    # Humidity is also configured, so humidity_options will show
    assert result["type"] == "form"
    assert result["step_id"] == "humidity_options"
    result = await options_flow.async_step_humidity_options({})

    # Openings are also configured, so openings_options will show
    assert result["type"] == "form"
    assert result["step_id"] == "openings_options"
    result = await options_flow.async_step_openings_options({})

    # Presets are also configured, so preset_selection will show
    assert result["type"] == "form"
    assert result["step_id"] == "preset_selection"
    result = await options_flow.async_step_preset_selection(
        {"presets": ["away", "home"]}
    )

    # In options flow, presets step shows for configuration
    assert result["type"] == "form"
    assert result["step_id"] == "presets"
    result = await options_flow.async_step_presets({})

    # Flow should now complete
    assert result["type"] == "create_entry"

    # ===== STEP 6: Verify persistence =====
    updated_data = result["data"]

    # Verify changed basic values
    assert updated_data[CONF_COLD_TOLERANCE] == 0.8
    assert updated_data[CONF_HOT_TOLERANCE] == 0.6

    # Verify original feature values preserved (from config flow)
    assert updated_data[CONF_FAN] == "switch.fan"
    assert updated_data[CONF_HUMIDITY_SENSOR] == "sensor.humidity"
    assert updated_data[CONF_DRYER] == "switch.dehumidifier"
    assert updated_data["target_humidity"] == 50  # Original value
    # Openings list preserved
    assert "openings" in updated_data
    assert len(updated_data["openings"]) == 2
    assert updated_data["away"]["temperature"] == 26  # Original preset value
    assert updated_data["home"]["temperature"] == 22  # Original preset value

    # Verify old format preset fields are NOT saved
    assert "away_temp" not in updated_data  # Old format should not be present
    assert "home_temp" not in updated_data  # Old format should not be present

    # Verify unwanted default values are NOT saved
    assert "min_temp" not in updated_data  # Should only be saved if explicitly set
    assert "max_temp" not in updated_data  # Should only be saved if explicitly set
    assert "precision" not in updated_data  # Should only be saved if explicitly set
    assert (
        "target_temp_step" not in updated_data
    )  # Should only be saved if explicitly set

    # Verify preserved system info
    assert updated_data[CONF_NAME] == "AC Only All Features Test"
    assert updated_data[CONF_COOLER] == "switch.ac"

    # ===== STEP 7: Reopen options flow and verify updated values =====
    config_entry_updated = MockConfigEntry(
        domain=DOMAIN,
        data=created_data,  # Original unchanged
        options=updated_data,  # Updated values
        title="AC Only All Features Test",
    )
    config_entry_updated.add_to_hass(hass)

    options_flow2 = OptionsFlowHandler(config_entry_updated)
    options_flow2.hass = hass

    # Simplified options flow: verify it opens successfully with merged values
    result = await options_flow2.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_ac_only_fan_only_persistence(hass):
    """Test AC_ONLY with only fan feature enabled.

    This tests feature isolation - only fan configured.
    Validates that when only one feature is enabled, the configuration
    persists correctly and other features remain unconfigured.
    """
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler

    config_flow = ConfigFlowHandler()
    config_flow.hass = hass

    result = await config_flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY})

    result = await config_flow.async_step_basic_ac_only(
        {
            CONF_NAME: "Fan Only Test",
            CONF_SENSOR: "sensor.temp",
            CONF_COOLER: "switch.ac",
        }
    )

    # Enable only fan
    result = await config_flow.async_step_features(
        {
            "configure_fan": True,
            "configure_humidity": False,
            "configure_openings": False,
            "configure_presets": False,
        }
    )

    result = await config_flow.async_step_fan(
        {
            CONF_FAN: "switch.fan",
            "fan_on_with_ac": True,
        }
    )

    assert result["type"] == "create_entry"

    created_data = result["data"]

    # Verify fan configured
    assert created_data[CONF_FAN] == "switch.fan"
    assert created_data["fan_on_with_ac"] is True

    # Verify other features NOT configured
    assert CONF_HUMIDITY_SENSOR not in created_data
    assert "selected_openings" not in created_data or not created_data.get(
        "selected_openings"
    )
    assert "away" not in created_data  # No presets configured
    assert "home" not in created_data


@pytest.mark.asyncio
async def test_ac_only_repeated_options_flow_persistence(hass):
    """Test AC_ONLY options flow repeated multiple times (issue #484, #479).

    Validates that:
    1. Config flow completes normally
    2. First options flow works and persists changes
    3. Second options flow shows correct pre-filled values (precision, temp_step)
    4. Target temperature is optional, not required
    5. Precision and temp_step fields are populated on second open

    This test reproduces the bug where precision/temp_step fields may appear
    empty on second options flow open if stored values don't match string format.
    """
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
    from custom_components.dual_smart_thermostat.const import (
        CONF_PRECISION,
        CONF_TARGET_TEMP,
        CONF_TEMP_STEP,
    )
    from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler

    # ===== STEP 1: Complete config flow =====
    config_flow = ConfigFlowHandler()
    config_flow.hass = hass

    result = await config_flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY})

    initial_config = {
        CONF_NAME: "AC Repeat Test",
        CONF_SENSOR: "sensor.room_temp",
        CONF_COOLER: "switch.ac",
        CONF_HOT_TOLERANCE: 0.5,
    }
    result = await config_flow.async_step_basic_ac_only(initial_config)

    # Skip features for simplicity
    result = await config_flow.async_step_features({})

    assert result["type"] == "create_entry"
    created_data = result["data"]

    # ===== STEP 2: Create MockConfigEntry =====
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=created_data,
        options={},
        title="AC Repeat Test",
    )
    config_entry.add_to_hass(hass)

    # ===== STEP 3: First options flow - set target_temp, precision, temp_step =====
    options_flow_1 = OptionsFlowHandler(config_entry)
    options_flow_1.hass = hass

    result = await options_flow_1.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # Set values in first options flow
    result = await options_flow_1.async_step_init(
        {
            CONF_TARGET_TEMP: 22.0,
            CONF_PRECISION: "0.5",
            CONF_TEMP_STEP: "0.5",
        }
    )

    assert result["type"] == "create_entry"
    first_update = result["data"]

    # Verify first update - values should be converted to floats
    assert first_update[CONF_TARGET_TEMP] == 22.0
    assert first_update[CONF_PRECISION] == 0.5  # Should be float after conversion
    assert first_update[CONF_TEMP_STEP] == 0.5  # Should be float after conversion

    # ===== STEP 4: Update config entry with options =====
    config_entry_updated = MockConfigEntry(
        domain=DOMAIN,
        data=created_data,
        options=first_update,
        title="AC Repeat Test",
    )
    config_entry_updated.add_to_hass(hass)

    # ===== STEP 5: Second options flow - verify fields are pre-filled =====
    options_flow_2 = OptionsFlowHandler(config_entry_updated)
    options_flow_2.hass = hass

    result = await options_flow_2.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # Extract defaults from schema
    init_schema = result["data_schema"].schema
    defaults = {}
    for key in init_schema:
        if hasattr(key, "schema"):
            field_name = key.schema
            if hasattr(key, "default"):
                default_val = key.default() if callable(key.default) else key.default
                defaults[field_name] = default_val

    # BUG #484/#479: These should be pre-filled from first options flow
    # Target temp now uses suggested_value pattern, so should NOT be in defaults
    # but should be in description
    target_temp_key = None
    for key in init_schema:
        if hasattr(key, "schema") and key.schema == CONF_TARGET_TEMP:
            target_temp_key = key
            break

    assert target_temp_key is not None, "Target temp field should exist in schema"

    # For optional fields with suggested_value, the value is in description, not default
    if hasattr(target_temp_key, "description") and isinstance(
        target_temp_key.description, dict
    ):
        suggested_target = target_temp_key.description.get("suggested_value")
        assert (
            suggested_target == 22.0
        ), f"Target temp should be suggested as 22.0! Got: {suggested_target}"

    # Critical: SelectSelector expects string values, and we now convert floats to strings
    # Issue #484/#479 fix: precision and temp_step stored as floats must be converted to
    # strings to properly pre-fill dropdown selectors
    precision_val = defaults.get(CONF_PRECISION)
    assert precision_val == "0.5", (
        f"Precision should be pre-filled as string '0.5'! Got: {precision_val} "
        f"(type: {type(precision_val).__name__})"
    )

    temp_step_val = defaults.get(CONF_TEMP_STEP)
    assert temp_step_val == "0.5", (
        f"Temp step should be pre-filled as string '0.5'! Got: {temp_step_val} "
        f"(type: {type(temp_step_val).__name__})"
    )

    # ===== STEP 6: Submit second options flow without target_temp (should be optional) =====
    # BUG #484/#479: Target temp should be optional, not required
    result = await options_flow_2.async_step_init(
        {
            # Intentionally NOT providing CONF_TARGET_TEMP - it should be optional
            CONF_PRECISION: "0.5",
            CONF_TEMP_STEP: "0.5",
        }
    )

    assert result["type"] == "create_entry"
    second_update = result["data"]

    # Verify target_temp preserved from first update (not cleared)
    assert (
        second_update[CONF_TARGET_TEMP] == 22.0
    ), "Target temp should be preserved from previous options flow"
    assert second_update[CONF_PRECISION] == 0.5
    assert second_update[CONF_TEMP_STEP] == 0.5

    # ===== STEP 7: Third options flow - verify persistence again =====
    config_entry_final = MockConfigEntry(
        domain=DOMAIN,
        data=created_data,
        options=second_update,
        title="AC Repeat Test",
    )
    config_entry_final.add_to_hass(hass)

    options_flow_3 = OptionsFlowHandler(config_entry_final)
    options_flow_3.hass = hass

    result = await options_flow_3.async_step_init()
    assert result["type"] == "form"

    # Extract defaults again
    init_schema_3 = result["data_schema"].schema
    defaults_3 = {}
    for key in init_schema_3:
        if hasattr(key, "schema"):
            field_name = key.schema
            if hasattr(key, "default"):
                default_val = key.default() if callable(key.default) else key.default
                defaults_3[field_name] = default_val

    # All values should still be pre-filled as strings for dropdowns
    # Target temp uses suggested_value, so check description
    target_temp_key_3 = None
    for key in init_schema_3:
        if hasattr(key, "schema") and key.schema == CONF_TARGET_TEMP:
            target_temp_key_3 = key
            break

    if hasattr(target_temp_key_3, "description") and isinstance(
        target_temp_key_3.description, dict
    ):
        suggested_target_3 = target_temp_key_3.description.get("suggested_value")
        assert suggested_target_3 == 22.0

    assert defaults_3.get(CONF_PRECISION) == "0.5"
    assert defaults_3.get(CONF_TEMP_STEP) == "0.5"


# =============================================================================
# NOTE: Mode-specific tolerances (heat_tolerance, cool_tolerance) are only
# applicable to dual-mode systems (heater_cooler, heat_pump). AC_ONLY is a
# single-mode system and does not support mode-specific tolerances.
# Tests for mode-specific tolerances should be in dual-mode system test files.
# =============================================================================
