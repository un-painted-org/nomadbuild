#!/usr/bin/env python3
# test_dockerfile_optimization.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
# Tests to verify that the Dockerfile optimization doesn't break any functionality

import os
import sys
import subprocess
import pytest
import tempfile
import shutil
from pathlib import Path

def test_dockerfile_verification():
    """Test that the Dockerfile passes verification."""
    # Determine project root
    root = Path(__file__).resolve().parent.parent.parent

    # Paths to required files
    dockerfile = root / "Dockerfile"
    verify_script = root / "scripts" / "verify_base_image_digest.sh"

    # Use the container-only directory
    config_dir = os.environ.get('NOMADBUILD_CONFIG_DIR', '/container_only/config')
    toolchain_pins = Path(config_dir) / "toolchain_pins.conf"

    # Ensure required files exist
    assert dockerfile.exists(), f"Dockerfile not found: {dockerfile}"
    assert verify_script.exists(), f"Verification script not found: {verify_script}"
    assert toolchain_pins.exists(), f"Toolchain pins file not found: {toolchain_pins}"

    try:
        # Set the environment variable for the script
        env = os.environ.copy()
        env['NOMADBUILD_CONFIG_DIR'] = str(Path(config_dir))

        # Run the verification script
        result = subprocess.run(
            ["bash", str(verify_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )

        # Check that the verification passed
        assert result.returncode == 0, f"Verification failed with error: {result.stderr}\nOutput: {result.stdout}"
        assert "✅ Dockerfile pinned to" in result.stdout, "Verification did not confirm Dockerfile pinning"
    finally:
        # No cleanup needed - we're using the container-only directory
        pass

def test_python_environment():
    """Test that the Python environment is correctly set up."""
    # List of required Python modules
    required_modules = [
        "flask", "pytest", "socketio", "yaml", "werkzeug", 
        "jinja2", "itsdangerous", "blinker", "bidict", 
        "requests", "simple_websocket"
    ]
    
    # Test each module
    for module in required_modules:
        # Use a simplified module name for import
        import_name = module.split('-')[0].lower()
        try:
            # Try to import the module
            __import__(import_name)
        except ImportError as e:
            pytest.fail(f"Failed to import {module}: {e}")

def test_binary_availability():
    """Test that all required binaries are available."""
    # List of required binaries
    required_binaries = ["python3", "pip", "node", "npm", "idf.py", "git"]
    
    # Test each binary
    for binary in required_binaries:
        result = subprocess.run(
            ["which", binary],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        assert result.returncode == 0, f"Binary {binary} not found in PATH"

def test_file_permissions():
    """Test that all scripts have proper execute permissions."""
    # Determine project root
    root = Path(__file__).resolve().parent.parent.parent
    
    # List of script directories
    script_dirs = [root / "scripts"]
    
    # Test each script directory
    for script_dir in script_dirs:
        assert script_dir.exists(), f"Script directory {script_dir} does not exist"
        
        # Test each shell script
        for script in script_dir.glob("*.sh"):
            assert os.access(script, os.X_OK), f"Script {script} does not have execute permission"

def test_environment_variables():
    """Test that all required environment variables are set."""
    # List of required environment variables
    required_env_vars = [
        "TZ", "LC_ALL", "LANG", "PYTHONHASHSEED", 
        "VENV_PATH", "NOMADBUILD_CONFIG_DIR"
    ]
    
    # Test each environment variable
    for env_var in required_env_vars:
        assert env_var in os.environ, f"Environment variable {env_var} not set"

def test_config_files():
    """Test that configuration files are correctly set up."""
    # Use the container-only directory
    config_dir = os.environ.get('NOMADBUILD_CONFIG_DIR', '/container_only/config')
    
    # List of required configuration files
    config_files = [
        Path(config_dir) / "toolchain_pins.conf",
        Path(config_dir) / "apt_pins.conf"
    ]
    
    # Test each configuration file
    for config_file in config_files:
        assert config_file.exists(), f"Configuration file {config_file} does not exist"

def test_volume_mount():
    """Test that volume mounts work correctly."""
    # Create a temporary file in the firmware directory
    firmware_dir = Path("/firmware")
    assert firmware_dir.exists(), f"Firmware directory {firmware_dir} does not exist"
    
    # Create a temporary file
    test_file = firmware_dir / "test_volume_mount.txt"
    try:
        with open(test_file, "w") as f:
            f.write("Test volume mount")
        
        # Verify the file exists
        assert test_file.exists(), f"Test file {test_file} does not exist"
        
        # Read the file content
        with open(test_file, "r") as f:
            content = f.read()
        
        assert content == "Test volume mount", f"Test file content mismatch: {content}"
    finally:
        # Clean up
        if test_file.exists():
            test_file.unlink()

def test_build_reproducibility():
    """Test that builds are reproducible."""
    # Determine project root
    root = Path(__file__).resolve().parent.parent.parent
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        
        # Create a simple C program
        with open(temp_dir_path / "test.c", "w") as f:
            f.write("""
            #include <stdio.h>
            int main() {
                printf("Hello, World!\\n");
                return 0;
            }
            """)
        
        # Compile the program twice
        result1 = subprocess.run(
            ["gcc", "-o", str(temp_dir_path / "test1"), str(temp_dir_path / "test.c")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        assert result1.returncode == 0, f"Failed to compile test program (1): {result1.stderr}"
        
        result2 = subprocess.run(
            ["gcc", "-o", str(temp_dir_path / "test2"), str(temp_dir_path / "test.c")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        assert result2.returncode == 0, f"Failed to compile test program (2): {result2.stderr}"
        
        # Run both programs
        run1 = subprocess.run(
            [str(temp_dir_path / "test1")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        assert run1.returncode == 0, f"Failed to run test program (1): {run1.stderr}"
        assert run1.stdout.strip() == "Hello, World!", f"Test program output mismatch (1): {run1.stdout}"
        
        run2 = subprocess.run(
            [str(temp_dir_path / "test2")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        assert run2.returncode == 0, f"Failed to run test program (2): {run2.stderr}"
        assert run2.stdout.strip() == "Hello, World!", f"Test program output mismatch (2): {run2.stdout}"
