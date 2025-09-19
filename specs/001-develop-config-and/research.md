# Research: Implementing Config & Options Flow (dual_smart_thermostat)

## Purpose
Capture context, prior work, and risks before implementing the remaining system types and validating the flows.

## Current status (provided)
- `simple_heater` system: implemented and tested
- `ac_only` system: implemented and tested
- `heater_with_cooler` system: implementation in progress
- `heat_pump` system: not implemented / not verified
- Configurable feature steps already separated; need verification against spec
- English translations are present for the first two implemented system types
- Three main steps implemented but need a code-quality and spec-compliance review

## Goals
- Implement remaining system types incrementally (one system type per iteration)
- Ensure config flow and options flow parity, including defaults and selectors
- Verify feature step ordering (openings before presets) and non-blocking ordering guidance
- Provide tests for each system type and for each configurable feature module

## Constraints & Principles
- Follow the repository constitution: small modules, single source of truth for schemas, test-first approach, Home Assistant selector primitives.
- No backward-compatibility migration required for the initial release.

## Risks
- Selector filters too strict (will hide valid entities) — mitigate by using domain-only selectors.
- Ordering vs dependency UX: ensure clear messaging and validation while avoiding hard blocks.
- Missing tests for option flow parity — mitigate by adding focused tests per feature.

## References
- Feature spec: `/workspaces/dual_smart_thermostat/specs/001-develop-config-and/spec.md`
