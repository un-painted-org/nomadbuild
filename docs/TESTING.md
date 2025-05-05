# TESTING

This document outlines how to run the full test suite for the project, both inside Docker and in a local Python environment.

## Project Rules Reminder
- Do not mark backlog items as completed without explicit instruction.
- Do not delete files; any removals must be moved to the `archive/` directory.
- Only work on a single backlog item at a time.

## Prerequisites

### Using Docker
- Ensure [Docker](https://www.docker.com/) is installed and running.
- The Docker image `nomadbuild` should be built. To build, run:
  ```bash
  docker build -t nomadbuild .
  ```

## Running Tests with Docker

From the project root, run the provided test script:

```bash
# Run all tests (default)
./scripts/test.sh --all

# Run only builder tests
./scripts/test.sh --builder

# Run only web UI tests
./scripts/test.sh --web-ui

# Run version-related tests
./scripts/test.sh --version

# Run tests in a specific path
./scripts/test.sh --path src/tests/my_test_file.py

# Run quietly (minimal output)
./scripts/test.sh --quiet
```

The script will:
1. Verify or build the `nomadbuild` image.
2. Mount the project into the container.
3. Clear Python bytecode files.
4. Invoke `pytest` with the selected path.

## Test Organization

- `src/tests/test_builder_build.py`: Unit tests covering the builder logic.
- `src/tests/test_builder_gitops.py`: Integration-style tests for Git operations in the build process.
- Additional tests for web UI and version management may be found under `src/tests/`.

---

# Running the NomadBuild Test Suite

NomadBuild ships with a comprehensive pytest suite covering build orchestration, flashing helpers, and the Web-UI backend.

## Using Docker (recommended)

```bash
# Ensure the image is built
./nomadbuild.sh --build-image

# Run tests inside the container
./scripts/test.sh --quiet
```

## Container Environment Requirement

**Important**: All tests are designed to run exclusively inside the Docker container environment. This ensures reproducibility and consistent test results across different development environments.

The test suite includes verification that tests are running inside a container environment and will fail with a clear error message if run outside the container.

Always use the provided `./scripts/test.sh` script to run tests, which ensures they run inside the Docker container.

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