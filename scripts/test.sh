#!/bin/bash
# test.sh
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#

# test.sh - Wrapper script to run pytest inside the Docker container.

set -e # Exit on error

IMAGE_NAME="nomadbuild"
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT=$(realpath "$SCRIPT_DIR/..")

echo "--- NOMADBUILD Test Runner ---"

# Parse arguments
TEST_PATH="/app/src/tests"
VERBOSE="-v"

show_help() {
    echo "Usage: ./scripts/test.sh [OPTIONS]"
    echo
    echo "Options:"
    echo "  --all           Run all tests (default)"
    echo "  --web-ui        Run only web UI tests"
    echo "  --builder       Run only builder tests"
    echo "  --version       Run only version tests"
    echo "  --path PATH     Run tests in specific path"
    echo "  --quiet         Run with minimal output"
    echo "  --help          Show this help message"
    echo
    exit 0
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            TEST_PATH="/app/src/tests"
            shift ;;
        --web-ui)
            TEST_PATH="/app/src/tests/test_web_ui.py"
            shift ;;
        --builder)
            TEST_PATH="/app/src/tests/test_builder_*.py"
            shift ;;
        --version)
            TEST_PATH="/app/src/tests/test_version_*.py"
            shift ;;
        --path)
            if [[ -z "$2" || "$2" == --* ]]; then 
                echo "Error: --path requires an argument." >&2
                show_help
            fi
            # Convert to container path
            if [[ "$2" == /* ]]; then
                # Absolute path
                TEST_PATH="$2"
            else
                # Relative path
                TEST_PATH="/app/${2#./}"
            fi
            shift 2 ;;
        --quiet)
            VERBOSE=""
            shift ;;
        --help)
            show_help ;;
        *)
            echo "Error: Unknown option: $1" >&2
            show_help ;;
    esac
done

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
        echo "Error: Docker image build failed during test preparation."
        exit 1
    fi
    echo "Docker image build complete."
else
    echo "Docker image '$IMAGE_NAME' found locally."
fi

# Verify base image digest matches the pinned configuration
bash "$SCRIPT_DIR/verify_base_image_digest.sh" "$PROJECT_ROOT/build/toolchain_pins.conf"

echo "--- Running Pytest ---"
echo "Test path: $TEST_PATH"

# Pytest and dependencies are installed globally via Dockerfile
# Clear .pyc files and run pytest targeting the correct directory with ESP-IDF environment
CMD_INSIDE_CONTAINER="source \$IDF_PATH/export.sh > /dev/null 2>&1 && source /opt/venv/bin/activate && export PYTHONDONTWRITEBYTECODE=1 && find /app -name '*.pyc' -delete && bash /app/scripts/verify_pinned_versions.sh /app/build/apt_pins.conf && bash /app/scripts/verify_toolchain_versions.sh /app/build/toolchain_pins.conf && python3 -m pip install -q pytest-sugar && /opt/venv/bin/python -B -m pytest -q --disable-warnings --tb=short --durations=10 --color=yes --cache-clear \$TEST_PATH"

# Run the Docker container with bash entrypoint
# Mount the current directory to /app to ensure tests run against local code
# Mount the firmware directory to potentially access generated files
docker run --rm -it --entrypoint /bin/bash -v "$PROJECT_ROOT:/app" -v "$PROJECT_ROOT/firmware:/firmware" "$IMAGE_NAME" -c "$CMD_INSIDE_CONTAINER"

EXIT_CODE=$?
echo "--- Pytest Finished (Exit Code: $EXIT_CODE) ---"
exit $EXIT_CODE 