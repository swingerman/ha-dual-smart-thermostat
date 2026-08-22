# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Assistant Dual Smart Thermostat - An enhanced thermostat component supporting multiple HVAC modes (heating, cooling, heat pump, fan, humidity control), advanced features (floor temperature control, window/door sensors, presets), and sophisticated control logic.

**Target**: Home Assistant 2026.3.2+ (dev/CI on 2026.7.4)
**Language**: Python 3.14

## Essential Commands

### Development with Docker (Recommended)

**IMPORTANT: For Claude Code development, always use Docker scripts for testing and linting to ensure consistent environment and avoid local Python dependency issues.**

The project provides convenient Docker scripts in the `scripts/` folder:

```bash
# Testing - Use docker-test for all test runs
./scripts/docker-test                              # Run all tests
./scripts/docker-test tests/test_heater_mode.py    # Run specific test file
./scripts/docker-test -k "heater"                  # Run tests matching pattern
./scripts/docker-test --cov                        # Run with coverage report
./scripts/docker-test --log-cli-level=DEBUG        # Run with debug logging

# Linting - Use docker-lint for all code quality checks (REQUIRED before commit)
./scripts/docker-lint                              # Check all linting (isort, black, flake8, codespell, ruff)
./scripts/docker-lint --fix                        # Auto-fix linting issues

# Interactive Shell - For debugging and exploration
./scripts/docker-shell                             # Open bash shell in container
./scripts/docker-shell python                      # Open Python REPL in container
```

### Without Docker

`pip install -r requirements-dev.txt && pre-commit install`, then the standard `pytest` /
`pre-commit` invocations. `README-DOCKER.md` covers pinning a specific HA version.

## Architecture Overview

### Modular Design Pattern

The codebase uses a **separation of concerns** architecture with distinct layers:

1. **Device Layer** (`hvac_device/`) - Hardware abstraction for different HVAC equipment types
2. **Manager Layer** (`managers/`) - Shared business logic (features, state, environment)
3. **Controller Layer** (`hvac_controller/`) - Orchestration between devices and managers
4. **Climate Entity** (`climate.py`) - Home Assistant integration interface

## Critical Development Rules

### Before You Write Code

1. State how you will verify this change (test, batch command, browser check, etc.)
2. Write the test verification step first
3. Then implement the code
4. Run verification and iterate until it passes

### Configuration Flow Integration

**CRITICAL**: Every added or modified configuration option MUST be integrated into the
appropriate configuration flows (config, reconfigure, and/or options). A parameter that
is not wired into a flow is unreachable for UI users.

Rule of thumb: needed during initial setup -> config + reconfigure flows; adjustable later
-> options flow; often both. Flow changes require tests in `tests/config_flow/`.

For the full procedure - which flow to update, how to add a step, validation, translations,
and a worked example - use the `config-flow-integration` skill.

### Configuration Dependencies

**CRITICAL**: A new parameter that requires another to work (e.g. `max_floor_temp` needs
`floor_sensor`) must be recorded in the dependency tracking - see the
`config-flow-integration` skill for the files to update and how to validate.

### Configuration Flow Step Ordering

**Openings and presets are always the last two steps** - they depend on every earlier
choice. Full dependency rules: `docs/config_flow/step_ordering.md`.

### Linting Requirements

Run `./scripts/docker-lint` before committing; CI rejects failures. The tool list and their
settings live in `.pre-commit-config.yaml` and `setup.cfg`.

## Testing Strategy

### Adding Tests

**DO NOT create standalone bug-fix test files.** Add cases to the existing consolidated
files instead - `tests/config_flow/` is organised by system type, not by bug.

`docs/TESTING.md` has the full decision tree for where a given test belongs.

### Running Tests

`./scripts/docker-test [pytest args]` and `./scripts/docker-lint [--fix]` pass arguments
through, so any pytest selector works. See `README-DOCKER.md` for the non-Docker path.

## Important Constraints

### Backward Compatibility
- Never break existing YAML configurations
- Configuration migrations must be handled gracefully
- State restoration must handle old and new formats

### Home Assistant Integration
- Use Home Assistant's async patterns (`async def`, `await`)
- Respect entity lifecycle (setup, update, remove)
- Follow Home Assistant coding standards

### Device Safety
- Always check device availability before operations
- Handle sensor failures gracefully (stale detection)
- Respect min cycle durations to prevent equipment damage
- Floor temperature limits prevent overheating

## Special Considerations

### Heat Pump Mode
Single switch controls both heating and cooling based on `heat_pump_cooling` sensor state. Requires careful state tracking.

### Two-Stage Heating
Secondary heater activates after timeout if primary heater runs continuously. Day-based memory prevents premature secondary activation.

### Floor Temperature Protection
Min/max floor temperature limits prevent damage. These limits can be set globally and overridden per preset.

### Opening Detection
Window/door sensors pause HVAC operation. Supports timeout and closing_timeout for debouncing. Scope can be limited to specific HVAC modes.

### Preset Modes
Temperature/humidity presets depend on all other configuration. Must be configured last in flow.

### Fan Speed Control

Automatic capability detection drives variable-speed fan support. Design trade-offs and
test patterns live in `custom_components/dual_smart_thermostat/hvac_device/CLAUDE.md`,
loaded automatically when working in that directory.

## Releases

While writing releases, focus on user value and key changes. Avoid technical jargon unless necessary.

## Local Environment

The dev Home Assistant instance stores its config registry at
`config/.storage/core.config_entries` - useful when debugging config-flow persistence.
