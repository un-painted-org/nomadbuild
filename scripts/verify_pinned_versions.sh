#!/bin/bash
# verify_pinned_versions.sh
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
# Script to verify installed package versions against a configuration file.
# Used inside the Docker build process.

set -e

# --- Use real commands or allow overrides via arguments --- #
CONFIG_FILE="$1"

# --- Helper functions for command execution (allows test overriding via BASH_ENV) --- #
_get_dpkg_version() {
    # Use command -v to ensure dpkg-query exists, then execute
    command -v dpkg-query >/dev/null && dpkg-query -W -f='${Version}' "$1" 2>/dev/null || echo "not-installed"
}

# --- Validate Config File Argument (now $1) --- #
if [ -z "$CONFIG_FILE" ] || [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Configuration file (arg 1) not provided or not found at $CONFIG_FILE" >&2
    exit 1
fi

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