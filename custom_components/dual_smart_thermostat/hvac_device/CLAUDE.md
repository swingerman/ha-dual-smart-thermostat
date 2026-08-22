# Fan device notes

## Speed control

Capability detection is automatic (`_detect_fan_capabilities`): `fan`-domain entities with
`preset_modes` use those, ones exposing `percentage` fall back to a fixed
`auto/low/medium/high` mapping, and `switch`-domain fans get no speed control at all. This
is deliberate - there is no way to override the detected capabilities by configuration.

Detection runs at startup **and** is retried when the fan entity's state changes, so a fan
from an integration that connects late (ESPHome, MQTT) is picked up without a reload (#636).
A fan mode restored from a previous session is held until detection succeeds, then applied.

Test patterns for all of the above: `tests/test_fan_speed_control.py`.
