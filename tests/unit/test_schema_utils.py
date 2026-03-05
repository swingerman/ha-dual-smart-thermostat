"""Unit tests for schema_utils module.

Tests the schema utility functions that create selectors for config/options flows.
"""

from unittest.mock import MagicMock

from homeassistant.const import UnitOfTemperature
import pytest

from custom_components.dual_smart_thermostat.const import (
    CONF_COLD_TOLERANCE,
    CONF_HOT_TOLERANCE,
)
from custom_components.dual_smart_thermostat.schema_utils import (
    get_temperature_selector,
    get_tolerance_selector,
)
from custom_components.dual_smart_thermostat.schemas import get_core_schema


class TestGetToleranceSelector:
    """Tests for the get_tolerance_selector function.

    This function handles temperature DIFFERENCES (deltas) correctly,
    unlike get_temperature_selector which handles absolute temperatures.

    Issue #523: Users in Fahrenheit mode were forced to enter tolerance
    values >= 32 because the old code converted 0°C → 32°F using absolute
    temperature conversion instead of scaling the delta values.
    """

    def test_tolerance_selector_celsius_no_conversion(self):
        """Test that Celsius users see correct min/max/step values.

        A tolerance of 0-10°C should display as 0-10°C (no conversion).
        """
        hass = MagicMock()
        hass.config.units.temperature_unit = UnitOfTemperature.CELSIUS

        selector = get_tolerance_selector(
            hass=hass, min_value=0, max_value=10, step=0.05
        )

        config = selector.config
        assert config["min"] == 0
        assert config["max"] == 10
        assert config["step"] == 0.05
        assert config["unit_of_measurement"] == "°C"

    def test_tolerance_selector_fahrenheit_scales_delta_values(self):
        """Test that Fahrenheit users see correctly SCALED values.

        Issue #523: Tolerances are temperature DELTAS, not absolute temps.
        A 0-10°C range should become 0-18°F (multiply by 1.8), NOT 32-50°F.

        This is the critical fix for the Fahrenheit tolerance bug.
        """
        hass = MagicMock()
        hass.config.units.temperature_unit = UnitOfTemperature.FAHRENHEIT

        selector = get_tolerance_selector(
            hass=hass, min_value=0, max_value=10, step=0.05
        )

        config = selector.config
        # min_value should be 0 * 1.8 = 0, NOT 32 (absolute conversion)
        assert config["min"] == 0
        # max_value should be 10 * 1.8 = 18, NOT 50 (absolute conversion)
        assert config["max"] == 18
        # step should be a Fahrenheit-friendly value (0.1), not 0.05 * 1.8 = 0.09
        assert config["step"] == 0.1
        assert config["unit_of_measurement"] == "°F"

    def test_tolerance_selector_fahrenheit_default_tolerance_range(self):
        """Test that default tolerance range (0.3°C) is valid in Fahrenheit.

        The default tolerance of 0.3°C should be displayable in Fahrenheit
        as approximately 0.54°F. This test ensures users can select small
        tolerance values in Fahrenheit mode.
        """
        hass = MagicMock()
        hass.config.units.temperature_unit = UnitOfTemperature.FAHRENHEIT

        # Using default parameters
        selector = get_tolerance_selector(hass=hass)

        config = selector.config
        # Default min is 0, should stay 0
        assert config["min"] == 0
        # Default step should be a Fahrenheit-friendly value (0.1)
        assert config["step"] == 0.1

    def test_tolerance_selector_fahrenheit_step_allows_round_values(self):
        """Test that Fahrenheit tolerance step allows entering round values.

        Issue #543: Users in Fahrenheit mode can't enter values like 1.0°F
        because the step (0.05°C * 1.8 = 0.09°F) doesn't divide evenly into
        common Fahrenheit tolerance values. The step should be a user-friendly
        value like 0.1 in Fahrenheit mode.
        """
        hass = MagicMock()
        hass.config.units.temperature_unit = UnitOfTemperature.FAHRENHEIT

        selector = get_tolerance_selector(
            hass=hass, min_value=0, max_value=10, step=0.05
        )

        config = selector.config
        step = config["step"]
        # User should be able to enter common Fahrenheit values
        # 1.0°F must be a valid multiple of the step
        assert 1.0 % step < 1e-9 or (step - (1.0 % step)) < 1e-9, (
            f"Step {step}°F doesn't allow entering 1.0°F. "
            f"1.0 % {step} = {1.0 % step}"
        )
        # 0.5°F must also be a valid multiple
        assert 0.5 % step < 1e-9 or (step - (0.5 % step)) < 1e-9, (
            f"Step {step}°F doesn't allow entering 0.5°F. "
            f"0.5 % {step} = {0.5 % step}"
        )

    def test_tolerance_selector_fahrenheit_options_flow_step(self):
        """Test options flow step (0.1°C) also works in Fahrenheit.

        The options flow uses step=0.1, which scales to 0.18°F - also
        not a round number. Users should be able to enter 1.0°F.
        """
        hass = MagicMock()
        hass.config.units.temperature_unit = UnitOfTemperature.FAHRENHEIT

        selector = get_tolerance_selector(
            hass=hass, min_value=0, max_value=10, step=0.1
        )

        config = selector.config
        step = config["step"]
        assert 1.0 % step < 1e-9 or (step - (1.0 % step)) < 1e-9, (
            f"Step {step}°F doesn't allow entering 1.0°F. "
            f"1.0 % {step} = {1.0 % step}"
        )

    def test_tolerance_selector_no_hass_uses_generic_degree(self):
        """Test that no hass instance uses generic degree symbol."""
        selector = get_tolerance_selector(hass=None, min_value=0, max_value=10)

        config = selector.config
        # Without hass, no conversion happens
        assert config["min"] == 0
        assert config["max"] == 10
        assert config["unit_of_measurement"] == "°"


class TestGetTemperatureSelector:
    """Tests for the get_temperature_selector function.

    This function handles ABSOLUTE temperatures and uses standard
    temperature conversion (°C to °F formula: F = C * 1.8 + 32).
    """

    def test_temperature_selector_celsius_no_conversion(self):
        """Test that Celsius users see correct min/max values."""
        hass = MagicMock()
        hass.config.units.temperature_unit = UnitOfTemperature.CELSIUS

        selector = get_temperature_selector(
            hass=hass, min_value=5, max_value=35, step=0.5
        )

        config = selector.config
        assert config["min"] == 5
        assert config["max"] == 35
        assert config["step"] == 0.5
        assert config["unit_of_measurement"] == "°C"

    def test_temperature_selector_fahrenheit_converts_absolute(self):
        """Test that Fahrenheit users see converted absolute temperatures.

        5°C → 41°F and 35°C → 95°F using the formula F = C * 1.8 + 32.
        """
        hass = MagicMock()
        hass.config.units.temperature_unit = UnitOfTemperature.FAHRENHEIT

        selector = get_temperature_selector(
            hass=hass, min_value=5, max_value=35, step=0.5
        )

        config = selector.config
        # 5°C should convert to 41°F (5 * 1.8 + 32 = 41)
        assert config["min"] == 41
        # 35°C should convert to 95°F (35 * 1.8 + 32 = 95)
        assert config["max"] == 95
        # Step scaled by 1.8
        assert config["step"] == 0.9
        assert config["unit_of_measurement"] == "°F"


class TestToleranceVsTemperatureComparison:
    """Comparison tests showing the difference between tolerance and temperature selectors.

    These tests demonstrate why we need separate functions:
    - Tolerance: temperature DELTA (multiply by 1.8 for F)
    - Temperature: absolute value (use conversion formula for F)
    """

    def test_zero_value_behaves_differently(self):
        """Test that 0 is handled differently between tolerance and temperature.

        For tolerance: 0°C delta = 0°F delta (no offset)
        For temperature: 0°C absolute = 32°F absolute (with offset)
        """
        hass = MagicMock()
        hass.config.units.temperature_unit = UnitOfTemperature.FAHRENHEIT

        tolerance_selector = get_tolerance_selector(
            hass=hass, min_value=0, max_value=10
        )
        temperature_selector = get_temperature_selector(
            hass=hass, min_value=0, max_value=10
        )

        # Tolerance: 0°C delta should stay 0°F
        assert tolerance_selector.config["min"] == 0

        # Temperature: 0°C absolute becomes 32°F
        assert temperature_selector.config["min"] == 32


class TestGetCoreSchemaToleranceSelectors:
    """Test that get_core_schema uses tolerance selectors (not percentage) for tolerance fields.

    Issue #526: Tolerance fields were incorrectly using get_percentage_selector()
    (0–100% range) instead of get_tolerance_selector() (temperature delta, 0–10°C).
    Percentage selectors show % unit and reject small values in Fahrenheit.
    """

    @pytest.mark.parametrize("system_type", ["heat_pump", "heater_cooler", "ac_only"])
    def test_cold_tolerance_uses_tolerance_selector_not_percentage(self, system_type):
        """Test that cold_tolerance field uses tolerance selector, not percentage.

        The tolerance selector uses °C/°F/° units and a max of 10.
        The percentage selector uses % unit and a max of 100.
        """
        hass = MagicMock()
        hass.config.units.temperature_unit = UnitOfTemperature.CELSIUS

        schema = get_core_schema(system_type, defaults={}, hass=hass)

        cold_tol_selector = None
        for key, value in schema.schema.items():
            if hasattr(key, "schema") and key.schema == CONF_COLD_TOLERANCE:
                cold_tol_selector = value
                break

        assert (
            cold_tol_selector is not None
        ), f"cold_tolerance field not found in get_core_schema for {system_type}"
        assert cold_tol_selector.config.get("unit_of_measurement") != "%", (
            f"cold_tolerance should not use percentage selector for {system_type}. "
            "Tolerances are temperature deltas, not percentages."
        )
        assert cold_tol_selector.config.get("max", 100) <= 20, (
            f"cold_tolerance max should be <= 20 for {system_type}, "
            f"got {cold_tol_selector.config.get('max')}. "
            "A max of 100 indicates a percentage selector is being used."
        )

    @pytest.mark.parametrize("system_type", ["heat_pump", "heater_cooler", "ac_only"])
    def test_hot_tolerance_uses_tolerance_selector_not_percentage(self, system_type):
        """Test that hot_tolerance field uses tolerance selector, not percentage."""
        hass = MagicMock()
        hass.config.units.temperature_unit = UnitOfTemperature.CELSIUS

        schema = get_core_schema(system_type, defaults={}, hass=hass)

        hot_tol_selector = None
        for key, value in schema.schema.items():
            if hasattr(key, "schema") and key.schema == CONF_HOT_TOLERANCE:
                hot_tol_selector = value
                break

        assert (
            hot_tol_selector is not None
        ), f"hot_tolerance field not found in get_core_schema for {system_type}"
        assert hot_tol_selector.config.get("unit_of_measurement") != "%", (
            f"hot_tolerance should not use percentage selector for {system_type}. "
            "Tolerances are temperature deltas, not percentages."
        )
        assert hot_tol_selector.config.get("max", 100) <= 20, (
            f"hot_tolerance max should be <= 20 for {system_type}, "
            f"got {hot_tol_selector.config.get('max')}. "
            "A max of 100 indicates a percentage selector is being used."
        )

    @pytest.mark.parametrize("system_type", ["heat_pump", "heater_cooler", "ac_only"])
    def test_cold_tolerance_fahrenheit_uses_scaled_delta(self, system_type):
        """Test that cold_tolerance is correctly scaled for Fahrenheit users.

        A 0–10°C delta range should become 0–18°F (multiply by 1.8),
        NOT 32–50°F (absolute temperature conversion).
        This ensures Fahrenheit users can enter small tolerance values.
        """
        hass = MagicMock()
        hass.config.units.temperature_unit = UnitOfTemperature.FAHRENHEIT

        schema = get_core_schema(system_type, defaults={}, hass=hass)

        cold_tol_selector = None
        for key, value in schema.schema.items():
            if hasattr(key, "schema") and key.schema == CONF_COLD_TOLERANCE:
                cold_tol_selector = value
                break

        assert cold_tol_selector is not None
        # min must be 0 (not 32 which would come from absolute °C→°F conversion)
        assert cold_tol_selector.config.get("min") == 0, (
            f"cold_tolerance min in Fahrenheit should be 0 (delta scaling), "
            f"got {cold_tol_selector.config.get('min')}. "
            "A min of 32 indicates incorrect absolute temperature conversion."
        )
