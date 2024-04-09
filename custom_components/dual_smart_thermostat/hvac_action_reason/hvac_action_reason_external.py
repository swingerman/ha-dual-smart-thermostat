from enum import StrEnum


class HVACActionReasonExternal(StrEnum):
    """External HVAC Action Reason for climate devices."""

    PRESENCE = "presence"

    SCHEDULE = "schedule"

    EMERGENCY = "emergency"

    MALFUNCTION = "malfunction"
