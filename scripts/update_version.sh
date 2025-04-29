#!/bin/bash
# update_version.sh
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
# Script to update version information placeholders in the HTML file

set -e

# Set target HTML file - adjust paths for container environment
TARGET_HTML="/app/src/web_templates/index.html"

# Get Git version information
VERSION="unknown"
BUILD_DATE=$(date +"%B %d, %Y")

# First try to get info from environment variables (can be passed to container)
if [ -n "$GIT_VERSION" ]; then
    echo "Using version information from environment: $GIT_VERSION"
    VERSION="$GIT_VERSION"
elif [ -d "/app/.git" ]; then
    # Try to get info from container's git repo (if it exists)
    echo "Getting version from container Git repository"
    # Get current branch or tag
    GIT_BRANCH=$(git -C /app rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    GIT_COMMIT=$(git -C /app rev-parse --short HEAD 2>/dev/null || echo "unknown")
    
    # Check if we're on a tag
    GIT_TAG=$(git -C /app describe --tags --exact-match 2>/dev/null || echo "")
    
    if [ -n "$GIT_TAG" ]; then
        VERSION="$GIT_TAG"
    else
        VERSION="$GIT_BRANCH@$GIT_COMMIT"
    fi
elif [ -d "/firmware/.git" ]; then
    # Try to get info from firmware directory git repo (if mounted)
    echo "Getting version from mounted firmware Git repository"
    # Get current branch or tag
    GIT_BRANCH=$(git -C /firmware rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    GIT_COMMIT=$(git -C /firmware rev-parse --short HEAD 2>/dev/null || echo "unknown")
    
    # Check if we're on a tag
    GIT_TAG=$(git -C /firmware describe --tags --exact-match 2>/dev/null || echo "")
    
    if [ -n "$GIT_TAG" ]; then
        VERSION="$GIT_TAG"
    else
        VERSION="$GIT_BRANCH@$GIT_COMMIT"
    fi
else
    # Fallback to hard-coded version
    echo "No Git repository found, using fallback version"
    VERSION="nomadbuild-$(date +%Y%m%d)"
fi

echo "Updating version placeholders in $TARGET_HTML"
echo "Version: $VERSION"
echo "Build date: $BUILD_DATE"

# Check if file exists
if [ ! -f "$TARGET_HTML" ]; then
    echo "ERROR: Target HTML file not found: $TARGET_HTML"
    exit 1
fi

# Replace placeholders in the HTML file
sed -i "s/%%VERSION%%/$VERSION/g" "$TARGET_HTML"
sed -i "s/%%BUILD_DATE%%/$BUILD_DATE/g" "$TARGET_HTML"

echo "Version placeholders updated successfully." 