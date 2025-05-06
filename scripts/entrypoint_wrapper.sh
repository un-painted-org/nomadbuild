#!/bin/bash
# entrypoint_wrapper.sh
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#

# entrypoint_wrapper.sh - Sets up ESP-IDF environment and executes the command/args passed.

echo "Sourcing ESP-IDF environment..."
source "$IDF_PATH/export.sh"

# --- Activate Virtual Environment (after IDF env) --- #
VENV_PATH="/opt/venv"
if [ -f "$VENV_PATH/bin/activate" ]; then
    echo "Activating Python virtual environment at $VENV_PATH..."
    source "$VENV_PATH/bin/activate"
else
    echo "WARNING: Virtual environment activation script not found at $VENV_PATH/bin/activate"
    # Attempting to continue without venv might fail later steps
fi

# Verify required Python packages are installed (dependencies should already be pre-installed)
if ! python -c "import flask, flask_socketio" &>/dev/null; then
    echo "WARNING: Required Python packages not found, installation was supposed to happen during image build"
    # echo "Attempting emergency installation of required packages..."
    # pip install flask flask-socketio pytest pytest-mock requests
else
    echo "Required Python packages verified."
fi

# Update version information in templates
if [ -x "/app/scripts/update_version.sh" ]; then
    echo "Updating version information in templates..."
    /app/scripts/update_version.sh
else
    echo "WARNING: Version update script not found or not executable."
fi

# Check for vendor JavaScript files
if [ -x "/app/scripts/check_vendor_files.sh" ]; then
    echo "Checking for vendor JavaScript libraries..."
    /app/scripts/check_vendor_files.sh
else
    echo "WARNING: Vendor file check script not found or not executable."
fi

# Check if python command
if [[ "$1" == "python3" ]]; then
    echo "Running Python with /app in PYTHONPATH..."
    shift # Remove python3 from args
    echo "Command: python3 $@"
    PYTHONPATH="/app:$PYTHONPATH" python3 "$@"
else
    # Execute the command and arguments passed to this script from docker run
    echo "Executing: $@"
    exec "$@"
fi 