import enum


class HVACActionReasonInternal(enum.StrEnum):
    """Internal HVAC Action Reason for climate devices."""

    TARGET_TEMP_NOT_REACHED = "target_temp_not_reached"

    TARGET_TEMP_REACHED = "target_temp_reached"

    TARGET_TEMP_NOT_REACHED_WITH_FAN = "target_temp_not_reached_with_fan"

    TARGET_HUMIDITY_NOT_REACHED = "target_humidity_not_reached"

    TARGET_HUMIDITY_REACHED = "target_humidity_reached"

    MISCONFIGURATION = "misconfiguration"

    OPENING = "opening"

    LIMIT = "limit"

    OVERHEAT = "overheat"

    TEMPERATURE_SENSOR_STALLED = "temperature_sensor_stalled"

    HUMIDITY_SENSOR_STALLED = "humidity_sensor_stalled"
