import enum


class HVACActionReasonAuto(enum.StrEnum):
    """Auto-mode-selected HVAC Action Reason.

    Values declared in Phase 0 and reserved for Auto Mode (Phase 1). They
    appear in the sensor's ``options`` list but are not emitted by any
    controller until Phase 1 wires the priority evaluation engine.
    """

    AUTO_PRIORITY_HUMIDITY = "auto_priority_humidity"

    AUTO_PRIORITY_TEMPERATURE = "auto_priority_temperature"

    AUTO_PRIORITY_COMFORT = "auto_priority_comfort"
