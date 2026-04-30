"""Tests for EnvironmentManager additions in Phase 1.4 (apparent temperature)."""

from unittest.mock import MagicMock

from homeassistant.const import UnitOfTemperature

from custom_components.dual_smart_thermostat.managers.environment_manager import (
    EnvironmentManager,
    _rothfusz_heat_index_f,
)


def test_rothfusz_heat_index_at_threshold_minimum_humidity() -> None:
    """At 80°F (≈27°C) and 40% RH, heat index ≈ 80°F (formula barely active)."""
    hi = _rothfusz_heat_index_f(80.0, 40.0)
    assert 79.0 <= hi <= 81.0


def test_rothfusz_heat_index_high_humidity_above_threshold() -> None:
    """At 80°F and 80% RH, heat index ≈ 84°F (mild humidity boost)."""
    hi = _rothfusz_heat_index_f(80.0, 80.0)
    assert 83.0 <= hi <= 85.0


def test_rothfusz_heat_index_hot_humid() -> None:
    """At 90°F and 80% RH, heat index ≈ 113°F (per NWS table)."""
    hi = _rothfusz_heat_index_f(90.0, 80.0)
    assert 110.0 <= hi <= 116.0


def test_rothfusz_heat_index_low_humidity_extreme_temp() -> None:
    """At 100°F and 20% RH, heat index ≈ 99°F."""
    hi = _rothfusz_heat_index_f(100.0, 20.0)
    assert 96.0 <= hi <= 102.0


def _make_env(**config_overrides) -> EnvironmentManager:
    """Build an EnvironmentManager with a mocked hass and a fresh config dict."""
    hass = MagicMock()
    hass.config.units.temperature_unit = UnitOfTemperature.CELSIUS
    config: dict = {}
    config.update(config_overrides)
    return EnvironmentManager(hass, config)


def test_env_manager_default_use_apparent_temp_is_false() -> None:
    """Without CONF_USE_APPARENT_TEMP set, the flag stores False."""
    env = _make_env()
    assert env._use_apparent_temp is False


def test_env_manager_reads_use_apparent_temp_from_config() -> None:
    """When config sets the flag, it is stored on the manager."""
    from custom_components.dual_smart_thermostat.const import CONF_USE_APPARENT_TEMP

    env = _make_env(**{CONF_USE_APPARENT_TEMP: True})
    assert env._use_apparent_temp is True


def test_env_manager_humidity_sensor_stalled_default_false() -> None:
    """Default humidity-stalled flag is False."""
    env = _make_env()
    assert env.humidity_sensor_stalled is False


def test_env_manager_humidity_sensor_stalled_setter_updates_flag() -> None:
    """Setter flips the flag."""
    env = _make_env()
    env.humidity_sensor_stalled = True
    assert env.humidity_sensor_stalled is True
