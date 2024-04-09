from enum import StrEnum


class HVACActionReasonInternal(StrEnum):
    """Internal HVAC Action Reason for climate devices."""

    TARGET_TEMP_NOT_REACHED = "target_temp_not_reached"

    TARGET_TEMP_REACHED = "target_temp_reached"

    MISCONFIGURATION = "misconfiguration"

    OPENING = "opening"

    LIMIT = "limit"

    OVERHEAT = "overheat"
