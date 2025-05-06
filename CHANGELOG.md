# Changelog

All notable changes to the NomadBuild project will be documented in this file.

## [v0.9.6] - 2025-05-06

### Fixed
- Fixed git tag verification in web UI to properly handle tag output format
- Fixed web UI build log copy functionality during and after builds
- Ensured attribution modal works during builds
- Fixed repository URL format in build_info.json
- Fixed entrypoint_wrapper.sh permissions

### Added
- Added comprehensive tests for git tag verification
- Added implementation summaries for completed backlog items

### Changed
- Updated help text with new tagline and simplified options
- Updated documentation for CSV-based flashing

## [v0.9.5] - 2025-05-05

### Added
- Implemented CSV-based multi-device flashing with `--flash-csv` parameter
- Added negative test cases for CSV flashing
- Added improved error handling for flashing operations

### Changed
- Made `--flash-ip` and `--flash-csv` options mutually exclusive
- Updated documentation to clarify that flash options are mutually exclusive
- Improved user experience by simplifying CSV file handling messages
- Enhanced CSV file handling by copying file into container instead of mounting
- Fixed order of build and flash summaries to show build summary first

## [v0.9.4] - 2025-04-30

### Added
- Implemented `--build-image clean` parameter to clean firmware files and rebuild Docker image
- Added spinner animation for vendor setup and Docker build processes
- Added color coding to CLI output for better readability

### Changed
- Optimized CLI output for flashing with cleaner messages and better error handling
- Improved user experience with better build and flash summaries
- Enhanced spinner animation with cursor hiding/showing
- Updated README.md to include git clone instructions in Quick-Start section

### Fixed
- Fixed spinner animation cursor positioning and output formatting
- Fixed `--build-image clean` to not show build summary
- Added helpful message about preserved firmware when using `--build-image clean`

## [v0.9.3] - 2025-04-30

### Added
- Implemented multi-stage Docker builds for better performance and smaller image size
- Added reproducibility checks to verify build consistency
- Moved backlog to .backlog directory for better organization

### Changed
- Pinned base image and toolchain versions for improved reproducibility
- Added .config.yaml.md5 to .gitignore

## Key Features Added Since v0.9.3

1. **CSV-Based Multi-Device Flashing**
   - Flash multiple devices at once using a simple CSV file
   - Improved error handling and device verification
   - Clear success/failure reporting for each device

2. **Build Process Improvements**
   - Added `--build-image clean` option for fresh Docker image and clean firmware directory
   - Implemented spinner animation for long-running processes
   - Enhanced CLI output with color coding and better formatting

3. **Web UI Enhancements**
   - Fixed git tag verification for more reliable builds
   - Improved build log functionality during and after builds
   - Fixed attribution modal accessibility

4. **Reproducibility and Testing**
   - Added comprehensive tests for git tag verification
   - Fixed repository URL format in build information
   - Enhanced error handling throughout the application

5. **Documentation and User Experience**
   - Updated help text with clearer options and examples
   - Improved documentation for CSV-based flashing
   - Enhanced error messages and user feedback
