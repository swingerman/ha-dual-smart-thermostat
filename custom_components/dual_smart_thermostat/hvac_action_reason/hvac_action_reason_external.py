import enum


class HVACActionReasonExternal(enum.StrEnum):
    """External HVAC Action Reason for climate devices."""

    PRESENCE = "presence"

    SCHEDULE = "schedule"

    EMERGENCY = "emergency"

    MALFUNCTION = "malfunction"
