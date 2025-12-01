"""Test preset template configuration flow integration.

Tests that config flow accepts both static numeric values and template
strings for preset temperatures, with proper validation.
"""

from homeassistant.core import HomeAssistant
import pytest
import voluptuous as vol


class TestPresetTemplatesConfigFlow:
    """Test US5: Config flow accepts templates with validation."""

    @pytest.mark.asyncio
    async def test_config_flow_accepts_template_input(self, hass: HomeAssistant):
        """Test T062: Verify template string accepted in config flow."""
        from custom_components.dual_smart_thermostat.schemas import (
            validate_template_or_number,
        )

        # Act: Validate template string
        template_value = "{{ states('input_number.away_temp') }}"
        result = validate_template_or_number(template_value)

        # Assert: Template string accepted
        assert result == template_value
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_config_flow_static_value_backward_compatible(
        self, hass: HomeAssistant
    ):
        """Test T063: Verify numeric value still accepted (backward compatibility)."""
        from custom_components.dual_smart_thermostat.schemas import (
            validate_template_or_number,
        )

        # Act: Validate numeric values
        int_result = validate_template_or_number(20)
        float_result = validate_template_or_number(20.5)
        string_number_result = validate_template_or_number("21")

        # Assert: All numeric forms accepted
        assert int_result == 20
        assert float_result == 20.5
        assert string_number_result == 21.0  # Converted to float

    @pytest.mark.asyncio
    async def test_config_flow_template_syntax_validation(self, hass: HomeAssistant):
        """Test T064: Verify invalid template rejected with vol.Invalid."""
        from custom_components.dual_smart_thermostat.schemas import (
            validate_template_or_number,
        )

        # Arrange: Invalid template (missing closing braces)
        invalid_template = "{{ states('sensor.temp'"

        # Act & Assert: Invalid template raises vol.Invalid
        with pytest.raises(vol.Invalid) as exc_info:
            validate_template_or_number(invalid_template)

        # Assert: Error message mentions template syntax
        assert "template" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_config_flow_valid_template_syntax_accepted(
        self, hass: HomeAssistant
    ):
        """Test T065: Verify valid template passes validation."""
        from custom_components.dual_smart_thermostat.schemas import (
            validate_template_or_number,
        )

        # Arrange: Various valid template forms
        valid_templates = [
            "{{ states('input_number.away_temp') }}",
            "{{ states('sensor.outdoor_temp') | float }}",
            "{{ 16 if is_state('sensor.season', 'winter') else 26 }}",
            "{{ states('input_number.base') | float + 2 }}",
        ]

        # Act & Assert: All valid templates accepted
        for template in valid_templates:
            result = validate_template_or_number(template)
            assert result == template
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_config_flow_none_value_accepted(self, hass: HomeAssistant):
        """Test that None is accepted (for optional fields)."""
        from custom_components.dual_smart_thermostat.schemas import (
            validate_template_or_number,
        )

        # Act: Validate None
        result = validate_template_or_number(None)

        # Assert: None accepted
        assert result is None

    @pytest.mark.asyncio
    async def test_config_flow_invalid_type_rejected(self, hass: HomeAssistant):
        """Test that invalid types are rejected."""
        from custom_components.dual_smart_thermostat.schemas import (
            validate_template_or_number,
        )

        # Arrange: Invalid types
        invalid_values = [
            [],
            {},
            True,
        ]

        # Act & Assert: All invalid types rejected
        for value in invalid_values:
            with pytest.raises(vol.Invalid):
                validate_template_or_number(value)
