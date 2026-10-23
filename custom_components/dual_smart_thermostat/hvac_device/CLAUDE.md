# Fan device notes

## Speed control

Speed control lives in `FanSpeedControl` (`fan_speed.py`); `FanDevice` delegates to it.
Capability detection is automatic (`_detect_fan_capabilities`): `fan`-domain entities with
`preset_modes` use those, ones exposing `percentage` fall back to a fixed
`auto/low/medium/high` mapping, `switch`-domain fans get no speed control at all, and a
`climate` entity with `fan_modes` uses them verbatim (`quiet`, `strong`, ...) via
`climate.set_fan_mode`. This is deliberate - there is no way to override the detected
capabilities by configuration.

A thermostat has exactly one fan-speed target, chosen once in the factory
(`_select_fan_speed`): the fan device's control if a fan device exists (a separate fan
entity therefore always wins), else the first climate role, else none. It is stored with
`features.set_fan_speed`; nothing downstream decides ownership. After every turn on of a
climate child, `ClimatePort` asks the control to re-apply the speed (many ACs reset it on a
mode change); the control acts only when it targets that same climate entity. With two
different climates the first climate role wins (heater, cooler, fan, dryer order); the other
one gets the fan speed by being configured as the `fan` role.

Detection runs at startup **and** is retried when the fan entity's state changes, so a fan
from an integration that connects late (ESPHome, MQTT) is picked up without a reload (#636).
A fan mode restored from a previous session is held until detection succeeds, then applied.

Test patterns for all of the above: `tests/test_fan_speed_control.py`.
