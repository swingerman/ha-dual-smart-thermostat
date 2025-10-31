"""Tests for EnvironmentManager tolerance selection logic."""

from homeassistant.components.climate.const import HVACMode
import pytest

from custom_components.dual_smart_thermostat.const import (
    CONF_COLD_TOLERANCE,
    CONF_COOL_TOLERANCE,
    CONF_HEAT_TOLERANCE,
    CONF_HOT_TOLERANCE,
    CONF_SENSOR,
)
from custom_components.dual_smart_thermostat.managers.environment_manager import (
    EnvironmentManager,
)


@pytest.fixture
def basic_config():
    """Return basic configuration for EnvironmentManager."""
    return {
        CONF_SENSOR: "sensor.temperature",
        CONF_COLD_TOLERANCE: 0.5,
        CONF_HOT_TOLERANCE: 0.5,
    }


@pytest.fixture
def config_with_mode_specific_tolerances():
    """Return configuration with mode-specific tolerances."""
    return {
        CONF_SENSOR: "sensor.temperature",
        CONF_COLD_TOLERANCE: 0.5,
        CONF_HOT_TOLERANCE: 0.5,
        CONF_HEAT_TOLERANCE: 0.3,
        CONF_COOL_TOLERANCE: 2.0,
    }


@pytest.fixture
def environment_manager(hass, basic_config):
    """Return EnvironmentManager instance with basic config."""
    return EnvironmentManager(hass, basic_config)


@pytest.fixture
def environment_manager_with_tolerances(hass, config_with_mode_specific_tolerances):
    """Return EnvironmentManager instance with mode-specific tolerances."""
    return EnvironmentManager(hass, config_with_mode_specific_tolerances)


class TestSetHvacMode:
    """Test set_hvac_mode() method."""

    @pytest.mark.asyncio
    async def test_set_hvac_mode_stores_mode_correctly(self, hass, environment_manager):
        """Test that set_hvac_mode stores the HVAC mode correctly."""
        environment_manager.set_hvac_mode(HVACMode.HEAT)
        assert environment_manager._hvac_mode == HVACMode.HEAT

        environment_manager.set_hvac_mode(HVACMode.COOL)
        assert environment_manager._hvac_mode == HVACMode.COOL

        environment_manager.set_hvac_mode(HVACMode.HEAT_COOL)
        assert environment_manager._hvac_mode == HVACMode.HEAT_COOL

        environment_manager.set_hvac_mode(HVACMode.FAN_ONLY)
        assert environment_manager._hvac_mode == HVACMode.FAN_ONLY


class TestGetActiveToleranceForMode:
    """Test _get_active_tolerance_for_mode() method."""

    @pytest.mark.asyncio
    async def test_heat_mode_uses_heat_tolerance(
        self, hass, environment_manager_with_tolerances
    ):
        """Test HEAT mode uses heat_tolerance when configured."""
        env = environment_manager_with_tolerances
        env.set_hvac_mode(HVACMode.HEAT)

        cold_tol, hot_tol = env._get_active_tolerance_for_mode()

        assert cold_tol == 0.3  # heat_tolerance
        assert hot_tol == 0.3  # heat_tolerance

    @pytest.mark.asyncio
    async def test_cool_mode_uses_cool_tolerance(
        self, hass, environment_manager_with_tolerances
    ):
        """Test COOL mode uses cool_tolerance when configured."""
        env = environment_manager_with_tolerances
        env.set_hvac_mode(HVACMode.COOL)

        cold_tol, hot_tol = env._get_active_tolerance_for_mode()

        assert cold_tol == 2.0  # cool_tolerance
        assert hot_tol == 2.0  # cool_tolerance

    @pytest.mark.asyncio
    async def test_fan_only_mode_uses_cool_tolerance(
        self, hass, environment_manager_with_tolerances
    ):
        """Test FAN_ONLY mode uses cool_tolerance when configured."""
        env = environment_manager_with_tolerances
        env.set_hvac_mode(HVACMode.FAN_ONLY)

        cold_tol, hot_tol = env._get_active_tolerance_for_mode()

        assert cold_tol == 2.0  # cool_tolerance
        assert hot_tol == 2.0  # cool_tolerance

    @pytest.mark.asyncio
    async def test_heat_cool_mode_heating_uses_heat_tolerance(
        self, hass, environment_manager_with_tolerances
    ):
        """Test HEAT_COOL mode uses heat_tolerance when currently heating."""
        env = environment_manager_with_tolerances
        env.set_hvac_mode(HVACMode.HEAT_COOL)
        env._target_temp = 21.0
        env._cur_temp = 20.0  # Below target -> heating

        cold_tol, hot_tol = env._get_active_tolerance_for_mode()

        assert cold_tol == 0.3  # heat_tolerance
        assert hot_tol == 0.3  # heat_tolerance

    @pytest.mark.asyncio
    async def test_heat_cool_mode_cooling_uses_cool_tolerance(
        self, hass, environment_manager_with_tolerances
    ):
        """Test HEAT_COOL mode uses cool_tolerance when currently cooling."""
        env = environment_manager_with_tolerances
        env.set_hvac_mode(HVACMode.HEAT_COOL)
        env._target_temp = 21.0
        env._cur_temp = 22.0  # Above target -> cooling

        cold_tol, hot_tol = env._get_active_tolerance_for_mode()

        assert cold_tol == 2.0  # cool_tolerance
        assert hot_tol == 2.0  # cool_tolerance

    @pytest.mark.asyncio
    async def test_legacy_fallback_when_heat_tolerance_none(
        self, hass, environment_manager
    ):
        """Test legacy fallback when heat_tolerance is None."""
        env = environment_manager
        env.set_hvac_mode(HVACMode.HEAT)

        cold_tol, hot_tol = env._get_active_tolerance_for_mode()

        assert cold_tol == 0.5  # cold_tolerance (legacy)
        assert hot_tol == 0.5  # hot_tolerance (legacy)

    @pytest.mark.asyncio
    async def test_legacy_fallback_when_cool_tolerance_none(
        self, hass, environment_manager
    ):
        """Test legacy fallback when cool_tolerance is None."""
        env = environment_manager
        env.set_hvac_mode(HVACMode.COOL)

        cold_tol, hot_tol = env._get_active_tolerance_for_mode()

        assert cold_tol == 0.5  # cold_tolerance (legacy)
        assert hot_tol == 0.5  # hot_tolerance (legacy)

    @pytest.mark.asyncio
    async def test_legacy_fallback_when_both_tolerances_none(self, hass):
        """Test legacy fallback when both mode-specific tolerances are None."""
        config = {
            CONF_SENSOR: "sensor.temperature",
            CONF_COLD_TOLERANCE: 0.4,
            CONF_HOT_TOLERANCE: 0.6,
        }
        env = EnvironmentManager(hass, config)
        env.set_hvac_mode(HVACMode.HEAT)

        cold_tol, hot_tol = env._get_active_tolerance_for_mode()

        assert cold_tol == 0.4  # cold_tolerance (legacy)
        assert hot_tol == 0.6  # hot_tolerance (legacy)

    @pytest.mark.asyncio
    async def test_tolerance_selection_with_none_hvac_mode(
        self, hass, environment_manager_with_tolerances
    ):
        """Test tolerance selection falls back to legacy when hvac_mode is None."""
        env = environment_manager_with_tolerances
        # Don't set hvac_mode, it should be None by default

        cold_tol, hot_tol = env._get_active_tolerance_for_mode()

        # Should fall back to legacy tolerances
        assert cold_tol == 0.5  # cold_tolerance
        assert hot_tol == 0.5  # hot_tolerance


class TestIsTooColdWithModeAwareness:
    """Test is_too_cold() with mode-aware tolerance selection."""

    @pytest.mark.asyncio
    async def test_is_too_cold_uses_heat_tolerance_in_heat_mode(
        self, hass, environment_manager_with_tolerances
    ):
        """Test is_too_cold uses heat_tolerance in HEAT mode."""
        env = environment_manager_with_tolerances
        env.set_hvac_mode(HVACMode.HEAT)
        env._target_temp = 20.0
        env._cur_temp = 19.6

        # With heat_tolerance=0.3: 20.0 >= 19.6 + 0.3 -> 20.0 >= 19.9 -> True
        assert env.is_too_cold() is True

        # At boundary
        env._cur_temp = 19.7
        # 20.0 >= 19.7 + 0.3 -> 20.0 >= 20.0 -> True
        assert env.is_too_cold() is True

        # Just above threshold
        env._cur_temp = 19.71
        # 20.0 >= 19.71 + 0.3 -> 20.0 >= 20.01 -> False
        assert env.is_too_cold() is False

    @pytest.mark.asyncio
    async def test_is_too_cold_uses_legacy_when_no_mode_specific(
        self, hass, environment_manager
    ):
        """Test is_too_cold uses legacy tolerance when mode-specific not set."""
        env = environment_manager
        env.set_hvac_mode(HVACMode.HEAT)
        env._target_temp = 20.0
        env._cur_temp = 19.4

        # With cold_tolerance=0.5: 20.0 >= 19.4 + 0.5 -> 20.0 >= 19.9 -> True
        assert env.is_too_cold() is True

        env._cur_temp = 19.5
        # 20.0 >= 19.5 + 0.5 -> 20.0 >= 20.0 -> True
        assert env.is_too_cold() is True

        env._cur_temp = 19.51
        # 20.0 >= 19.51 + 0.5 -> 20.0 >= 20.01 -> False
        assert env.is_too_cold() is False


class TestIsTooHotWithModeAwareness:
    """Test is_too_hot() with mode-aware tolerance selection."""

    @pytest.mark.asyncio
    async def test_is_too_hot_uses_cool_tolerance_in_cool_mode(
        self, hass, environment_manager_with_tolerances
    ):
        """Test is_too_hot uses cool_tolerance in COOL mode."""
        env = environment_manager_with_tolerances
        env.set_hvac_mode(HVACMode.COOL)
        env._target_temp = 22.0
        env._cur_temp = 24.1

        # With cool_tolerance=2.0: 24.1 >= 22.0 + 2.0 -> 24.1 >= 24.0 -> True
        assert env.is_too_hot() is True

        # At boundary
        env._cur_temp = 24.0
        # 24.0 >= 22.0 + 2.0 -> 24.0 >= 24.0 -> True
        assert env.is_too_hot() is True

        # Just below threshold
        env._cur_temp = 23.99
        # 23.99 >= 22.0 + 2.0 -> 23.99 >= 24.0 -> False
        assert env.is_too_hot() is False

    @pytest.mark.asyncio
    async def test_is_too_hot_uses_legacy_when_no_mode_specific(
        self, hass, environment_manager
    ):
        """Test is_too_hot uses legacy tolerance when mode-specific not set."""
        env = environment_manager
        env.set_hvac_mode(HVACMode.COOL)
        env._target_temp = 22.0
        env._cur_temp = 22.6

        # With hot_tolerance=0.5: 22.6 >= 22.0 + 0.5 -> 22.6 >= 22.5 -> True
        assert env.is_too_hot() is True

        env._cur_temp = 22.5
        # 22.5 >= 22.0 + 0.5 -> 22.5 >= 22.5 -> True
        assert env.is_too_hot() is True

        env._cur_temp = 22.49
        # 22.49 >= 22.0 + 0.5 -> 22.49 >= 22.5 -> False
        assert env.is_too_hot() is False
