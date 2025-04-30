#!/bin/bash
# repro.sh
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#

# repro.sh - Wrapper script to run the Bitaxe INTERNAL reproducibility build check.

set -e # Exit on error

TAG=""

# --- Help Function ---
usage() {
    echo "Usage: $0 --tag <tag>"
    echo "  Checks internal reproducibility for a specific ESP-Miner tag."
    echo "Example: $0 --tag v2.6.3"
    exit 1
}

# --- Argument Parsing ---
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --tag)
      if [[ -z "$2" || "$2" == --* ]]; then echo "Error: --tag requires an argument." >&2; usage; fi
      TAG="$2"
      shift # past argument
      shift # past value
      ;;
    -h|--help)
        usage
        ;;
    *)
      # unknown option
      echo "Error: Unknown option: $1" >&2
      usage
      ;;
  esac
done

# Check if tag was provided
if [ -z "$TAG" ]; then
  echo "Error: --tag argument is required." >&2
  usage
fi

IMAGE_NAME="nomadbuild"
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT=$(realpath "$SCRIPT_DIR/..")

echo "--- Preparing for Reproducibility Check for Tag: $TAG ---"
echo "--- Using Docker Image: $IMAGE_NAME ---"

# --- Docker Check ---
if ! command -v docker &> /dev/null; then
    echo "Error: docker command could not be found."
    exit 1
fi
echo "Docker installation verified."

# --- Image Check & Non-Interactive Build ---
if ! docker image inspect "$IMAGE_NAME" &> /dev/null; then
    echo "Docker image '$IMAGE_NAME' not found locally. Building non-interactively..."
    if ! docker build -t "$IMAGE_NAME" "$PROJECT_ROOT"; then
        echo "Error: Docker image build failed during repro check preparation."
        exit 1
    fi
    echo "Docker image build complete."
else
    echo "Docker image '$IMAGE_NAME' found locally."
fi

echo "--- Running Reproducibility Check ---"

# Construct the command to run inside the container
# Needs to source IDF env and run the specific repro script
# The repro script is copied to /app/scripts/repro_builder.py in the Dockerfile
CMD_INSIDE_CONTAINER=". /opt/esp/idf/export.sh && python3 /app/scripts/repro_builder.py --tag $TAG"

# Run the Docker container
# No volume mount needed as repro script handles its own cloning within container
docker run -it --rm --entrypoint /bin/bash "$IMAGE_NAME" -c "$CMD_INSIDE_CONTAINER"

EXIT_CODE=$?
echo "--- Reproducibility Check Finished (Exit Code: $EXIT_CODE) ---"
exit $EXIT_CODE 