#!/usr/bin/env bash
# verify_base_image_digest.sh
# SPDX-License-Identifier: MIT
# Script to verify:
# 1. Tests are running inside a container environment
# 2. The Docker base image is pinned by digest in the Dockerfile

set -e

# ----- Container Environment Verification -----
# Check if we're running inside a container by looking for container-specific files
verify_container_environment() {
    # Multiple checks to detect container environment
    local in_container=false

    # Check 1: Look for .dockerenv file
    if [ -f "/.dockerenv" ]; then
        in_container=true
    fi

    # Check 2: Look for container in cgroup
    if grep -q "docker\|lxc\|kubepods" /proc/1/cgroup 2>/dev/null; then
        in_container=true
    fi

    # Check 3: Look for container-specific environment variables
    if [ -n "$CONTAINER_RUNTIME" ] || [ -n "$KUBERNETES_SERVICE_HOST" ]; then
        in_container=true
    fi

    # Fail if not in container environment
    if [ "$in_container" = "false" ]; then
        echo "❌ ERROR: Tests must run inside the container environment!" >&2
        echo "   This ensures reproducibility and consistent test results." >&2
        echo "   Please use ./scripts/test.sh to run tests properly." >&2
        exit 1
    fi

    echo "✅ Verified: Running in container environment"
}

# ----- Base Image Digest Verification -----
verify_base_image_digest() {
    # Use container-only directory for pin files
    local CONTAINER_ONLY_DIR="/container_only"
    local CONFIG_DIR="${NOMADBUILD_CONFIG_DIR:-${CONTAINER_ONLY_DIR}/config}"
    local CONFIG_FILE="${CONFIG_DIR}/toolchain_pins.conf"

    # Create the directory if it doesn't exist
    mkdir -p "${CONFIG_DIR}"

    # Create the file if it doesn't exist
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "Creating $CONFIG_FILE..."
        echo "base_image=sha256:6b4adab7b282e9261a154d7130fb4945a3c28bd35c2e914357c2f522643cb92a" > "$CONFIG_FILE"
    fi

    # Extract expected digest and trim whitespace
    local expected=$(grep '^base_image=' "$CONFIG_FILE" | cut -d '=' -f2 | xargs)
    if [ -z "$expected" ]; then
        echo "Error: 'base_image' not set in $CONFIG_FILE" >&2
        exit 1
    fi

    local image="espressif/idf"
    local image_ref="$image@$expected"

    echo "🔍 Verifying base image digest pin: $image_ref"

    # Dockerfile pin check
    local dockerfile="$(dirname "$0")/../Dockerfile"
    if grep -qE "^FROM[[:space:]]+$image_ref" "$dockerfile"; then
        echo "✅ Dockerfile pinned to $image_ref"
    else
        echo "❌ Dockerfile FROM not pinned to $image_ref" >&2
        echo "Expected: FROM $image_ref" >&2
        exit 1
    fi
}

# ----- Main Execution -----
# First verify we're in a container environment
verify_container_environment

# Then verify the base image digest
verify_base_image_digest

# If we reach here, all verifications passed
exit 0