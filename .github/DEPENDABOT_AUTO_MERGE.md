# Dependabot Auto-Merge Configuration

This repository has been configured with automated Dependabot dependency updates and auto-merge functionality.

## Overview

The auto-merge system automatically merges Dependabot pull requests that meet specific safety criteria, reducing manual maintenance overhead while maintaining code quality and security.

## Configuration Files

### 1. Dependabot Configuration (`.github/dependabot.yml`)
- **GitHub Actions**: Weekly updates with proper commit message formatting
- **Python Dependencies**: Weekly updates with safety exclusions
- **Excluded Packages**: Home Assistant, major version updates for critical tools
- **Commit Messages**: Standardized with "chore" prefix and scope

### 2. Auto-Merge Workflow (`.github/workflows/dependabot-auto-merge.yml`)
- **Trigger**: Only on Dependabot PRs
- **Safety Checks**: Version analysis, critical package detection
- **Quality Gates**: Linting, testing, and code quality checks
- **Merge Strategy**: Squash merge with standardized commit messages

### 3. Enhanced Security Checks (`.github/workflows/security-check.yml`)
- **Security Scanning**: Safety, Bandit, Semgrep
- **Dependency Auditing**: pip-audit for vulnerability detection
- **Code Quality**: Radon complexity analysis, maintainability metrics
- **Schedule**: Weekly automated security scans

## Auto-Merge Criteria

### ✅ Safe to Auto-Merge
- **Patch/Minor Updates**: Only version updates that don't change major version
- **Non-Critical Packages**: Excludes core development tools and Home Assistant
- **Passing Checks**: All linting, testing, and quality checks must pass
- **Standard Dependencies**: Regular Python packages and GitHub Actions

### ❌ Manual Review Required
- **Major Version Updates**: Any dependency with breaking changes
- **Critical Packages**: pytest, black, isort, sonarcloud, homeassistant
- **Failing Checks**: Any linting, testing, or quality check failures
- **Security Issues**: Any detected vulnerabilities or security concerns

## Workflow Integration

### Build Workflows Enhanced
1. **Linting Workflow**: Added Flake8 and MyPy checks
2. **Testing Workflow**: Enhanced with coverage reporting and artifacts
3. **Security Workflow**: Comprehensive security and quality scanning
4. **E2E Workflow**: Maintained existing end-to-end testing

### Quality Gates
- **Linting**: isort, black, flake8, mypy
- **Testing**: pytest with coverage reporting
- **Security**: Safety, Bandit, Semgrep, pip-audit
- **Quality**: Radon complexity, Xenon maintainability

## Monitoring and Notifications

### PR Comments
The auto-merge workflow automatically comments on Dependabot PRs with:
- ✅ **Success**: Auto-merge approved and completed
- ❌ **Skipped**: Manual review required (with reasons)
- ❌ **Failed**: Checks did not pass (with details)

### Artifacts
- **Coverage Reports**: HTML and XML coverage reports
- **Security Reports**: JSON reports from all security tools
- **Quality Reports**: Complexity and maintainability metrics

## Manual Override

### Disabling Auto-Merge
To disable auto-merge for a specific PR:
1. Add the label `no-auto-merge` to the PR
2. Comment with `@dependabot ignore this dependency` for permanent exclusion

### Emergency Stop
To temporarily disable all auto-merge:
1. Add the `dependabot-auto-merge-disabled` label to the repository
2. Or modify the workflow file to add a condition

## Security Considerations

### Protected Updates
- **Home Assistant**: Never auto-updated (matches HACS requirements)
- **Testing Tools**: Major version updates require manual review
- **Security Tools**: All security-related updates require approval

### Vulnerability Response
- **Critical Vulnerabilities**: Auto-merge may be temporarily disabled
- **Security Alerts**: All security scans run on every PR
- **Audit Reports**: Weekly dependency vulnerability scanning

## Maintenance

### Regular Tasks
- **Weekly Security Scans**: Automated vulnerability detection
- **Quality Reports**: Code complexity and maintainability tracking
- **Dependency Updates**: Automated with safety checks

### Manual Reviews
- **Major Updates**: All major version changes require manual approval
- **Critical Dependencies**: Core development tools need human oversight
- **Security Issues**: Any detected vulnerabilities require investigation

## Troubleshooting

### Common Issues
1. **Auto-merge Skipped**: Check PR title format and package exclusions
2. **Checks Failing**: Review linting, testing, or security scan results
3. **Merge Conflicts**: Resolve conflicts and re-run checks

### Debug Information
- **Workflow Logs**: Check GitHub Actions logs for detailed information
- **PR Comments**: Auto-generated status comments explain decisions
- **Artifacts**: Download reports for detailed analysis

## Best Practices

### For Maintainers
- **Review Weekly**: Check security scan results and quality reports
- **Monitor Alerts**: Respond to security alerts and vulnerability reports
- **Update Exclusions**: Modify dependabot.yml for new critical dependencies

### For Contributors
- **Dependency Updates**: Most updates are automated, focus on feature development
- **Security Issues**: Report any security concerns immediately
- **Quality Gates**: Ensure code passes all automated checks

## Configuration Customization

### Adding Exclusions
Edit `.github/dependabot.yml` to add new packages to ignore:
```yaml
ignore:
  - dependency-name: "package-name"
    update-types: ["version-update:semver-major"]
```

### Modifying Safety Checks
Edit `.github/workflows/dependabot-auto-merge.yml` to adjust safety criteria:
```yaml
DANGEROUS_PACKAGES=("package1" "package2")
```

### Updating Quality Gates
Modify workflow files to add or remove quality checks as needed.

---

*This configuration provides a balance between automation and safety, ensuring dependencies stay updated while maintaining code quality and security.*