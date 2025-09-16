#!/bin/bash
set -e

# Regenerate Playwright E2E test baselines for Dual Smart Thermostat
# This script ensures Home Assistant is running and updates all visual baselines

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
E2E_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$(dirname "$E2E_DIR")")"

echo "🔧 Dual Smart Thermostat E2E Baseline Regeneration"
echo "========================================================"
echo "E2E Directory: $E2E_DIR"
echo "Project Root: $PROJECT_ROOT"
echo ""

# Change to E2E directory
cd "$E2E_DIR"

# Function to check if Home Assistant is responsive
check_ha_health() {
    echo "🏥 Checking Home Assistant health..."
    if curl -f -s http://localhost:8123/ > /dev/null 2>&1; then
        echo "✅ Home Assistant is responsive"
        return 0
    else
        echo "❌ Home Assistant is not responding"
        return 1
    fi
}

# Function to wait for Home Assistant to be ready
wait_for_ha() {
    echo "⏳ Waiting for Home Assistant to be ready..."
    local timeout=120
    local count=0
    
    while [ $count -lt $timeout ]; do
        if check_ha_health; then
            echo "✅ Home Assistant is ready!"
            return 0
        fi
        
        echo "   Waiting... ($((count + 5))/${timeout}s)"
        sleep 5
        count=$((count + 5))
    done
    
    echo "❌ Timeout waiting for Home Assistant"
    return 1
}

# Check if Docker Compose is available
if ! command -v docker &> /dev/null || ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker and docker-compose are required"
    exit 1
fi

# Start Home Assistant if not running
echo "🚀 Starting Home Assistant test environment..."
if docker compose ps | grep -q "ha-dual-smart-thermostat-e2e.*Up"; then
    echo "✅ Home Assistant container already running"
else
    echo "🔄 Starting Home Assistant container..."
    docker compose up -d
    echo "✅ Container started"
fi

# Wait for Home Assistant to be ready
if ! wait_for_ha; then
    echo "❌ Failed to start Home Assistant. Check container logs:"
    echo "   docker compose logs homeassistant"
    exit 1
fi

# Check if Node.js and npm are available
if ! command -v node &> /dev/null || ! command -v npm &> /dev/null; then
    echo "❌ Node.js and npm are required for Playwright"
    echo "   Please install Node.js v18 or higher"
    exit 1
fi

# Check if Playwright is installed
if [ ! -f "package.json" ]; then
    echo "📦 Creating package.json..."
    npm init -y > /dev/null 2>&1
fi

if ! npm list @playwright/test > /dev/null 2>&1; then
    echo "📦 Installing Playwright..."
    npm install -D @playwright/test
    npx playwright install
fi

# Clean existing baselines (optional - uncomment if you want clean regeneration)
# echo "🧹 Cleaning existing baselines..."
# find tests/ -name "*-snapshots" -type d -exec rm -rf {} + 2>/dev/null || true

# Regenerate all baselines
echo "📸 Regenerating visual baselines..."
echo "   This will update all screenshot comparisons"

if npx playwright test --update-snapshots; then
    echo "✅ Baselines regenerated successfully"
    
    # Show what was updated
    echo ""
    echo "📊 Updated baseline files:"
    find tests/ -name "*-snapshots" -type d | while read -r dir; do
        if [ -d "$dir" ]; then
            echo "   📁 $dir"
            find "$dir" -name "*.png" | head -5 | while read -r file; do
                echo "      📷 $(basename "$file")"
            done
            local count=$(find "$dir" -name "*.png" | wc -l)
            if [ "$count" -gt 5 ]; then
                echo "      ... and $((count - 5)) more files"
            fi
        fi
    done
    
    # Optional: Commit changes if in git repository
    if git rev-parse --git-dir > /dev/null 2>&1; then
        echo ""
        read -p "🤔 Commit updated baselines to git? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "📝 Committing baseline updates..."
            git add tests/
            if git commit -m "Update E2E test baselines"; then
                echo "✅ Baselines committed successfully"
            else
                echo "⚠️  No changes to commit (baselines unchanged)"
            fi
        else
            echo "⏭️  Skipping git commit"
        fi
    fi
    
else
    echo "❌ Failed to regenerate baselines"
    echo "   Check the test output above for errors"
    exit 1
fi

echo ""
echo "🎉 Baseline regeneration complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Review updated screenshots to ensure they look correct"
echo "   2. Run normal tests to verify: npx playwright test"
echo "   3. Commit changes if not already done"
echo ""
echo "📚 For more information, see: tests/e2e/README.md"