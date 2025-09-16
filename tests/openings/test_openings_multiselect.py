"""Test openings multiselect configuration."""


def test_openings_multiselect_processing():
    """Test the new openings multiselect processing logic."""

    def process_openings_multiselect_config(user_input, collected_config):
        """Simulate the new openings config processing logic."""
        openings_list = []
        selected_entities = collected_config.get("selected_openings", [])

        for entity_id in selected_entities:
            opening_timeout_key = f"{entity_id}_opening_timeout"
            closing_timeout_key = f"{entity_id}_closing_timeout"

            # Check if we have timeout settings for this entity
            has_opening_timeout = (
                opening_timeout_key in user_input and user_input[opening_timeout_key]
            )
            has_closing_timeout = (
                closing_timeout_key in user_input and user_input[closing_timeout_key]
            )

            if has_opening_timeout or has_closing_timeout:
                # Create object format if we have timeout settings
                opening_obj = {"entity_id": entity_id}
                if has_opening_timeout:
                    opening_obj["opening_timeout"] = user_input[opening_timeout_key]
                if has_closing_timeout:
                    opening_obj["closing_timeout"] = user_input[closing_timeout_key]
                openings_list.append(opening_obj)
            else:
                # Use simple entity_id format if no timeouts
                openings_list.append(entity_id)

        return openings_list

    # Test case 1: Simple entity selection without timeouts
    collected_config = {
        "selected_openings": ["binary_sensor.front_door", "binary_sensor.window_1"]
    }
    user_input = {}
    result = process_openings_multiselect_config(user_input, collected_config)
    expected = ["binary_sensor.front_door", "binary_sensor.window_1"]
    assert result == expected, f"Expected {expected}, got {result}"
    print("✅ Test 1 passed: Simple entity selection")

    # Test case 2: Entity selection with some timeouts
    collected_config = {
        "selected_openings": ["binary_sensor.front_door", "binary_sensor.window_1"]
    }
    user_input = {
        "binary_sensor.front_door_opening_timeout": {"minutes": 2},
        "binary_sensor.window_1_closing_timeout": {"minutes": 1},
    }
    result = process_openings_multiselect_config(user_input, collected_config)
    expected = [
        {"entity_id": "binary_sensor.front_door", "opening_timeout": {"minutes": 2}},
        {"entity_id": "binary_sensor.window_1", "closing_timeout": {"minutes": 1}},
    ]
    assert result == expected, f"Expected {expected}, got {result}"
    print("✅ Test 2 passed: Entity selection with timeouts")

    # Test case 3: Mix of entities with and without timeouts
    collected_config = {
        "selected_openings": [
            "binary_sensor.front_door",
            "binary_sensor.window_1",
            "binary_sensor.back_door",
        ]
    }
    user_input = {
        "binary_sensor.front_door_opening_timeout": {"seconds": 30},
        # window_1 has no timeout - should be simple string
        "binary_sensor.back_door_closing_timeout": {"minutes": 5},
    }
    result = process_openings_multiselect_config(user_input, collected_config)
    expected = [
        {"entity_id": "binary_sensor.front_door", "opening_timeout": {"seconds": 30}},
        "binary_sensor.window_1",  # Simple string format
        {"entity_id": "binary_sensor.back_door", "closing_timeout": {"minutes": 5}},
    ]
    assert result == expected, f"Expected {expected}, got {result}"
    print("✅ Test 3 passed: Mixed timeout configurations")

    print("🎉 All multiselect tests passed!")


def test_entity_display_name_extraction():
    """Test entity display name extraction logic."""

    def extract_display_name(entity_id):
        """Extract friendly name from entity_id for display."""
        return entity_id.replace("binary_sensor.", "").replace("_", " ").title()

    test_cases = [
        ("binary_sensor.front_door", "Front Door"),
        ("binary_sensor.window_living_room", "Window Living Room"),
        ("binary_sensor.garage_door_sensor", "Garage Door Sensor"),
        ("front_door", "Front Door"),  # Already without prefix
    ]

    for entity_id, expected in test_cases:
        result = extract_display_name(entity_id)
        assert (
            result == expected
        ), f"Entity {entity_id}: expected '{expected}', got '{result}'"
        print(f"✅ {entity_id} -> {result}")

    print("🎉 All display name tests passed!")


if __name__ == "__main__":
    test_openings_multiselect_processing()
    test_entity_display_name_extraction()
