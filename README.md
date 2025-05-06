# NomadBuild

![License: MIT](https://img.shields.io/badge/license-MIT-green) MIT © 2025 marsmensch

> NomadBuild - Self-sovereign Bitaxe firmware builder & flasher.

## Building Trust in Open Source Hardware

The Bitaxe project offers fantastic open-source hardware, but how can you be sure the firmware running on your device truly matches the public source code? Relying solely on pre-compiled binaries introduces trust assumptions about the build process and distribution channel.

**Self-sovereign building** empowers users by allowing them to compile the firmware directly from the official `bitaxeorg/ESP-Miner` source code within a controlled, reproducible environment. NomadBuild aims to make this process secure and accessible.

The "gold standard" is **reproducible builds**, where identical source code and build environments produce byte-for-byte identical binaries. While perfectly matching official release binaries is difficult due to subtle environment variations, NomadBuild focuses on ensuring **internally reproducible builds** within its controlled Docker environment. This is achieved by using pinned versions for all dependencies (base image, system packages, Python packages, toolchain) and controlling build timestamps, providing high confidence in the generated firmware's integrity relative to the chosen source tag.

*(See [docs/INTRODUCTION.md](docs/INTRODUCTION.md) for a more detailed discussion on the importance of self-sovereign and reproducible builds.)*
*(See [docs/REPRODUCIBILITY_NOTES.md](docs/REPRODUCIBILITY_NOTES.md) for details on the reproducibility methodology.)*

## Features

* **Self-Sovereign Builds:** Compile Bitaxe firmware directly from official sources in a controlled Docker environment.
* **Reproducibility Focused:** Ensures internally reproducible builds using pinned dependencies (`config.yaml`, `Dockerfile`) and fixed timestamps (`SOURCE_DATE_EPOCH`).
* **Web UI & CLI:** Interact via an easy-to-use web interface or a command-line script (`nomadbuild.sh`).
* **Tag-Based Builds:** Build specific, tagged releases from the `bitaxeorg/ESP-Miner` repository.
* **One-Click Flashing:** Flash built firmware (and web UI) over the network (OTA) to one or multiple devices.
* **Multi-Device Flashing:** Flash multiple Bitaxe devices using a simple CSV file (`--flash-csv`).
* **Device Verification:** Performs strict checks to ensure compatibility before flashing.
* **Build Management:** Cancelable builds, real-time logs, and progress indicators via the Web UI.
* **Custom Versioning:** Appends a `-sovereign` suffix to distinguish self-built firmware.
* **Comprehensive Testing:** Includes over 140 tests covering build logic, flashing, and the Web UI.

## Installation

1.  **Prerequisites:** Ensure you have Docker installed and running.
2.  **Clone the Repository:**

        git clone https://github.com/marsmensch/nomadbuild.git
        cd nomadbuild

3.  **Build the Docker Image:** This command uses `config.yaml` and `Dockerfile.template` to generate the final `Dockerfile` and builds the image. Dependency versions are strictly pinned for reproducibility.

        # Build or update the local Docker image
        ./nomadbuild.sh --build-image

        # Optional: Clean previous image and firmware files first
        # ./nomadbuild.sh --build-image clean

## Usage

### Web Interface (Recommended)

Launch the web UI and access it in your browser:

    ./nomadbuild.sh --webui

Navigate to `http://localhost:9090` and follow the on-screen steps to select a version, build the firmware, and flash your device(s).

**Screenshots:**

* **Build Process:**
    ![NomadBuild Build Screen](img/BUILD.jpg)

* **Flashing Firmware:**
    ![NomadBuild Flash Screen](img/FLASH.jpg)

* **Build & Flash Flow:**
    ![Bitaxe Firmware Build and Flash Process](img/BUILD_AND_FLASH.gif)

### Command Line Interface (CLI)

Use the `nomadbuild.sh` script for command-line operations:

    # Build the latest stable firmware tag
    ./nomadbuild.sh --build

    # Build a specific firmware tag
    ./nomadbuild.sh --tag v2.7.0

    # Build and flash to a single device IP
    ./nomadbuild.sh --tag v2.7.0 --flash-ip 192.168.1.100

    # Build and flash multiple devices from a CSV file
    # (CSV format: one IP address per line, comments start with #)
    ./nomadbuild.sh --tag v2.7.0 --flash-csv devices.csv

    # Force flashing without interactive confirmation
    ./nomadbuild.sh --tag v2.7.0 --flash-ip 192.168.1.100 --force-flash

    # See all options
    ./nomadbuild.sh --help

*(See [docs/USAGE.md](docs/USAGE.md) for more detailed command-line instructions.)*

### Build Artifacts

Built firmware files are stored in the `firmware/` directory, named with the version tag (e.g., `firmware/esp-miner-v2.7.0.bin`, `firmware/www-v2.7.0.bin`). A `build_info.json` file containing build details is also created in this directory.

## Configuration

NomadBuild uses `config.yaml` to define and pin all dependencies:

* Base Docker image (`espressif/idf`) digest
* Toolchain versions (GCC, CMake, Python, etc.)
* APT package versions
* Python package versions

The `scripts/generate_dockerfile.py` script uses `config.yaml` and `Dockerfile.template` to create the final `Dockerfile` used for building the image, ensuring all versions are locked according to the configuration.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests on the GitHub repository.

## Testing

NomadBuild includes a comprehensive test suite using `pytest`. Tests are designed to run *inside* the Docker container to ensure a consistent environment.

To run the tests:

    # Ensure the Docker image is built on a clean baseline first
    ./nomadbuild.sh --build-image clean

    # Run all tests (quietly)
    ./nomadbuild.sh --test

*(See [docs/TESTING.md](docs/TESTING.md) and [docs/WEB_UI_TESTING.md](docs/WEB_UI_TESTING.md) for more details on test organization and execution.)*

## Reproducibility Check

You can verify the internal reproducibility of the build process for a specific tag:

    ./nomadbuild.sh --repro --tag v2.7.0

This script runs the build twice within the Docker container for the specified tag and compares the SHA-256 hashes of the generated generic merged binaries. *(See [docs/REPRODUCIBILITY_NOTES.md](docs/REPRODUCIBILITY_NOTES.md))*

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgements

* This project relies heavily on the excellent open-source work by the **Bitaxe Community** ([bitaxe.org](https://bitaxe.org/), [ESP-Miner Repository](https://github.com/bitaxeorg/ESP-Miner)).
* Built using the official **Espressif IDF Docker image**.
* Uses various open-source libraries (See Attributions in the Web UI).