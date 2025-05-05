# Backlog Item 124: Implement Docker Image Cleanup for Tagged Releases

## Description

This backlog item focuses on implementing a safe and efficient Docker image cleanup mechanism for nomadbuild. When a new tagged release is built, the system should offer to clean up existing Docker images to free up disk space while ensuring that only nomadbuild-related images are affected. This feature will be integrated with the existing `--build-image` option to provide a seamless experience.

## Requirements

1. Add safe cleanup option for nomadbuild Docker images
2. Integrate with existing --build-image option
3. Implement user confirmation before cleanup
4. Ensure only nomadbuild-related images are affected
5. Add proper error handling and reporting

## Implementation Details

### 1. Safe Cleanup Option

Implement a safe cleanup mechanism that only targets nomadbuild-related Docker images:

- Add a new `--cleanup` option to the nomadbuild.sh script
- Implement a function to identify nomadbuild-related images
- Create a mechanism to safely remove these images
- Ensure the cleanup process doesn't affect other Docker images

Example implementation:
```bash
# Function to identify nomadbuild-related Docker images
identify_nomadbuild_images() {
    # Get all images related to nomadbuild
    local images=$(docker images --format "{{.ID}} {{.Repository}} {{.Tag}}" | grep "nomadbuild" || true)
    
    if [ -z "$images" ]; then
        echo "No nomadbuild-related Docker images found."
        return 1
    fi
    
    echo "Found the following nomadbuild-related Docker images:"
    echo "$images" | while read -r id repo tag; do
        echo "  $repo:$tag ($id)"
    done
    
    return 0
}

# Function to safely remove nomadbuild-related Docker images
cleanup_nomadbuild_images() {
    local force=$1
    
    # Get all images related to nomadbuild
    local images=$(docker images --format "{{.ID}}" --filter "reference=nomadbuild*" || true)
    
    if [ -z "$images" ]; then
        echo "No nomadbuild-related Docker images found to clean up."
        return 0
    fi
    
    # Count the number of images
    local image_count=$(echo "$images" | wc -l)
    
    # Ask for confirmation if force is not set
    if [ "$force" != "true" ]; then
        echo "Found $image_count nomadbuild-related Docker image(s) to clean up."
        read -p "Do you want to proceed with cleanup? (y/N) " confirm
        if [[ "$confirm" != [yY] && "$confirm" != [yY][eE][sS] ]]; then
            echo "Cleanup aborted."
            return 1
        fi
    fi
    
    # Remove the images
    echo "Removing nomadbuild-related Docker images..."
    local removed_count=0
    
    for id in $images; do
        if docker rmi "$id" >/dev/null 2>&1; then
            removed_count=$((removed_count + 1))
        else
            echo "Warning: Failed to remove image $id. It may be in use."
        fi
    done
    
    echo "Successfully removed $removed_count out of $image_count nomadbuild-related Docker image(s)."
    
    return 0
}
```

### 2. Integration with --build-image Option

Integrate the cleanup functionality with the existing `--build-image` option:

- Modify the argument parsing to accept a new `--cleanup` flag
- Update the `--build-image` logic to include cleanup when requested
- Ensure cleanup happens before building a new image
- Add documentation for the new option

Example implementation:
```bash
# Add to argument parsing section
--cleanup)
    CLEANUP_IMAGES=true; shift ;;
--force-cleanup)
    CLEANUP_IMAGES=true; FORCE_CLEANUP=true; shift ;;

# Add to the build image section
if [ "$CLEANUP_IMAGES" = true ]; then
    echo "Cleaning up existing nomadbuild Docker images..."
    if cleanup_nomadbuild_images "$FORCE_CLEANUP"; then
        echo "Cleanup completed successfully."
    else
        echo "Cleanup was aborted or failed."
        # Continue with build anyway
    fi
fi
```

### 3. User Confirmation

Implement a user confirmation mechanism to prevent accidental deletion:

- Always ask for confirmation before removing images
- Provide a `--force-cleanup` option to skip confirmation
- Show the list of images that will be removed
- Allow the user to abort the cleanup process

Example implementation:
```bash
# Function to ask for user confirmation
confirm_cleanup() {
    local images="$1"
    local image_count="$2"
    
    echo "The following $image_count nomadbuild-related Docker image(s) will be removed:"
    echo "$images"
    echo ""
    echo "WARNING: This action cannot be undone."
    read -p "Do you want to proceed with cleanup? (y/N) " confirm
    
    if [[ "$confirm" != [yY] && "$confirm" != [yY][eE][sS] ]]; then
        return 1
    fi
    
    return 0
}
```

### 4. Targeted Cleanup

Ensure that only nomadbuild-related images are affected by the cleanup:

- Use Docker filters to target only nomadbuild-related images
- Implement safety checks to prevent accidental deletion of other images
- Add logging to track which images are being removed
- Verify image references before removal

Example implementation:
```bash
# Function to safely remove Docker images with verification
safe_remove_images() {
    local filter="$1"
    local force="$2"
    
    # Get images matching the filter
    local images=$(docker images --format "{{.ID}} {{.Repository}} {{.Tag}}" --filter "$filter" || true)
    
    if [ -z "$images" ]; then
        echo "No images found matching filter: $filter"
        return 0
    fi
    
    # Verify that all images are nomadbuild-related
    local non_nomadbuild_images=""
    echo "$images" | while read -r id repo tag; do
        if [[ "$repo" != *"nomadbuild"* ]]; then
            non_nomadbuild_images="$non_nomadbuild_images\n$repo:$tag ($id)"
        fi
    done
    
    if [ -n "$non_nomadbuild_images" ]; then
        echo "Error: Found non-nomadbuild images that would be affected by cleanup:"
        echo -e "$non_nomadbuild_images"
        echo "Cleanup aborted for safety."
        return 1
    fi
    
    # Continue with removal
    # ... (rest of the removal logic)
}
```

### 5. Error Handling and Reporting

Implement proper error handling and reporting for the cleanup process:

- Add detailed error messages for each failure case
- Handle Docker command failures gracefully
- Provide a summary of the cleanup results
- Log all cleanup actions for debugging

Example implementation:
```bash
# Function to handle cleanup errors
handle_cleanup_error() {
    local error_code="$1"
    local error_message="$2"
    
    echo "Error during cleanup: $error_message (code: $error_code)"
    
    case "$error_code" in
        1)
            echo "No images found to clean up."
            ;;
        2)
            echo "User aborted the cleanup process."
            ;;
        3)
            echo "Failed to remove one or more images. They may be in use by containers."
            echo "Try stopping any running nomadbuild containers first."
            ;;
        4)
            echo "Docker command failed. Please check Docker installation."
            ;;
        *)
            echo "Unknown error occurred during cleanup."
            ;;
    esac
    
    return "$error_code"
}

# Function to generate cleanup report
generate_cleanup_report() {
    local removed_images="$1"
    local failed_images="$2"
    local start_time="$3"
    local end_time="$4"
    
    local duration=$((end_time - start_time))
    local removed_count=$(echo "$removed_images" | wc -l)
    local failed_count=$(echo "$failed_images" | wc -l)
    
    echo "Cleanup Report:"
    echo "---------------"
    echo "Duration: $duration seconds"
    echo "Images removed: $removed_count"
    echo "Images failed to remove: $failed_count"
    
    if [ "$removed_count" -gt 0 ]; then
        echo ""
        echo "Successfully removed images:"
        echo "$removed_images"
    fi
    
    if [ "$failed_count" -gt 0 ]; then
        echo ""
        echo "Failed to remove images:"
        echo "$failed_images"
    fi
    
    echo ""
    echo "Disk space freed: $(calculate_space_freed) MB"
}
```

### 6. Advanced Cleanup Options

Implement advanced cleanup options for more control:

- Add a `--prune-builder` option to run `docker builder prune`
- Add a `--cleanup-all` option to remove all unused Docker images
- Add a `--cleanup-dangling` option to remove only dangling images
- Add a `--cleanup-older-than` option to remove images older than a specified age

Example implementation:
```bash
# Function to prune Docker builder cache
prune_builder_cache() {
    local force="$1"
    
    echo "Pruning Docker builder cache..."
    
    if [ "$force" = "true" ]; then
        docker builder prune -a -f
    else
        docker builder prune -a
    fi
    
    return $?
}

# Function to remove dangling images
cleanup_dangling_images() {
    local force="$1"
    
    echo "Removing dangling Docker images..."
    
    if [ "$force" = "true" ]; then
        docker rmi $(docker images -f "dangling=true" -q) 2>/dev/null || true
    else
        local dangling_images=$(docker images -f "dangling=true" -q)
        if [ -z "$dangling_images" ]; then
            echo "No dangling images found."
            return 0
        fi
        
        local image_count=$(echo "$dangling_images" | wc -l)
        echo "Found $image_count dangling image(s)."
        read -p "Do you want to remove them? (y/N) " confirm
        if [[ "$confirm" != [yY] && "$confirm" != [yY][eE][sS] ]]; then
            echo "Cleanup aborted."
            return 1
        fi
        
        docker rmi $dangling_images 2>/dev/null || true
    fi
    
    return 0
}
```

## Testing

The changes should be tested by:

1. **Basic Functionality Testing**:
   - Test the `--cleanup` option with existing nomadbuild images
   - Verify that only nomadbuild-related images are removed
   - Test the user confirmation mechanism
   - Verify that the cleanup process works correctly

2. **Integration Testing**:
   - Test the integration with the `--build-image` option
   - Verify that cleanup happens before building a new image
   - Test the `--force-cleanup` option
   - Verify that the cleanup process doesn't affect other Docker images

3. **Error Handling Testing**:
   - Test the cleanup process with no nomadbuild images
   - Test the cleanup process with images that are in use
   - Test the cleanup process with invalid Docker commands
   - Verify that error messages are clear and helpful

4. **Advanced Options Testing**:
   - Test the `--prune-builder` option
   - Test the `--cleanup-all` option
   - Test the `--cleanup-dangling` option
   - Test the `--cleanup-older-than` option

## Acceptance Criteria

- The `--cleanup` option is added to the nomadbuild.sh script
- The cleanup process only affects nomadbuild-related Docker images
- User confirmation is required before removing images
- The `--force-cleanup` option skips user confirmation
- The cleanup process is integrated with the `--build-image` option
- Proper error handling and reporting is implemented
- Advanced cleanup options are available for more control
- The cleanup process is well-documented in the help text
