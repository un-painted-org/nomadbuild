# Backlog Item 96: Reproducibility Commands

## Description

This backlog item focuses on implementing reproducibility commands in the nomadbuild.sh script to help users verify that their builds are reproducible. The implementation includes adding a `--repro` option to check build reproducibility. All functionality runs exclusively inside the container.

## Requirements

1. Add `--repro` option to nomadbuild.sh
2. Implement reproducibility checks inside the container
3. Ensure all operations run inside the container

## Implementation Details

### 1. Add `--repro` Option to nomadbuild.sh

The `--repro` option is already partially implemented in nomadbuild.sh. It passes the option to the container, which then runs the repro.sh script to perform a reproducibility check for a specific ESP-Miner tag.

Key aspects of the implementation:
- The `--repro` option requires a tag to be specified with the `--tag` option
- nomadbuild.sh passes these options to the container
- Inside the container, the repro.sh script performs two builds of the same tag and compares the results
- It provides clear feedback on whether the builds are reproducible

### 2. Implement Reproducibility Checks

The reproducibility checks are implemented in the repro.sh and repro_builder.py scripts that run inside the container. These scripts:
- Clone the ESP-Miner repository
- Check out a specific tag
- Perform two builds with identical inputs
- Compare the resulting binary files
- Report whether the builds are reproducible

Key aspects of the implementation:
- Normalize file timestamps to ensure reproducibility
- Use SOURCE_DATE_EPOCH to make builds deterministic
- Clean the build environment between runs
- Calculate SHA256 hashes of the binary outputs for comparison
- All operations run inside the container



### 3. Container-Based Implementation

All functionality is implemented to run exclusively inside the container:
- The nomadbuild.sh script only adds command-line options and passes them to the container
- All file operations, command execution, and analysis happen inside the container
- No host-specific code is used except for simple flag additions in nomadbuild.sh

## User Value Analysis

### 1. `--repro` Option

The `--repro` option provides value to users by:
- Allowing them to verify that their builds are reproducible
- Helping them identify issues in the build process that affect reproducibility
- Providing confidence that the build process is reliable and deterministic
- Supporting compliance with best practices for secure and auditable builds

### 2. User Experience Considerations

To ensure a good user experience, the implementation:
- Provides clear and actionable feedback
- Uses consistent terminology and formatting
- Handles errors gracefully
- Includes helpful documentation and examples
- Integrates seamlessly with the existing workflow
- Maintains the container-based approach of nomadbuild

## Testing

The implementation is tested with:
- Unit tests for the reproducibility commands
- Integration tests with the nomadbuild.sh script
- Tests that verify options are correctly passed to the container
- Tests that verify the scripts exist and are executable
- Tests that verify help information is displayed correctly

## Acceptance Criteria

- The `--repro` option is added to nomadbuild.sh and works correctly
- The reproducibility checks provide accurate results
- All functionality runs exclusively inside the container
- The implementation is well-documented and includes examples
- All tests pass
