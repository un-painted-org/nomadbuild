#!/usr/bin/env bash
# verify_toolchain_versions.sh
# SPDX-License-Identifier: MIT
# Script to verify installed CLI tool versions against a configuration file.

set -e

CONFIG_FILE="$1"
if [ -z "$CONFIG_FILE" ] || [ ! -f "$CONFIG_FILE" ]; then
    echo "Usage: $0 path/to/toolchain_pins.conf" >&2
    exit 1
fi

echo "--- Verifying Toolchain Versions ---"
ALL_MATCH=true

while IFS= read -r line; do
    # skip comments and empty lines
    [[ "$line" =~ ^# ]] && continue
    [[ -z "$line" ]] && continue

    tool=$(echo "$line" | cut -d '=' -f1)
    expected=$(echo "$line" | cut -d '=' -f2)
    
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