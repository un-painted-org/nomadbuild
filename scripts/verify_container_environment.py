#!/usr/bin/env python3
# verify_container_environment.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
# Script to verify that the container environment is correctly set up
# after Dockerfile optimization.

import subprocess
import os
import sys
import time

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
    
    if missing_binaries:
        print(f"❌ Missing binaries: {', '.join(missing_binaries)}")
        return False
    
    print("✅ All required binaries are available")
    return True

def test_python_environment():
    """Test that the Python environment is correctly set up."""
    required_modules = [
        "flask", "pytest", "socketio", "yaml", "werkzeug", 
        "jinja2", "itsdangerous", "blinker", "bidict", 
        "requests", "simple_websocket"
    ]
    missing_modules = []
    
    print("Testing Python environment...")
    for module in required_modules:
        # Use a simplified module name for import
        import_name = module.split('-')[0].lower()
        result = subprocess.run(
            ["python3", "-c", f"import {import_name}"], 
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            missing_modules.append(module)
            print(f"❌ Python module {module} not available: {result.stderr.strip()}")
        else:
            print(f"✅ Python module {module} is available")
    
    if missing_modules:
        print(f"❌ Missing Python modules: {', '.join(missing_modules)}")
        return False
    
    print("✅ Python environment correctly set up")
    return True

def test_file_permissions():
    """Test that all scripts have proper execute permissions."""
    script_dirs = ["/app/scripts"]
    non_executable_scripts = []
    
    print("Testing file permissions...")
    for script_dir in script_dirs:
        if not os.path.exists(script_dir):
            print(f"❌ Script directory {script_dir} does not exist")
            return False
            
        for script in os.listdir(script_dir):
            if script.endswith(".sh"):
                path = os.path.join(script_dir, script)
                if not os.access(path, os.X_OK):
                    non_executable_scripts.append(path)
                    print(f"❌ {path} does not have execute permission")
                else:
                    print(f"✅ {path} has execute permission")
    
    if non_executable_scripts:
        print(f"❌ Scripts without execute permission: {', '.join(non_executable_scripts)}")
        return False
    
    print("✅ All scripts have proper execute permissions")
    return True

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

def test_environment_variables():
    """Test that all required environment variables are set."""
    required_env_vars = [
        "TZ", "LC_ALL", "LANG", "PYTHONHASHSEED", 
        "VENV_PATH", "NOMADBUILD_CONFIG_DIR"
    ]
    missing_env_vars = []
    
    print("Testing environment variables...")
    for env_var in required_env_vars:
        if env_var not in os.environ:
            missing_env_vars.append(env_var)
            print(f"❌ Environment variable {env_var} not set")
        else:
            print(f"✅ Environment variable {env_var} = {os.environ[env_var]}")
    
    if missing_env_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_env_vars)}")
        return False
    
    print("✅ All required environment variables are set")
    return True

def test_build_performance():
    """Test build performance by measuring the time to compile a simple program."""
    print("Testing build performance...")
    
    # Create a simple C program
    test_dir = "/tmp/build_test"
    os.makedirs(test_dir, exist_ok=True)
    
    with open(f"{test_dir}/test.c", "w") as f:
        f.write("""
        #include <stdio.h>
        int main() {
            printf("Hello, World!\\n");
            return 0;
        }
        """)
    
    # Compile the program and measure the time
    start_time = time.time()
    result = subprocess.run(
        ["gcc", "-o", f"{test_dir}/test", f"{test_dir}/test.c"],
        capture_output=True,
        text=True
    )
    end_time = time.time()
    
    if result.returncode != 0:
        print(f"❌ Failed to compile test program: {result.stderr}")
        return False
    
    # Run the program
    result = subprocess.run(
        [f"{test_dir}/test"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Failed to run test program: {result.stderr}")
        return False
    
    if result.stdout.strip() != "Hello, World!":
        print(f"❌ Test program output mismatch: {result.stdout}")
        return False
    
    print(f"✅ Build performance: {end_time - start_time:.2f} seconds")
    return True

def test_config_files():
    """Test that configuration files are correctly set up."""
    config_files = [
        "/container_only/config/toolchain_pins.conf",
        "/container_only/config/apt_pins.conf"
    ]
    missing_config_files = []
    
    print("Testing configuration files...")
    for config_file in config_files:
        if not os.path.exists(config_file):
            missing_config_files.append(config_file)
            print(f"❌ Configuration file {config_file} does not exist")
        else:
            print(f"✅ Configuration file {config_file} exists")
    
    if missing_config_files:
        print(f"❌ Missing configuration files: {', '.join(missing_config_files)}")
        return False
    
    print("✅ All configuration files are correctly set up")
    return True

def main():
    """Run all tests."""
    tests = [
        test_binary_availability,
        test_python_environment,
        test_file_permissions,
        test_volume_mounts,
        test_environment_variables,
        test_config_files,
        test_build_performance
    ]
    
    print("=== Container Environment Verification ===")
    
    success = True
    for test in tests:
        print(f"\n--- Running {test.__name__} ---")
        if not test():
            success = False
        print(f"--- Completed {test.__name__} ---")
    
    print("\n=== Verification Summary ===")
    if success:
        print("✅ All container verification tests passed")
        return 0
    else:
        print("❌ Some container verification tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
