#!/usr/bin/env bash
# verify_toolchain_versions.sh
# SPDX-License-Identifier: MIT
# Script to verify installed CLI tool versions against a configuration file.

set -e

# --- Use container-only directory for pin files --- #
CONTAINER_ONLY_DIR="/container_only"
CONFIG_DIR="${NOMADBUILD_CONFIG_DIR:-${CONTAINER_ONLY_DIR}/config}"
CONFIG_FILE="${CONFIG_DIR}/toolchain_pins.conf"

# Create the directory if it doesn't exist
mkdir -p "${CONFIG_DIR}"

# Create the file if it doesn't exist
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Creating $CONFIG_FILE..."
    cat > "$CONFIG_FILE" << EOF
# Toolchain components with pinned versions
# Format: component=version

base_image=sha256:6b4adab7b282e9261a154d7130fb4945a3c28bd35c2e914357c2f522643cb92a
gcc=13.3.0
cmake=3.30.2
objcopy=2.42
python3=3.12.3
EOF
fi

echo "--- Verifying Toolchain Versions ---"
ALL_MATCH=true

while IFS= read -r line; do
    # skip comments and empty lines
    [[ "$line" =~ ^# ]] && continue
    [[ -z "$line" ]] && continue

    tool=$(echo "$line" | cut -d '=' -f1)
    expected=$(echo "$line" | cut -d '=' -f2)

    # Skip base_image line
    [[ "$tool" == "base_image" ]] && continue

    case "$tool" in
        gcc)
            version=$(gcc --version | head -n1 | awk '{print $NF}')
            ;;
        cmake)
            version=$(cmake --version | head -n1 | awk '{print $3}')
            ;;
        objcopy)
            version=$(objcopy --version | head -n1 | awk '{print $NF}')
            ;;
        python3)
            version=$(python3 --version | awk '{print $2}')
            ;;
        *)
            echo "Unknown tool: $tool" >&2
            exit 1
            ;;
    esac

    echo -n "Checking $tool... Expected: $expected, Found: $version - "
    if [ "$version" = "$expected" ]; then
        echo "OK"
    else
        echo "MISMATCH!"
        ALL_MATCH=false
    fi

done < "$CONFIG_FILE"

echo "-----------------------------------"
if [ "$ALL_MATCH" = true ]; then
    echo "All toolchain versions match."
    exit 0
else
    echo "One or more toolchain versions do not match." >&2
    exit 1
fi