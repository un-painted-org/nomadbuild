#!/usr/bin/env bash
# verify_container.sh
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
# Script to verify the container environment after Dockerfile optimization

set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT=$(realpath "$SCRIPT_DIR/..")

# Define the container image
CONTAINER_IMAGE="nomadbuild:latest"

echo "=== Container Verification Script ==="
echo "Verifying container image: $CONTAINER_IMAGE"

# Check if the container image exists
if ! docker image inspect "$CONTAINER_IMAGE" &> /dev/null; then
    echo "❌ Container image $CONTAINER_IMAGE does not exist"
    echo "Please build the container image first with ./nomadbuild.sh --build-image"
    exit 1
fi

echo "✅ Container image $CONTAINER_IMAGE exists"

# Create a temporary directory for volume mounting
TEMP_DIR=$(mktemp -d)
echo "Created temporary directory: $TEMP_DIR"

# Run the container with the verification script
echo "Running verification script in container..."
docker run --rm \
    -v "$TEMP_DIR:/firmware" \
    -v "$PROJECT_ROOT/scripts/verify_container_environment.py:/app/verify_container_environment.py" \
    "$CONTAINER_IMAGE" \
    python3 /app/verify_container_environment.py

# Check the exit status
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Container verification passed"
else
    echo "❌ Container verification failed with exit code $EXIT_CODE"
fi

# Clean up
echo "Cleaning up temporary directory: $TEMP_DIR"
rm -rf "$TEMP_DIR"

# Return the exit code from the verification script
exit $EXIT_CODE
