"""Schema utilities for config and options flows."""

from __future__ import annotations

from homeassistant.const import DEGREE, PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector
from homeassistant.util.unit_conversion import TemperatureConverter


def seconds_to_duration(seconds: int) -> dict[str, int]:
    """Convert seconds to duration dict format for DurationSelector.

    Args:
        seconds: Total number of seconds

    Returns:
        Dict with hours, minutes, seconds breakdown

    Example:
        >>> seconds_to_duration(300)
        {'hours': 0, 'minutes': 5, 'seconds': 0}
    """
    hours = seconds // 3600
    remainder = seconds % 3600
    minutes = remainder // 60
    secs = remainder % 60
    return {"hours": hours, "minutes": minutes, "seconds": secs}


def get_temperature_selector(
    hass: HomeAssistant | None = None,
    min_value: float = 5.0,
    max_value: float = 35.0,
    step: float = 0.1,
    unit_of_measurement: str | None = None,
) -> selector.NumberSelector:
    """Get a temperature selector that respects user's unit preference.

    Args:
        hass: HomeAssistant instance to get user's temperature unit preference
        min_value: Minimum value in Celsius (will be converted if needed)
        max_value: Maximum value in Celsius (will be converted if needed)
        step: Step value (will be adjusted for Fahrenheit)
        unit_of_measurement: Optional override for unit symbol

    Returns:
        NumberSelector configured with appropriate temperature unit
    """
    # Determine temperature unit and symbol
    if hass is not None and unit_of_measurement is None:
        temp_unit = hass.config.units.temperature_unit

        # Convert ranges if user prefers Fahrenheit
        if temp_unit == UnitOfTemperature.FAHRENHEIT:
            min_value = TemperatureConverter.convert(
                min_value, UnitOfTemperature.CELSIUS, UnitOfTemperature.FAHRENHEIT
            )
            max_value = TemperatureConverter.convert(
                max_value, UnitOfTemperature.CELSIUS, UnitOfTemperature.FAHRENHEIT
            )
            # Adjust step for Fahrenheit (Celsius step * 1.8)
            step = round(step * 1.8, 1)
            unit_symbol = "°F"
        else:
            unit_symbol = "°C"
    else:
        # Fallback to generic degree symbol if hass not provided
        unit_symbol = unit_of_measurement or DEGREE

    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=min_value,
            max=max_value,
            step=step,
            unit_of_measurement=unit_symbol,
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def get_tolerance_selector(
    hass: HomeAssistant | None = None,
    min_value: float = 0.0,
    max_value: float = 10.0,
    step: float = 0.05,
) -> selector.NumberSelector:
    """Get a tolerance/hysteresis selector that handles temperature deltas correctly.

    Unlike get_temperature_selector() which converts absolute temperatures
    (0°C → 32°F), this function handles temperature DIFFERENCES correctly
    (0.3°C → 0.54°F by multiplying by 1.8).

    Tolerance values represent how far the temperature must deviate from the
    setpoint before triggering HVAC action. They are deltas, not absolute temps.

    Args:
        hass: HomeAssistant instance to get user's temperature unit preference
        min_value: Minimum tolerance in Celsius (will be scaled for Fahrenheit)
        max_value: Maximum tolerance in Celsius (will be scaled for Fahrenheit)
        step: Step value in Celsius (will be scaled for Fahrenheit)

    Returns:
        NumberSelector configured for tolerance input
    """
    # Determine temperature unit and scale values appropriately
    if hass is not None:
        temp_unit = hass.config.units.temperature_unit

        # For Fahrenheit, scale the delta values (multiply by 1.8)
        # NOT absolute conversion which would turn 0°C into 32°F
        if temp_unit == UnitOfTemperature.FAHRENHEIT:
            min_value = round(min_value * 1.8, 2)
            max_value = round(max_value * 1.8, 2)
            step = round(step * 1.8, 2)
            unit_symbol = "°F"
        else:
            unit_symbol = "°C"
    else:
        # Fallback to generic degree symbol if hass not provided
        unit_symbol = DEGREE

    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=min_value,
            max=max_value,
            step=step,
            unit_of_measurement=unit_symbol,
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def get_percentage_selector(
    min_value: float = 0.0,
    max_value: float = 100.0,
    step: float = 1.0,
) -> selector.NumberSelector:
    """Get a standardized percentage selector."""
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=min_value,
            max=max_value,
            step=step,
            unit_of_measurement=PERCENTAGE,
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def get_time_selector(
    min_value: int = 0,
    max_value: int = 3600,
    step: int = 1,
) -> selector.DurationSelector:
    """Get a standardized time selector using DurationSelector.

    Note: min_value, max_value, and step parameters are kept for backward compatibility
    but are not used by DurationSelector. Use allow_negative parameter if needed.
    """
    return selector.DurationSelector(
        selector.DurationSelectorConfig(allow_negative=False)
    )


def get_entity_selector(domain: str | list[str]) -> selector.EntitySelector:
    """Get a standardized entity selector for a specific domain or list of domains.

    Args:
        domain: A single domain string or list of domain strings

    Returns:
        EntitySelector configured for the specified domain(s)
    """
    return selector.EntitySelector(selector.EntitySelectorConfig(domain=domain))


def get_boolean_selector() -> selector.BooleanSelector:
    """Get a standardized boolean selector."""
    return selector.BooleanSelector()


def get_select_selector(
    options: list[str] | list[dict[str, str]],
    mode: selector.SelectSelectorMode = selector.SelectSelectorMode.DROPDOWN,
) -> selector.SelectSelector:
    """Get a standardized select selector."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options,
            mode=mode,
        )
    )


def get_multi_select_selector(
    options: list[str] | list[dict[str, str]],
) -> selector.SelectSelector:
    """Get a standardized multi-select selector."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options,
            multiple=True,
            mode=selector.SelectSelectorMode.LIST,
        )
    )


def get_text_selector(
    multiline: bool = False,
    type_: selector.TextSelectorType = selector.TextSelectorType.TEXT,
) -> selector.TextSelector:
    """Get a standardized text selector."""
    return selector.TextSelector(
        selector.TextSelectorConfig(
            multiline=multiline,
            type=type_,
        )
    )
