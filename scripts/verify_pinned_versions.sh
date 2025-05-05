#!/bin/bash
# verify_pinned_versions.sh
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
# Script to verify installed package versions against a configuration file.
# Used inside the Docker build process.

set -e

# --- Use container-only directory for pin files --- #
CONTAINER_ONLY_DIR="/container_only"
CONFIG_DIR="${NOMADBUILD_CONFIG_DIR:-${CONTAINER_ONLY_DIR}/config}"
CONFIG_FILE="${CONFIG_DIR}/apt_pins.conf"

# Create the directory if it doesn't exist
mkdir -p "${CONFIG_DIR}"

# Create the file if it doesn't exist
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Creating $CONFIG_FILE..."
    cat > "$CONFIG_FILE" << EOF
# APT packages with pinned versions
# Format: package=version

ca-certificates=20240203
curl=8.5.0-2ubuntu10.6
gnupg=2.4.4-2ubuntu17
pandoc=3.1.3+ds-2
perl=5.38.2-3.2build2.1
python3-pip=24.0+dfsg-1ubuntu1
python3-venv=3.12.3-0ubuntu2
nodejs=22.15.0-1nodesource1
EOF
fi

# --- Helper functions for command execution (allows test overriding via BASH_ENV) --- #
_get_dpkg_version() {
    # Use command -v to ensure dpkg-query exists, then execute
    command -v dpkg-query >/dev/null && dpkg-query -W -f='${Version}' "$1" 2>/dev/null || echo "not-installed"
}

echo "--- Verifying Pinned APT Package Versions --- "

ALL_MATCH=true

while IFS= read -r line; do
    # Skip comments and empty lines
    if [[ "$line" =~ ^# ]] || [[ -z "$line" ]]; then
        continue
    fi

    # Parse package and expected version
    package=$(echo "$line" | cut -d '=' -f1)
    expected_version=$(echo "$line" | cut -d '=' -f2)

    # Get installed version
    # Use dpkg-query, redirect stderr to /dev/null in case package not installed
    installed_version=$(_get_dpkg_version "$package")

    # Normal package check
    echo -n "Checking $package... Expected: $expected_version, Found: $installed_version - "
    if [ "$installed_version" = "$expected_version" ]; then
        echo "OK"
    else
        echo "MISMATCH!"
        ALL_MATCH=false
    fi
done < "$CONFIG_FILE"

echo "---------------------------------------------"

if [ "$ALL_MATCH" = true ]; then
    echo "Verification SUCCESS: All pinned package versions match."
    exit 0
else
    echo "Verification FAILED: One or more package versions do not match the pinned configuration." >&2
    exit 1
fi