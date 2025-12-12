import logging
import re
from typing import Any

from homeassistant.components.climate.const import (
    ATTR_HUMIDITY,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
)
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import Template

from ..const import CONF_MAX_FLOOR_TEMP, CONF_MIN_FLOOR_TEMP

_LOGGER = logging.getLogger(__name__)


class TargeTempEnv:
    temperature: float | None

    def __init__(self, **kwargs) -> None:
        super(TargeTempEnv, self).__init__(**kwargs)
        self.temperature = kwargs.get(ATTR_TEMPERATURE) or None


class RangeTempEnv:
    target_temp_low: float | None
    target_temp_high: float | None

    def __init__(self, **kwargs) -> None:
        super(RangeTempEnv, self).__init__(**kwargs)
        self.target_temp_low = kwargs.get(ATTR_TARGET_TEMP_LOW) or None
        self.target_temp_high = kwargs.get(ATTR_TARGET_TEMP_HIGH) or None


class FloorTempLimitEnv:
    min_floor_temp: float | None
    max_floor_temp: float | None

    def __init__(self, **kwargs) -> None:
        super(FloorTempLimitEnv, self).__init__(**kwargs)
        _LOGGER.debug(f"FloorTempLimitEnv kwargs: {kwargs}")
        self.min_floor_temp = kwargs.get(CONF_MIN_FLOOR_TEMP) or None
        self.max_floor_temp = kwargs.get(CONF_MAX_FLOOR_TEMP) or None


class TempEnv(TargeTempEnv, RangeTempEnv, FloorTempLimitEnv):
    def __init__(self, **kwargs) -> None:
        super(TempEnv, self).__init__(**kwargs)
        _LOGGER.debug(f"TempEnv kwargs: {kwargs}")


class HumidityEnv:
    humidity: float | None

    def __init__(self, **kwargs) -> None:
        super(HumidityEnv, self).__init__()
        _LOGGER.debug(f"HumidityEnv kwargs: {kwargs}")
        self.humidity = kwargs.get(ATTR_HUMIDITY) or None


class PresetEnv(TempEnv, HumidityEnv):
    def __init__(self, **kwargs):
        # Initialize template tracking structures BEFORE calling super().__init__()
        self._template_fields: dict[str, str] = {}  # field_name -> template_string
        self._last_good_values: dict[str, float] = (
            {}
        )  # field_name -> last successful value
        self._referenced_entities: set[str] = (
            set()
        )  # entity_ids referenced in templates

        super(PresetEnv, self).__init__(**kwargs)
        _LOGGER.debug(f"kwargs: {kwargs}")

        # Process temperature fields for template detection
        self._process_field("temperature", kwargs.get(ATTR_TEMPERATURE))
        self._process_field("target_temp_low", kwargs.get(ATTR_TARGET_TEMP_LOW))
        self._process_field("target_temp_high", kwargs.get(ATTR_TARGET_TEMP_HIGH))

    def _process_field(self, field_name: str, value: Any) -> None:
        """Process temperature field to determine if static or template."""
        if value is None:
            return

        if isinstance(value, (int, float)):
            # Static value - store as float and set last_good_value
            setattr(self, field_name, float(value))
            self._last_good_values[field_name] = float(value)
            _LOGGER.debug(
                f"PresetEnv: {field_name} stored as static value: {float(value)}"
            )
        elif isinstance(value, str):
            # Try to parse as number first (config stores numbers as strings)
            try:
                float_val = float(value)
                # It's a numeric string, treat as static value
                setattr(self, field_name, float_val)
                self._last_good_values[field_name] = float_val
                _LOGGER.debug(
                    f"PresetEnv: {field_name} stored as static value from string: {float_val}"
                )
                return
            except ValueError:
                pass  # Not a number, treat as template

            # Template string - store in template_fields and extract entities
            self._template_fields[field_name] = value
            self._extract_entities(value)
            _LOGGER.debug(f"PresetEnv: {field_name} detected as template: {value}")

    def _extract_entities(self, template_str: str) -> None:
        """Extract entity IDs from template string using regex.

        Parses template strings for entity_id patterns like:
        - states('sensor.temperature')
        - is_state('binary_sensor.motion', 'on')
        - state_attr('climate.thermostat', 'temperature')
        """
        try:
            # Pattern to match entity IDs in common template functions
            # Matches: states('entity.id'), is_state('entity.id', ...), state_attr('entity.id', ...)
            pattern = (
                r"(?:states|is_state|state_attr)\s*\(\s*['\"]([a-z_]+\.[a-z0-9_]+)['\"]"
            )
            matches = re.findall(pattern, template_str, re.IGNORECASE)

            if matches:
                self._referenced_entities.update(matches)
                _LOGGER.debug(f"PresetEnv: Extracted entities from template: {matches}")
        except Exception as e:
            _LOGGER.debug(f"PresetEnv: Could not extract entities from template: {e}")

    def get_temperature(self, hass: HomeAssistant) -> float | None:
        """Get temperature, evaluating template if needed."""
        if "temperature" in self._template_fields:
            return self._evaluate_template(hass, "temperature")
        return self.temperature

    def get_target_temp_low(self, hass: HomeAssistant) -> float | None:
        """Get target_temp_low, evaluating template if needed."""
        if "target_temp_low" in self._template_fields:
            return self._evaluate_template(hass, "target_temp_low")
        return self.target_temp_low

    def get_target_temp_high(self, hass: HomeAssistant) -> float | None:
        """Get target_temp_high, evaluating template if needed."""
        if "target_temp_high" in self._template_fields:
            return self._evaluate_template(hass, "target_temp_high")
        return self.target_temp_high

    def _evaluate_template(self, hass: HomeAssistant, field_name: str) -> float:
        """Safely evaluate template with fallback to previous value."""
        template_str = self._template_fields.get(field_name)
        if not template_str:
            # No template for this field, return last good value or default
            return self._last_good_values.get(field_name, 20.0)

        try:
            template = Template(template_str, hass)
            # Note: async_render is actually synchronous despite the name
            result = template.async_render()
            temp = float(result)

            # Update last good value
            self._last_good_values[field_name] = temp
            _LOGGER.debug(
                f"PresetEnv: Template evaluation success for {field_name}: {template_str} -> {temp}"
            )
            return temp
        except Exception as e:
            # Keep previous value on error
            previous = self._last_good_values.get(field_name, 20.0)
            _LOGGER.warning(
                f"PresetEnv: Template evaluation failed for {field_name}. "
                f"Template: {template_str}, Entities: {self._referenced_entities}, "
                f"Error: {e}, Keeping previous: {previous}"
            )
            return previous

    @property
    def referenced_entities(self) -> set[str]:
        """Return set of entities referenced in templates."""
        return self._referenced_entities

    def has_templates(self) -> bool:
        """Check if this preset uses any templates."""
        return len(self._template_fields) > 0

    @property
    def to_dict(self) -> dict:
        return self.__dict__

    def has_temp_range(self) -> bool:
        return self.target_temp_low is not None and self.target_temp_high is not None

    def has_temp(self) -> bool:
        return self.temperature is not None

    def has_humidity(self) -> bool:
        return self.humidity is not None

    def has_floor_temp_limits(self) -> bool:
        return self.min_floor_temp is not None or self.max_floor_temp is not None
