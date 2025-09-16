# ha-dual-smart-thermostat Constitution

## Core Principles

### I. Integration-first, library-friendly
All features should be developed with a clear, testable boundary so they can be exercised independently and reused where reasonable. New functionality should favour small, well-scoped modules (files, helper functions, classes) and avoid cross-cutting global state. Public helpers and constants should live in clearly named modules (for example, `schema_utils`, `const`, `feature_steps`).

### II. User-focused UX parity (Config vs Options)
Config flow and options flow must provide consistent experiences. Schema factories and shared selector helpers should be the single source of truth for UI fields and defaults to avoid divergence between initial install and later options editing.

### III. Test-first and CI-gated
Every behavioral change must have at least one test (unit/integration) that documents expected behavior. New features require tests covering happy path and 1-2 edge cases. The repository must remain green on CI for a PR to be merged.

### IV. Contracted Integration with Home Assistant
Respect Home Assistant APIs and selector primitives (domain selectors, number/text/select helpers). Avoid over-restrictive filters in selectors that prevent legitimate entities from being chosen by users. Where defaults exist, mirror them between config and options flows.

### V. Simplicity, Observability, and Safety
Keep integrations small and readable. Add logging for important state transitions. Fail gracefully in flows (validate inputs, provide helpful error messages). Prefer explicit configuration migrations over silent breaking changes.

## Additional Constraints

- Language: Python 3.13+ (as required by Home Assistant). Keep dependency list minimal and pinned in `requirements.txt`.
- Tests: Use `pytest` and Home Assistant test helpers provided in the repo. Tests must not rely on external network resources.
- No secrets in repo: Do not commit credentials or tokens. Use placeholders and document how to supply secrets in local development.

## Development Workflow and Quality Gates

- Branching: Work on feature branches; open PRs against `master` (default branch) with a clear summary and test results.
- CI: All PRs must pass linting, type checks (if applicable), and the test suite. Fast pre-merge checks should include the focused test files touched by the PR.
- Reviews: At least one approving review required. Large or risky changes should include a migration plan and changelog entry.

## Governance

- The constitution governs repository-level expectations. Amendments require a PR that updates this file and references the reason for change.
- The repository owner or maintainers may veto changes that break the CI or reduce test coverage.

**Version**: 1.0.0 | **Ratified**: 2025-09-15 | **Last Amended**: 2025-09-15