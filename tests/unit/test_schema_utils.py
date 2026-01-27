"""Unit tests for schema_utils module.

Tests the schema utility functions that create selectors for config/options flows.
"""

from unittest.mock import MagicMock

from homeassistant.const import UnitOfTemperature

from custom_components.dual_smart_thermostat.schema_utils import (
    get_temperature_selector,
    get_tolerance_selector,
)


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
        # step should be 0.05 * 1.8 = 0.09
        assert config["step"] == 0.09
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
        # Default step should be scaled for Fahrenheit (0.05 * 1.8 = 0.09)
        assert config["step"] == 0.09

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
