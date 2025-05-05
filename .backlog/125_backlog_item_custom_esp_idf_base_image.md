# Backlog Item 125: Create Custom ESP-IDF Base Image for ESP32-S3

## Description

This backlog item focuses on creating a custom ESP-IDF Docker base image specifically optimized for ESP32-S3 development. Instead of using the official ESP-IDF image that includes support for all ESP32 variants, we'll build a dedicated image that only includes the components necessary for building Bitaxe firmware for ESP32-S3. This approach will significantly reduce the image size, improve build times, and enhance reproducibility.

## Requirements

1. Build dedicated ESP-IDF image with ESP32-S3 support only
2. Minimize image size by including only required components
3. Create Dockerfile for custom base image
4. Integrate with existing multi-stage build process
5. Document custom image build process

## Implementation Details

### 1. Custom ESP-IDF Base Image

Create a custom ESP-IDF Docker image specifically for ESP32-S3 development:

- Use the ESP-IDF Docker image build process as a reference
- Clone only the specific ESP-IDF version needed (e.g., v5.4.1)
- Install only the ESP32-S3 toolchain
- Include only the necessary components for Bitaxe firmware

Example Dockerfile for the custom base image:
```dockerfile
# Use a minimal Ubuntu base image
FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# Build arguments
ARG IDF_CLONE_URL=https://github.com/espressif/esp-idf.git
ARG IDF_CLONE_BRANCH_OR_TAG=v5.4.1
ARG IDF_CHECKOUT_REF=
ARG IDF_CLONE_SHALLOW=1
ARG IDF_INSTALL_TARGETS=esp32s3

# Install essential packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    wget \
    flex \
    bison \
    gperf \
    python3 \
    python3-pip \
    python3-venv \
    cmake \
    ninja-build \
    ccache \
    libffi-dev \
    libssl-dev \
    dfu-util \
    libusb-1.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create a Python virtual environment
ENV VENV_PATH=/opt/esp/python_env/idf5.4_py3.10_env
RUN python3 -m venv $VENV_PATH

# Set up IDF_PATH and IDF_TOOLS_PATH
ENV IDF_PATH=/opt/esp/idf
ENV IDF_TOOLS_PATH=/opt/esp/tools

# Clone ESP-IDF repository
RUN mkdir -p /opt/esp && \
    cd /opt/esp && \
    if [ "${IDF_CLONE_SHALLOW}" = "1" ]; then \
        git clone --recursive --shallow-submodules -b ${IDF_CLONE_BRANCH_OR_TAG} ${IDF_CLONE_URL} idf; \
    else \
        git clone --recursive -b ${IDF_CLONE_BRANCH_OR_TAG} ${IDF_CLONE_URL} idf; \
    fi && \
    if [ -n "${IDF_CHECKOUT_REF}" ]; then \
        cd idf && \
        git checkout ${IDF_CHECKOUT_REF} && \
        git submodule update --init --recursive; \
    fi

# Install ESP-IDF tools for ESP32-S3 only
RUN cd /opt/esp/idf && \
    $VENV_PATH/bin/python -m pip install --no-cache-dir -r requirements.txt && \
    ./install.sh ${IDF_INSTALL_TARGETS} && \
    rm -rf .git

# Set up environment variables
ENV PATH=$VENV_PATH/bin:$IDF_PATH/tools:$PATH

# Create a script to set up the environment
RUN echo "#!/bin/bash" > /opt/esp/entrypoint.sh && \
    echo "source $IDF_PATH/export.sh" >> /opt/esp/entrypoint.sh && \
    echo "exec \"\$@\"" >> /opt/esp/entrypoint.sh && \
    chmod +x /opt/esp/entrypoint.sh

# Clean up unnecessary files to reduce image size
RUN find $IDF_PATH -name __pycache__ -type d -exec rm -rf {} +; 2>/dev/null || true && \
    find $IDF_PATH -name "*.pyc" -delete && \
    find $IDF_PATH -name "*.pyo" -delete && \
    find $VENV_PATH -name __pycache__ -type d -exec rm -rf {} +; 2>/dev/null || true && \
    find $VENV_PATH -name "*.pyc" -delete && \
    find $VENV_PATH -name "*.pyo" -delete && \
    rm -rf $IDF_PATH/docs $IDF_PATH/examples $IDF_PATH/tools/esp_app_trace $IDF_PATH/tools/test_apps

# Set the entrypoint
ENTRYPOINT ["/opt/esp/entrypoint.sh"]
CMD ["/bin/bash"]
```

### 2. Image Size Optimization

Implement strategies to minimize the image size:

- Use a multi-stage build process
- Remove unnecessary components and tools
- Clean up build artifacts and temporary files
- Strip debug symbols from binaries
- Use a minimal base image

Example optimization techniques:
```dockerfile
# Remove unnecessary components
RUN cd $IDF_PATH/components && \
    # Keep only necessary components
    mkdir -p /tmp/essential_components && \
    cp -r \
        app_trace \
        bootloader \
        bt \
        driver \
        esp_common \
        esp_event \
        esp_hw_support \
        esp_rom \
        esp_system \
        esp_timer \
        esp_wifi \
        freertos \
        hal \
        heap \
        log \
        lwip \
        mbedtls \
        newlib \
        nvs_flash \
        soc \
        spi_flash \
        tcpip_adapter \
        /tmp/essential_components/ && \
    rm -rf * && \
    cp -r /tmp/essential_components/* . && \
    rm -rf /tmp/essential_components

# Strip binaries to reduce size
RUN find $IDF_TOOLS_PATH -type f -executable -exec strip --strip-unneeded {} \; 2>/dev/null || true

# Remove documentation and examples
RUN rm -rf $IDF_PATH/docs $IDF_PATH/examples $IDF_PATH/tools/esp_app_trace $IDF_PATH/tools/test_apps

# Remove git repositories
RUN find $IDF_PATH -name .git -type d -exec rm -rf {} +; 2>/dev/null || true
```

### 3. Custom Base Image Dockerfile

Create a dedicated Dockerfile for building the custom ESP-IDF base image:

- Place the Dockerfile in a dedicated directory (e.g., `tools/docker`)
- Include a README with build instructions
- Add a build script to simplify the build process
- Document all build arguments and their default values

Example build script:
```bash
#!/bin/bash
# build_custom_idf_image.sh

set -e

# Default values
IDF_VERSION="v5.4.1"
IMAGE_TAG="idf-custom:$IDF_VERSION-esp32s3"
SHALLOW_CLONE=1

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --idf-version)
            IDF_VERSION="$2"
            IMAGE_TAG="idf-custom:$IDF_VERSION-esp32s3"
            shift 2
            ;;
        --no-shallow)
            SHALLOW_CLONE=0
            shift
            ;;
        --tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "Building custom ESP-IDF image with the following settings:"
echo "  IDF Version: $IDF_VERSION"
echo "  Image Tag: $IMAGE_TAG"
echo "  Shallow Clone: $SHALLOW_CLONE"
echo

# Build the image
docker build -t "$IMAGE_TAG" \
    --build-arg IDF_CLONE_BRANCH_OR_TAG="$IDF_VERSION" \
    --build-arg IDF_CLONE_SHALLOW="$SHALLOW_CLONE" \
    --build-arg IDF_INSTALL_TARGETS="esp32s3" \
    tools/docker

echo "Build complete. The image is tagged as $IMAGE_TAG"
```

### 4. Integration with Multi-Stage Build

Integrate the custom base image with our existing multi-stage build process:

- Update the Dockerfile template to use the custom base image
- Ensure all necessary environment variables are set
- Verify that the build process works correctly with the new base image
- Add fallback mechanisms in case the custom image is not available

Example integration in the Dockerfile template:
```dockerfile
# Use our custom ESP-IDF image for ESP32-S3
ARG BASE_IMAGE=idf-custom:v5.4.1-esp32s3
ARG BASE_IMAGE_FALLBACK=espressif/idf@sha256:6b4adab7b282e9261a154d7130fb4945a3c28bd35c2e914357c2f522643cb92a

# Try to use the custom image, fall back to the official image if not available
FROM ${BASE_IMAGE} AS builder_custom
FROM ${BASE_IMAGE_FALLBACK} AS builder_fallback

# Use a multi-stage build to determine which base image to use
FROM builder_custom AS builder_check
RUN echo "Using custom ESP-IDF image for ESP32-S3"
FROM builder_fallback AS builder_check_fallback
RUN echo "Using fallback ESP-IDF image"

# Final builder stage
FROM builder_check AS builder

# Rest of the Dockerfile remains the same
# ...
```

### 5. Documentation

Create comprehensive documentation for the custom base image:

- Document the build process
- Explain the benefits of using the custom image
- Provide instructions for updating the image
- Include troubleshooting information
- Document the components included in the image

Example documentation:
```markdown
# Custom ESP-IDF Base Image for ESP32-S3

This directory contains the Dockerfile and build scripts for creating a custom ESP-IDF Docker image specifically optimized for ESP32-S3 development. This custom image is significantly smaller than the official ESP-IDF image and only includes the components necessary for building Bitaxe firmware.

## Building the Image

To build the custom image, run the following command from the project root:

```bash
./tools/docker/build_custom_idf_image.sh
```

This will create an image tagged as `idf-custom:v5.4.1-esp32s3`.

### Build Arguments

The build script accepts the following arguments:

- `--idf-version <version>`: The ESP-IDF version to use (default: v5.4.1)
- `--no-shallow`: Disable shallow cloning of the ESP-IDF repository
- `--tag <tag>`: Custom tag for the image (default: idf-custom:v5.4.1-esp32s3)

## Using the Custom Image

The nomadbuild.sh script will automatically use the custom image if available. If the custom image is not available, it will fall back to the official ESP-IDF image.

## Updating the Image

When a new version of ESP-IDF is released, you can update the custom image by running:

```bash
./tools/docker/build_custom_idf_image.sh --idf-version v5.x.y
```

Then update the `BASE_IMAGE` argument in the Dockerfile template to use the new version.

## Components Included

The custom image includes only the following ESP-IDF components:

- app_trace
- bootloader
- bt
- driver
- esp_common
- esp_event
- esp_hw_support
- esp_rom
- esp_system
- esp_timer
- esp_wifi
- freertos
- hal
- heap
- log
- lwip
- mbedtls
- newlib
- nvs_flash
- soc
- spi_flash
- tcpip_adapter

## Troubleshooting

If you encounter issues with the custom image, try rebuilding it with the `--no-shallow` option, which performs a full clone of the ESP-IDF repository instead of a shallow clone.
```

## Testing

The changes should be tested by:

1. **Build Verification**:
   - Build the custom ESP-IDF base image
   - Verify that the image size is significantly smaller than the official image
   - Check that all necessary components are included

2. **Integration Testing**:
   - Update the Dockerfile template to use the custom base image
   - Build the nomadbuild image using the custom base image
   - Verify that the build process works correctly

3. **Firmware Building**:
   - Build Bitaxe firmware using the custom base image
   - Verify that the firmware builds successfully
   - Compare build times with the official image

4. **Edge Cases**:
   - Test fallback mechanisms when the custom image is not available
   - Verify behavior with different ESP-IDF versions
   - Test with various build options and configurations

## Acceptance Criteria

- Custom ESP-IDF base image is successfully built with ESP32-S3 support only
- Image size is at least 30% smaller than the official ESP-IDF image
- All necessary components for building Bitaxe firmware are included
- Integration with the existing multi-stage build process works correctly
- Documentation for the custom image build process is comprehensive and clear
- Bitaxe firmware builds successfully using the custom base image
- Build times are improved compared to using the official image
