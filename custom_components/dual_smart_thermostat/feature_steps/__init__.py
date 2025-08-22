"""Feature-specific configuration steps for dual smart thermostat."""

from .fan import FanSteps
from .humidity import HumiditySteps
from .openings import OpeningsSteps
from .presets import PresetsSteps

__all__ = [
    "OpeningsSteps",
    "FanSteps",
    "HumiditySteps",
    "PresetsSteps",
]
