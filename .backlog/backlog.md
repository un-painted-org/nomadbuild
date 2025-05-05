# NomadBuild Backlog

This file contains the backlog of items to be implemented in the NomadBuild project.

## Backlog Items

93. **Web UI Tests** - *Pending*
   - Implement tests for Web UI components
   - Test API endpoints
   - Test Socket.IO events

94. **Stress/Concurrency Tests** - *Pending*
   - Test build cancellation under load
   - Verify isolation of build_cancel_event
   - Test cleanup with multiple simultaneous builds

95. **Coverage Threshold in CI** - *Pending*
   - Implement coverage threshold with pytest --cov
   - Fail CI on coverage drops
   - Generate HTML coverage reports

97. **GitHub Templates** - *Pending*
   - Add issue templates
   - Add PR templates
   - Update contributing guidelines

98. **Release Generation Script** - *Pending*
   - Create script for generating releases
   - Format changelog entries
   - Automate version bumping

99. **Enhance Build Reproducibility** - *Pending*
   - Vendor dependencies
   - Normalize timestamps
   - Canonicalize configs
   - Record tool versions
   - Implement verification tests

100. **Fix Skipped Web UI Tests** - *Pending*
   - Address skipped tests in Web UI test suite
   - Fix test environment issues
   - Ensure all tests run consistently

101. **Add Web UI Server Endpoint Socket.IO Tests** - *Pending*
   - Test Socket.IO events
   - Test API endpoints
   - Verify real-time updates

102. **Integrate Repro Commands into nomadbuild.sh** - *Pending*
   - Add reproducibility commands to main script
   - Ensure consistent interface
   - Document new options

103. **Integrate Test Commands into nomadbuild.sh** - *Pending*
   - Add test commands to main script
   - Pass options to test.sh
   - Document test options

104. **Add Dockerfile Generation Option to nomadbuild.sh** - *Pending*
   - Add option to regenerate Dockerfile
   - Integrate with existing MD5 tracking
   - Document new option

105. **Implement NerdQAxe Support** - *Pending*
   - Add support for NerdQAxe product family
   - Implement device detection logic
   - Consolidate build UI into "pick your device type" interface
   - Dynamically load latest tags from NerdQAxe/Bitaxe repositories
   - Implement single "pick your desired tag" option for firmware selection
   - Test with NerdQAxe hardware

106. **Add Direct Link to NerdQAxe Web Flasher** - *Pending*
   - Add link to https://shufps.github.io/nerdqaxe-web-flasher/
   - Integrate with NerdQAxe support
   - Document flashing options

107. **Improve Documentation for nomadbuild.sh Wrapper** - *Pending*
   - Emphasize using wrapper script exclusively
   - Document all options
   - Provide usage examples

108. **Create Table of Scripts with Responsibilities** - *Pending*
   - Document all scripts in the project
   - List responsibilities for each script
   - Show relationships between scripts

109. **Simplify and Standardize Documentation** - *Pending*
   - Ensure consistent documentation style
   - Remove redundant information
   - Improve readability

110. **Fix Skipped Web UI Tests** - *Pending*
   - Address skipped tests in Web UI test suite
   - Fix test environment issues
   - Ensure all tests run consistently

113. **Restructure Dockerfile Template for Better Readability and Size** - *Pending*
   - Replace long path strings with variables
   - Consolidate redundant mkdir commands
   - Group related commands to reduce layers
   - Add clear section comments
   - Optimize for smaller image size

114. **Implement User-Customizable Firmware Patches Feature** - *Pending*
   - Create "feature appstore" for firmware patches
   - Allow selection of experimental patches
   - Support patches from GitHub repositories
   - Add metadata for patches (description, compatibility)
   - Implement safeguards for patched firmware

115. **Fix Multi-Stage Build ARG Declarations** - *Pending*
   - Fix ARG declarations in multi-stage builds to follow Docker best practices
   - Move global ARGs before the first FROM instruction
   - Re-declare ARGs after each new FROM instruction
   - Add documentation about ARG scoping in multi-stage builds
   - Update verification tests to check ARG declarations

116. **Improve Error Handling in Dockerfile Commands** - *Pending*
   - Add consistent error handling to all shell commands in the Dockerfile
   - Use `2>/dev/null || true` for commands that might fail safely
   - Ensure build doesn't fail due to expected conditions (e.g., no files found)
   - Add logging for important operations
   - Update verification tests to check error handling

117. **Enhance Verification of Multi-Stage Builds** - *Pending*
   - Add specific verification for multi-stage builds
   - Verify that unnecessary build tools are removed in the final image
   - Compare contents of builder and runtime stages
   - Verify that only necessary files are copied from builder to runtime
   - Add automated image size comparison

118. **Implement Comprehensive Binary and Module Version Testing** - *Pending*
   - Enhance binary availability tests to check versions
   - Verify functionality of critical binaries
   - Add version checks for Python modules
   - Test compatibility between different components
   - Create a version matrix for all dependencies

119. **Improve Volume Mount Testing** - *Pending*
   - Add tests for file permissions in volume mounts
   - Test large file handling (>100MB)
   - Test concurrent access to volume mounts
   - Verify persistence across container restarts
   - Test with different host filesystem types

120. **Implement Stress and Performance Testing** - *Pending*
   - Add stress tests to verify container behavior under load
   - Test with multiple simultaneous builds
   - Measure and compare build times before and after optimization
   - Test memory usage under load
   - Verify resource cleanup after stress tests

121. **Add Security Scanning for Docker Images** - *Pending*
   - Implement security scanning for Docker images
   - Check for known vulnerabilities in packages
   - Verify minimal attack surface in optimized image
   - Scan for sensitive information in the image
   - Create security reports for each build

122. **Enhance Reproducibility Testing** - *Pending*
   - Implement reproducibility testing across different environments
   - Verify builds are reproducible on different host systems
   - Test reproducibility after system changes
   - Add deterministic build options
   - Create reproducibility reports

123. **Implement Ultra-Reliable Parallel Flashing** - *Pending*
   - Create comprehensive test suite for flashing process
   - Implement fail-fast error detection and handling
   - Add parallel processing of multiple flashing tasks
   - Ensure proper resource isolation between parallel tasks
   - Implement detailed logging and diagnostics for flashing operations

124. **Implement Docker Image Cleanup for Tagged Releases** - *Pending*
   - Add safe cleanup option for nomadbuild Docker images
   - Integrate with existing --build-image option
   - Implement user confirmation before cleanup
   - Ensure only nomadbuild-related images are affected
   - Add proper error handling and reporting

125. **Create Custom ESP-IDF Base Image for ESP32-S3** - *Pending*
   - Build dedicated ESP-IDF image with ESP32-S3 support only
   - Minimize image size by including only required components
   - Create Dockerfile for custom base image
   - Integrate with existing multi-stage build process
   - Document custom image build process

126. **Implement CSV-Based Multi-Device Flashing** - *Pending*
   - Add --flash-csv parameter to specify a CSV file with IP addresses
   - Display the number of configured IP addresses before flashing starts
   - Implement interactive confirmation for batch flashing
   - Verify device models before flashing each device
   - Show detailed update progress for each device
   - Ensure clear distinction between success and failure messages
   - Add comprehensive test cases for CSV parsing and multi-device flashing

127. **Enhance CSV-Based Flashing with Version Targeting** - *Pending*
   - Extend CSV format to include optional firmware version per device
   - Group devices by firmware version for efficient building
   - Build and flash each firmware version group separately
   - Use current stable version for devices without specified version
   - Maintain all device verification and safety measures
   - Provide clear progress reporting for each firmware version group
   - Add dry-run mode to preview operations without executing them
   - Add comprehensive test cases for multi-version flashing

   Example CSV format:
   ```
   # Sample CSV file for flashing multiple devices with specific firmware versions
   # Format: IP address, firmware version (optional)
   # If no firmware version is specified, the current stable version will be used

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

128. **Implement Firmware Build Caching** - *Pending*
   - Cache built firmware binaries indexed by version and build parameters
   - Validate cache integrity before using cached firmware
   - Implement cache expiration policy to manage disk space
   - Provide options to force rebuild even when cache is available
   - Ensure cache is compatible with reproducible build requirements

129. **Implement Parallel Firmware Building** - *Pending*
   - Build multiple firmware versions in parallel using separate containers
   - Implement resource management to prevent system overload
   - Provide clear progress reporting for parallel builds
   - Handle failures in individual build processes gracefully
   - Ensure build isolation to maintain reproducibility

130. **Implement Firmware Version Aliases** - *Pending*
   - Support common version aliases like "latest", "stable", and "lts"
   - Allow custom aliases to be defined in configuration
   - Resolve aliases to specific versions at runtime
   - Provide clear feedback about which specific version an alias resolves to
   - Ensure backward compatibility with explicit version specifications
