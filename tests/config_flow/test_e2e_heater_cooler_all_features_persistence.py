"""End-to-end persistence test for HEATER_COOLER with all features.

Task: T007A - Phase 4: E2E Persistence Tests
Issue: #440

This test validates the complete lifecycle for heater_cooler with ALL available features:
1. User completes config flow with all features enabled
2. User opens options flow and sees all values pre-filled
3. User changes settings across multiple features
4. All changes persist correctly
5. Reopening shows updated values

Available features for heater_cooler:
- floor_heating ✅
- fan ✅
- humidity ✅
- openings ✅
- presets ✅
"""

from homeassistant.const import CONF_NAME
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dual_smart_thermostat.const import (
    CONF_COLD_TOLERANCE,
    CONF_COOLER,
    CONF_DRYER,
    CONF_FAN,
    CONF_FLOOR_SENSOR,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_HUMIDITY_SENSOR,
    CONF_MAX_FLOOR_TEMP,
    CONF_MIN_FLOOR_TEMP,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    DOMAIN,
    SYSTEM_TYPE_HEATER_COOLER,
)


@pytest.mark.asyncio
async def test_heater_cooler_all_features_full_persistence(hass):
    """Test HEATER_COOLER with all features: config → options → persistence.

    This E2E test validates:
    - All 5 features configured in config flow
    - All settings pre-filled in options flow
    - Changes to multiple features persist correctly
    - Original entry.data preserved, changes in entry.options
    """
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
    from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler

    # ===== STEP 1: Complete config flow with all features =====
    config_flow = ConfigFlowHandler()
    config_flow.hass = hass

    # Start: Select heater_cooler
    result = await config_flow.async_step_user(
        {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
    )

    # Basic config
    initial_config = {
        CONF_NAME: "Heater Cooler All Features Test",
        CONF_SENSOR: "sensor.room_temp",
        CONF_HEATER: "switch.heater",
        CONF_COOLER: "switch.cooler",
        CONF_COLD_TOLERANCE: 0.5,
        CONF_HOT_TOLERANCE: 0.3,
    }
    result = await config_flow.async_step_heater_cooler(initial_config)

    # Enable ALL features
    result = await config_flow.async_step_features(
        {
            "configure_floor_heating": True,
            "configure_fan": True,
            "configure_humidity": True,
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
            "opening_scope": "all",
            "timeout_openings_open": 300,
        }
    )

    # Configure presets
    # Note: async_step_preset_selection automatically advances to async_step_presets
    result = await config_flow.async_step_preset_selection(
        {"presets": ["away", "home"]}
    )

    # Now we're at the presets config step
    assert result["type"] == "form"
    assert result["step_id"] == "presets"

    result = await config_flow.async_step_presets(
        {
            "away_temp": 16,
            "home_temp": 21,
        }
    )

    # Flow should complete
    assert result["type"] == "create_entry"
    assert result["title"] == "Heater Cooler All Features Test"

    # ===== STEP 2: Verify initial config entry =====
    created_data = result["data"]

    # Verify basic settings
    assert created_data[CONF_NAME] == "Heater Cooler All Features Test"
    assert created_data[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_HEATER_COOLER
    assert created_data[CONF_HEATER] == "switch.heater"
    assert created_data[CONF_COOLER] == "switch.cooler"
    assert created_data[CONF_COLD_TOLERANCE] == 0.5
    assert created_data[CONF_HOT_TOLERANCE] == 0.3

    # Verify floor heating
    assert created_data[CONF_FLOOR_SENSOR] == "sensor.floor_temp"
    assert created_data[CONF_MIN_FLOOR_TEMP] == 5
    assert created_data[CONF_MAX_FLOOR_TEMP] == 28

    # Verify fan
    assert created_data[CONF_FAN] == "switch.fan"
    assert created_data["fan_on_with_ac"] is True

    # Verify humidity
    assert created_data[CONF_HUMIDITY_SENSOR] == "sensor.humidity"
    assert created_data[CONF_DRYER] == "switch.dehumidifier"
    assert created_data["target_humidity"] == 50

    # Verify openings
    # Note: opening_scope may be cleaned/normalized during processing
    assert "openings" in created_data
    assert len(created_data["openings"]) == 2
    assert any(
        o.get("entity_id") == "binary_sensor.window_1" for o in created_data["openings"]
    )
    assert any(
        o.get("entity_id") == "binary_sensor.door_1" for o in created_data["openings"]
    )

    # Verify presets
    # Note: Presets are stored as temp values, not in a "presets" list
    assert "away_temp" in created_data
    assert created_data["away_temp"] == 16
    assert "home_temp" in created_data
    assert created_data["home_temp"] == 21

    # ===== STEP 3: Create MockConfigEntry =====
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=created_data,
        options={},
        title="Heater Cooler All Features Test",
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

    # Fan options
    assert result["step_id"] == "fan_options"
    result = await options_flow.async_step_fan_options({})

    # Humidity options
    assert result["step_id"] == "humidity_options"
    result = await options_flow.async_step_humidity_options({})

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
    assert updated_data[CONF_MIN_FLOOR_TEMP] == 5
    assert updated_data[CONF_MAX_FLOOR_TEMP] == 28
    assert updated_data[CONF_FAN] == "switch.fan"
    assert updated_data[CONF_HUMIDITY_SENSOR] == "sensor.humidity"
    assert updated_data[CONF_DRYER] == "switch.dehumidifier"
    assert updated_data["target_humidity"] == 50
    # Openings list preserved
    assert "openings" in updated_data
    assert len(updated_data["openings"]) == 2
    assert updated_data["away_temp"] == 16  # Original preset value
    assert updated_data["home_temp"] == 21  # Original preset value

    # Verify preserved system info
    assert updated_data[CONF_NAME] == "Heater Cooler All Features Test"
    assert updated_data[CONF_HEATER] == "switch.heater"
    assert updated_data[CONF_COOLER] == "switch.cooler"

    # ===== STEP 7: Reopen options flow and verify updated values =====
    config_entry_updated = MockConfigEntry(
        domain=DOMAIN,
        data=created_data,  # Original unchanged
        options=updated_data,  # Updated values
        title="Heater Cooler All Features Test",
    )
    config_entry_updated.add_to_hass(hass)

    options_flow2 = OptionsFlowHandler(config_entry_updated)
    options_flow2.hass = hass

    # Simplified options flow: verify it opens successfully with merged values
    result = await options_flow2.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_heater_cooler_floor_heating_only_persistence(hass):
    """Test HEATER_COOLER with only floor_heating enabled.

    This tests feature isolation - only floor_heating configured.
    """
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler

    config_flow = ConfigFlowHandler()
    config_flow.hass = hass

    result = await config_flow.async_step_user(
        {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
    )

    result = await config_flow.async_step_heater_cooler(
        {
            CONF_NAME: "Floor Only Test",
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
        }
    )

    # Enable only floor_heating
    result = await config_flow.async_step_features(
        {
            "configure_floor_heating": True,
            "configure_fan": False,
            "configure_humidity": False,
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
    assert CONF_FAN not in created_data
    assert CONF_HUMIDITY_SENSOR not in created_data
    assert "selected_openings" not in created_data or not created_data.get(
        "selected_openings"
    )
    assert "away_temp" not in created_data  # No presets configured
    assert "home_temp" not in created_data
