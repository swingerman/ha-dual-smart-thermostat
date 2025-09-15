#!/usr/bin/env bash
# Install system dependencies needed by Home Assistant dev environment inside the devcontainer.
# This script is idempotent and safe to run multiple times. It will try to use apt and sudo
# if necessary. It deliberately exits non-fatally when run in environments where apt isn't
# available (e.g., non-Debian hosts); callers can opt-in to ignore failures.

set -euo pipefail

# Avoid interactive prompts during package install
export DEBIAN_FRONTEND=noninteractive

PKGS=(libpcap0.8 libpcap0.8-dev libpcap-dev ffmpeg libturbojpeg0 libjpeg-turbo-progs)

has_command() { command -v "$1" >/dev/null 2>&1; }

if ! has_command apt-get; then
    echo "apt-get not found; skipping system package installation. If you need these packages, install them manually:" >&2
    echo "  libpcap-dev python3-pcapy ffmpeg libjpeg-turbo-progs" >&2
    exit 0
fi

SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    if has_command sudo; then
        SUDO=sudo
    else
        echo "Not running as root and sudo not available; attempting apt-get as non-root will likely fail." >&2
    fi
fi

echo "Updating apt cache..."
${SUDO} apt-get update -y

echo "Installing packages: ${PKGS[*]}"
# Use --no-install-recommends to keep image smaller
# Pass Dpkg options to avoid config prompts when packages need configuration
${SUDO} apt-get install -y --no-install-recommends \
    -o Dpkg::Options::="--force-confdef" \
    -o Dpkg::Options::="--force-confold" \
    "${PKGS[@]}" || {
    echo "apt-get failed installing some packages. You can re-run this script as root inside the container or install the listed packages manually." >&2
    exit 1
}


echo "Installed system packages. Cleaning apt caches..."
${SUDO} apt-get clean
${SUDO} rm -rf /var/lib/apt/lists/*

echo "Verifying libpcap presence..."
if ldconfig -p | grep -qi pcap; then
    echo "libpcap seems present"
else
    echo "Warning: libpcap not found in ldconfig output" >&2
fi

echo "Attempting to install Python pcap binding via pip (best-effort)."
if has_command pip3; then
    pip3 install --upgrade pip setuptools wheel || true
    # Try to build/install pypcap. This may fail for Python 3.13; the script continues in that case.
    if pip3 install --no-binary :all: pypcap; then
        echo "pypcap installed via pip"
    else
        echo "Warning: pip install pypcap failed. If you need a working Python pcap binding consider:" >&2
        echo "  - using a distro Python (python3.11) with the 'python3-pcapy' package, or" >&2
        echo "  - running your code in a separate container/image that provides a prebuilt pcap binding, or" >&2
        echo "  - waiting for upstream wheels for Python 3.13." >&2
    fi
else
    echo "pip3 not found; skipping Python pcap install"
fi

echo "Devcontainer dependencies install completed."

exit 0
