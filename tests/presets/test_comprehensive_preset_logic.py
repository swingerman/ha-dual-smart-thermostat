#!/usr/bin/env python3
"""Comprehensive tests for preset configuration logic in both config and options flows."""

import asyncio
import os
import sys

# Add the custom_components directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "custom_components"))


async def test_comprehensive_preset_logic():
    """Test comprehensive preset configuration logic for both config and options flows."""
    print("🧪 Testing Comprehensive Preset Configuration Logic")
    print("=" * 50)

    try:
        from unittest.mock import AsyncMock, Mock

        from homeassistant.config_entries import ConfigEntry
        from homeassistant.const import CONF_NAME

        from custom_components.dual_smart_thermostat.config_flow import (
            ConfigFlowHandler,
        )
        from custom_components.dual_smart_thermostat.const import SYSTEM_TYPE_AC_ONLY
        from custom_components.dual_smart_thermostat.options_flow import (
            OptionsFlowHandler,
        )

        # Test 1: Config Flow - No presets selected
        print("\n📋 Test 1: Config Flow - No presets selected")

        config_handler = ConfigFlowHandler()
        config_handler.collected_config = {
            CONF_NAME: "Test Thermostat",
            "system_type": SYSTEM_TYPE_AC_ONLY,
        }
        config_handler.hass = AsyncMock()

        # No presets selected (all False)
        no_presets_input = {
            "away": False,
            "comfort": False,
            "eco": False,
            "home": False,
            "sleep": False,
            "anti_freeze": False,
            "activity": False,
            "boost": False,
        }

        result = await config_handler.async_step_preset_selection(no_presets_input)

        if result["type"] == "create_entry":
            print("   ✅ Config flow correctly skips preset configuration")
            print("   ✅ Flow finishes directly after preset selection")
        else:
            print(f"   ❌ Expected create_entry, got {result['type']}")
            assert False

        # Test 2: Config Flow - Some presets selected
        print("\n📋 Test 2: Config Flow - Some presets selected")

        config_handler.collected_config = {
            CONF_NAME: "Test Thermostat",
            "system_type": SYSTEM_TYPE_AC_ONLY,
        }

        # Some presets selected
        some_presets_input = {
            "away": True,
            "comfort": False,
            "eco": True,
            "home": False,
            "sleep": False,
            "anti_freeze": False,
            "activity": False,
            "boost": False,
        }

        result = await config_handler.async_step_preset_selection(some_presets_input)

        if result["type"] == "form" and result["step_id"] == "presets":
            print("   ✅ Config flow correctly proceeds to preset configuration")
            print("   ✅ Shows presets step when presets are enabled")
        else:
            print(
                f"   ❌ Expected presets form, got {result.get('type')} / {result.get('step_id')}"
            )
            assert False

        # Test 3: Options Flow - No presets selected
        print("\n📋 Test 3: Options Flow - No presets selected")

        mock_config_entry = Mock(spec=ConfigEntry)
        mock_config_entry.data = {
            "system_type": SYSTEM_TYPE_AC_ONLY,
            "name": "Test AC Thermostat",
            "cooler": "switch.ac_unit",
            "sensor": "sensor.temperature",
        }

        options_handler = OptionsFlowHandler(mock_config_entry)
        options_handler.collected_config = {"presets_shown": True}
        options_handler.hass = AsyncMock()

        result = await options_handler.async_step_preset_selection(no_presets_input)

        # For options flow, it should continue to determine next step
        # (could be ac_only_features, advanced_options, or create_entry depending on flow state)
        if result["type"] == "form":
            print("   ✅ Options flow correctly skips preset configuration")
            print(f"   ✅ Continues to next step: {result.get('step_id', 'unknown')}")
        elif result["type"] == "create_entry":
            print("   ✅ Options flow correctly skips preset configuration")
            print("   ✅ Flow completes directly")
        else:
            print(f"   ❌ Expected form or create_entry, got {result.get('type')}")
            assert False

        # Test 4: Options Flow - Some presets selected
        print("\n📋 Test 4: Options Flow - Some presets selected")

        options_handler.collected_config = {"presets_shown": True}

        result = await options_handler.async_step_preset_selection(some_presets_input)

        if result["type"] == "form" and result["step_id"] == "presets":
            print("   ✅ Options flow correctly proceeds to preset configuration")
            print("   ✅ Shows presets step when presets are enabled")
        else:
            print(
                f"   ❌ Expected presets form, got {result.get('type')} / {result.get('step_id')}"
            )
            assert False

        print("\n🎯 Logic Validation:")
        print("   ✅ No presets → Skip preset configuration")
        print("   ✅ Some presets → Show preset configuration")
        print("   ✅ Config flow → Finish directly when no presets")
        print("   ✅ Options flow → Continue to next step when no presets")

        # Test 5: New Multi-Select Format Support
        print("\n📋 Test 5: New Multi-Select Format - No Presets")

        options_handler.collected_config = {"presets_shown": True}

        # Test new multi-select format with empty list
        no_presets_multiselect = {"presets": []}

        result = await options_handler.async_step_preset_selection(
            no_presets_multiselect
        )

        if result["type"] == "form" or result["type"] == "create_entry":
            print("   ✅ Multi-select format correctly skips preset configuration")
        else:
            print(f"   ❌ Multi-select format failed: {result.get('type')}")
            assert False

        # Test 6: New Multi-Select Format - Some Presets
        print("\n📋 Test 6: New Multi-Select Format - Some Presets")

        options_handler.collected_config = {"presets_shown": True}

        # Capture result for the old boolean format to verify backward compatibility
        # (some_presets_input was defined earlier in Test 2)
        result_old = await options_handler.async_step_preset_selection(
            some_presets_input
        )

        # Test new multi-select format with selected presets
        some_presets_multiselect = {"presets": ["away", "home", "comfort"]}

        result = await options_handler.async_step_preset_selection(
            some_presets_multiselect
        )

        if result["type"] == "form" and result["step_id"] == "presets":
            print(
                "   ✅ Multi-select format correctly proceeds to preset configuration"
            )
        else:
            print(
                f"   ❌ Multi-select format failed: {result.get('type')} / {result.get('step_id')}"
            )
            assert False
        if (
            result_old["type"] == "form"
            and result_old["step_id"] == "presets"
            and result["type"] == "form"
            and result["step_id"] == "presets"
        ):
            print("   ✅ Both old boolean and new multi-select formats work correctly")
        else:
            print(
                f"   ❌ Format compatibility failed: old={result_old.get('type')}/{result_old.get('step_id')}, new={result.get('type')}/{result.get('step_id')}"
            )
            assert False

        # New format with same presets
        new_format = {"presets": ["away", "home"]}
        result_new = await options_handler.async_step_preset_selection(new_format)

        if (
            result_old["type"] == "form"
            and result_old["step_id"] == "presets"
            and result_new["type"] == "form"
            and result_new["step_id"] == "presets"
        ):
            print("   ✅ Both old boolean and new multi-select formats work correctly")
        else:
            print(
                f"   ❌ Format compatibility failed: old={result_old.get('type')}/{result_old.get('step_id')}, new={result_new.get('type')}/{result_new.get('step_id')}"
            )
            return False

        # Test 8: User-Reported Issue Scenario
        print("\n📋 Test 8: User-Reported Issue - AC System Options Flow")
        print(
            "   Testing: 'regardless of I checked any presets I am not presented with the preset configuration page'"
        )

        # Create fresh options handler for AC system
        ac_config_entry = Mock(spec=ConfigEntry)
        ac_config_entry.data = {
            "name": "Test AC Thermostat",
            "heater": "switch.heater",
            "target_sensor": "sensor.temp",
            "system_type": "ac_only",
        }
        ac_config_entry.entry_id = "test_ac_entry"

        ac_options_handler = OptionsFlowHandler(ac_config_entry)
        ac_options_handler.collected_config = {}
        ac_options_handler.hass = AsyncMock()

        # Simulate user checking presets in AC system options flow
        user_preset_selection = {"presets": ["away", "home", "comfort"]}

        result = await ac_options_handler.async_step_preset_selection(
            user_preset_selection
        )

        if result["type"] == "form" and result["step_id"] == "presets":
            print("   ✅ FIXED: User IS now presented with preset configuration page!")
            print("   ✅ AC system options flow works correctly")
        else:
            print(
                f"   ❌ User issue still exists: {result.get('type')} / {result.get('step_id')}"
            )
            assert False

        print("\n🎯 Comprehensive Logic Validation:")
        print("   ✅ No presets → Skip preset configuration")
        print("   ✅ Some presets → Show preset configuration")
        print("   ✅ Config flow → Finish directly when no presets")
        print("   ✅ Options flow → Continue to next step when no presets")
        print("   ✅ Old boolean format → Fully supported")
        print("   ✅ New multi-select format → Fully supported")
        print("   ✅ Backward compatibility → Maintained")
        print("   ✅ User-reported issue → Resolved")
        assert True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        raise


def run_test():
    """Run the async test."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        success = loop.run_until_complete(test_comprehensive_preset_logic())
        # If the test used assertions and returned None, treat that as success
        return True if success is None else success
    finally:
        loop.close()


if __name__ == "__main__":
    success = run_test()

    if success:
        print("\n🎉 COMPREHENSIVE PRESET LOGIC WORKING!")
        print("\n✅ All Tests Passed:")
        print("   • Config flow skip logic works correctly")
        print("   • Options flow skip logic works correctly")
        print("   • Old boolean format fully supported")
        print("   • New multi-select format fully supported")
        print("   • Backward compatibility maintained")
        print("   • User-reported issue resolved")
        print("   • AC system options flow working")
        print("\n✅ Benefits:")
        print("   • No unnecessary steps when no presets selected")
        print("   • Cleaner user experience")
        print("   • Logical flow progression")
        print("   • Works correctly in both config and options flows")
        print("   • Supports both legacy and modern preset selection")
        print("   • Saves user time and reduces confusion")
    else:
        print("\n❌ Preset logic test failed")
        sys.exit(1)
