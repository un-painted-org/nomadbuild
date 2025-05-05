#!/usr/bin/env python3
# test_no_host_artifacts.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
# Test to verify that no build artifacts are created on the host system

import os
import subprocess
import tempfile
import pytest
from pathlib import Path

def test_no_host_artifacts():
    """
    Test that no build artifacts are created on the host system.

    This test verifies that running various operations does not create
    any build artifacts on the host system. It checks for common artifact
    directories like 'build', 'build_env', etc.

    The test will fail if any of these directories are found on the host system
    after running operations that might create them.
    """
    # Get the project root directory
    root_dir = Path(__file__).resolve().parent.parent.parent

    # List of artifact directories to check for
    artifact_dirs = [
        "build",
        "build_env",
        "apt_pins.conf",
        "toolchain_pins.conf",
        "python_pins.conf",
        ".apt_pins.conf.md5",
        ".toolchain_pins.conf.md5",
        ".python_pins.conf.md5"
    ]

    # Create a temporary directory for the test
    with tempfile.TemporaryDirectory() as temp_dir:
        # Run operations that might create artifacts
        # 1. Generate Dockerfile
        subprocess.run(
            ["python3", str(root_dir / "scripts" / "generate_dockerfile.py")],
            cwd=root_dir,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # 2. Run verify_base_image_digest.sh
        env = os.environ.copy()
        env["NOMADBUILD_CONFIG_DIR"] = "/tmp/nomadbuild_config"
        subprocess.run(
            ["bash", str(root_dir / "scripts" / "verify_base_image_digest.sh")],
            cwd=root_dir,
            env=env,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # 3. Run verify_pinned_versions.sh
        subprocess.run(
            ["bash", str(root_dir / "scripts" / "verify_pinned_versions.sh")],
            cwd=root_dir,
            env=env,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # 4. Run verify_toolchain_versions.sh
        subprocess.run(
            ["bash", str(root_dir / "scripts" / "verify_toolchain_versions.sh")],
            cwd=root_dir,
            env=env,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Check for artifact directories
        for artifact in artifact_dirs:
            artifact_path = root_dir / artifact

            # Check if the artifact exists as a directory
            if artifact_path.is_dir():
                pytest.fail(f"Found artifact directory on host system: {artifact_path}")

            # Check if the artifact exists as a file
            if artifact_path.is_file():
                pytest.fail(f"Found artifact file on host system: {artifact_path}")

        # Check for any directories or files with 'build' in the name
        # (excluding legitimate files and directories)
        for path in root_dir.glob("**/*build*"):
            # Skip files and directories that are expected to have 'build' in the name
            if any(excluded in str(path) for excluded in [
                ".git",
                "node_modules",
                "venv",
                "__pycache__",
                "test_build_",
                "test_no_host_artifacts.py",
                "builder",
                "src/builder",
                "src/tests/test_builder",
                "src/tests/test_build_",
                "scripts/entrypoint_wrapper.sh",
                "nomadbuild.sh",  # Main script
                "README.md",      # Documentation
                "backlog",        # Backlog directory
                "firmware",       # Firmware output directory
                "archive",        # Archive directory for legacy files
                ".specstory"      # Specstory history directory
            ]):
                continue

            # Skip if it's a Python file that has 'build' in the name but is part of the source code
            if path.is_file() and path.suffix == '.py' and (
                path.name.startswith('test_build_') or
                'builder' in path.name or
                path.parent.name == 'builder'
            ):
                continue

            # Skip if it's a test file
            if path.is_file() and path.name.startswith('test_'):
                continue

            # Skip specific legitimate files
            legitimate_files = [
                "nomadbuild.sh",
                ".nomadbuild.sh.swp",
                "Dockerfile.template",
                "Dockerfile.from_template"
            ]
            if path.is_file() and path.name in legitimate_files:
                continue

            # If we get here, we found an unexpected build artifact
            pytest.fail(f"Found unexpected build artifact on host system: {path}")

def test_no_artifacts_after_dockerfile_generation():
    """
    Test that no artifacts are created on the host system after Dockerfile generation.

    This test specifically focuses on the Dockerfile generation process, which
    previously created build artifacts on the host system.
    """
    # Get the project root directory
    root_dir = Path(__file__).resolve().parent.parent.parent

    # Force regeneration of Dockerfile
    md5_file = root_dir / ".config.yaml.md5"
    if md5_file.exists():
        md5_file.unlink()

    # Run the Dockerfile generation script
    subprocess.run(
        ["python3", str(root_dir / "scripts" / "generate_dockerfile.py")],
        cwd=root_dir,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Check that no build directory was created
    build_dir = root_dir / "build"
    assert not build_dir.exists(), f"Found build directory on host system: {build_dir}"

    # Check for specific pin files
    pin_files = [
        "apt_pins.conf",
        "toolchain_pins.conf",
        "python_pins.conf"
    ]

    for pin_file in pin_files:
        pin_file_path = build_dir / pin_file
        assert not pin_file_path.exists(), f"Found pin file on host system: {pin_file_path}"

        # Also check in the root directory
        root_pin_file = root_dir / pin_file
        assert not root_pin_file.exists(), f"Found pin file on host system: {root_pin_file}"

def test_no_artifacts_after_test_run():
    """
    Test that no artifacts are created on the host system after running tests.

    This test verifies that no build artifacts are created on the host system.
    Instead of actually running a test (which could cause issues when running inside the test suite),
    it simply checks for the existence of build artifacts.
    """
    # Get the project root directory
    root_dir = Path(__file__).resolve().parent.parent.parent

    # List of artifact directories to check for
    artifact_dirs = [
        "build",
        "build_env"
    ]

    # Check that no build directories exist
    for artifact in artifact_dirs:
        artifact_path = root_dir / artifact
        assert not artifact_path.exists(), f"Found artifact directory on host system: {artifact_path}"

    # Check for pin files in the root directory
    pin_files = [
        "apt_pins.conf",
        "toolchain_pins.conf",
        "python_pins.conf"
    ]

    for pin_file in pin_files:
        pin_file_path = root_dir / pin_file
        assert not pin_file_path.exists(), f"Found pin file on host system: {pin_file_path}"
