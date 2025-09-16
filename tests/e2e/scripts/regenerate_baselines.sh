#!/bin/bash

# Regenerate Baselines Script for Dual Smart Thermostat E2E Tests
# This script regenerates visual test baselines when UI changes are intentional

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
E2E_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}Dual Smart Thermostat E2E - Baseline Regeneration${NC}"
echo "=================================================="

# Function to check if Docker Compose is running
check_docker_compose() {
    echo -e "${YELLOW}Checking Docker Compose status...${NC}"
    cd "$E2E_DIR"
    
    if docker compose ps | grep -q "homeassistant.*Up.*healthy"; then
        echo -e "${GREEN}✓ Home Assistant container is running and healthy${NC}"
        return 0
    else
        echo -e "${RED}✗ Home Assistant container is not running or not healthy${NC}"
        return 1
    fi
}

# Function to start Docker Compose if not running
start_docker_compose() {
    echo -e "${YELLOW}Starting Home Assistant container...${NC}"
    cd "$E2E_DIR"
    
    docker compose up -d
    
    echo -e "${YELLOW}Waiting for Home Assistant to be healthy...${NC}"
    local max_attempts=60
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if docker compose ps | grep -q "homeassistant.*Up.*healthy"; then
            echo -e "${GREEN}✓ Home Assistant is ready!${NC}"
            return 0
        fi
        
        echo -n "."
        sleep 5
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}✗ Timeout waiting for Home Assistant to be healthy${NC}"
    docker compose logs homeassistant
    return 1
}

# Function to install Playwright if needed
install_playwright() {
    echo -e "${YELLOW}Checking Playwright installation...${NC}"
    cd "$E2E_DIR"
    
    if [ ! -d "node_modules" ] || [ ! -f "node_modules/.bin/playwright" ]; then
        echo -e "${YELLOW}Installing Playwright dependencies...${NC}"
        npm install
        npx playwright install
    else
        echo -e "${GREEN}✓ Playwright is already installed${NC}"
    fi
}

# Function to backup existing baselines
backup_baselines() {
    local baseline_dir="$E2E_DIR/test-results/baselines"
    
    if [ -d "$baseline_dir" ]; then
        local backup_dir="$E2E_DIR/test-results/baselines-backup-$(date +%Y%m%d-%H%M%S)"
        echo -e "${YELLOW}Backing up existing baselines to: ${backup_dir}${NC}"
        cp -r "$baseline_dir" "$backup_dir"
        echo -e "${GREEN}✓ Baselines backed up${NC}"
    else
        echo -e "${YELLOW}No existing baselines found, skipping backup${NC}"
    fi
}

# Function to regenerate baselines
regenerate_baselines() {
    echo -e "${YELLOW}Regenerating visual test baselines...${NC}"
    cd "$E2E_DIR"
    
    # Remove existing baselines
    if [ -d "test-results/baselines" ]; then
        rm -rf test-results/baselines
        echo -e "${YELLOW}Removed existing baselines${NC}"
    fi
    
    # Run tests with baseline update
    echo -e "${YELLOW}Running Playwright tests with --update-snapshots...${NC}"
    npx playwright test --update-snapshots
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Baselines regenerated successfully${NC}"
    else
        echo -e "${RED}✗ Failed to regenerate baselines${NC}"
        return 1
    fi
}

# Function to show baseline summary
show_baseline_summary() {
    local baseline_dir="$E2E_DIR/test-results/baselines"
    
    if [ -d "$baseline_dir" ]; then
        echo -e "${BLUE}Baseline Summary:${NC}"
        echo "=================="
        find "$baseline_dir" -name "*.png" | wc -l | xargs echo "Total baseline images:"
        
        echo -e "\n${BLUE}Baseline files by browser:${NC}"
        for browser in chromium firefox webkit; do
            local count=$(find "$baseline_dir" -path "*$browser*" -name "*.png" | wc -l)
            echo "$browser: $count images"
        done
        
        echo -e "\n${YELLOW}Baseline directory: ${baseline_dir}${NC}"
        echo -e "${YELLOW}Remember to commit these baselines to version control!${NC}"
    else
        echo -e "${RED}No baselines found${NC}"
    fi
}

# Main execution
main() {
    echo -e "${BLUE}Starting baseline regeneration process...${NC}"
    
    # Check if Docker Compose is running, start if needed
    if ! check_docker_compose; then
        if ! start_docker_compose; then
            echo -e "${RED}Failed to start Home Assistant container${NC}"
            exit 1
        fi
    fi
    
    # Install Playwright if needed
    install_playwright
    
    # Backup existing baselines
    backup_baselines
    
    # Regenerate baselines
    if regenerate_baselines; then
        show_baseline_summary
        echo -e "${GREEN}✅ Baseline regeneration completed successfully!${NC}"
        
        echo -e "\n${YELLOW}Next steps:${NC}"
        echo "1. Review the generated baselines in test-results/baselines/"
        echo "2. Run 'npx playwright test' to verify tests pass with new baselines"
        echo "3. Commit the new baselines to version control"
        echo "4. Consider running tests on different environments to ensure consistency"
    else
        echo -e "${RED}❌ Baseline regeneration failed${NC}"
        exit 1
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Regenerate visual test baselines for Dual Smart Thermostat E2E tests"
            echo ""
            echo "Options:"
            echo "  -h, --help     Show this help message"
            echo "  --no-backup    Skip backing up existing baselines"
            echo ""
            echo "This script will:"
            echo "1. Ensure Home Assistant container is running"
            echo "2. Install Playwright dependencies if needed"
            echo "3. Backup existing baselines (unless --no-backup)"
            echo "4. Regenerate all visual test baselines"
            echo "5. Show summary of generated baselines"
            exit 0
            ;;
        --no-backup)
            backup_baselines() { echo -e "${YELLOW}Skipping baseline backup as requested${NC}"; }
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run main function
main