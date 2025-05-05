# Backlog Item 105: Integrate Reproducibility Commands into nomadbuild.sh

## Description

Currently, reproducibility checks are performed using `scripts/repro.sh`, but the documentation incorrectly suggests that these commands are integrated into `nomadbuild.sh` with options like `--repro`, `--binary-diff`, etc. These commands need to be properly integrated into the main `nomadbuild.sh` script to provide a unified interface as documented.

## Requirements

1. Modify `nomadbuild.sh` to support the following options:
   - `--repro`: Run reproducibility checks (equivalent to `scripts/repro.sh`)
   - `--tag <tag>`: Specify the tag to check for reproducibility
   - `--binary-diff`: Enable binary diffing when hashes don't match
   - `--clean-container`: Use clean containers for each build
   - `--output-dir <path>`: Specify output directory for reproducibility artifacts

2. Ensure proper parameter validation and error handling

3. Update help text in `nomadbuild.sh` to document these new options

4. Implement proper forwarding of these options to the underlying `scripts/repro.sh` script

5. Test the implementation thoroughly to ensure it works as expected

## Acceptance Criteria

1. Running `./nomadbuild.sh --repro --tag v2.6.3` successfully performs a reproducibility check
2. All documented options work correctly
3. Appropriate error messages are displayed when invalid options are provided
4. Help text clearly explains the available options
5. Documentation accurately reflects the actual functionality

## Notes

This backlog item is critical as the current documentation incorrectly suggests functionality that doesn't exist, which could lead to user confusion and frustration.

## Priority

High - This is a critical fix to align the actual functionality with the documentation.
