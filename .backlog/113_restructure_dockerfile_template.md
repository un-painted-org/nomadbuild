# Backlog Item #113: Restructure Dockerfile Template for Better Readability and Size

## Overview
The current Dockerfile.template needs restructuring to improve readability and reduce the resulting Docker image size. Multiple long path strings should be replaced with more readable variables, and redundant mkdir commands should be consolidated.

## Requirements

### Functional Requirements
1. Replace long path strings with environment variables for better readability
2. Consolidate redundant mkdir commands into single RUN instructions
3. Group related commands to reduce the number of layers
4. Add clear section comments for better organization
5. Optimize the Dockerfile to reduce the final image size

### Technical Requirements
1. Maintain all existing functionality
2. Ensure all pin files are still created in the container-only directory
3. Preserve the reproducibility of builds
4. Ensure all tests pass after the restructuring
5. Verify the Docker image still builds correctly

## Implementation Details

### Suggested Improvements
1. **Add Environment Variables for Common Paths**:
   - Define variables for common paths like `/app`, `/firmware`, `/opt/venv`
   - Use these variables consistently throughout the Dockerfile

2. **Consolidate Directory Creation**:
   - Group all `mkdir` commands into a single RUN instruction
   - Create all required directories in one step

3. **Optimize Layer Structure**:
   - Combine related RUN commands to reduce the number of layers
   - Group installation steps logically

4. **Improve Readability**:
   - Add clear section comments
   - Format multi-line commands consistently
   - Use consistent indentation

5. **Fix the Container-Only Directory Issue**:
   - Remove references to host build directory
   - Create pin files directly in the container

## Acceptance Criteria
- [  ] Dockerfile.template is restructured with environment variables for paths
- [  ] Redundant mkdir commands are consolidated
- [  ] Related commands are grouped to reduce layers
- [  ] Clear section comments are added
- [  ] The resulting Docker image is smaller than the current one
- [  ] All tests pass
- [  ] The Docker image builds correctly
- [  ] No build artifacts are created on the host system

## Notes
This is a refactoring task to improve code quality and reduce image size. No functional changes are expected.
