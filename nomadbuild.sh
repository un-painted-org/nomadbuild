#!/bin/bash
# nomadbuild.sh
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#

# nomadbuild.sh - Main entry point for NomadBuild.
# Builds firmware or flashes devices using a Docker container.

set -e # Exit immediately if a command exits with a non-zero status.

IMAGE_NAME="nomadbuild"
# SCRIPT_DIR should be the directory this script is in (now the project root)
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT=$SCRIPT_DIR # Project root is where the script now resides

# Function to display the header (Moved before call)
display_header() {
    printf "%b%s%b%s%b\n" "\e[36m" "                                    " "\e[33m" "____          _ __    __" "\e[0m"
    printf "%b%s%b%s%b\n" "\e[36m" "   ____  ____  ____ ___  ____ _____/ " "\e[33m" "/ /_  __  __(_) /___/ /" "\e[0m"
    printf "%b%s%b%s%b\n" "\e[36m" "  / __ \\/ __ \\/ __ \`__ \\/ __ \`/ __  " "\e[33m" "/ __ \\/ / / / / / __  / " "\e[0m"
    printf "%b%s%b%s%b\n" "\e[36m" " / / / / /_/ / / / / / / /_/ / /_/" "\e[33m" " / /_/ / /_/ / / / /_/ /" "\e[0m"
    printf "%b%s%b%s%b\n" "\e[36m" "/_/ /_/\\____/_/ /_/ /_/\\__,_/\\__,_" "\e[33m" "/_.___/\\__,_/_/_/\\__,_/   " "\e[0m"

    # Function to get version info (Moved inside display_header for tidiness)
    get_version_info() {
        local version="unknown"
        if [ -d "$PROJECT_ROOT/.git" ]; then
            if command -v git &> /dev/null; then
                GIT_TAG=$(git -C "$PROJECT_ROOT" describe --tags --exact-match --always 2>/dev/null || echo "")
                if [ -n "$GIT_TAG" ]; then
                    version="$GIT_TAG"
                else
                    GIT_BRANCH=$(git -C "$PROJECT_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
                    GIT_COMMIT=$(git -C "$PROJECT_ROOT" rev-parse --short HEAD 2>/dev/null || echo "unknown")
                    version="$GIT_BRANCH@$GIT_COMMIT"
                fi
            else
                version="unknown (git not found)"
            fi
        elif [ -f "$PROJECT_ROOT/VERSION" ]; then
            version=$(cat "$PROJECT_ROOT/VERSION")
        fi
        echo "$version"
    }

    # Get version info
    VERSION_INFO=$(get_version_info)
    # Use ANSI code for gray
    printf "%bVersion: %s%b" "\e[90m" "${VERSION_INFO}" "\e[0m"
    echo # Add an empty line for spacing
}

# --- Display Header --- #
display_header # Call the header function early

# Function to display help
function show_help {
    cat << EOF
NomadBuild - Build & Flash Bitaxe Firmware via Docker

Usage: ./nomadbuild.sh [ACTION] [OPTIONS]

Actions:
  --webui               Start web UI (Recommended)
  --build               Build latest firmware (Default if no other action)
  --tag <VERSION>       Build specific firmware version (e.g., v2.6.3)
  --flash-ip <IP>       Flash firmware to device at <IP>
  --restart-webui       Restart web UI (stops existing container)
  --build-image [clean] Only build/rebuild the Docker image
                        Add 'clean' to remove existing image first (e.g., after upgrade)
  --test [OPTIONS]      Run tests (passes options to test.sh)
  --repro               Run reproducibility check
  --help                Show this help

Options:
  --no-cache            Force Docker image rebuild without cache
  --force-flash         Flash device without confirmation
  --skip-firmware       Skip building main firmware
  --skip-www            Skip building web interface files
  --verbose-build       Show detailed build output

Examples:
  ./nomadbuild.sh --webui
  ./nomadbuild.sh --build --tag v2.6.3
  ./nomadbuild.sh --flash-ip 192.168.1.100
  ./nomadbuild.sh --build-image clean

EOF
    exit 0
}

# --- Argument Parsing (Manual) ---
BUILD_IMAGE=false
CLEAN_IMAGE=false
DO_BUILD_LATEST=false
WEB_UI=false
RESTART_WEB_UI=false
NO_CACHE=false
RUN_TESTS=false
TEST_ARGS=()
RUN_REPRO=false
DOCKER_CMD_ARGS=() # Arguments for the python script inside docker
HAS_ACTION_FLAG=false

# Handle help first
for arg in "$@"; do
    if [[ "$arg" == "-h" || "$arg" == "--help" ]]; then
        show_help
    fi
done

# Process other arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --build)
            DO_BUILD_LATEST=true; HAS_ACTION_FLAG=true; shift ;;
        --tag)
            if [[ -z "$2" || "$2" == --* ]]; then echo "Error: --tag requires an argument." >&2; show_help; fi
            DOCKER_CMD_ARGS+=("--tag" "$2"); HAS_ACTION_FLAG=true; shift 2 ;;
        --flash-ip)
             if [[ -z "$2" || "$2" == --* ]]; then echo "Error: --flash-ip requires an argument." >&2; show_help; fi
            DOCKER_CMD_ARGS+=("--flash-ip" "$2"); HAS_ACTION_FLAG=true; shift 2 ;;
        --build-image)
            BUILD_IMAGE=true;
            HAS_ACTION_FLAG=true;
            # Check if the next argument is "clean"
            if [[ $# -gt 1 && "$2" == "clean" ]]; then
                CLEAN_IMAGE=true;
                shift 2;
            else
                shift;
            fi ;;
        --no-cache)
            NO_CACHE=true; shift ;;
        --force-flash)
            DOCKER_CMD_ARGS+=("--force-flash"); shift ;;
        --skip-firmware)
            DOCKER_CMD_ARGS+=("--skip-firmware"); shift ;;
        --skip-www)
            DOCKER_CMD_ARGS+=("--skip-www"); shift ;;
        --verbose-build)
            DOCKER_CMD_ARGS+=("--verbose-build"); HAS_ACTION_FLAG=true; shift ;;
        --web-ui|--webui)
            WEB_UI=true; HAS_ACTION_FLAG=true; shift ;;
        --restart-web-ui|--restart-webui)
            RESTART_WEB_UI=true; HAS_ACTION_FLAG=true; shift ;;
        --test)
            RUN_TESTS=true; HAS_ACTION_FLAG=true; shift ;;
        --repro)
            RUN_REPRO=true; HAS_ACTION_FLAG=true; shift ;;
        # Special handling for test arguments
        --all|--web-ui|--builder|--version|--path|--quiet)
            if [ "$RUN_TESTS" = true ]; then
                # Store the current argument
                current_arg="$1"
                TEST_ARGS+=("$current_arg")
                shift

                # If this is --path, also grab its argument
                if [[ "$current_arg" == "--path" && $# -gt 0 && "$1" != "--"* ]]; then
                    TEST_ARGS+=("$1")
                    shift
                fi
            else
                echo "Error: Test option $1 must come after --test" >&2
                show_help
            fi
            ;;
        *)
            echo "Error: Unknown option: $1" >&2; show_help ;;
    esac
done

# --- Check Flags and Decide Action ---
ONLY_BUILD_IMAGE=false

# If --build-image was specified (with or without clean), we only want to build the image
if [ "$BUILD_IMAGE" = true ]; then
    if [ "$CLEAN_IMAGE" = true ]; then
        echo "Building a clean Docker image (removing existing image first)..."
    else
        echo "Only --build-image specified."
    fi
    ONLY_BUILD_IMAGE=true
elif [ "$HAS_ACTION_FLAG" = false ]; then
    # No action flag was specified
    # Display header with version
    # display_header # Already displayed at the top

    # Show simplified help for no arguments
    echo "To use this tool, please specify an action:"
    echo
    printf "%b\n" "\e[32m• For beginners: ./nomadbuild.sh --webui    (Recommended)\e[0m"
    printf "%b\n" "\e[33m• Build firmware: ./nomadbuild.sh --build\e[0m"
    printf "%b\n" "\e[35m• See all options: ./nomadbuild.sh --help\e[0m"
    echo
    exit 0
fi

# Handle clean image request
if [ "$CLEAN_IMAGE" = true ]; then
    if docker image inspect "$IMAGE_NAME" &> /dev/null; then
        echo "Removing existing Docker image: $IMAGE_NAME..."
        if docker rmi -f "$IMAGE_NAME" &> /dev/null; then
            echo "Successfully removed existing Docker image."
            echo "This ensures a completely fresh build after upgrading nomadbuild."
            # Force build image flag to true
            BUILD_IMAGE=true
            # Force no-cache to ensure a completely fresh build
            NO_CACHE=true
        else
            echo "Error: Failed to remove existing Docker image."
            echo "You may need to stop any running containers using this image first."
            exit 1
        fi
    else
        echo "No existing Docker image found. Will build a fresh image."
        BUILD_IMAGE=true
        NO_CACHE=true
    fi
fi

# --- Docker Check ---
if ! command -v docker &> /dev/null; then
    echo "Error: docker command could not be found."
    echo "Please ensure Docker is installed and in your PATH."
    exit 1
fi
# echo "Docker installation verified." # Removed verbosity

BUILD_WAS_PERFORMED=false
IMAGE_EXISTS=false
if docker image inspect "$IMAGE_NAME" &> /dev/null; then
    IMAGE_EXISTS=true
fi

# --- Image Check & Build ---
# Build if image doesn't exist OR if --build-image flag is explicitly set
if [ "$IMAGE_EXISTS" = false ] || [ "$BUILD_IMAGE" = true ]; then
    if [ "$BUILD_IMAGE" = true ] && [ "$IMAGE_EXISTS" = true ] && [ "$CLEAN_IMAGE" = false ]; then
        echo "Forcing rebuild of existing Docker image: $IMAGE_NAME..."
    elif [ "$IMAGE_EXISTS" = false ]; then
        if [ "$CLEAN_IMAGE" = true ]; then
            echo "Building fresh Docker image after clean removal..."
        else
            echo "Docker image '$IMAGE_NAME' not found locally. Building new image..."
        fi
    fi

    # Ensure vendor files are downloaded before building image
    if [ -f "./scripts/download_vendors.sh" ]; then
        echo -n "Setting up vendor JavaScript files... "

        # Define a function for the spinner animation
        spinner() {
            local pid=$1
            local delay=0.2
            local i=1
            local sp="/-\|"
            echo -n " "

            while ps -p $pid > /dev/null; do
                printf "\b%s" "${sp:i++%${#sp}:1}"
                sleep $delay
            done

            printf "\b "
        }

        # Make the script executable
        chmod +x ./scripts/download_vendors.sh

        # Run the download script in the background and show spinner
        ./scripts/download_vendors.sh >/dev/null 2>&1 &
        DOWNLOAD_PID=$!
        spinner $DOWNLOAD_PID

        # Check if the download was successful
        wait $DOWNLOAD_PID
        DOWNLOAD_EXIT_CODE=$?
        if [ $DOWNLOAD_EXIT_CODE -ne 0 ]; then
            printf "failed\n"
            echo "WARNING: download_vendors.sh failed. CDN dependencies may not be properly embedded."
        else
            printf "done\n"
        fi
    else
        echo "WARNING: download_vendors.sh script not found at ./scripts/download_vendors.sh. CDN dependencies may not be properly embedded."
    fi

    # Build command with optional --no-cache flag
    BUILD_CMD="docker build -q" # Restore -q for quiet build, outputting only image ID on success

    if [ "$NO_CACHE" = true ]; then
        # echo "Using --no-cache option as requested."
        BUILD_CMD="$BUILD_CMD --no-cache"
    fi

    BUILD_CMD="$BUILD_CMD -t \"$IMAGE_NAME\" \"$PROJECT_ROOT\""

    # Build the image using docker build command directly from project root
    echo -n "Building Docker image (this may take a few minutes)... "

    # Create a unique temporary file for this run
    TEMP_OUTPUT_FILE="/tmp/docker_build_output.$$"

    # Run the build command in the background and capture its output
    eval $BUILD_CMD > "$TEMP_OUTPUT_FILE" 2>&1 &
    BUILD_PID=$!

    # Show spinner while building
    spinner $BUILD_PID

    # Check if the build was successful
    wait $BUILD_PID
    BUILD_EXIT_CODE=$?

    # Get the build output
    BUILD_OUTPUT=$(cat "$TEMP_OUTPUT_FILE")
    rm -f "$TEMP_OUTPUT_FILE"

    if [ $BUILD_EXIT_CODE -eq 0 ]; then
        printf "done\n"
        echo "Image build complete. ID: $BUILD_OUTPUT" # Output only the image ID on success
        BUILD_WAS_PERFORMED=true
    else
        printf "failed\n"
        echo "Error: Docker image build failed."
        echo "Build output: $BUILD_OUTPUT"
        exit 1
    fi
elif [ "$IMAGE_EXISTS" = true ]; then
    echo "Docker image '$IMAGE_NAME' found locally."
fi

# --- Exit if only build image was requested ---
if [ "$ONLY_BUILD_IMAGE" = true ]; then
    # Add a message about existing firmware if it exists
    if [ -d "$PROJECT_ROOT/firmware" ] && [ -n "$(ls -A "$PROJECT_ROOT/firmware" 2>/dev/null)" ]; then
        echo ""
        echo "Note: Existing firmware files have been preserved in the firmware directory."
        echo "To build firmware, run: ./nomadbuild.sh --build"
    fi
    exit 0
fi

# --- Run Tests if requested ---
if [ "$RUN_TESTS" = true ]; then
    echo "Running tests with options: ${TEST_ARGS[@]}"
    if [ -f "$SCRIPT_DIR/scripts/test.sh" ]; then
        chmod +x "$SCRIPT_DIR/scripts/test.sh"
        if "$SCRIPT_DIR/scripts/test.sh" "${TEST_ARGS[@]}"; then
            echo "Tests completed successfully."
            exit 0
        else
            echo "Error: Tests failed." >&2
            exit 1
        fi
    else
        echo "Error: test.sh script not found at $SCRIPT_DIR/scripts/test.sh" >&2
        exit 1
    fi
fi

# --- Run Reproducibility Check if requested ---
if [ "$RUN_REPRO" = true ]; then
    echo "Running reproducibility check..."

    # Check if we have a tag specified
    TAG_ARG=""
    TAG_VALUE=""
    i=0
    while [ $i -lt ${#DOCKER_CMD_ARGS[@]} ]; do
        if [[ "${DOCKER_CMD_ARGS[$i]}" == "--tag" && $(($i+1)) -lt ${#DOCKER_CMD_ARGS[@]} ]]; then
            TAG_ARG="--tag ${DOCKER_CMD_ARGS[$((i+1))]}"
            TAG_VALUE="${DOCKER_CMD_ARGS[$((i+1))]}"
            break
        fi
        ((i++))
    done

    if [ -z "$TAG_ARG" ]; then
        echo "Error: Reproducibility check requires a tag. Use --tag <VERSION>" >&2
        exit 1
    fi

    # Pass the --repro option to the container
    CMD_IN_CONTAINER=("python3" "-m" "src.builder.cli")
    REPRO_ARGS=("--repro")

    # Add the tag argument
    if [ -n "$TAG_VALUE" ]; then
        REPRO_ARGS+=("--tag" "$TAG_VALUE")
    fi

    # Mount project root's firmware directory
    FIRMWARE_DIR="$PROJECT_ROOT/firmware"
    if [ ! -d "$FIRMWARE_DIR" ]; then
        echo "Creating firmware directory at $FIRMWARE_DIR"
        mkdir -p "$FIRMWARE_DIR"
    fi

    docker run -it --rm -v "$FIRMWARE_DIR:/firmware" "$IMAGE_NAME" "${CMD_IN_CONTAINER[@]}" "${REPRO_ARGS[@]}"

    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 0 ]; then
        echo "Reproducibility check completed successfully."
    else
        echo "Error: Reproducibility check failed." >&2
    fi
    exit $EXIT_CODE
fi



# Function to stop any existing web UI containers
stop_existing_containers() {
    local container_stopped=false

    # Check for existing containers on port 9090
    local existing_container=$(docker ps --format "{{.ID}} {{.Names}}" | grep -E "(9090/tcp|0.0.0.0:9090)" || true)

    # Also specifically check for a container named "nomadbuild-web"
    local existing_nomadbuild=$(docker ps --format "{{.ID}} {{.Names}}" | grep "nomadbuild-web" || true)

    if [ ! -z "$existing_container" ]; then
        local container_id=$(echo $existing_container | cut -d' ' -f1)
        local container_name=$(echo $existing_container | cut -d' ' -f2)
        echo "Stopping container on port 9090: $container_name ($container_id)"
        docker stop $container_id >/dev/null
        container_stopped=true
    fi

    if [ ! -z "$existing_nomadbuild" ] && [ "$existing_nomadbuild" != "$existing_container" ]; then
        local container_id=$(echo $existing_nomadbuild | cut -d' ' -f1)
        local container_name=$(echo $existing_nomadbuild | cut -d' ' -f2)
        echo "Stopping NomadBuild web UI container: $container_name ($container_id)"
        docker stop $container_id >/dev/null
        container_stopped=true
    fi

    if [ "$container_stopped" = true ]; then
        echo "Existing containers have been stopped."
        # Small pause to ensure network ports are freed
        sleep 1
    else
        echo "No existing web UI containers found."
    fi
}

# --- Execute Web UI if Requested ---
if [ "$WEB_UI" = true ] || [ "$RESTART_WEB_UI" = true ]; then
    if [ "$RESTART_WEB_UI" = true ]; then
        echo "Restarting NomadBuild Web UI..."
        stop_existing_containers
    else
        echo "Starting NomadBuild Web UI..."

        # Early exit if a NomadBuild Web UI container is already running
        RUNNING_CONTAINER_ID=$(docker ps -q --filter "name=nomadbuild-web")
        if [ -n "$RUNNING_CONTAINER_ID" ]; then
            printf "\e[33mA NomadBuild Web UI container is already running (ID: $RUNNING_CONTAINER_ID).\e[0m\n"
            echo "Access it at: http://localhost:9090"
            echo "If you wish to restart it use: $0 --restart-webui"
            echo "Or stop it manually: docker stop $RUNNING_CONTAINER_ID"
            exit 0
        fi

        # Check if port 9090 is already in use by a Docker container
        EXISTING_CONTAINER=$(docker ps --format "{{.ID}} {{.Names}}" | grep -E "(9090/tcp|0.0.0.0:9090)" || true)

        if [ ! -z "$EXISTING_CONTAINER" ]; then
            CONTAINER_ID=$(echo $EXISTING_CONTAINER | cut -d' ' -f1)
            CONTAINER_NAME=$(echo $EXISTING_CONTAINER | cut -d' ' -f2)
            printf "\e[33m%s\e[0m\n" "WARNING: Port 9090 is already in use by Docker container: $CONTAINER_NAME ($CONTAINER_ID)"
            echo ""
            echo "To stop the existing container, run:"
            echo "  docker stop $CONTAINER_ID"
            echo ""
            echo "Then try running the web-ui again:"
            echo "  $0 --webui"
            echo ""
            echo "Or use a single command to stop the existing container and start a new one:"
            printf "  \e[32m%s\e[0m\n" "docker stop \$(docker ps --filter=\"name=nomadbuild-web\" -q) && $0 --webui"
            echo ""
            exit 1
        fi
    fi

    # Mount project root's firmware directory
    FIRMWARE_DIR="$PROJECT_ROOT/firmware"
    if [ ! -d "$FIRMWARE_DIR" ]; then
        echo "Creating firmware directory at $FIRMWARE_DIR"
        mkdir -p "$FIRMWARE_DIR"
    fi

    # Run the web UI
    CMD_IN_CONTAINER=("python3" "-m" "src.web_ui")
    # echo "Running web UI container with command: ${CMD_IN_CONTAINER[@]}"

    # Find the browser based on OS
    BROWSER_CMD=""
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS - open in a new window
        BROWSER_CMD="open -n http://localhost:9090"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux - try to find a browser that can open in a new window
        if command -v google-chrome &> /dev/null; then
            BROWSER_CMD="google-chrome --new-window http://localhost:9090"
        elif command -v firefox &> /dev/null; then
            BROWSER_CMD="firefox --new-window http://localhost:9090"
        elif command -v chromium-browser &> /dev/null; then
            BROWSER_CMD="chromium-browser --new-window http://localhost:9090"
        elif command -v xdg-open &> /dev/null; then
            # fallback, may not open new window on all systems
            BROWSER_CMD="xdg-open http://localhost:9090"
            echo "Note: Using xdg-open which may not always open in a new window"
        else
            echo "Cannot auto-open browser. Please navigate to http://localhost:9090 in a new browser window"
        fi
    elif [[ "$OSTYPE" == "msys"* || "$OSTYPE" == "cygwin"* ]]; then
        # Windows
        BROWSER_CMD="start \"NomadBuild Web UI\" http://localhost:9090"
    fi

    # Start the container in detached mode
    # echo "Starting Docker container for NomadBuild Web UI..."
    echo ""
    echo "----------------------------------------------------------------------------------------"
    echo "  NomadBuild Web UI will be available at: http://localhost:9090"
    echo "----------------------------------------------------------------------------------------"
    echo ""

    # Run Docker with a static container name for easy identification
    CONTAINER_ID=$(docker run -d --name nomadbuild-web --rm \
        -p 9090:9090 \
        -v "$FIRMWARE_DIR:/firmware" \
        "$IMAGE_NAME" "${CMD_IN_CONTAINER[@]}" 2>&1)

    # Check if container started successfully
    if [ $? -ne 0 ]; then
        echo "Error starting Docker container: $CONTAINER_ID"
        exit 1
    fi

    if [ -z "$CONTAINER_ID" ]; then
        echo "Failed to start Docker container: Empty container ID returned."
        exit 1
    fi

    echo "Container started with ID: $CONTAINER_ID (name: nomadbuild-web)"

    # Wait for the web server to start before opening browser
    echo "Waiting for web server to become available..."

    MAX_WAIT=60  # Wait up to 60 seconds
    WAIT_INTERVAL=3  # Check every 3 seconds
    ELAPSED=0
    SERVER_READY=false

    while [ $ELAPSED -lt $MAX_WAIT ]; do
        # Check if container is still running
        if ! docker ps -q --filter "id=$CONTAINER_ID" --filter "status=running" >/dev/null 2>&1; then
            echo "Error: Container stopped unexpectedly during startup." >&2
            echo "Container logs:" >&2
            docker logs "$CONTAINER_ID" 2>&1 || echo "Could not retrieve logs." >&2
            exit 1
        fi

        # Try to connect to web server to verify it's up
        if curl -s --fail http://localhost:9090 >/dev/null 2>&1; then
            SERVER_READY=true
            break
        fi

        sleep $WAIT_INTERVAL
        ELAPSED=$((ELAPSED + WAIT_INTERVAL))
    done

    # Final status message
    if [ "$SERVER_READY" = true ]; then
         echo "Web server is ready!"
    else
        echo "Warning: Web server did not respond within $MAX_WAIT seconds, but container is still running." >&2
        echo "Attempting to open browser anyway. You may need to wait longer or refresh." >&2
        # Optionally show last few logs on timeout
        # echo "Last container logs:" >&2
        # docker logs "$CONTAINER_ID" | tail -n 10 >&2
    fi

    # Open browser if command exists
    if [ -n "$BROWSER_CMD" ]; then
        echo "Opening browser to http://localhost:9090 in a new window"
        eval $BROWSER_CMD
    fi

    echo "Web UI is running in the background. Access it at http://localhost:9090"
    echo "To stop the container, run: docker stop $CONTAINER_ID (or docker stop nomadbuild-web)"

    exit 0
fi

# --- Execute Builder ---
echo "Starting NomadBuild container..."
# Mount project root's firmware directory
FIRMWARE_DIR="$PROJECT_ROOT/firmware"
if [ ! -d "$FIRMWARE_DIR" ]; then
    echo "Creating firmware directory at $FIRMWARE_DIR"
    mkdir -p "$FIRMWARE_DIR"
fi

CMD_IN_CONTAINER=("python3" "-m" "src.builder.cli")
echo "Running docker container with command: ${CMD_IN_CONTAINER[@]} ${DOCKER_CMD_ARGS[@]}"

docker run -it --rm -v "$FIRMWARE_DIR:/firmware" "$IMAGE_NAME" "${CMD_IN_CONTAINER[@]}" "${DOCKER_CMD_ARGS[@]}"

EXIT_CODE=$?
exit $EXIT_CODE