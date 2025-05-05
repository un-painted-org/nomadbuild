#!/usr/bin/env bash
# generate_dockerfile.sh
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
# Script to generate a Dockerfile from configuration files with version pins

set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT=$(realpath "$SCRIPT_DIR/..")
TEMPLATE_FILE="$PROJECT_ROOT/Dockerfile.template"
OUTPUT_FILE="$PROJECT_ROOT/Dockerfile"

# Use container-only directory for pin files
CONTAINER_ONLY_DIR="/container_only"
CONFIG_DIR="${CONTAINER_ONLY_DIR}/config"
mkdir -p "${CONFIG_DIR}"

APT_PINS_FILE="${CONFIG_DIR}/apt_pins.conf"
TOOLCHAIN_PINS_FILE="${CONFIG_DIR}/toolchain_pins.conf"
PYTHON_PINS_FILE="${CONFIG_DIR}/python_pins.conf"

# Set environment variable for other scripts to use
export NOMADBUILD_CONFIG_DIR="${CONFIG_DIR}"

# Check if Dockerfile.template exists, if not, create it from the current Dockerfile
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "Dockerfile.template not found. Creating from current Dockerfile..."
    if [ ! -f "$OUTPUT_FILE" ]; then
        echo "Error: Neither Dockerfile.template nor Dockerfile found." >&2
        exit 1
    fi

    # Create a backup of the current Dockerfile
    cp "$OUTPUT_FILE" "$OUTPUT_FILE.bak"
    echo "Backup created at $OUTPUT_FILE.bak"

    # Extract base image digest from current Dockerfile
    BASE_IMAGE_DIGEST=$(grep -E "^FROM espressif/idf@sha256:" "$OUTPUT_FILE" | sed -E 's/.*@(sha256:[a-f0-9]+).*/\1/')

    # Create template by replacing the base image digest with a placeholder
    cat "$OUTPUT_FILE" | sed -E "s|FROM espressif/idf@$BASE_IMAGE_DIGEST|FROM espressif/idf@\${BASE_IMAGE_DIGEST}|" > "$TEMPLATE_FILE"

    echo "Created Dockerfile.template from current Dockerfile."

    # Update toolchain_pins.conf with the base image digest
    mkdir -p "$(dirname "$TOOLCHAIN_PINS_FILE")"
    echo "base_image=$BASE_IMAGE_DIGEST" > "$TOOLCHAIN_PINS_FILE"
    echo "Added base_image=$BASE_IMAGE_DIGEST to $TOOLCHAIN_PINS_FILE"
fi

# No need to check for required files as we create them if they don't exist

# Create all pin files in the container-only directory
echo "Creating pin files in container-only directory: ${CONFIG_DIR}..."

# Create apt_pins.conf if it doesn't exist
if [ ! -f "$APT_PINS_FILE" ]; then
    echo "Creating $APT_PINS_FILE..."
    echo "# APT packages with pinned versions" > "$APT_PINS_FILE"
    echo "# Format: package=version" >> "$APT_PINS_FILE"
    echo "" >> "$APT_PINS_FILE"
fi

# Create toolchain_pins.conf if it doesn't exist
if [ ! -f "$TOOLCHAIN_PINS_FILE" ]; then
    echo "Creating $TOOLCHAIN_PINS_FILE..."
    echo "# Toolchain components with pinned versions" > "$TOOLCHAIN_PINS_FILE"
    echo "# Format: component=version" >> "$TOOLCHAIN_PINS_FILE"
    echo "base_image=sha256:6b4adab7b282e9261a154d7130fb4945a3c28bd35c2e914357c2f522643cb92a" >> "$TOOLCHAIN_PINS_FILE"
    echo "" >> "$TOOLCHAIN_PINS_FILE"
fi

# Create python_pins.conf if it doesn't exist
if [ ! -f "$PYTHON_PINS_FILE" ]; then
    echo "Creating $PYTHON_PINS_FILE..."
    echo "# Python packages with pinned versions" > "$PYTHON_PINS_FILE"
    echo "# Format: package=version" >> "$PYTHON_PINS_FILE"
    echo "" >> "$PYTHON_PINS_FILE"
fi

# Function to extract a value from a config file
# Args: $1 = config file, $2 = key
get_config_value() {
    local file="$1"
    local key="$2"
    grep -E "^$key=" "$file" | cut -d '=' -f2 | xargs
}

# Get base image digest from toolchain_pins.conf
BASE_IMAGE_DIGEST=$(get_config_value "$TOOLCHAIN_PINS_FILE" "base_image")
if [ -z "$BASE_IMAGE_DIGEST" ]; then
    echo "Error: base_image not found in $TOOLCHAIN_PINS_FILE" >&2
    exit 1
fi

# Use the dedicated Python script for Dockerfile generation
PYTHON_SCRIPT="$SCRIPT_DIR/generate_dockerfile.py"

# Check if the Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: generate_dockerfile.py not found at $PYTHON_SCRIPT" >&2
    exit 1
fi

# Make sure the script is executable
chmod +x "$PYTHON_SCRIPT"

# Run the Python script
python3 "$PYTHON_SCRIPT"

echo "✅ Dockerfile successfully generated from template"

exit 0
