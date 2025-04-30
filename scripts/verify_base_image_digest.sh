#!/usr/bin/env bash
# verify_base_image_digest.sh
# SPDX-License-Identifier: MIT
# Script to verify the Docker base image is pinned by digest and available locally.

set -e

CONFIG_FILE="$1"
if [ -z "$CONFIG_FILE" ] || [ ! -f "$CONFIG_FILE" ]; then
    echo "Usage: $0 path/to/toolchain_pins.conf" >&2
    exit 1
fi

# Extract expected digest and trim whitespace
expected=$(grep '^base_image=' "$CONFIG_FILE" | cut -d '=' -f2 | xargs)
if [ -z "$expected" ]; then
    echo "Error: 'base_image' not set in $CONFIG_FILE" >&2
    exit 1
fi

image="espressif/idf"
image_ref="$image@$expected"

echo "🔍 Verifying base image digest pin: $image_ref"

# 1) Dockerfile pin check
dockerfile="$(dirname "$0")/../Dockerfile"
if grep -qE "^FROM[[:space:]]+$image_ref" "$dockerfile"; then
    echo "✅ Dockerfile pinned to $image_ref"
else
    echo "❌ Dockerfile FROM not pinned to $image_ref" >&2
    echo "Expected: FROM $image_ref" >&2
    exit 1
fi

# 2) Local image presence & pull (skip if CLI not available)
if ! command -v docker > /dev/null 2>&1; then
    echo "⚠️ Docker CLI not available, skipping local image presence check"
    exit 0
fi

echo "🔍 Checking if $image_ref is present locally..."
if docker image inspect "$image_ref" > /dev/null 2>&1; then
    echo "✅ Verified: Image $image_ref is present locally."
else
    echo "⚠️  Image $image_ref not found locally. Attempting to pull..."
    if docker pull "$image_ref" > /dev/null 2>&1; then
        echo "✅ Image successfully pulled and verified."
    else
        echo "❌ Failed to pull image $image_ref. Aborting." >&2
        exit 1
    fi
fi

# 3) Confirm digest matches
actual=$(docker image inspect "$image_ref" --format '{{index .RepoDigests 0}}' 2>/dev/null || echo "")
echo "📦 Local Repo Digest: $actual"

if [ "$actual" = "$image_ref" ]; then
    echo "✅ Digest matches expected value."
    exit 0
else
    echo "❌ Digest mismatch! Expected $image_ref but found $actual" >&2
    exit 1
fi 