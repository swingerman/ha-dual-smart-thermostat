"""Tests for EnvironmentManager additions in Phase 1.4 (apparent temperature)."""

from unittest.mock import MagicMock

from homeassistant.components.climate import HVACMode
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


def test_apparent_temp_falls_back_when_flag_off() -> None:
    """Flag off → apparent_temp returns cur_temp regardless of humidity."""
    env = _make_env()
    env._cur_temp = 32.0
    env._cur_humidity = 80.0
    assert env.apparent_temp == 32.0


def test_apparent_temp_falls_back_when_cur_temp_none() -> None:
    """No temp → apparent_temp returns None."""
    from custom_components.dual_smart_thermostat.const import CONF_USE_APPARENT_TEMP

    env = _make_env(**{CONF_USE_APPARENT_TEMP: True})
    env._cur_temp = None
    env._cur_humidity = 80.0
    assert env.apparent_temp is None


def test_apparent_temp_falls_back_when_humidity_none() -> None:
    """Humidity unavailable → apparent_temp returns cur_temp."""
    from custom_components.dual_smart_thermostat.const import CONF_USE_APPARENT_TEMP

    env = _make_env(**{CONF_USE_APPARENT_TEMP: True})
    env._cur_temp = 32.0
    env._cur_humidity = None
    assert env.apparent_temp == 32.0


def test_apparent_temp_falls_back_when_humidity_stalled() -> None:
    """Humidity stalled → apparent_temp returns cur_temp."""
    from custom_components.dual_smart_thermostat.const import CONF_USE_APPARENT_TEMP

    env = _make_env(**{CONF_USE_APPARENT_TEMP: True})
    env._cur_temp = 32.0
    env._cur_humidity = 80.0
    env.humidity_sensor_stalled = True
    assert env.apparent_temp == 32.0


def test_apparent_temp_falls_back_below_27c_threshold() -> None:
    """Below 27°C (Rothfusz validity threshold) → returns cur_temp."""
    from custom_components.dual_smart_thermostat.const import CONF_USE_APPARENT_TEMP

    env = _make_env(**{CONF_USE_APPARENT_TEMP: True})
    env._cur_temp = 26.9  # just below
    env._cur_humidity = 80.0
    assert env.apparent_temp == 26.9


def test_apparent_temp_above_threshold_humid_celsius() -> None:
    """Above threshold + humid → apparent_temp > cur_temp."""
    from custom_components.dual_smart_thermostat.const import CONF_USE_APPARENT_TEMP

    env = _make_env(**{CONF_USE_APPARENT_TEMP: True})
    env._cur_temp = 32.0  # ≈90°F
    env._cur_humidity = 80.0
    apparent = env.apparent_temp
    assert apparent is not None
    assert 39.0 < apparent < 47.0
    assert apparent > env._cur_temp


def test_apparent_temp_fahrenheit_input_conversion() -> None:
    """Same physical conditions in °F input → consistent output in °F."""
    from custom_components.dual_smart_thermostat.const import CONF_USE_APPARENT_TEMP

    hass = MagicMock()
    hass.config.units.temperature_unit = UnitOfTemperature.FAHRENHEIT
    env = EnvironmentManager(hass, {CONF_USE_APPARENT_TEMP: True})
    env._cur_temp = 90.0  # 90°F = 32.2°C
    env._cur_humidity = 80.0
    apparent = env.apparent_temp
    # 90°F / 80% RH → 113°F per NWS table (window 110-116).
    assert 110.0 < apparent < 116.0


def test_effective_temp_for_mode_returns_cur_when_flag_off() -> None:
    """Flag off → returns cur_temp for every mode."""
    env = _make_env()
    env._cur_temp = 32.0
    env._cur_humidity = 80.0
    for mode in (
        HVACMode.HEAT,
        HVACMode.COOL,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
        HVACMode.AUTO,
    ):
        assert env.effective_temp_for_mode(mode) == 32.0


def test_effective_temp_for_mode_cool_returns_apparent_when_eligible() -> None:
    """COOL mode + flag on + humid + above 27°C → returns apparent_temp."""
    from custom_components.dual_smart_thermostat.const import CONF_USE_APPARENT_TEMP

    env = _make_env(**{CONF_USE_APPARENT_TEMP: True})
    env._cur_temp = 32.0
    env._cur_humidity = 80.0
    eff = env.effective_temp_for_mode(HVACMode.COOL)
    assert eff is not None
    assert eff > 32.0  # apparent boosts above raw


def test_effective_temp_for_mode_non_cool_returns_cur() -> None:
    """Non-COOL modes → returns cur_temp even when flag is on."""
    from custom_components.dual_smart_thermostat.const import CONF_USE_APPARENT_TEMP

    env = _make_env(**{CONF_USE_APPARENT_TEMP: True})
    env._cur_temp = 32.0
    env._cur_humidity = 80.0
    for mode in (HVACMode.HEAT, HVACMode.DRY, HVACMode.FAN_ONLY, HVACMode.AUTO):
        assert env.effective_temp_for_mode(mode) == 32.0


def test_is_too_hot_uses_apparent_when_mode_cool_and_flag_on() -> None:
    """is_too_hot consults apparent_temp when env._hvac_mode == COOL and flag on.

    Setup: target=27.0, hot_tolerance=0.5, cur_temp=27.4 (raw is_too_hot=False
    because cur_temp < target+tolerance). With humidity=80%, apparent ≈ 30°C
    (well above 27.5 threshold) → apparent is_too_hot=True.

    Asserts that the apparent path is consulted when the env is in COOL mode.
    """
    from custom_components.dual_smart_thermostat.const import (
        CONF_HOT_TOLERANCE,
        CONF_TARGET_TEMP,
        CONF_USE_APPARENT_TEMP,
    )

    env = _make_env(
        **{
            CONF_USE_APPARENT_TEMP: True,
            CONF_TARGET_TEMP: 27.0,
            CONF_HOT_TOLERANCE: 0.5,
        }
    )
    env._cur_temp = 27.4  # raw is just below target+tolerance (27.5)
    env._cur_humidity = 80.0  # apparent boosts above threshold
    env._hvac_mode = HVACMode.COOL
    assert env.is_too_hot() is True


def test_is_too_hot_uses_raw_when_mode_not_cool() -> None:
    """is_too_hot uses raw cur_temp when env._hvac_mode != COOL even with flag on."""
    from custom_components.dual_smart_thermostat.const import (
        CONF_HOT_TOLERANCE,
        CONF_TARGET_TEMP,
        CONF_USE_APPARENT_TEMP,
    )

    env = _make_env(
        **{
            CONF_USE_APPARENT_TEMP: True,
            CONF_TARGET_TEMP: 27.0,
            CONF_HOT_TOLERANCE: 0.5,
        }
    )
    env._cur_temp = 27.4
    env._cur_humidity = 80.0
    env._hvac_mode = HVACMode.HEAT  # NOT cool
    # Raw cur_temp 27.4 < target+tolerance (27.5) → False.
    assert env.is_too_hot() is False


def test_is_too_hot_uses_raw_when_flag_off() -> None:
    """Flag off → raw cur_temp regardless of mode."""
    from custom_components.dual_smart_thermostat.const import (
        CONF_HOT_TOLERANCE,
        CONF_TARGET_TEMP,
    )

    env = _make_env(
        **{
            CONF_TARGET_TEMP: 27.0,
            CONF_HOT_TOLERANCE: 0.5,
        }
    )
    env._cur_temp = 27.4
    env._cur_humidity = 80.0
    env._hvac_mode = HVACMode.COOL
    assert env.is_too_hot() is False
