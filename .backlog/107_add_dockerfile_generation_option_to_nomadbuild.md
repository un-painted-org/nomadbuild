# Backlog Item 107: Add Dockerfile Generation Option to nomadbuild.sh

## Description

The documentation incorrectly suggests that `nomadbuild.sh` has a `--generate-dockerfile` option to generate a new Dockerfile from the configuration file. This functionality needs to be properly integrated into the main `nomadbuild.sh` script to provide a unified interface as documented.

## Requirements

1. Modify `nomadbuild.sh` to support the following option:
   - `--generate-dockerfile`: Generate a new Dockerfile from the configuration file without building the image

2. Ensure proper parameter validation and error handling

3. Update help text in `nomadbuild.sh` to document this new option

4. Implement the functionality to call the appropriate script for Dockerfile generation

5. Test the implementation thoroughly to ensure it works as expected

## Acceptance Criteria

1. Running `./nomadbuild.sh --generate-dockerfile` successfully generates a new Dockerfile
2. The option works correctly and generates a valid Dockerfile
3. Appropriate error messages are displayed when there are issues with the configuration file
4. Help text clearly explains the available option
5. Documentation accurately reflects the actual functionality

## Notes

This backlog item is needed to align the actual functionality with the documentation. Currently, users need to manually run the Dockerfile generation script or rely on the automatic generation during the build process.

## Priority

Medium - This is a useful feature that would improve the user experience, but it's not as critical as the reproducibility and testing commands.
