# Backlog Item 118: Implement Comprehensive Binary and Module Version Testing

## Description

This backlog item focuses on implementing comprehensive testing for binary and module versions to ensure compatibility and correct functionality. Currently, the verification script only checks if binaries and modules exist but doesn't verify their versions or functionality.

## Requirements

1. Enhance binary availability tests to check versions
2. Verify functionality of critical binaries
3. Add version checks for Python modules
4. Test compatibility between different components
5. Create a version matrix for all dependencies

## Implementation Details

### Current Issues

The current verification script only checks if binaries and modules exist but doesn't verify their versions or functionality:

```python
def test_binary_availability():
    """Test that all required binaries are available in the container."""
    required_binaries = ["python3", "pip", "node", "npm", "idf.py", "git"]
    missing_binaries = []
    
    print("Testing binary availability...")
    for binary in required_binaries:
        result = subprocess.run(["which", binary], capture_output=True, text=True)
        if result.returncode != 0:
            missing_binaries.append(binary)
            print(f"❌ {binary} not found in PATH")
        else:
            print(f"✅ {binary} found at {result.stdout.strip()}")
```

A binary might exist but be the wrong version or not work correctly.

### Proposed Solution

1. **Enhance Binary Availability Tests**: Update the binary availability tests to check versions.

```python
def test_binary_availability():
    """Test that all required binaries are available and functional in the container."""
    required_binaries = {
        "python3": {"version_flag": "--version", "expected_version": "3.12.3"},
        "pip": {"version_flag": "--version", "expected_version": "24.0"},
        "node": {"version_flag": "--version", "expected_version": "v22.15.0"},
        "npm": {"version_flag": "--version", "expected_version": "10.5.0"},
        "idf.py": {"version_flag": "--version", "expected_version": "v5.4"},
        "git": {"version_flag": "--version", "expected_version": "2.42"}
    }
    
    missing_or_incorrect_binaries = []
    
    print("Testing binary availability and versions...")
    for binary, info in required_binaries.items():
        # Check if binary exists
        which_result = subprocess.run(["which", binary], capture_output=True, text=True)
        if which_result.returncode != 0:
            missing_or_incorrect_binaries.append(f"{binary} (not found)")
            print(f"❌ {binary} not found in PATH")
            continue
            
        # Check version
        version_result = subprocess.run(
            [binary, info["version_flag"]], 
            capture_output=True, 
            text=True
        )
        if version_result.returncode != 0:
            missing_or_incorrect_binaries.append(f"{binary} (version check failed)")
            print(f"❌ {binary} version check failed: {version_result.stderr}")
            continue
            
        if info["expected_version"] not in version_result.stdout:
            missing_or_incorrect_binaries.append(
                f"{binary} (wrong version: {version_result.stdout.strip()})"
            )
            print(f"❌ {binary} has wrong version: {version_result.stdout.strip()}")
            continue
            
        print(f"✅ {binary} found at {which_result.stdout.strip()} with correct version")
```

2. **Verify Functionality of Critical Binaries**: Add tests to verify that critical binaries work correctly.

```python
def test_binary_functionality():
    """Test that critical binaries work correctly."""
    # Test Python functionality
    python_result = subprocess.run(
        ["python3", "-c", "print('Hello, World!')"],
        capture_output=True,
        text=True
    )
    if python_result.returncode != 0 or python_result.stdout.strip() != "Hello, World!":
        print(f"❌ Python functionality test failed: {python_result.stderr}")
        return False
    
    # Test Node.js functionality
    node_result = subprocess.run(
        ["node", "-e", "console.log('Hello, World!')"],
        capture_output=True,
        text=True
    )
    if node_result.returncode != 0 or node_result.stdout.strip() != "Hello, World!":
        print(f"❌ Node.js functionality test failed: {node_result.stderr}")
        return False
    
    # Test Git functionality
    git_result = subprocess.run(
        ["git", "--version"],
        capture_output=True,
        text=True
    )
    if git_result.returncode != 0:
        print(f"❌ Git functionality test failed: {git_result.stderr}")
        return False
    
    print("✅ All critical binaries are functional")
    return True
```

3. **Add Version Checks for Python Modules**: Update the Python environment tests to check module versions.

```python
def test_python_environment():
    """Test that the Python environment is correctly set up with the right versions."""
    required_modules = {
        "flask": {"expected_version": "3.0.0"},
        "pytest": {"expected_version": "8.3.5"},
        "socketio": {"expected_version": "5.10.0"},
        "yaml": {"expected_version": "6.0.1"},
        "werkzeug": {"expected_version": "3.0.1"},
        "jinja2": {"expected_version": "3.1.3"},
        "itsdangerous": {"expected_version": "2.1.2"},
        "blinker": {"expected_version": "1.7.0"},
        "bidict": {"expected_version": "0.22.1"},
        "requests": {"expected_version": "2.31.0"},
        "simple_websocket": {"expected_version": "1.0.0"}
    }
    
    missing_or_incorrect_modules = []
    
    print("Testing Python environment...")
    for module, info in required_modules.items():
        # Use a simplified module name for import
        import_name = module.split('-')[0].lower()
        
        # Check if module can be imported
        import_result = subprocess.run(
            ["python3", "-c", f"import {import_name}; print({import_name}.__version__)"],
            capture_output=True,
            text=True
        )
        if import_result.returncode != 0:
            missing_or_incorrect_modules.append(f"{module} (not importable)")
            print(f"❌ Python module {module} not importable: {import_result.stderr.strip()}")
            continue
        
        # Check version
        version = import_result.stdout.strip()
        if version != info["expected_version"]:
            missing_or_incorrect_modules.append(f"{module} (wrong version: {version})")
            print(f"❌ Python module {module} has wrong version: {version}")
            continue
        
        print(f"✅ Python module {module} is available with correct version {version}")
```

4. **Create a Version Matrix**: Create a version matrix for all dependencies to ensure compatibility.

```python
def create_version_matrix():
    """Create a version matrix for all dependencies."""
    # Define the dependencies to check
    dependencies = {
        "binaries": {
            "python3": {"version_flag": "--version"},
            "pip": {"version_flag": "--version"},
            "node": {"version_flag": "--version"},
            "npm": {"version_flag": "--version"},
            "idf.py": {"version_flag": "--version"},
            "git": {"version_flag": "--version"}
        },
        "python_modules": [
            "flask", "pytest", "socketio", "yaml", "werkzeug",
            "jinja2", "itsdangerous", "blinker", "bidict",
            "requests", "simple_websocket"
        ]
    }
    
    # Create the version matrix
    version_matrix = {}
    
    # Check binary versions
    for binary, info in dependencies["binaries"].items():
        version_result = subprocess.run(
            [binary, info["version_flag"]],
            capture_output=True,
            text=True
        )
        if version_result.returncode == 0:
            version_matrix[binary] = version_result.stdout.strip()
        else:
            version_matrix[binary] = "ERROR"
    
    # Check Python module versions
    for module in dependencies["python_modules"]:
        import_name = module.split('-')[0].lower()
        import_result = subprocess.run(
            ["python3", "-c", f"import {import_name}; print({import_name}.__version__)"],
            capture_output=True,
            text=True
        )
        if import_result.returncode == 0:
            version_matrix[module] = import_result.stdout.strip()
        else:
            version_matrix[module] = "ERROR"
    
    # Print the version matrix
    print("Version Matrix:")
    for dependency, version in version_matrix.items():
        print(f"{dependency}: {version}")
    
    # Save the version matrix to a file
    with open("/app/version_matrix.json", "w") as f:
        json.dump(version_matrix, f, indent=2)
    
    return version_matrix
```

## Testing

The changes should be tested by:

1. Building the Docker image with the enhanced verification script
2. Running the verification script to check binary and module versions
3. Verifying that critical binaries work correctly
4. Testing compatibility between different components
5. Creating and reviewing the version matrix

## Acceptance Criteria

- Binary availability tests check versions and functionality
- Python environment tests check module versions
- Critical binaries are verified to work correctly
- Compatibility between different components is tested
- A version matrix is created for all dependencies
- The verification script reports detailed results of the version checks
