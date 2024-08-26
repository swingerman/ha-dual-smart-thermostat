import logging

from homeassistant.components.climate.const import (
    ATTR_HUMIDITY,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
)
from homeassistant.const import ATTR_TEMPERATURE

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


class TempEnv(TargeTempEnv, RangeTempEnv):
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
        super(PresetEnv, self).__init__(**kwargs)
        _LOGGER.debug(f"kwargs: {kwargs}")

    @property
    def to_dict(self) -> dict:
        return self.__dict__

    def has_temp_range(self) -> bool:
        return self.target_temp_low is not None and self.target_temp_high is not None

    def has_temp(self) -> bool:
        return self.temperature is not None

    def has_humidity(self) -> bool:
        return self.humidity is not None
