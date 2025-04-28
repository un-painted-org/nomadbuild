# NomadBuild

![License](https://img.shields.io/badge/license-MIT-green)

> Self-sovereign Bitaxe firmware builder & flasher.

## TL;DR Quick-Start

```bash
# 1. Build (or update) the local Docker image
./nomadbuild.sh --build-image

# 2. Launch the Web-UI
./nomadbuild.sh --webui
```

Navigate to http://localhost:9090 and follow the on-screen steps to build or flash your Bitaxe firmware.

## Features

* 100 % reproducible builds from upstream ESP-Miner sources
* One-click flashing over LAN
* Cancelable builds, progress bar, realtime logs
* Future: NerdQAxe++ support, automated release images

## Want to hack?

```bash
# Run tests
./scripts/test.sh --quiet
```

See `docs/TESTING.md` for detailed guidance.

## License

MIT © 2025 marsmensch

## Motivation: Building Trust in Open Source Hardware

The Bitaxe project offers fantastic open-source hardware, but how can you be sure the firmware running on your device truly matches the public source code? Relying solely on pre-compiled binaries introduces trust assumptions about the build process and distribution channel.

**Self-sovereign building** empowers users by allowing them to compile the firmware directly from the official source code within a controlled environment. This tool aims to make that process accessible.

The "gold standard" is **reproducible builds**, where identical source code and build environments produce byte-for-byte identical binaries. While perfectly matching official release binaries is difficult due to subtle environment variations, this tool focuses on ensuring **internally reproducible builds** within its controlled Docker environment, providing high confidence in the generated firmware's integrity relative to the chosen source tag.

*(See [docs/INTRODUCTION.md](docs/INTRODUCTION.md) for a more detailed discussion on the importance of self-sovereign and reproducible builds.)*

## Usage

### Prerequisites

*   Docker installed and running.

### Running NomadBuild

NomadBuild is run using a single script from the project root directory. This script handles checking Docker, building the required `nomadbuild` Docker image if it's missing or requested, and then executing the build/flash process within the container.

**Scripts:**

*   **Linux/macOS:** `nomadbuild.sh`
*   **Windows (PowerShell):** `nomadbuild.ps1`

**How it Works:**
1.  Checks if Docker is running.
2.  Checks if the `nomadbuild` Docker image exists locally.
3.  If the image is missing, or if the `--build-image` (Linux/macOS) or `-BuildImage` (Windows) flag is provided, it will build/rebuild the image.
4.  **Requires at least one action flag** (`--build`, `--tag`, `--flash-ip`) to proceed with running the container process. If only `--build-image` is provided, it exits after building the image.
5.  It runs the builder process inside a container, passing the relevant arguments to the Python script.

**Arguments:**

*   **Action Flags (At least one required to run container):**
    *   `--build` / `-Build`: Build the latest stable firmware tag.
    *   `--tag <TAG>` / `-Tag <TAG>`: Build a specific firmware tag (e.g., `v2.6.3`).
    *   `--flash-ip <IP,..>` / `-FlashIP <IP,..>`: Flash firmware (latest stable unless `--tag` specified) to one or more comma-separated IP addresses. Implies a build.
*   **Image Build Flag:**
    *   `--build-image` / `-BuildImage`: Force build/rebuild of the `nomadbuild` Docker image before running any other action. If this is the *only* flag provided, the script exits after the build.
*   **Build/Flash Modifiers:**
    *   `--force-flash` / `-ForceFlash`: Skip interactive confirmation before flashing.
    *   `--skip-firmware` / `-SkipFirmware`: Skip flashing main firmware (`esp-miner.bin`).
    *   `--skip-www` / `-SkipWWW`: Skip flashing web UI (`www.bin`).
    *   `--verbose-build` / `-VerboseBuild`: Stream verbose `idf.py build` output to console.
*   **Help:**
    *   `-h`, `--help` / `-Help`: Display the help message and exit.

**Examples:**

*   **Build Latest Stable Tag:**
    *   Linux/macOS: `./nomadbuild.sh --build`
    *   Windows: `.\nomadbuild.ps1 -Build`

*   **Build Specific Tag:**
    *   Linux/macOS: `./nomadbuild.sh --tag v2.6.3`
    *   Windows: `.\nomadbuild.ps1 -Tag v2.6.3`

*   **Flash Latest Stable Tag:**
    *   Linux/macOS: `./nomadbuild.sh --flash-ip 192.168.1.100`
    *   Windows: `.\nomadbuild.ps1 -FlashIP 192.168.1.100`

*   **Build v2.6.3 and Force Flash:**
    *   Linux/macOS: `./nomadbuild.sh --tag v2.6.3 --flash-ip 1.2.3.4 --force-flash`
    *   Windows: `.\nomadbuild.ps1 -Tag v2.6.3 -FlashIP 1.2.3.4 -ForceFlash`

*   **Only Ensure Docker Image is Built/Updated:**
    *   Linux/macOS: `./nomadbuild.sh --build-image`
    *   Windows: `.\nomadbuild.ps1 -BuildImage`

*   **Force Image Rebuild and Build Specific Tag:**
    *   Linux/macOS: `./nomadbuild.sh --build-image --tag v2.6.3`
    *   Windows: `.\nomadbuild.ps1 -BuildImage -Tag v2.6.3`

*   **Display Help:**
    *   Linux/macOS: `./nomadbuild.sh --help`
    *   Windows: `.\nomadbuild.ps1 -Help`

Built artifacts (e.g., `esp-miner-v2.6.3.bin`, `www-v2.6.3.bin`) and logs (`build.log`, `idf_build_output.log` unless using `--verbose-build`) will appear in the `./firmware` directory on your host machine.

### Check Internal Build Reproducibility

Use the included wrapper script `scripts/repro.sh` to verify that the build process itself is deterministic within the standard Docker environment. This requires specifying the tag to check.

```bash
# Check reproducibility of a specific tag
./scripts/repro.sh --tag v2.6.3
```
*(Note: This checks internal consistency, not against official release factory images. See [docs/REPRODUCIBILITY_NOTES.md](docs/REPRODUCIBILITY_NOTES.md) for details).*

## Build Process Details

*   **Docker Image:** The `nomadbuild` Docker image is built using the official `espressif/idf:v5.4` Docker image for a consistent and reproducible ESP-IDF toolchain.
*   **Tag-Based Builds:** The script fetches and builds specific, tagged releases from the official `bitaxeorg/ESP-Miner` repository.
*   **Reproducibility Focused:**
    *   Sets `SOURCE_DATE_EPOCH` based on the commit timestamp of the selected tag to ensure timestamp consistency.
    *   Requires necessary steps for reproducibility (timestamp retrieval) to succeed.
*   **Custom Version Suffix:** Automatically appends a `-sovereign` suffix to the version string (via `version.txt`) built into the firmware, distinguishing self-built firmware.
*   **Artifact Analysis:** Parses build outputs (`flasher_args.json`, partition tables, binary sizes) for verification and consistency checks.
*   **Versioned Output Files:** Copies final binaries to the output volume with the version tag appended (e.g., `esp-miner-v2.6.3.bin`).
*   **Web UI Notice Injection:** Modifies the AxeOS source code (`app.topbar.component.html`) *before* building to inject a small text notice below the logo, identifying it as a self-build.
*   **Optional OTA Flashing:** Can flash the built `esp-miner.bin` (firmware) and `www.bin` (web UI) directly to one or more Bitaxe devices via their network API.
*   **Interactive Confirmation:** Prompts the user before flashing each device (can be overridden with `--force-flash`).
*   **Device Identification:** Attempts to identify the connected Bitaxe model using API information and `models.json` config, displaying it for user awareness.
*   **Post-Flash Verification:** Checks if the device comes back online after firmware flashing and verifies the expected version string is reported via the API.
*   **Internal Reproducibility Verified:** The build process uses fixed versions and timestamps to ensure that building the same tag twice within the provided Docker environment produces identical *generic merged binaries*, verified using the `repro.sh` script.

* GitHub Repository: https://github.com/marsmensch/nomadbuild