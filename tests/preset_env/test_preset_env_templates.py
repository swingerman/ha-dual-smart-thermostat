"""Test template support in PresetEnv."""

from homeassistant.components.climate.const import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
)
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
import pytest

from custom_components.dual_smart_thermostat.preset_env.preset_env import PresetEnv


class TestStaticValueBackwardCompatibility:
    """Test US1: Static preset temperatures work unchanged (backward compatibility)."""

    @pytest.mark.asyncio
    async def test_static_value_backward_compatible(self, hass: HomeAssistant):
        """Test T010: Verify numeric values stored as floats."""
        # Arrange: Create PresetEnv with static numeric temperature
        preset_env = PresetEnv(**{ATTR_TEMPERATURE: 20})

        # Act: Get temperature using new getter
        temp = preset_env.get_temperature(hass)

        # Assert: Value returned as float, exactly matching input
        assert temp == 20.0
        assert isinstance(temp, float)

    @pytest.mark.asyncio
    async def test_static_value_no_template_tracking(self, hass: HomeAssistant):
        """Test T011: Verify no template fields registered for static values."""
        # Arrange: Create PresetEnv with static temperature
        preset_env = PresetEnv(**{ATTR_TEMPERATURE: 18.5})

        # Act: Check template tracking structures
        # Assert: No templates detected
        assert (
            not hasattr(preset_env, "_template_fields")
            or len(preset_env._template_fields) == 0
        )
        assert (
            not hasattr(preset_env, "has_templates") or not preset_env.has_templates()
        )

    @pytest.mark.asyncio
    async def test_get_temperature_static_value(self, hass: HomeAssistant):
        """Test T012: Verify getter returns static value without hass parameter issues."""
        # Arrange: Create PresetEnv with static temperature
        preset_env = PresetEnv(**{ATTR_TEMPERATURE: 22.0})

        # Act: Call getter with hass (required signature)
        temp = preset_env.get_temperature(hass)

        # Assert: Returns correct value, no errors with hass parameter
        assert temp == 22.0

    @pytest.mark.asyncio
    async def test_static_range_mode_temperatures(self, hass: HomeAssistant):
        """Test range mode with static temp_low and temp_high."""
        # Arrange: Create PresetEnv with range mode static values
        preset_env = PresetEnv(
            **{ATTR_TARGET_TEMP_LOW: 18.0, ATTR_TARGET_TEMP_HIGH: 24.0}
        )

        # Act: Get temperatures
        temp_low = preset_env.get_target_temp_low(hass)
        temp_high = preset_env.get_target_temp_high(hass)

        # Assert: Both return correct static values
        assert temp_low == 18.0
        assert temp_high == 24.0

    @pytest.mark.asyncio
    async def test_integer_converted_to_float(self, hass: HomeAssistant):
        """Test integer input converted to float for consistency."""
        # Arrange: Create PresetEnv with integer temperature
        preset_env = PresetEnv(**{ATTR_TEMPERATURE: 20})  # Integer, not float

        # Act: Get temperature
        temp = preset_env.get_temperature(hass)

        # Assert: Returns as float
        assert temp == 20.0
        assert isinstance(temp, float)


class TestTemplateDetectionAndEvaluation:
    """Test US2: Simple template with entity reference."""

    @pytest.mark.asyncio
    async def test_template_detection_string_value(
        self, hass: HomeAssistant, setup_template_test_entities
    ):
        """Test T022: Verify string stored in _template_fields."""
        # Arrange: Create PresetEnv with template string
        template_str = "{{ states('input_number.away_temp') }}"
        preset_env = PresetEnv(**{ATTR_TEMPERATURE: template_str})

        # Assert: Template detected and stored
        assert "temperature" in preset_env._template_fields
        assert preset_env._template_fields["temperature"] == template_str
        assert preset_env.has_templates()

    @pytest.mark.asyncio
    async def test_entity_extraction_simple(
        self, hass: HomeAssistant, setup_template_test_entities
    ):
        """Test T023: Verify Template.extract_entities() populates _referenced_entities."""
        # Arrange: Create PresetEnv with template referencing entity
        template_str = "{{ states('input_number.away_temp') | float }}"
        preset_env = PresetEnv(**{ATTR_TEMPERATURE: template_str})

        # Assert: Entity extracted
        assert "input_number.away_temp" in preset_env.referenced_entities

    @pytest.mark.asyncio
    async def test_template_evaluation_success(
        self, hass: HomeAssistant, setup_template_test_entities
    ):
        """Test T024: Verify template.async_render() called and result converted to float."""
        # Arrange: Setup test entities and create preset with template
        await setup_template_test_entities
        template_str = "{{ states('input_number.away_temp') }}"
        preset_env = PresetEnv(**{ATTR_TEMPERATURE: template_str})

        # Act: Get temperature (triggers template evaluation)
        temp = preset_env.get_temperature(hass)

        # Assert: Template evaluated to float value from entity
        assert temp == 18.0  # input_number.away_temp set to 18 in fixture
        assert isinstance(temp, float)

    @pytest.mark.asyncio
    async def test_template_evaluation_entity_unavailable(
        self, hass: HomeAssistant, setup_template_test_entities
    ):
        """Test T025: Verify fallback to last_good_value with warning log."""
        # Arrange: Setup entities and create preset
        await setup_template_test_entities
        template_str = "{{ states('input_number.away_temp') }}"
        preset_env = PresetEnv(**{ATTR_TEMPERATURE: template_str})

        # Act: Get temperature (establishes last_good_value)
        first_temp = preset_env.get_temperature(hass)
        assert first_temp == 18.0

        # Make entity unavailable
        hass.states.async_set("input_number.away_temp", "unavailable")
        await hass.async_block_till_done()

        # Get temperature again (should fall back)
        second_temp = preset_env.get_temperature(hass)

        # Assert: Fallback to last good value
        assert second_temp == 18.0  # Same as previous successful evaluation

    @pytest.mark.asyncio
    async def test_template_evaluation_fallback_to_default(
        self, hass: HomeAssistant, setup_template_test_entities
    ):
        """Test T026: Verify 20.0 default when no previous value."""
        # Arrange: Create preset with template referencing non-existent entity
        template_str = "{{ states('sensor.nonexistent') }}"
        preset_env = PresetEnv(**{ATTR_TEMPERATURE: template_str})

        # Act: Get temperature (no previous value, entity doesn't exist)
        temp = preset_env.get_temperature(hass)

        # Assert: Falls back to 20.0 default
        assert temp == 20.0

    @pytest.mark.asyncio
    async def test_template_with_filters(
        self, hass: HomeAssistant, setup_template_test_entities
    ):
        """Test template with Jinja2 filters (| float)."""
        # Arrange: Setup entities and create preset with filtered template
        await setup_template_test_entities
        template_str = "{{ states('input_number.eco_temp') | float }}"
        preset_env = PresetEnv(**{ATTR_TEMPERATURE: template_str})

        # Act: Get temperature
        temp = preset_env.get_temperature(hass)

        # Assert: Template evaluated correctly with filter
        assert temp == 20.0  # input_number.eco_temp set to 20 in fixture

    @pytest.mark.asyncio
    async def test_range_mode_with_templates(
        self, hass: HomeAssistant, setup_template_test_entities
    ):
        """Test range mode with both template values."""
        # Arrange: Setup entities and create range preset with templates
        await setup_template_test_entities
        preset_env = PresetEnv(
            **{
                ATTR_TARGET_TEMP_LOW: "{{ states('sensor.outdoor_temp') | float - 2 }}",
                ATTR_TARGET_TEMP_HIGH: "{{ states('sensor.outdoor_temp') | float + 4 }}",
            }
        )

        # Act: Get temperatures
        temp_low = preset_env.get_target_temp_low(hass)
        temp_high = preset_env.get_target_temp_high(hass)

        # Assert: Both templates evaluated (outdoor_temp = 20 in fixture)
        assert temp_low == 18.0  # 20 - 2
        assert temp_high == 24.0  # 20 + 4


class TestComplexConditionalTemplates:
    """Test US3: Complex conditional templates with multiple entity references."""

    @pytest.mark.asyncio
    async def test_template_complex_conditional(
        self, hass: HomeAssistant, setup_template_test_entities
    ):
        """Test T046: Verify if/else template logic works correctly."""
        # Arrange: Setup entities and create preset with conditional template
        await setup_template_test_entities
        template_str = "{{ 16 if is_state('sensor.season', 'winter') else 26 }}"
        preset_env = PresetEnv(**{ATTR_TEMPERATURE: template_str})

        # Act: Get temperature with season='winter'
        temp_winter = preset_env.get_temperature(hass)

        # Assert: Winter condition evaluates to 16
        assert temp_winter == 16.0

        # Change season to summer
        hass.states.async_set("sensor.season", "summer")
        await hass.async_block_till_done()

        # Act: Get temperature with season='summer'
        temp_summer = preset_env.get_temperature(hass)

        # Assert: Summer condition evaluates to 26
        assert temp_summer == 26.0

    @pytest.mark.asyncio
    async def test_entity_extraction_multiple_entities(
        self, hass: HomeAssistant, setup_template_test_entities
    ):
        """Test T047: Verify templates with multiple entity references extract all entities."""
        # Arrange: Create preset with template referencing multiple entities
        template_str = """
        {{ 18 if is_state('binary_sensor.someone_home', 'on')
           else (16 if is_state('sensor.season', 'winter') else 26) }}
        """
        preset_env = PresetEnv(**{ATTR_TEMPERATURE: template_str})

        # Assert: All referenced entities extracted
        referenced = preset_env.referenced_entities
        assert "binary_sensor.someone_home" in referenced
        assert "sensor.season" in referenced
        assert len(referenced) == 2

    @pytest.mark.asyncio
    async def test_template_with_multiple_conditions(
        self, hass: HomeAssistant, setup_template_test_entities
    ):
        """Test T049: Verify complex template with season + presence logic."""
        # Arrange: Setup entities and create complex conditional template
        await setup_template_test_entities
        template_str = """
        {{ 22 if is_state('binary_sensor.someone_home', 'on')
           else (16 if is_state('sensor.season', 'winter') else 26) }}
        """
        preset_env = PresetEnv(**{ATTR_TEMPERATURE: template_str})

        # Act: Get temperature with someone_home='on' (fixture default)
        temp_home = preset_env.get_temperature(hass)

        # Assert: Home condition takes precedence (22°C)
        assert temp_home == 22.0

        # Change to away
        hass.states.async_set("binary_sensor.someone_home", "off")
        await hass.async_block_till_done()

        # Act: Get temperature when away in winter
        temp_away_winter = preset_env.get_temperature(hass)

        # Assert: Falls through to winter condition (16°C)
        assert temp_away_winter == 16.0

        # Change season to summer
        hass.states.async_set("sensor.season", "summer")
        await hass.async_block_till_done()

        # Act: Get temperature when away in summer
        temp_away_summer = preset_env.get_temperature(hass)

        # Assert: Falls through to summer condition (26°C)
        assert temp_away_summer == 26.0


class TestRangeModeWithTemplates:
    """Test US4: Temperature range mode with template support."""

    @pytest.mark.asyncio
    async def test_range_mode_mixed_static_template(
        self, hass: HomeAssistant, setup_template_test_entities
    ):
        """Test T054: One static value and one template work together in range mode."""
        # Arrange: Setup entities and create preset with mixed values
        await setup_template_test_entities
        preset_env = PresetEnv(
            **{
                ATTR_TARGET_TEMP_LOW: 18.0,  # Static value
                ATTR_TARGET_TEMP_HIGH: "{{ states('sensor.outdoor_temp') | float + 4 }}",  # Template
            }
        )

        # Act: Get temperatures
        temp_low = preset_env.get_target_temp_low(hass)
        temp_high = preset_env.get_target_temp_high(hass)

        # Assert: Static returns fixed value, template evaluates
        assert temp_low == 18.0  # Static
        assert temp_high == 24.0  # 20 + 4 from template

        # Change outdoor temp
        hass.states.async_set("sensor.outdoor_temp", "25")
        await hass.async_block_till_done()

        # Act: Get temperatures again
        temp_low_after = preset_env.get_target_temp_low(hass)
        temp_high_after = preset_env.get_target_temp_high(hass)

        # Assert: Static unchanged, template updated
        assert temp_low_after == 18.0  # Still static
        assert temp_high_after == 29.0  # 25 + 4 from updated template
