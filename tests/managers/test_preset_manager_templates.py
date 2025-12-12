"""Test PresetManager template integration."""

from unittest.mock import Mock

from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
import pytest

from custom_components.dual_smart_thermostat.managers.preset_manager import (
    PresetManager,
)
from custom_components.dual_smart_thermostat.preset_env.preset_env import PresetEnv


class TestPresetManagerTemplateIntegration:
    """Test PresetManager calls template evaluation correctly."""

    @pytest.mark.asyncio
    async def test_preset_manager_calls_template_evaluation(
        self, hass: HomeAssistant, setup_template_test_entities
    ):
        """Test T027: Verify PresetManager uses getters."""
        # Arrange: Setup entities and create preset with template
        setup_template_test_entities
        template_str = "{{ states('input_number.away_temp') }}"
        preset_env = PresetEnv(**{ATTR_TEMPERATURE: template_str})

        # Create mock PresetManager components
        config = {}
        environment = Mock()
        environment.target_temp = None
        features = Mock()
        features.is_range_mode = False

        preset_manager = PresetManager(hass, config, environment, features)
        preset_manager._presets = {"away": preset_env}
        preset_manager._preset_modes = ["away"]

        # Mock state to trigger apply_old_state
        old_state = Mock()
        old_state.attributes = {
            "preset_mode": "away",
            "temperature": None,
        }

        # Act: Apply old state (which should use getter)
        await preset_manager.apply_old_state(old_state)

        # Assert: Environment target temp set from template evaluation
        assert environment.target_temp == 18.0  # Value from template

    @pytest.mark.asyncio
    async def test_preset_manager_applies_evaluated_temperature(
        self, hass: HomeAssistant, setup_template_test_entities
    ):
        """Test T028: Verify environment.target_temp updated with template result."""
        # Arrange: Setup entities
        setup_template_test_entities

        # Change entity value to verify template evaluation
        hass.states.async_set(
            "input_number.eco_temp", "22", {"unit_of_measurement": "°C"}
        )
        await hass.async_block_till_done()

        template_str = "{{ states('input_number.eco_temp') | float }}"
        preset_env = PresetEnv(**{ATTR_TEMPERATURE: template_str})

        config = {}
        environment = Mock()
        environment.target_temp = None
        environment.saved_target_temp = 20.0
        features = Mock()
        features.is_range_mode = False

        preset_manager = PresetManager(hass, config, environment, features)
        preset_manager._presets = {"eco": preset_env}
        preset_manager._preset_modes = ["eco"]

        old_state = Mock()
        old_state.attributes = {
            "preset_mode": "eco",
            "temperature": None,
        }

        # Act: Apply old state
        await preset_manager.apply_old_state(old_state)

        # Assert: Target temp is the evaluated template value (22, not the original entity value 20)
        assert environment.target_temp == 22.0

    @pytest.mark.asyncio
    async def test_preset_manager_range_mode_with_templates(
        self, hass: HomeAssistant, setup_template_test_entities
    ):
        """Test PresetManager handles range mode templates."""
        # Arrange: Setup entities
        setup_template_test_entities

        preset_env = PresetEnv(
            **{
                "target_temp_low": "{{ states('sensor.outdoor_temp') | float - 2 }}",
                "target_temp_high": "{{ states('sensor.outdoor_temp') | float + 4 }}",
            }
        )

        config = {}
        environment = Mock()
        environment.target_temp_low = None
        environment.target_temp_high = None
        environment.saved_target_temp_low = None
        environment.saved_target_temp_high = None
        features = Mock()
        features.is_range_mode = True

        preset_manager = PresetManager(hass, config, environment, features)
        preset_manager._presets = {"eco": preset_env}
        preset_manager._preset_modes = ["eco"]

        old_state = Mock()
        old_state.attributes = {
            "preset_mode": "eco",
            "target_temp_low": None,
            "target_temp_high": None,
        }

        # Act: Apply old state
        await preset_manager.apply_old_state(old_state)

        # Assert: Both temps set from templates (outdoor_temp = 20 in fixture)
        assert environment.target_temp_low == 18.0  # 20 - 2
        assert environment.target_temp_high == 24.0  # 20 + 4
