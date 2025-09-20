#!/bin/bash

# Test runner script for dual-smart-thermostat E2E tests
# This script helps run tests both locally and provides Docker fallback
# Based on lovelace-fluid-level-background-card implementation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Default test type
TEST_TYPE="all"
FORCE_DOCKER=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --e2e)
            TEST_TYPE="e2e"
            shift
            ;;
        --all)
            TEST_TYPE="all"
            shift
            ;;
        --setup)
            TEST_TYPE="setup"
            shift
            ;;
        --cleanup)
            TEST_TYPE="cleanup"
            shift
            ;;
        --docker)
            FORCE_DOCKER=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--e2e|--all|--setup|--cleanup|--docker|--help]"
            echo ""
            echo "Options:"
            echo "  --e2e       Run only E2E tests"
            echo "  --all       Run all tests (same as --e2e for this project)"
            echo "  --setup     Setup test environment only"
            echo "  --cleanup   Cleanup test environment only"
            echo "  --docker    Use Docker for Home Assistant (recommended)"
            echo "  --help      Show this help message"
            echo ""
            echo "Environment Requirements:"
            echo "  For local HA: pip install homeassistant"
            echo "  For Docker:   docker and docker-compose"
            echo ""
            echo "Examples:"
            echo "  $0                    # Run all tests with Docker if available"
            echo "  $0 --e2e --docker     # Run E2E tests with Docker"
            echo "  $0 --setup            # Setup test environment only"
            exit 0
            ;;
        *)
            log_error "Unknown option $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    log_error "Node.js is not installed. Please install Node.js 18 or later."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    log_error "npm is not installed. Please install npm."
    exit 1
fi

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
E2E_DIR="$(dirname "$SCRIPT_DIR")"

# Change to E2E directory
cd "$E2E_DIR"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    log_info "Installing dependencies..."
    npm ci
fi

# Check Docker availability
DOCKER_AVAILABLE=false
if command -v docker &> /dev/null; then
    if docker info >/dev/null 2>&1; then
        if command -v docker-compose &> /dev/null || docker compose version &> /dev/null 2>&1; then
            DOCKER_AVAILABLE=true
        fi
    fi
fi

# Determine preferred method based on availability
USE_DOCKER=false
if [ "$FORCE_DOCKER" = true ]; then
    USE_DOCKER=true
    if [ "$DOCKER_AVAILABLE" = false ]; then
        log_error "Docker was requested but is not available or not running"
        exit 1
    fi
elif [ "$DOCKER_AVAILABLE" = true ]; then
    USE_DOCKER=true
    log_info "Docker available - using Docker for Home Assistant"
fi

# Setup test environment
setup_test_env() {
    log_info "Setting up test environment..."

    if [ "$USE_DOCKER" = true ]; then
        log_info "Starting test environment with Docker..."
        
        # Use local docker-compose file if it exists, otherwise fall back to main one
        COMPOSE_FILE="docker-compose.local.yml"
        if [ ! -f "$COMPOSE_FILE" ]; then
            COMPOSE_FILE="docker-compose.yml"
        fi
        
        if command -v docker-compose &> /dev/null; then
            docker-compose -f "$COMPOSE_FILE" up -d
        else
            docker compose -f "$COMPOSE_FILE" up -d
        fi

        # Wait for Home Assistant to be ready
        log_info "Waiting for Home Assistant to start..."
        
        # Cross-platform timeout implementation
        WAIT_TIMEOUT=180
        WAIT_COUNT=0
        
        until curl -f http://localhost:8123 >/dev/null 2>&1; do 
            echo "  Waiting for HA to respond... ($(date))"
            
            # Check timeout
            if [ $WAIT_COUNT -ge $WAIT_TIMEOUT ]; then
                log_error "Home Assistant failed to start within timeout ($WAIT_TIMEOUT seconds)"
                if command -v docker-compose &> /dev/null; then
                    docker-compose -f "$COMPOSE_FILE" logs
                else
                    docker compose -f "$COMPOSE_FILE" logs
                fi
                exit 1
            fi
            
            # Check if container is still running
            if ! docker ps | grep -q "homeassistant\|ha-"; then
                log_error "Home Assistant container is not running!"
                if command -v docker-compose &> /dev/null; then
                    docker-compose -f "$COMPOSE_FILE" logs homeassistant
                else
                    docker compose -f "$COMPOSE_FILE" logs homeassistant
                fi
                exit 1
            fi
            
            sleep 5
            WAIT_COUNT=$((WAIT_COUNT + 5))
        done

        # Additional check for trusted networks auth bypass
        log_info "Verifying trusted networks authentication bypass..."
        
        AUTH_WAIT_COUNT=0
        AUTH_TIMEOUT=30
        
        until curl -s http://localhost:8123/ | grep -q "Home Assistant" && ! curl -s http://localhost:8123/ | grep -q "auth"; do 
            if [ $AUTH_WAIT_COUNT -ge $AUTH_TIMEOUT ]; then
                log_warning "Could not verify auth bypass - tests may still work"
                break
            fi
            echo "  Waiting for trusted networks auth to activate..."
            sleep 3
            AUTH_WAIT_COUNT=$((AUTH_WAIT_COUNT + 3))
        done

        log_success "Docker test environment is ready!"
    else
        log_info "Starting Home Assistant locally..."
        
        # Check if Home Assistant is installed
        if ! command -v hass &> /dev/null; then
            log_error "Home Assistant not found. Please install it:"
            log_error "  pip install homeassistant"
            log_error "  OR use Docker: $0 --docker"
            exit 1
        fi
        
        # Start Home Assistant in background
        log_info "Starting Home Assistant with local script..."
        node scripts/test-setup.js &
        HASS_PID=$!

        # Wait for Home Assistant to be ready
        log_info "Waiting for Home Assistant to start..."
        
        LOCAL_WAIT_COUNT=0
        LOCAL_TIMEOUT=120
        
        until curl -f http://localhost:8123 >/dev/null 2>&1; do 
            if [ $LOCAL_WAIT_COUNT -ge $LOCAL_TIMEOUT ]; then
                log_error "Home Assistant failed to start within timeout"
                kill $HASS_PID 2>/dev/null || true
                exit 1
            fi
            echo "  Waiting for local HA to respond... ($(date))"
            sleep 5
            LOCAL_WAIT_COUNT=$((LOCAL_WAIT_COUNT + 5))
        done

        log_success "Local Home Assistant is ready!"
        echo "HASS_PID=$HASS_PID" > .hass_pid
    fi
}

# Cleanup test environment
cleanup_test_env() {
    log_info "Cleaning up test environment..."

    if [ "$USE_DOCKER" = true ]; then
        COMPOSE_FILE="docker-compose.local.yml"
        if [ ! -f "$COMPOSE_FILE" ]; then
            COMPOSE_FILE="docker-compose.yml"
        fi
        
        if command -v docker-compose &> /dev/null; then
            docker-compose -f "$COMPOSE_FILE" down -v >/dev/null 2>&1 || true
        else
            docker compose -f "$COMPOSE_FILE" down -v >/dev/null 2>&1 || true
        fi
    else
        # Kill local Home Assistant processes
        if [ -f ".hass_pid" ]; then
            HASS_PID=$(cat .hass_pid | grep HASS_PID | cut -d'=' -f2)
            if [ -n "$HASS_PID" ]; then
                kill $HASS_PID 2>/dev/null || true
            fi
            rm -f .hass_pid
        fi
        
        # Fallback: kill any remaining processes
        pkill -f "test-setup.js" 2>/dev/null || true
        pkill -f "hass.*ha_config" 2>/dev/null || true
    fi

    log_success "Cleanup complete!"
}

# Run E2E tests
run_e2e_tests() {
    log_info "Installing Playwright browsers if needed..."
    npx playwright install --with-deps >/dev/null 2>&1 || {
        log_warning "Playwright install failed - continuing anyway"
    }

    log_info "Running E2E tests..."
    
    # Set environment variables
    export CI=false  # Enable local-friendly settings
    
    # Run tests with appropriate reporter
    npx playwright test --reporter=list,html || {
        log_error "E2E tests failed!"
        log_info "Check test-results/ for detailed logs and screenshots"
        log_info "Open playwright-report/index.html for interactive report"
        return 1
    }
    
    log_success "E2E tests completed successfully!"
    log_info "View detailed report: npx playwright show-report"
}

# Main execution
case $TEST_TYPE in
    "setup")
        setup_test_env
        log_success "Environment setup complete! Home Assistant running at http://localhost:8123"
        log_info "Run 'npm test' to execute tests, or '$0 --cleanup' to stop"
        ;;
    "cleanup")
        cleanup_test_env
        ;;
    "e2e"|"all")
        log_info "Running E2E tests with $([ "$USE_DOCKER" = true ] && echo "Docker" || echo "local Home Assistant")..."

        # Setup environment
        setup_test_env
        
        # Ensure cleanup happens on exit
        trap cleanup_test_env EXIT

        # Run E2E tests
        if run_e2e_tests; then
            log_success "All tests completed successfully! 🎉"
        else
            log_error "Tests failed! Check the output above for details."
            exit 1
        fi
        ;;
    *)
        log_error "Unknown test type: $TEST_TYPE"
        exit 1
        ;;
esac