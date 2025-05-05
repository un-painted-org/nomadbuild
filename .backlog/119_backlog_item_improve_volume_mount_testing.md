# Backlog Item 119: Improve Volume Mount Testing

## Description

This backlog item focuses on improving the testing of Docker volume mounts to ensure they work correctly under various conditions. Currently, the volume mount test only verifies basic file creation and reading but doesn't test permissions, large file handling, or concurrent access, which are common issues with Docker volume mounts.

## Requirements

1. Add tests for file permissions in volume mounts
2. Test large file handling (>100MB)
3. Test concurrent access to volume mounts
4. Verify persistence across container restarts
5. Test with different host filesystem types

## Implementation Details

### Current Issues

The current volume mount test only verifies basic file creation and reading:

```python
def test_volume_mounts():
    """Test that volume mounts work correctly."""
    print("Testing volume mounts...")
    test_file = "/firmware/test_volume_mount.txt"
    
    try:
        # Create a test file in the volume mount
        with open(test_file, "w") as f:
            f.write("Test volume mount")
        
        # Verify the file exists
        if not os.path.exists(test_file):
            print(f"❌ Test file {test_file} does not exist")
            return False
        
        # Read the file content
        with open(test_file, "r") as f:
            content = f.read()
        
        if content != "Test volume mount":
            print(f"❌ Test file content mismatch: {content}")
            return False
        
        print(f"✅ Volume mount /firmware is working correctly")
        return True
    except Exception as e:
        print(f"❌ Error testing volume mount: {e}")
        return False
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)
```

This test doesn't check file permissions, large file handling, or concurrent access, which are common issues with Docker volume mounts.

### Proposed Solution

1. **Add Tests for File Permissions**: Test that files in volume mounts have the correct permissions.

```python
def test_volume_mount_permissions():
    """Test that files in volume mounts have the correct permissions."""
    print("Testing volume mount permissions...")
    test_file = "/firmware/test_permissions.sh"
    
    try:
        # Create a test script in the volume mount
        with open(test_file, "w") as f:
            f.write("#!/bin/bash\necho 'Permission test'")
        
        # Make the script executable
        os.chmod(test_file, 0o755)
        
        # Verify the script has execute permission
        if not os.access(test_file, os.X_OK):
            print(f"❌ Test script {test_file} does not have execute permission")
            return False
        
        # Execute the script
        result = subprocess.run(
            [test_file],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0 or result.stdout.strip() != "Permission test":
            print(f"❌ Test script execution failed: {result.stderr}")
            return False
        
        print(f"✅ Volume mount permissions are working correctly")
        return True
    except Exception as e:
        print(f"❌ Error testing volume mount permissions: {e}")
        return False
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)
```

2. **Test Large File Handling**: Test that large files can be created and read in volume mounts.

```python
def test_volume_mount_large_files():
    """Test that large files can be created and read in volume mounts."""
    print("Testing volume mount large file handling...")
    test_file = "/firmware/test_large_file.bin"
    file_size = 100 * 1024 * 1024  # 100MB
    
    try:
        # Create a large test file in the volume mount
        with open(test_file, "wb") as f:
            f.write(b"\0" * file_size)
        
        # Verify the file exists and has the correct size
        if not os.path.exists(test_file):
            print(f"❌ Large test file {test_file} does not exist")
            return False
        
        if os.path.getsize(test_file) != file_size:
            print(f"❌ Large test file size mismatch: {os.path.getsize(test_file)} != {file_size}")
            return False
        
        # Read the file content (just the first and last bytes to verify)
        with open(test_file, "rb") as f:
            first_byte = f.read(1)
            f.seek(file_size - 1)
            last_byte = f.read(1)
        
        if first_byte != b"\0" or last_byte != b"\0":
            print(f"❌ Large test file content mismatch")
            return False
        
        print(f"✅ Volume mount large file handling is working correctly")
        return True
    except Exception as e:
        print(f"❌ Error testing volume mount large file handling: {e}")
        return False
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)
```

3. **Test Concurrent Access**: Test that multiple processes can access the same file in a volume mount.

```python
def test_volume_mount_concurrent_access():
    """Test that multiple processes can access the same file in a volume mount."""
    print("Testing volume mount concurrent access...")
    test_file = "/firmware/test_concurrent_access.txt"
    
    try:
        # Create a test file in the volume mount
        with open(test_file, "w") as f:
            f.write("0")
        
        # Create multiple processes to increment the counter in the file
        processes = []
        for i in range(10):
            process = multiprocessing.Process(
                target=increment_counter,
                args=(test_file,)
            )
            processes.append(process)
            process.start()
        
        # Wait for all processes to complete
        for process in processes:
            process.join()
        
        # Read the final counter value
        with open(test_file, "r") as f:
            counter = int(f.read())
        
        if counter != 10:
            print(f"❌ Concurrent access test failed: counter = {counter}, expected 10")
            return False
        
        print(f"✅ Volume mount concurrent access is working correctly")
        return True
    except Exception as e:
        print(f"❌ Error testing volume mount concurrent access: {e}")
        return False
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)

def increment_counter(file_path):
    """Increment the counter in the file."""
    # Read the current counter value
    with open(file_path, "r") as f:
        counter = int(f.read())
    
    # Increment the counter
    counter += 1
    
    # Write the new counter value
    with open(file_path, "w") as f:
        f.write(str(counter))
```

4. **Verify Persistence Across Container Restarts**: Test that files in volume mounts persist across container restarts.

```python
def test_volume_mount_persistence():
    """Test that files in volume mounts persist across container restarts."""
    print("Testing volume mount persistence...")
    test_file = "/firmware/test_persistence.txt"
    
    try:
        # Create a test file in the volume mount
        with open(test_file, "w") as f:
            f.write("Persistence test")
        
        # Restart the container
        subprocess.run(
            ["docker", "restart", os.environ.get("HOSTNAME")],
            check=True
        )
        
        # Wait for the container to restart
        time.sleep(5)
        
        # Verify the file still exists
        if not os.path.exists(test_file):
            print(f"❌ Test file {test_file} does not exist after container restart")
            return False
        
        # Read the file content
        with open(test_file, "r") as f:
            content = f.read()
        
        if content != "Persistence test":
            print(f"❌ Test file content mismatch after container restart: {content}")
            return False
        
        print(f"✅ Volume mount persistence is working correctly")
        return True
    except Exception as e:
        print(f"❌ Error testing volume mount persistence: {e}")
        return False
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)
```

## Testing

The changes should be tested by:

1. Building the Docker image with the enhanced volume mount tests
2. Running the verification script to test volume mount functionality
3. Verifying that files in volume mounts have the correct permissions
4. Testing large file handling in volume mounts
5. Testing concurrent access to volume mounts
6. Verifying persistence across container restarts
7. Testing with different host filesystem types

## Acceptance Criteria

- Volume mount tests check file permissions
- Large file handling in volume mounts is tested
- Concurrent access to volume mounts is tested
- Persistence across container restarts is verified
- Tests work with different host filesystem types
- The verification script reports detailed results of the volume mount tests
