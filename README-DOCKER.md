# Docker-Based Development Workflow

This guide explains how to use Docker for development, testing, and linting without opening the VS Code devcontainer. This approach is ideal for CI/CD, testing with different Home Assistant versions, or working outside of VS Code.

## Overview

The Docker-based workflow provides:
- **Isolated environment** - Consistent development environment across all systems
- **Version flexibility** - Test with different Home Assistant versions easily
- **No VS Code required** - Run commands and view logs from your terminal
- **Fast iteration** - Volume mounts for live code reloading
- **CI/CD ready** - Same environment used locally and in CI/CD pipelines

## Prerequisites

- Docker Desktop or Docker Engine installed
- Docker Compose (included with Docker Desktop)
- Basic familiarity with Docker concepts

## Quick Start

### 1. Build the Development Image

```bash
# Build with default Home Assistant version (2025.1.0)
docker-compose build dev

# Or build with a specific version
HA_VERSION=2025.2.0 docker-compose build dev
```

### 2. Run Tests

```bash
# Run all tests
./scripts/docker-test

# Run specific test file
./scripts/docker-test tests/test_heater_mode.py

# Run tests matching a pattern
./scripts/docker-test -k "test_heating"

# Run with coverage report
./scripts/docker-test --cov
```

### 3. Run Linting

```bash
# Check all linting rules (isort, black, flake8, codespell, ruff)
./scripts/docker-lint

# Auto-fix issues where possible
./scripts/docker-lint --fix
```

### 4. Interactive Shell

```bash
# Open bash shell in container
./scripts/docker-shell

# Open Python REPL
./scripts/docker-shell python
```

## Detailed Usage

### Building with Different Home Assistant Versions

You can test your integration with different Home Assistant versions by setting the `HA_VERSION` build argument:

```bash
# Test with HA 2025.1.0
HA_VERSION=2025.1.0 docker-compose build dev

# Test with HA 2025.2.0
HA_VERSION=2025.2.0 docker-compose build dev

# Test with latest HA (whatever is currently published)
HA_VERSION=latest docker-compose build dev
```

After building with a specific version, all commands (`docker-test`, `docker-lint`, etc.) will use that version until you rebuild.

### Running Tests

The `docker-test` script is a wrapper around `pytest` that runs in the Docker container:

```bash
# Run all tests
./scripts/docker-test

# Run specific test directory
./scripts/docker-test tests/config_flow/

# Run specific test file
./scripts/docker-test tests/test_heater_mode.py

# Run specific test function
./scripts/docker-test tests/test_heater_mode.py::test_heater_mode_on

# Run tests matching pattern
./scripts/docker-test -k "heater"

# Run with verbose output
./scripts/docker-test -v

# Run with debug logging
./scripts/docker-test --log-cli-level=DEBUG

# Run with coverage report
./scripts/docker-test --cov

# Generate HTML coverage report
./scripts/docker-test --cov --cov-report=html
```

### Running Linting

The `docker-lint` script runs all linting checks required before committing:

```bash
# Check all linting rules
./scripts/docker-lint

# Auto-fix issues (isort, black, ruff)
./scripts/docker-lint --fix
```

The linting checks include:
- **isort** - Import sorting
- **black** - Code formatting (88 character line length)
- **flake8** - Style/linting
- **codespell** - Spell checking
- **ruff** - Modern Python linter

### Interactive Development

Open an interactive shell in the container for manual testing and debugging:

```bash
# Open bash shell
./scripts/docker-shell

# Inside the container, you can run any command:
pytest tests/test_heater_mode.py -v
python -m pytest --collect-only
hass --version
```

### Direct Docker Compose Commands

You can also use `docker-compose` directly for more control:

```bash
# Run any command in the dev container
docker-compose run --rm dev <command>

# Examples:
docker-compose run --rm dev pytest
docker-compose run --rm dev black .
docker-compose run --rm dev python -c "import homeassistant; print(homeassistant.__version__)"

# Keep container running in background
docker-compose up -d dev

# View logs
docker-compose logs -f dev

# Stop containers
docker-compose down
```

## Configuration Directory Mounting

### Important: `/config` Folder for Home Assistant

The Docker setup properly mounts the `./config` directory to `/config` inside the container. This is **required** for Home Assistant to function correctly:

```yaml
# In docker-compose.yml
volumes:
  - .:/workspace:rw          # Source code (read-write)
  - ./config:/config:rw      # HA config directory (read-write)
```

**What this means:**
- Home Assistant stores its configuration in `/config`
- The `./config` directory in your project root is mounted to `/config` in the container
- Any changes in the container's `/config` are reflected in your local `./config` folder
- Scripts like `scripts/develop` that run Home Assistant will use this config directory

**First-time setup:**
The `./config` directory will be created automatically when you first run Home Assistant in the container. If you need to initialize it manually:

```bash
./scripts/docker-shell
# Inside container:
mkdir -p /config
hass --script ensure_config -c /config
```

### Running Home Assistant Development Server

To run a full Home Assistant instance with your integration:

```bash
# Open shell in container
./scripts/docker-shell

# Inside container, run the development server
bash scripts/develop
```

Or run directly:

```bash
docker-compose run --rm -p 8123:8123 dev bash scripts/develop
```

This will:
1. Create `/config` if it doesn't exist
2. Initialize Home Assistant configuration
3. Start Home Assistant on port 8123
4. Mount your integration at `/workspace`

Access Home Assistant at http://localhost:8123

### Optional: Full Home Assistant Service

If you want to run a complete Home Assistant instance alongside your development container, uncomment the `homeassistant` service in `docker-compose.yml`:

```yaml
homeassistant:
  image: ghcr.io/home-assistant/home-assistant:${HA_VERSION:-2025.1}
  container_name: dual_thermostat_homeassistant
  volumes:
    - ./config:/config:rw
    - ./custom_components/dual_smart_thermostat:/config/custom_components/dual_smart_thermostat:ro
  ports:
    - "8123:8123"
  environment:
    - TZ=UTC
  restart: unless-stopped
```

Then run:

```bash
# Start Home Assistant service
docker-compose up -d homeassistant

# View logs
docker-compose logs -f homeassistant

# Stop service
docker-compose down
```

## Volume Mounts and Caching

The Docker setup uses several volume mounts for performance and convenience:

### Source Code Mounting
```yaml
- .:/workspace:rw
```
Your source code is mounted as read-write, so changes you make locally are immediately reflected in the container (no rebuild needed).

### Config Directory
```yaml
- ./config:/config:rw
```
Home Assistant configuration directory, shared between your local system and the container.

### Cache Volumes
```yaml
- pip-cache:/root/.cache/pip        # Speeds up pip installs
- pytest-cache:/workspace/.pytest_cache  # Speeds up pytest
- mypy-cache:/workspace/.mypy_cache      # Speeds up mypy
```

These named volumes persist between container runs, making subsequent test/lint runs faster.

## Troubleshooting

### Build Issues

**Problem:** Build fails with dependency errors

```bash
# Clean build (no cache)
docker-compose build --no-cache dev

# Check which HA version is installed
docker-compose run --rm dev python -c "import homeassistant; print(homeassistant.__version__)"
```

**Problem:** `pypcap` installation fails

This is expected on Python 3.13 and is not critical for most integration functionality. The build will continue with a warning.

### Test Issues

**Problem:** Tests fail due to import errors

```bash
# Verify Python path
docker-compose run --rm dev python -c "import sys; print(sys.path)"

# Verify custom_components is accessible
docker-compose run --rm dev ls -la custom_components/
```

**Problem:** Tests are slow

Ensure you've built the image (don't use `--build` on every run):

```bash
# Bad (rebuilds every time):
docker-compose run --build dev pytest

# Good (reuses built image):
docker-compose run --rm dev pytest
```

### Permission Issues

**Problem:** Permission denied errors on Linux

Docker Desktop on macOS/Windows handles permissions automatically. On Linux, you may need to adjust the `Dockerfile.dev` to use a non-root user matching your host UID/GID.

### Config Directory Issues

**Problem:** Home Assistant can't find configuration

Ensure the config directory is properly mounted:

```bash
# Check mount inside container
docker-compose run --rm dev ls -la /config

# Check local directory exists
ls -la config/
```

**Problem:** Config changes aren't persisting

Verify the mount is read-write (`:rw`) in `docker-compose.yml`.

### Image Size Issues

**Problem:** Docker image is too large

The development image includes all testing/linting dependencies and can be 1-2GB. To reduce size:

1. Use `.dockerignore` to exclude unnecessary files (already configured)
2. Use multi-stage builds (future improvement)
3. Prune old images: `docker system prune -a`

## Comparison: Docker vs DevContainer

| Feature | Docker (this setup) | DevContainer |
|---------|-------------------|-------------|
| **IDE Required** | No | Yes (VS Code) |
| **Version Testing** | Easy (build args) | Harder (edit .devcontainer.json) |
| **CI/CD** | Perfect | Not designed for CI/CD |
| **Logs/Commands** | Terminal-based | VS Code integrated |
| **Setup Time** | Fast (one build) | Slower (VS Code startup) |
| **Interactive Dev** | Via `docker-shell` | Native VS Code experience |

**Use Docker when:**
- Running CI/CD pipelines
- Testing with multiple HA versions
- Working without VS Code
- Automating tests/linting

**Use DevContainer when:**
- Doing interactive development in VS Code
- Want IDE integration (debugging, IntelliSense)
- Prefer GUI tools over terminal

**Both approaches work together** - use DevContainer for daily development and Docker for testing/CI/CD.

## Advanced Usage

### Custom Python Versions

```bash
# Build with Python 3.12
PYTHON_VERSION=3.12 docker-compose build dev
```

### Multiple Versions in Parallel

Test with multiple HA versions simultaneously:

```bash
# Terminal 1: Test with HA 2025.1.0
HA_VERSION=2025.1.0 docker-compose build dev
./scripts/docker-test

# Terminal 2: Test with HA 2025.2.0
HA_VERSION=2025.2.0 docker-compose build dev
./scripts/docker-test
```

### Pre-commit Hooks in Docker

Run pre-commit hooks using Docker:

```bash
docker-compose run --rm dev pre-commit run --all-files
```

### Running Security Scans

```bash
# Run bandit security scanner
docker-compose run --rm dev bandit -r custom_components/

# Run safety checker
docker-compose run --rm dev safety check

# Run pip-audit
docker-compose run --rm dev pip-audit
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Docker Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        ha-version: ['2025.1.0', '2025.2.0']
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: |
          HA_VERSION=${{ matrix.ha-version }} docker-compose build dev
      - name: Run tests
        run: ./scripts/docker-test --cov
      - name: Run linting
        run: ./scripts/docker-lint
```

## File Structure

```
dual_smart_thermostat/
├── Dockerfile.dev              # Development Docker image
├── docker-compose.yml          # Docker Compose configuration
├── .dockerignore              # Files excluded from Docker builds
├── config/                    # Home Assistant config directory (auto-created)
├── scripts/
│   ├── docker-test           # Test runner script
│   ├── docker-lint           # Linting script
│   └── docker-shell          # Interactive shell script
└── README-DOCKER.md          # This file
```

## Additional Resources

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [pytest Documentation](https://docs.pytest.org/)
- [Project CLAUDE.md](./CLAUDE.md) - Development guidelines

## Getting Help

If you encounter issues:

1. Check this README's Troubleshooting section
2. Verify your Docker installation: `docker --version && docker-compose --version`
3. Rebuild from scratch: `docker-compose build --no-cache dev`
4. Check Docker logs: `docker-compose logs dev`
5. Open an issue on GitHub with:
   - Your OS and Docker version
   - The command you ran
   - Full error output
   - Output of `docker-compose config`
