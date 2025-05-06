# TESTING

This document outlines how to run the full test suite for the project, both inside Docker and in a local Python environment.

## Prerequisites

### Using Docker
- Ensure [Docker](https://www.docker.com/) is installed and running.
- The Docker image `nomadbuild` should be built. To build, run:
  ```bash
  ./nomadbuild.sh --build-image
  ```

## Running Tests with Docker

From the project root, run the provided test script:

```bash
# Run all tests
./nomadbuild.sh --test
```

The script will:
1. Verify or build the `nomadbuild` image.
2. Mount the project into the container.
3. Clear Python bytecode files.
4. Invoke `pytest` to run all tests.

**Note:** While the `--test` command supports additional arguments like `--all`, `--builder`, `--web-ui`, `--version`, `--path`, and `--quiet`, these may not work as expected when passed through `nomadbuild.sh`. For more specific test runs, use the `scripts/test.sh` script directly inside the container.

## Test Organization

- `src/tests/test_builder_build.py`: Unit tests covering the builder logic.
- `src/tests/test_builder_gitops.py`: Integration-style tests for Git operations in the build process.
- Additional tests for web UI and version management may be found under `src/tests/`.

## Container Environment Requirement

**Important**: All tests are designed to run exclusively inside the Docker container environment. This ensures reproducibility and consistent test results across different development environments.

The test suite includes verification that tests are running inside a container environment and will fail with a clear error message if run outside the container.

Always use the provided `./nomadbuild.sh --test` command to run tests, which ensures they run inside the Docker container.

## What Gets Tested?

| Area | File Pattern |
| --- | --- |
| Build orchestration | `src/tests/test_builder_*` |
| Git operations | `src/tests/test_builder_git_ops.py` |
| Device helpers | `src/tests/test_builder_device.py` |
| CSV flashing | `src/tests/test_flash_csv.py` |
| Flash verification | `src/tests/test_flash_verification_failure.py` |
| Web-UI socket events | `src/tests/test_web_ui.py` |

All tests must pass (currently over 140 tests) before merging or tagging a release.

## Project Scripts and Their Responsibilities

The project includes several shell scripts that handle different aspects of the build, test, and deployment process. Here's a comprehensive table of the main scripts and their responsibilities:

| Script | Location | Responsibility |
| --- | --- | --- |
| `nomadbuild.sh` | Project root | Main entry point script that provides a unified interface for all operations (build, flash, test, etc.) |
| `entrypoint_wrapper.sh` | `scripts/` | Sets up the ESP-IDF environment and executes commands inside the Docker container |
| `test.sh` | `scripts/` | Runs the test suite inside the Docker container with various options |
| `repro.sh` | `scripts/` | Performs reproducibility checks for a specific ESP-Miner tag |
| `run_repro_check.sh` | `scripts/` | Internal script called by `repro.sh` to execute the reproducibility check |
| `generate_dockerfile.sh` | `scripts/` | Generates the Dockerfile from config.yaml and Dockerfile.template |
| `generate_dockerfile.py` | `scripts/` | Python script called by generate_dockerfile.sh to handle the actual generation |
| `download_vendors.sh` | `scripts/` | Downloads vendor JavaScript libraries for the web UI |
| `check_vendor_files.sh` | `scripts/` | Verifies that vendor JavaScript libraries are present |
| `update_version.sh` | `scripts/` | Updates version information in templates |
| `verify_base_image_digest.sh` | `scripts/` | Verifies that the base image digest matches the pinned configuration |
| `verify_container.sh` | `scripts/` | Verifies that code is running inside a container |
| `verify_pinned_versions.sh` | `scripts/` | Verifies that installed packages match the pinned versions |
| `verify_toolchain_versions.sh` | `scripts/` | Verifies that toolchain versions match the pinned versions |
| `add_license_headers.sh` | `scripts/` | Adds license headers to source files |

These scripts work together to provide a seamless experience for building, testing, and deploying the firmware.

## Advanced Testing Features

### Testing with Custom ESP-Miner Repository

For developers working on ESP-Miner forks or pull requests, NomadBuild supports building firmware from custom ESP-Miner repositories using an environment variable:

```bash
# Build from a custom ESP-Miner repository
NOMADBUILD_ESP_MINER_REPO_URL="https://github.com/yourusername/ESP-Miner.git" ./nomadbuild.sh --build --tag v2.7.0

# Note: The --tag parameter only works with actual tags, not branches
# To test a branch, you need to create a tag in your fork first
```

This feature is particularly useful for:
- Testing tagged releases from your fork before submitting pull requests
- Verifying fixes for issues by creating a tag in your fork
- Testing experimental features by creating tags in your development branches

To test changes from a branch:
1. Push your changes to your fork
2. Create a tag in your fork (e.g., `git tag v2.7.0-myfeature && git push origin v2.7.0-myfeature`)
3. Use that tag with the NOMADBUILD_ESP_MINER_REPO_URL environment variable

When using a custom repository URL, NomadBuild will display a clear warning indicating that a non-standard source is being used.