"""Contract tests for feature availability per system type.

Task: T007A - Phase 1: Contract Tests (Foundation)
Issue: #440

These tests validate the feature availability matrix:
- Which features are available for each system type
- Which features are blocked for incompatible system types

Feature Availability Matrix (Source of Truth):
| Feature         | simple_heater | ac_only | heater_cooler | heat_pump |
|-----------------|---------------|---------|---------------|-----------|
| floor_heating   | ✅            | ❌      | ✅            | ✅        |
| fan             | ❌            | ✅      | ✅            | ✅        |
| humidity        | ❌            | ✅      | ✅            | ✅        |
| openings        | ✅            | ✅      | ✅            | ✅        |
| presets         | ✅            | ✅      | ✅            | ✅        |

Rationale:
- floor_heating: Heating-based systems only (no cooling-only systems)
- fan: Systems with active cooling or heat pumps
- humidity: Systems with active cooling (dehumidification capability)
- openings: All systems (universal safety feature)
- presets: All systems (universal comfort feature)
"""

from unittest.mock import Mock

import pytest

from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
from custom_components.dual_smart_thermostat.const import (
    CONF_SYSTEM_TYPE,
    DOMAIN,
    SYSTEM_TYPE_AC_ONLY,
    SYSTEM_TYPE_HEAT_PUMP,
    SYSTEM_TYPE_HEATER_COOLER,
    SYSTEM_TYPE_SIMPLE_HEATER,
)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.config_entries = Mock()
    hass.config_entries.async_entries = Mock(return_value=[])
    hass.data = {DOMAIN: {}}
    return hass


class TestFeatureAvailabilityContracts:
    """Validate which features are available for each system type."""

    @pytest.mark.parametrize(
        "system_type,expected_features",
        [
            (
                SYSTEM_TYPE_SIMPLE_HEATER,
                ["configure_floor_heating", "configure_openings", "configure_presets"],
            ),
            (
                SYSTEM_TYPE_AC_ONLY,
                [
                    "configure_fan",
                    "configure_humidity",
                    "configure_openings",
                    "configure_presets",
                ],
            ),
            (
                SYSTEM_TYPE_HEATER_COOLER,
                [
                    "configure_floor_heating",
                    "configure_fan",
                    "configure_humidity",
                    "configure_openings",
                    "configure_presets",
                ],
            ),
            (
                SYSTEM_TYPE_HEAT_PUMP,
                [
                    "configure_floor_heating",
                    "configure_fan",
                    "configure_humidity",
                    "configure_openings",
                    "configure_presets",
                ],
            ),
        ],
    )
    async def test_available_features_per_system_type(
        self, mock_hass, system_type, expected_features
    ):
        """Test that only expected features are available for each system type.

        RED PHASE: This test should FAIL initially if feature availability
        is not correctly filtered per system type.

        Acceptance Criteria:
        - Features step schema shows only expected feature toggles
        - Unavailable features are not present in the schema
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: system_type}

        # Get the features step schema
        result = await flow.async_step_features()
        schema = result["data_schema"].schema

        # Extract actual feature toggles from schema
        actual_features = [
            key.schema
            for key in schema.keys()
            if hasattr(key, "schema") and key.schema.startswith("configure_")
        ]

        # Verify expected features are present
        for feature in expected_features:
            assert (
                feature in actual_features
            ), f"Expected feature '{feature}' not found for {system_type}"

        # Verify only expected features are present (no extras)
        assert sorted(actual_features) == sorted(
            expected_features
        ), f"Feature mismatch for {system_type}: got {actual_features}, expected {expected_features}"

    @pytest.mark.parametrize(
        "system_type,blocked_features",
        [
            (SYSTEM_TYPE_SIMPLE_HEATER, ["configure_fan", "configure_humidity"]),
            (SYSTEM_TYPE_AC_ONLY, ["configure_floor_heating"]),
            # heater_cooler and heat_pump support all features, so no blocked features
        ],
    )
    async def test_blocked_features_per_system_type(
        self, mock_hass, system_type, blocked_features
    ):
        """Test that blocked features cannot be enabled for incompatible system types.

        RED PHASE: This test should FAIL initially if blocked features are
        accessible for incompatible system types.

        Acceptance Criteria:
        - Blocked features are not present in features step schema
        - Schema does not allow configuration of blocked features
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: system_type}

        # Get the features step schema
        result = await flow.async_step_features()
        schema = result["data_schema"].schema

        # Extract actual feature toggles from schema
        actual_features = [
            key.schema
            for key in schema.keys()
            if hasattr(key, "schema") and key.schema.startswith("configure_")
        ]

        # Verify blocked features are NOT present
        for blocked_feature in blocked_features:
            assert (
                blocked_feature not in actual_features
            ), f"Blocked feature '{blocked_feature}' should not be available for {system_type}"

    @pytest.mark.parametrize(
        "system_type",
        [
            SYSTEM_TYPE_SIMPLE_HEATER,
            SYSTEM_TYPE_AC_ONLY,
            SYSTEM_TYPE_HEATER_COOLER,
            SYSTEM_TYPE_HEAT_PUMP,
        ],
    )
    async def test_openings_available_for_all_system_types(
        self, mock_hass, system_type
    ):
        """Test that openings feature is available for all system types.

        Openings is a universal safety feature that should be available
        for all system types.

        Acceptance Criteria:
        - configure_openings toggle is present in features step for all systems
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: system_type}

        result = await flow.async_step_features()
        schema = result["data_schema"].schema

        actual_features = [
            key.schema
            for key in schema.keys()
            if hasattr(key, "schema") and key.schema.startswith("configure_")
        ]

        assert (
            "configure_openings" in actual_features
        ), f"Openings feature should be available for {system_type}"

    @pytest.mark.parametrize(
        "system_type",
        [
            SYSTEM_TYPE_SIMPLE_HEATER,
            SYSTEM_TYPE_AC_ONLY,
            SYSTEM_TYPE_HEATER_COOLER,
            SYSTEM_TYPE_HEAT_PUMP,
        ],
    )
    async def test_presets_available_for_all_system_types(self, mock_hass, system_type):
        """Test that presets feature is available for all system types.

        Presets is a universal comfort feature that should be available
        for all system types.

        Acceptance Criteria:
        - configure_presets toggle is present in features step for all systems
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: system_type}

        result = await flow.async_step_features()
        schema = result["data_schema"].schema

        actual_features = [
            key.schema
            for key in schema.keys()
            if hasattr(key, "schema") and key.schema.startswith("configure_")
        ]

        assert (
            "configure_presets" in actual_features
        ), f"Presets feature should be available for {system_type}"

    @pytest.mark.parametrize(
        "system_type,expected_present",
        [
            (SYSTEM_TYPE_SIMPLE_HEATER, True),
            (SYSTEM_TYPE_AC_ONLY, False),
            (SYSTEM_TYPE_HEATER_COOLER, True),
            (SYSTEM_TYPE_HEAT_PUMP, True),
        ],
    )
    async def test_floor_heating_availability_by_system_type(
        self, mock_hass, system_type, expected_present
    ):
        """Test that floor_heating is only available for heating-capable systems.

        Floor heating requires heating capability, so it should be blocked
        for cooling-only systems (ac_only).

        Acceptance Criteria:
        - floor_heating available for heater-based systems
        - floor_heating blocked for ac_only
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: system_type}

        result = await flow.async_step_features()
        schema = result["data_schema"].schema

        actual_features = [
            key.schema
            for key in schema.keys()
            if hasattr(key, "schema") and key.schema.startswith("configure_")
        ]

        if expected_present:
            assert (
                "configure_floor_heating" in actual_features
            ), f"Floor heating should be available for {system_type}"
        else:
            assert (
                "configure_floor_heating" not in actual_features
            ), f"Floor heating should NOT be available for {system_type}"

    @pytest.mark.parametrize(
        "system_type,expected_present",
        [
            (SYSTEM_TYPE_SIMPLE_HEATER, False),
            (SYSTEM_TYPE_AC_ONLY, True),
            (SYSTEM_TYPE_HEATER_COOLER, True),
            (SYSTEM_TYPE_HEAT_PUMP, True),
        ],
    )
    async def test_fan_availability_by_system_type(
        self, mock_hass, system_type, expected_present
    ):
        """Test that fan feature is only available for cooling-capable systems.

        Fan feature requires cooling capability or heat pump operation.

        Acceptance Criteria:
        - fan available for systems with active cooling or heat pumps
        - fan blocked for heating-only systems (simple_heater)
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: system_type}

        result = await flow.async_step_features()
        schema = result["data_schema"].schema

        actual_features = [
            key.schema
            for key in schema.keys()
            if hasattr(key, "schema") and key.schema.startswith("configure_")
        ]

        if expected_present:
            assert (
                "configure_fan" in actual_features
            ), f"Fan feature should be available for {system_type}"
        else:
            assert (
                "configure_fan" not in actual_features
            ), f"Fan feature should NOT be available for {system_type}"

    @pytest.mark.parametrize(
        "system_type,expected_present",
        [
            (SYSTEM_TYPE_SIMPLE_HEATER, False),
            (SYSTEM_TYPE_AC_ONLY, True),
            (SYSTEM_TYPE_HEATER_COOLER, True),
            (SYSTEM_TYPE_HEAT_PUMP, True),
        ],
    )
    async def test_humidity_availability_by_system_type(
        self, mock_hass, system_type, expected_present
    ):
        """Test that humidity feature is only available for cooling-capable systems.

        Humidity control (dehumidification) requires cooling capability.

        Acceptance Criteria:
        - humidity available for systems with active cooling
        - humidity blocked for heating-only systems (simple_heater)
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: system_type}

        result = await flow.async_step_features()
        schema = result["data_schema"].schema

        actual_features = [
            key.schema
            for key in schema.keys()
            if hasattr(key, "schema") and key.schema.startswith("configure_")
        ]

        if expected_present:
            assert (
                "configure_humidity" in actual_features
            ), f"Humidity feature should be available for {system_type}"
        else:
            assert (
                "configure_humidity" not in actual_features
            ), f"Humidity feature should NOT be available for {system_type}"
