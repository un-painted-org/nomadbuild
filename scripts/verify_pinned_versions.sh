#!/bin/bash
# verify_pinned_versions.sh
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
# Script to verify installed package versions against a configuration file.
# Used inside the Docker build process.

set -e

CONFIG_FILE="$1"

if [ -z "$CONFIG_FILE" ] || [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Configuration file not provided or not found at $CONFIG_FILE" >&2
    exit 1
fi

echo "--- Verifying Pinned APT Package Versions --- "

ALL_MATCH=true

while IFS= read -r line || [[ -n "$line" ]]; do
    # Skip comments and empty lines
    if [[ "$line" =~ ^# ]] || [[ -z "$line" ]]; then
        continue
    fi

    # Parse package and expected version
    package=$(echo "$line" | cut -d '=' -f1)
    expected_version=$(echo "$line" | cut -d '=' -f2)

    # Get installed version
    # Use dpkg-query, redirect stderr to /dev/null in case package not installed
    installed_version=$(dpkg-query -W -f='${Version}' "$package" 2>/dev/null || echo "not-installed")

    # Special handling for nodejs version check
    if [ "$package" = "nodejs" ]; then
        installed_node_version=$(node --version 2>/dev/null || echo "node-not-installed")
        # Format expected version (remove nodesource suffix for comparison with `node --version`)
        # Example: 22.15.0-1nodesource1 -> v22.15.0
        formatted_expected_version="v$(echo "$expected_version" | cut -d '-' -f1)"
        echo -n "Checking $package... Expected: $formatted_expected_version, Found: $installed_node_version - "
        if [ "$installed_node_version" = "$formatted_expected_version" ]; then
            echo "OK"
        else
            echo "MISMATCH!"
            ALL_MATCH=false
        fi
    elif [ "$installed_version" = "not-installed" ]; then
        echo "Checking $package... MISMATCH! Package not installed."
        ALL_MATCH=false
    else
        # Normal package check
        echo -n "Checking $package... Expected: $expected_version, Found: $installed_version - "
        if [ "$installed_version" = "$expected_version" ]; then
            echo "OK"
        else
            echo "MISMATCH!"
            ALL_MATCH=false
        fi
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