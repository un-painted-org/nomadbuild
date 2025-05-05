# Backlog Item 111: Fix build_env Directory Regression

## Description
The test suite is creating a "build_env" folder on the host system, which violates the project rule that all operations should happen inside the container with no files created on the host system. This regression needs to be fixed to ensure that all build-related files are contained within the Docker container.

## Tasks
1. **Identify the Source of the Regression**:
   - Examine the code that creates the build_env directory
   - Determine why it's being created on the host system instead of inside the container
   - Identify all places in the code that reference the build_env directory

2. **Modify the Environment Directory Path**:
   - Change the ENV_DIR_NAME constant to use a hidden directory name (.container_build_env)
   - Update the get_env_dir() function to use a container-only directory (/container_only)
   - Ensure the container_only directory is created if it doesn't exist

3. **Ensure Container-Only Operation**:
   - Verify that all build-related files are created inside the container
   - Ensure no files are created on the host system during the build process
   - Update any code that might be accessing the build_env directory on the host system

4. **Test the Fix**:
   - Run the test suite to verify that no build_env directory is created on the host system
   - Ensure all tests pass with the new container-only directory structure
   - Verify that the build process still works correctly

## Acceptance Criteria
- No build_env directory is created on the host system during the test suite execution
- All tests pass with the new container-only directory structure
- The build process works correctly with the new directory structure
- All build-related files are contained within the Docker container
