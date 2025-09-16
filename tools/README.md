# Development Tools

This directory contains development and configuration tools for the Dual Smart Thermostat component.

## Configuration Dependency Tools

### `config_validator.py`
Validates thermostat configurations against critical parameter dependencies.

**Usage:**
```bash
# Run validation with test configurations
python tools/config_validator.py

# Validate a specific YAML config
python -c "
from tools.config_validator import validate_yaml_config
validate_yaml_config('''
name: Test Thermostat
heater: switch.heater
target_sensor: sensor.temperature
''')
"
```

**Features:**
- Validates 22 critical conditional dependencies
- Detects configuration conflicts
- Provides fix suggestions
- Analyzes feature groups

### `focused_config_dependencies.py`
Analysis script that generates the dependency data in `focused_config_dependencies.json`.

**Usage:**
```bash
# Regenerate dependency analysis
python tools/focused_config_dependencies.py
```

### `focused_config_dependencies.json`
Core dependency data containing:
- 22 conditional parameter dependencies
- Configuration examples for 6 feature groups
- Dependency relationships and validation rules

## Integration with Config Flow

To use these tools in the component's config flow:

```python
# In config_flow.py
from .tools.config_validator import ConfigValidator

validator = ConfigValidator()
is_valid, errors, warnings = validator.validate_config(user_input)
```

## Development Workflow

When adding new configuration parameters:

1. **Check dependencies**: Does the new parameter require another parameter?
2. **Update `focused_config_dependencies.json`**: Add new conditional dependencies
3. **Update `config_validator.py`**: Add validation rules
4. **Test validation**: Run `python tools/config_validator.py`
5. **Update documentation**: Update `docs/config/CRITICAL_CONFIG_DEPENDENCIES.md`

See the main [Copilot Instructions](../.copilot-instructions.md) for detailed development guidelines.
