import re

from custom_components.dual_smart_thermostat import schemas
from custom_components.dual_smart_thermostat.const import (
    CONF_HEAT_COOL_MODE,
    CONF_TARGET_TEMP_HIGH,
    CONF_TARGET_TEMP_LOW,
)


def name_of(k):
    if isinstance(k, str):
        return k
    s = str(k)
    m = re.search(r"['\"](.+?)['\"]", s)
    return m.group(1) if m else s


def test_get_presets_schema_single_mode():
    # heat_cool_mode disabled -> single temp field per preset
    # select at least one preset so schema produces fields
    user_input = {CONF_HEAT_COOL_MODE: False, "presets": ["away"]}
    schema = schemas.get_presets_schema(user_input)

    # Extract underlying mapping from voluptuous Schema
    mapping = getattr(schema, "schema", None) or schema
    if hasattr(mapping, "keys"):
        keys = list(mapping.keys())
    else:
        # As a last resort, attempt to call the schema with an empty dict
        try:
            keys = list(schema({}).keys())
        except Exception:
            keys = []

    # Normalize key names (voluptuous Optional objects -> their inner string)
    def name_of(k):
        if isinstance(k, str):
            return k
        s = str(k)
        m = re.search(r"['\"](.+?)['\"]", s)
        return m.group(1) if m else s

    names = [name_of(k) for k in keys]

    # keys should include the single temp for each preset in defaults
    assert any(n.endswith("_temp") and not n.endswith("_temp_low") for n in names)


def test_get_presets_schema_range_mode():
    # heat_cool_mode enabled -> low/high fields per preset
    user_input = {CONF_HEAT_COOL_MODE: True, "presets": ["away"]}
    schema = schemas.get_presets_schema(user_input)

    mapping = getattr(schema, "schema", None) or schema
    if hasattr(mapping, "keys"):
        keys = list(mapping.keys())
    else:
        try:
            keys = list(schema({}).keys())
        except Exception:
            keys = []

    names = [name_of(k) for k in keys]

    # Expect at least one low/high pair exists
    assert any(n.endswith("_temp_low") for n in names)
    assert any(n.endswith("_temp_high") for n in names)


def test_get_presets_schema_range_mode_inferred_from_target_range():
    # No explicit heat_cool_mode flag, but target ranges configured (e.g.
    # AC-only running in range mode) -> low/high fields must be rendered so
    # presets can be configured as ranges (issue #592).
    user_input = {
        CONF_TARGET_TEMP_LOW: 20,
        CONF_TARGET_TEMP_HIGH: 24,
        "presets": ["away"],
    }
    schema = schemas.get_presets_schema(user_input)

    mapping = getattr(schema, "schema", None) or schema
    if hasattr(mapping, "keys"):
        keys = list(mapping.keys())
    else:
        try:
            keys = list(schema({}).keys())
        except Exception:
            keys = []

    names = [name_of(k) for k in keys]

    assert any(n.endswith("_temp_low") for n in names)
    assert any(n.endswith("_temp_high") for n in names)
