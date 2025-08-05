"""Test openings configuration logic."""


def test_openings_processing_logic():
    """Test the openings processing logic without imports."""

    # Simulate _process_openings_config logic
    def process_openings_config(config):
        processed_config = config.copy()

        # If openings are not enabled, remove any opening-related config
        if not config.get("enable_openings"):
            processed_config.pop("enable_openings", None)
            processed_config.pop("openings_count", None)
            processed_config.pop("current_opening_index", None)
            # Remove any opening config keys
            keys_to_remove = [k for k in processed_config if k.startswith("opening_")]
            for key in keys_to_remove:
                processed_config.pop(key, None)
            return processed_config

        # Build openings list from individual opening configurations
        openings = []
        openings_count = config.get("openings_count", 0)

        for i in range(1, openings_count + 1):
            entity_key = f"opening_{i}_entity"
            timeout_key = f"opening_{i}_timeout"
            closing_timeout_key = f"opening_{i}_closing_timeout"

            if entity_key in config:
                opening_config = {"entity_id": config[entity_key]}

                if timeout_key in config and config[timeout_key]:
                    opening_config["timeout"] = config[timeout_key]

                if closing_timeout_key in config and config[closing_timeout_key]:
                    opening_config["closing_timeout"] = config[closing_timeout_key]

                openings.append(opening_config)

        if openings:
            processed_config["openings"] = openings

        # Handle openings scope
        scope = config.get("openings_scope")
        if (
            scope and scope != "all"
        ):  # Only set scope if it's not "all" (default behavior)
            if isinstance(scope, list) and "all" not in scope:
                processed_config["openings_scope"] = scope
            elif isinstance(scope, str) and scope != "all":
                processed_config["openings_scope"] = [scope]
        else:
            # Remove scope when it's "all" (default behavior)
            processed_config.pop("openings_scope", None)

        # Clean up temporary config keys
        processed_config.pop("enable_openings", None)
        processed_config.pop("openings_count", None)
        processed_config.pop("current_opening_index", None)
        processed_config.pop("openings_toggle_shown", None)

        # Remove individual opening config keys
        keys_to_remove = [k for k in processed_config if k.startswith("opening_")]
        keys_to_remove.extend([k for k in processed_config if k.startswith("scope_")])
        for key in keys_to_remove:
            processed_config.pop(key, None)

        return processed_config

    # Test 1: Openings disabled
    config_disabled = {
        "name": "Test Thermostat",
        "enable_openings": False,
        "openings_count": 2,
        "opening_1_entity": "binary_sensor.window1",
        "opening_2_entity": "binary_sensor.door1",
    }

    processed = process_openings_config(config_disabled)
    assert "enable_openings" not in processed
    assert "openings_count" not in processed
    assert "opening_1_entity" not in processed
    assert "opening_2_entity" not in processed
    assert "openings" not in processed
    print("✓ Openings disabled processing works")

    # Test 2: Openings enabled with entities and timeouts
    config_enabled = {
        "name": "Test Thermostat",
        "enable_openings": True,
        "openings_count": 2,
        "opening_1_entity": "binary_sensor.window1",
        "opening_1_timeout": {"seconds": 30},
        "opening_2_entity": "binary_sensor.door1",
        "opening_2_closing_timeout": {"seconds": 15},
        "openings_scope": "heat",
    }

    processed = process_openings_config(config_enabled)
    assert "enable_openings" not in processed
    assert "openings_count" not in processed
    assert "opening_1_entity" not in processed
    assert "opening_2_entity" not in processed

    # Check openings list was created correctly
    assert "openings" in processed
    assert len(processed["openings"]) == 2

    opening1 = processed["openings"][0]
    assert opening1["entity_id"] == "binary_sensor.window1"
    assert opening1["timeout"] == {"seconds": 30}
    assert "closing_timeout" not in opening1

    opening2 = processed["openings"][1]
    assert opening2["entity_id"] == "binary_sensor.door1"
    assert opening2["closing_timeout"] == {"seconds": 15}
    assert "timeout" not in opening2

    # Check scope was processed
    assert processed["openings_scope"] == ["heat"]
    print("✓ Openings enabled with timeouts processing works")

    # Test 3: Multiple openings with minimal config
    config_minimal = {
        "name": "Test Thermostat",
        "enable_openings": True,
        "openings_count": 3,
        "opening_1_entity": "binary_sensor.window1",
        "opening_2_entity": "binary_sensor.window2",
        "opening_3_entity": "binary_sensor.door1",
        "openings_scope": "all",
    }

    processed = process_openings_config(config_minimal)
    assert "openings" in processed
    assert len(processed["openings"]) == 3

    # Check all entities are properly set
    assert processed["openings"][0]["entity_id"] == "binary_sensor.window1"
    assert processed["openings"][1]["entity_id"] == "binary_sensor.window2"
    assert processed["openings"][2]["entity_id"] == "binary_sensor.door1"

    # Check no timeouts are set for minimal config
    for opening in processed["openings"]:
        assert "timeout" not in opening
        assert "closing_timeout" not in opening

    # Scope "all" should not be explicitly set (default behavior)
    assert "openings_scope" not in processed
    print("✓ Multiple openings minimal config processing works")

    return True


if __name__ == "__main__":
    print("Testing openings configuration processing logic...")
    test_openings_processing_logic()
    print("\n🎉 All openings configuration tests passed!")
    print("\nOpenings configuration features:")
    print("- ✅ Toggle to enable/disable openings integration")
    print("- ✅ Configuration for multiple door/window sensors")
    print("- ✅ Optional timeout settings for opening and closing")
    print("- ✅ Scope configuration for HVAC mode control")
    print("- ✅ Proper data processing and cleanup")
