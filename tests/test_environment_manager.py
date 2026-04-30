"""Tests for EnvironmentManager additions in Phase 1.4 (apparent temperature)."""

from custom_components.dual_smart_thermostat.managers.environment_manager import (
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
