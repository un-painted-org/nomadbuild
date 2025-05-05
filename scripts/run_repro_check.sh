#!/bin/bash
# run_repro_check.sh
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
# Simple wrapper script to run the reproducibility check directly

# Do not use set -e here, as we want to handle errors ourselves

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 --tag <tag>"
    echo "Example: $0 --tag v2.7.0"
    exit 1
fi

if [ "$1" != "--tag" ]; then
    echo "Error: First argument must be --tag"
    exit 1
fi

TAG="$2"
echo "Running reproducibility check for tag: $TAG"

# Source the ESP-IDF environment
. /opt/esp/idf/export.sh

# Run the repro_builder.py script directly
cd /app
python3 /app/scripts/repro_builder.py --tag "$TAG"
RESULT=$?

if [ $RESULT -ne 0 ]; then
    echo "Reproducibility check failed with exit code $RESULT"
    exit $RESULT
else
    echo "Reproducibility check completed successfully."
    exit 0
fi
