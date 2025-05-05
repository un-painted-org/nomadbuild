# Backlog Item: Enhance CSV-Based Multi-Device Flashing with Version Targeting

## Description
Enhance the CSV-based multi-device flashing feature to support specifying target firmware versions for each device in the CSV file. This will allow users to flash different devices with different firmware versions in a single operation.

## Requirements
1. Extend the CSV file format to optionally include a firmware version after the IP address (comma-separated)
2. If no firmware version is specified for a device, use the current stable version
3. If a firmware version is specified, ensure that exact version is used for that device
4. Group devices by firmware version to minimize build operations
5. For each firmware version group:
   - Build the specific firmware version
   - Flash all devices in that group with the built firmware
6. Maintain all existing device verification and safety measures
7. Provide clear progress reporting for each firmware version build and device flash

## Implementation Details

### CSV File Format
- Extended format with optional firmware version after the IP address
- Example:
  ```
  # Bitaxe Gammas that will always get the latest stable version
  192.168.1.100 
  192.168.1.101

  # Bitaxe Supras on my tested v2.6.5 release
  192.168.1.102, v2.6.5
  192.168.1.103, v2.6.5

  # Bitaxe Ultras on the older v2.6.1 release
  192.168.1.104, v2.6.1
  192.168.1.105, v2.6.1

  # Another Bitaxe Gamma, but pinned to at the
  # time of writing current stable v2.7.0 release
  192.168.1.106, v2.7.0
  ```

### Processing Flow
1. Parse the CSV file to extract IP addresses and firmware versions
2. Group devices by firmware version
3. For each firmware version group:
   - Build the specific firmware version
   - Flash all devices in that group with the built firmware
4. For devices without a specified version, use the current stable version

### Build and Flash Process
- For the example CSV file above, the process would be:
  - Run 1: Build firmware v2.6.1 and flash devices 192.168.1.104, 192.168.1.105
  - Run 2: Build firmware v2.6.5 and flash devices 192.168.1.102, 192.168.1.103
  - Run 3: Build firmware v2.7.0 (or latest stable) and flash devices 192.168.1.100, 192.168.1.101, 192.168.1.106

### User Experience
- Display a summary of the planned operations before starting
- Show progress for each firmware build and device flash
- Provide clear success/failure messages for each operation
- Allow the user to confirm before proceeding with the entire operation

## Potential Improvements to Consider
1. **Parallel Building**: Consider building multiple firmware versions in parallel to save time
2. **Caching Built Firmware**: Cache built firmware to avoid rebuilding the same version multiple times
3. **Selective Confirmation**: Allow the user to confirm each firmware version group separately
4. **Failure Handling**: Provide options for how to handle failures (continue with other groups or abort)
5. **Dry Run Mode**: Add a dry-run option to show what would be done without actually doing it
6. **Version Validation**: Validate that specified versions exist before starting the build process
7. **Progress Visualization**: Enhance the progress display to show overall progress across all groups
8. **Logging**: Improve logging to capture details of each operation for troubleshooting

## Acceptance Criteria
1. User can specify firmware versions for individual devices in the CSV file
2. Devices are correctly grouped by firmware version for efficient building
3. Each device receives the correct firmware version
4. All existing device verification and safety measures are maintained
5. Clear progress reporting is provided for each operation
6. Success and failure messages are easily distinguishable
7. All tests pass, including new tests for multi-version flashing
