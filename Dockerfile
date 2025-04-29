# Use the official ESP-IDF image matching the version used in ESP-Miner devcontainer
# Reference: https://github.com/bitaxeorg/ESP-Miner/blob/master/.devcontainer/Dockerfile
FROM espressif/idf:v5.4.1

# Set environment variables to non-interactive (avoids prompts during apt-get)
ENV DEBIAN_FRONTEND=noninteractive

# Install Node.js (v22.x as per ESP-Miner Dockerfile reference)
# Reference: https://github.com/nodesource/distributions#debian-versions
# Need sudo potentially, or run as root (espressif/idf image likely runs as root or specific user)
# Assuming root access based on standard Docker practices and ESP-IDF image needing tool access
USER root

# --- Copy and Process APT Pinning Configuration --- #
COPY build/apt_pins.conf /tmp/apt_pins.conf
# Generate individual APT preference files for each pinned package
RUN while IFS= read -r line || [[ -n "$line" ]]; do \
        if [[ "$line" =~ ^# ]] || [[ -z "$line" ]]; then continue; fi; \
        package=$(echo "$line" | cut -d '=' -f1); \
        version=$(echo "$line" | cut -d '=' -f2); \
        # Create a specific pin file for the package
        PIN_FILE="/etc/apt/preferences.d/pin-$package"; \
        echo "Generating pin file: $PIN_FILE for $package=$version"; \
        # Write the record using printf for better control over newlines
        printf "Package: %s\n" "$package" > "$PIN_FILE"; \
        printf "Pin: version %s\n" "$version" >> "$PIN_FILE"; \
        printf "Pin-Priority: 1001\n" >> "$PIN_FILE"; \
    done < /tmp/apt_pins.conf && \
    # Verify file content for debugging
    echo "--- Generated APT Preferences --- " && ls -l /etc/apt/preferences.d/ && cat /etc/apt/preferences.d/pin-* && echo "-------------------------------"

# --- Install System Dependencies (versions controlled by pinning) and Node.js --- #
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    pandoc \
    perl \
    python3-requests \
    python3-pip \
    python3-venv \
    # Setup NodeSource repo BEFORE attempting to install nodejs
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    # Install nodejs (version is pinned via preferences file)
    && apt-get install nodejs -y \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Pre-install Python dependencies in the ESP-IDF environment
# Set up a virtual environment for Python dependencies
ENV VENV_PATH=/opt/venv
RUN python3 -m venv $VENV_PATH
ENV PATH="$VENV_PATH/bin:$PATH"
# Install dependencies into the virtual environment
RUN pip install \
    flask==3.1.0 flask-socketio==5.5.1 pytest==8.3.5 pytest-mock==3.14.0 pytest-sugar==1.0.0 \
    requests==2.32.3 werkzeug==3.1.3 jinja2==3.1.6 itsdangerous==2.2.0 \
    blinker==1.9.0 python-socketio==5.13.0 python-engineio==4.12.0 \
    bidict==0.23.1 simple-websocket==1.1.0 h11==0.14.0 wsproto==1.2.0

# Node/NPM should now be in PATH

# --- Setup Builder Script --- 
# Create a working directory
WORKDIR /app

# Copy application code and scripts
COPY src/ /app/src/
COPY scripts/ /app/scripts/
COPY docs/ /app/docs/

# Create necessary directories
RUN mkdir -p /app/src/web_static/vendor/js /app/src/web_static/img /app/src/web_static/version /app/src/web_static/fonts

# Download and include vendor JavaScript libraries & fonts
RUN chmod +x /app/scripts/download_vendors.sh && /app/scripts/download_vendors.sh

# Make version update script executable
RUN chmod +x /app/scripts/update_version.sh

# Update version information in templates during build time
# This will be updated again at runtime by the entrypoint script
RUN /app/scripts/update_version.sh

# Copy tests (after dependencies are installed)
COPY src/tests/ /app/src/tests/

# Prepare firmware directory and entrypoint wrapper
RUN mkdir -p /firmware && chmod +x /app/scripts/entrypoint_wrapper.sh

# Define the volume mount point
VOLUME /firmware

# Expose the web server port
EXPOSE 9090

# The base image's entrypoint likely sources /opt/esp/idf/export.sh
# Verify PATH includes idf.py and Node executables
# RUN echo $PATH && which idf.py && which node && which npm # For debugging image build if needed

# Set the custom entrypoint wrapper script
ENTRYPOINT ["/app/scripts/entrypoint_wrapper.sh"]

# --- Verify Pinned Package Versions --- #
RUN chmod +x /app/scripts/verify_pinned_versions.sh && \
    /app/scripts/verify_pinned_versions.sh /tmp/apt_pins.conf

# Default command (if no args are passed to docker run)
# CMD ["python3", "-m", "src.bitaxe_builder"] # Removed - Command is now always passed via nomadbuild scripts 