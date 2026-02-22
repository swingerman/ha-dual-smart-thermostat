---
description: Create a full stable release for the project. Optionally pass a title suffix (e.g., "Template Presets Fix") or extra notes.
---

# Full Release

Create a stable release for Dual Smart Thermostat.

## User Input

```text
$ARGUMENTS
```

Consider the user input above (if provided) for the release title or extra context.

## Workflow

Follow these steps in order:

### 1. Determine Version and Gather Changes

- Read the current version from `custom_components/dual_smart_thermostat/manifest.json`
- Find the last **stable** (non-prerelease) release: `gh release list --limit 20` and filter out pre-releases
- Verify the manifest version is higher than the last stable release; if not, ask the user
- Gather ALL commits since the last stable release:
  ```
  git log <last-stable-tag>..HEAD --oneline
  ```
- Also check beta release notes for this version to ensure nothing is missed

### 2. Verify Manifest

- Confirm `manifest.json` version matches the intended release version (without "beta")
- If it already matches (from a prior beta bump), no change needed
- If it needs updating, edit, commit (`chore: bump version to vX.Y.Z`), and push

### 3. Generate Release Notes

Write release notes following this **exact format and tone**:

```markdown
## 🎉 What's New in vX.Y.Z

One or two enthusiastic sentences summarizing the headline value of this release. Focus on what users gain — comfort, reliability, new capabilities. Be specific.

---

## ✨ New Features

### 🌀 Feature Title
**One bold sentence explaining the user-facing value.**

- Bullet points with details the user cares about
- Focus on what changed for THEM, not implementation details
- Include before/after if helpful

- Details: #issue1, #issue2

---

## 🐛 Bug Fixes

### 🔧 Fix Title (user-facing description)
Description of what was broken and how it affected users. Be enthusiastic that it's fixed — these matter to people!

**Example:** If applicable, show a concrete before/after scenario.

- Details: #issue1, #issue2

---

## 📊 By the Numbers

- **N new features** — brief labels
- **N bug fixes** — brief labels
- **N tests** — all passing
- **100% backward compatible** — no configuration changes needed (or note if there ARE changes)

---

## 🔄 Migration Guide

**Drop-in replacement.** No configuration changes required.

Or, if there ARE migration steps, list them clearly with examples.

---

## 💝 Support This Project

If this integration makes your home smarter and more comfortable, consider supporting development:

[![Donate](https://img.shields.io/badge/Donate-PayPal-yellowgreen?style=for-the-badge&logo=paypal)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=S6NC9BYVDDJMA&source=url)
[![coffee](https://www.buymeacoffee.com/assets/img/custom_images/black_img.png)](https://www.buymeacoffee.com/swingerman)

Your support helps maintain this integration and develop new features! ☕️

---

**Full Changelog**: https://github.com/swingerman/ha-dual-smart-thermostat/compare/<last-stable-tag>...vX.Y.Z

---

💙 **Enjoying this integration?** Help others discover it:
- ⭐ Star the repository
- 🐛 Report issues you encounter
- 💬 Share your success stories
- 📣 Recommend to the Home Assistant community
```

#### Writing Style Rules

- **User value first**: Lead every section with what the user gains, not what was changed in code
- **Enthusiastic but honest**: Be genuinely excited about fixes and features — users care about these
- **Concrete examples**: Use before/after scenarios to make impact clear
- **No jargon**: Avoid code-level details (class names, method names). Describe behavior
- **Emojis**: Use them for section headers as shown in the template — they make scanning easier
- **Donation buttons**: ALWAYS include both PayPal and Buy Me a Coffee — these are essential
- **Community CTA**: ALWAYS include the star/report/share section at the end
- **Omit empty sections**: If there are no new features, skip that section entirely. Same for bug fixes

### 4. Create the Release

Determine the release title:
- Format: `vX.Y.Z - Short Descriptive Title`
- Title should capture the headline feature or theme (e.g., "Fan Speed Control & Reliability Improvements")
- If user provided a title hint in arguments, use that

```bash
gh release create vX.Y.Z --target master --title "vX.Y.Z - Title" --notes "<generated notes>"
```

Note: Do NOT use `--prerelease` — this is a stable release.

### 5. Run Test Count

Before finalizing, run `./scripts/docker-test` to get the current passing test count for the "By the Numbers" section. If you already know the count from a recent run, use that.

### 6. Report

Show the user the release URL and a summary of what was released.
