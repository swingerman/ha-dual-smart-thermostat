import enum


class HVACActionReasonInternal(enum.StrEnum):
    """Internal HVAC Action Reason for climate devices."""

    TARGET_TEMP_NOT_REACHED = "target_temp_not_reached"

    TARGET_TEMP_REACHED = "target_temp_reached"

    TARGET_TEMP_NOT_REACHED_WITH_FAN = "target_temp_not_reached_with_fan"

    MISCONFIGURATION = "misconfiguration"

    OPENING = "opening"

    LIMIT = "limit"

    OVERHEAT = "overheat"

    TEMPERATURE_SENSOR_TIMED_OUT = "temperature_sensor_timed_out"
