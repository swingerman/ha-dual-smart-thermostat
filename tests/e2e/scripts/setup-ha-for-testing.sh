#!/bin/bash

# Setup Home Assistant for E2E testing
# This script creates a user and bypasses onboarding

set -e

echo "🔧 Setting up Home Assistant for E2E testing..."

# Wait for HA to be ready
echo "⏳ Waiting for Home Assistant to be ready..."
for i in {1..60}; do
  if curl -f http://localhost:8123/manifest.json >/dev/null 2>&1; then
    break
  fi
  echo "  Waiting for HA manifest endpoint... ($i/60)"
  sleep 5
done

echo "✅ Home Assistant is ready!"

# Create onboarding completion marker using Python script
echo "🚀 Bypassing onboarding..."
docker compose -f docker-compose.local.yml exec homeassistant python3 /config/scripts/setup-ha.py || {
  echo "⚠️ Onboarding bypass failed, but continuing..."
}

# Restart HA to apply changes
echo "🔄 Restarting Home Assistant..."
docker compose -f docker-compose.local.yml restart homeassistant

# Wait for HA to be ready again
echo "⏳ Waiting for Home Assistant to restart..."
for i in {1..60}; do
  if curl -f http://localhost:8123/manifest.json >/dev/null 2>&1; then
    break
  fi
  echo "  Waiting for HA to restart... ($i/60)"
  sleep 5
done

echo "✅ Home Assistant setup complete!"

# Verify setup
echo "🔍 Verifying setup..."
if curl -s http://localhost:8123/ | grep -q "Home Assistant"; then
  echo "✅ HA accessible"
else
  echo "❌ HA not accessible"
  exit 1
fi

if curl -s http://localhost:8123/config/integrations | grep -q "Add Integration"; then
  echo "✅ Integrations page ready"
else
  echo "❌ Integrations page not ready"
  exit 1
fi

echo "🎉 Setup complete! Ready for E2E testing."
