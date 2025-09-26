# Home Assistant E2E Test Setup Documentation

This document describes how to set up a working Home Assistant environment for E2E testing, including how to bypass onboarding and create users.

## Current Working Setup

The working setup has been backed up to `backup/20250924_111836/` and includes:
- Completed onboarding (bypassed)
- User authentication configured
- Trusted networks enabled
- Custom component loaded

## Key Files for Onboarding Bypass

### 1. Onboarding Completion Marker
**File**: `ha_config/.storage/onboarding`
```json
{
  "version": 4,
  "minor_version": 1,
  "key": "onboarding",
  "data": {
    "done": [
      "user",
      "core_config", 
      "integration",
      "analytics",
      "integration",
      "core_config",
      "analytics"
    ]
  }
}
```

### 2. User Authentication
**File**: `ha_config/.storage/auth`
Contains user data with proper authentication setup.

## Setup Steps

### Step 1: Start Home Assistant
```bash
cd tests/e2e
npm run ha:start
npm run ha:wait
```

### Step 2: Create User and Bypass Onboarding
```bash
# Create a test user
docker compose exec homeassistant ha auth create --username testuser --password testpass123 --name "Test User"

# Create onboarding completion marker
docker compose exec homeassistant bash -c "cat > /config/.storage/onboarding << 'EOF'
{
  \"version\": 4,
  \"minor_version\": 1,
  \"key\": \"onboarding\",
  \"data\": {
    \"done\": [
      \"user\",
      \"core_config\",
      \"integration\", 
      \"analytics\",
      \"integration\",
      \"core_config\",
      \"analytics\"
    ]
  }
}
EOF"
```

### Step 3: Restart Home Assistant
```bash
npm run ha:restart
npm run ha:wait
```

### Step 4: Verify Setup
```bash
# Check that HA is accessible without onboarding
curl -s http://localhost:8123/ | grep -q "Home Assistant" && echo "✅ HA accessible" || echo "❌ HA not accessible"

# Check integrations page
curl -s http://localhost:8123/config/integrations | grep -q "Add Integration" && echo "✅ Integrations page ready" || echo "❌ Integrations page not ready"
```

## Configuration Files

### Trusted Networks (configuration.yaml)
```yaml
homeassistant:
  auth_providers:
    - type: trusted_networks
      trusted_networks:
        - 127.0.0.1
        - ::1
        - 172.16.0.0/12  
        - 192.168.0.0/16
        - 10.0.0.0/8
        - 192.168.65.0/24  # Docker Desktop network
        - 0.0.0.0/0  # Allow all IPs for E2E testing (DANGEROUS - testing only!)
      allow_bypass_login: true
    - type: homeassistant
```

## Testing the Setup

### Run Config Flow Tests
```bash
npm run test:chromium
```

### Expected Results
- Tests should navigate to `/config/integrations` without onboarding
- "Add Integration" button should be visible
- Integration search should work
- Config flow should start properly

## Troubleshooting

### If Onboarding Still Appears
1. Check that `.storage/onboarding` file exists and has correct content
2. Restart Home Assistant: `npm run ha:restart`
3. Clear browser cache and cookies

### If Authentication Issues
1. Verify trusted networks configuration
2. Check that user was created: `docker compose exec homeassistant ha auth list`
3. Ensure `allow_bypass_login: true` is set

### If Integration Not Found
1. Verify custom component is loaded: check `custom_components/dual_smart_thermostat/`
2. Check HA logs: `npm run ha:logs`
3. Restart HA to reload components

## CI/CD Application

The same steps can be applied in GitHub Actions:
1. Start HA with health checks
2. Create user with HA CLI
3. Create onboarding completion marker
4. Run tests

This approach is cleaner than handling onboarding in test code.
