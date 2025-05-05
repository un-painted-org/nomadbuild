# Backlog Item 106: Integrate Test Commands into nomadbuild.sh

## Description

Currently, testing is performed using `scripts/test.sh`, but the documentation incorrectly suggests that these commands are integrated into `nomadbuild.sh` with options like `--test`, `--test-builder`, etc. These commands need to be properly integrated into the main `nomadbuild.sh` script to provide a unified interface as documented.

## Requirements

1. Modify `nomadbuild.sh` to support the following options:
   - `--test`: Run all tests (equivalent to `scripts/test.sh --all`)
   - `--test-builder`: Run only builder tests
   - `--test-web-ui`: Run only web UI tests
   - `--test-version`: Run version-related tests
   - `--test-path <path>`: Run tests in a specific path
   - `--test-quiet`: Run tests with minimal output
   - `--test-native`: Run tests in the local environment instead of in Docker

2. Ensure proper parameter validation and error handling

3. Update help text in `nomadbuild.sh` to document these new options

4. Implement proper forwarding of these options to the underlying `scripts/test.sh` script

5. Test the implementation thoroughly to ensure it works as expected

## Acceptance Criteria

1. Running `./nomadbuild.sh --test` successfully runs all tests
2. All documented test options work correctly
3. Appropriate error messages are displayed when invalid options are provided
4. Help text clearly explains the available options
5. Documentation accurately reflects the actual functionality

## Notes

This backlog item is important as the current documentation incorrectly suggests functionality that doesn't exist, which could lead to user confusion and frustration.

## Priority

High - This is an important fix to align the actual functionality with the documentation.
