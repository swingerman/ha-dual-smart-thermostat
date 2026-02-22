---
description: Create a beta pre-release for the project. Optionally pass a version hint (e.g., "patch", "minor") or specific notes.
---

# Beta Release

Create a beta pre-release for Dual Smart Thermostat.

## User Input

```text
$ARGUMENTS
```

Consider the user input above (if provided) for version hints or extra release notes.

## Workflow

Follow these steps in order:

### 1. Determine Version

- Read the current version from `custom_components/dual_smart_thermostat/manifest.json`
- List recent GitHub releases with `gh release list --limit 10`
- Determine the next version:
  - If there are already beta releases for a version **higher** than the latest stable release, increment the beta number (e.g., `v0.11.3-beta1` → `v0.11.3-beta2`)
  - If the manifest version matches the latest stable release, bump the **patch** version (e.g., `v0.11.2` → `v0.11.3`) unless user requests a minor bump
- **CRITICAL**: The manifest version must NOT contain "beta" — only the clean version (e.g., `v0.11.3`), otherwise the hassfest workflow will fail

### 2. Bump Manifest (if needed)

If the manifest version needs to change:
- Edit `custom_components/dual_smart_thermostat/manifest.json` to update the `"version"` field
- Commit: `chore: bump version to vX.Y.Z`
- Push to master

### 3. Generate Release Notes

Gather commits since the last release (stable or beta) using:
```
git log <last-tag>..HEAD --oneline
```

Write concise release notes in this format:

```markdown
## What's New in vX.Y.Z-betaN

Brief one-line summary of what this beta includes.

### ✨ New Features

- Feature description focusing on user value (#issue)

### 🐛 Bug Fixes

- Fix description explaining what was wrong and what's now fixed (#issue)
```

Rules:
- Omit sections that have no entries (e.g., skip "New Features" if there are none)
- Focus on **user value**, not implementation details
- Reference issue numbers where applicable
- Keep it concise — beta notes are brief

### 4. Create the Release

```bash
gh release create vX.Y.Z-betaN --target master --prerelease --title "vX.Y.Z-betaN" --notes "<generated notes>"
```

### 5. Report

Show the user the release URL and a summary of what was released.
