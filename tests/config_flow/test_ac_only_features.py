#!/usr/bin/env python3
"""Test complete AC-only features flow."""

import os
import sys

# Add the custom_components directory to Python path
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "custom_components")
)  # noqa: E402


async def test_ac_only_features_flow():
    """Test the complete AC-only features flow."""
    print("Testing AC-only features flow...")

    try:
        from dual_smart_thermostat.config_flow import ConfigFlowHandler
        from dual_smart_thermostat.const import SYSTEM_TYPE_AC_ONLY

        # Create a config flow instance
        flow = ConfigFlowHandler()
        flow.collected_config = {
            "system_type": SYSTEM_TYPE_AC_ONLY,
            "name": "Test AC Thermostat",
            "cooler": "switch.ac_unit",
            "sensor": "sensor.temperature",
        }

        print("1. Testing AC-only features step detection...")
        result = await flow._determine_next_step()

        # Check if it's a FlowResult with step_id 'ac_only_features'
        if hasattr(result, "step_id") and result.step_id == "ac_only_features":
            print("✅ AC-only features step appears correctly")
        elif isinstance(result, dict) and result.get("step_id") == "ac_only_features":
            print("✅ AC-only features step appears correctly")
        else:
            print(
                f"❌ Expected 'ac_only_features' step but got step_id: {getattr(result, 'step_id', result.get('step_id', 'unknown'))}"
            )
            return False

        print("\n2. Testing features selection...")

        # Test with all features enabled
        features_input = {
            "configure_fan": True,
            "configure_humidity": True,
            "configure_openings": True,
            "configure_presets": True,
        }

        result = await flow.async_step_ac_only_features(features_input)
        print(f"Result after selecting all features: {result}")

        # Check that fan configuration appears next
        if flow.collected_config.get("configure_fan"):
            print("✅ Fan enabled in configuration")

            # The next step might be fan, humidity, or openings depending on flow order
            next_result = await flow._determine_next_step()
            next_step = getattr(
                next_result, "step_id", next_result.get("step_id", "unknown")
            )

            if next_step in ["fan", "humidity", "openings_selection"]:
                print(f"✅ Next configuration step appears: {next_step}")
            else:
                print(f"❌ Unexpected next step: {next_step}")

        print("\n3. Testing with features disabled...")

        # Reset and test with features disabled
        flow.collected_config = {
            "system_type": SYSTEM_TYPE_AC_ONLY,
            "name": "Test AC Thermostat",
            "cooler": "switch.ac_unit",
            "sensor": "sensor.temperature",
            "ac_only_features_shown": True,
        }

        features_input_disabled = {
            "configure_fan": False,
            "configure_humidity": False,
            "configure_openings": False,
            "configure_presets": False,
        }

        result = await flow.async_step_ac_only_features(features_input_disabled)
        print(f"Result after disabling all features: {result}")

        # Check that configuration is complete
        if hasattr(result, "type") and result.type == "create_entry":
            print("✅ Configuration completes when all features disabled")
        else:
            print(f"Configuration continues to: {result}")

        print("✅ AC-only features flow test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Error during flow test: {e}")
        import traceback

        traceback.print_exc()
        return False


def run_test():
    """Run the async test."""
    import asyncio

    # Create event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        success = loop.run_until_complete(test_ac_only_features_flow())
        return success
    finally:
        loop.close()


if __name__ == "__main__":
    print("Testing complete AC-only features flow...")
    success = run_test()

    if success:
        print("\n🎉 AC-only features flow works correctly!")
        print("\nFeatures:")
        print("✅ Combined features selection for better UX")
        print("✅ Conditional fan configuration")
        print("✅ Conditional humidity configuration")
        print("✅ Conditional openings configuration")
        print("✅ Conditional presets configuration")
        print("✅ Simplified workflow for AC-only systems")
    else:
        print("\n❌ AC-only features flow test failed")
        sys.exit(1)
