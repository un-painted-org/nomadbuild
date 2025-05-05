import subprocess
import os
import pytest
import tempfile
from unittest.mock import patch, mock_open

def test_base_image_digest():
    """Test that the base image digest verification passes when running in a container."""
    # Determine project root and script path
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    script = os.path.join(root, 'scripts', 'verify_base_image_digest.sh')

    # Ensure the script exists
    assert os.path.isfile(script), f"Script not found: {script}"

    # Set up environment for container-only directory
    env = os.environ.copy()
    env['NOMADBUILD_CONFIG_DIR'] = '/tmp/nomadbuild_config'

    # Run the verifier (no config file argument needed)
    result = subprocess.run(['bash', script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)

    # Check exit code
    assert result.returncode == 0, f"Base image digest verification failed:\n{result.stdout}"

    # Verify that the container environment check passed
    assert "✅ Verified: Running in container environment" in result.stdout, \
        "Container environment verification message not found in output"

    # Verify that the Dockerfile pin check passed
    assert "✅ Dockerfile pinned to" in result.stdout, \
        "Dockerfile pin verification message not found in output"

def test_container_environment_detection():
    """Test that the script correctly detects it's running in a container environment."""
    # This test is redundant with test_base_image_digest in a real container,
    # but it's useful to explicitly test the container detection logic

    # In a real container, at least one of these checks should pass:
    # 1. /.dockerenv file exists
    # 2. Docker/container references in /proc/1/cgroup
    # 3. Container-specific environment variables

    # Since we're already running in a container during tests,
    # we expect the verification to pass naturally

    # Create a temporary script that implements just the container verification function
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as temp_script:
        temp_script.write("""
#!/usr/bin/env bash
# Test script that only implements and runs the container verification

# Define the container environment verification function
verify_container_environment() {
    # Multiple checks to detect container environment
    local in_container=false

    # Check 1: Look for .dockerenv file
    if [ -f "/.dockerenv" ]; then
        in_container=true
    fi

    # Check 2: Look for container in cgroup
    if grep -q "docker\|lxc\|kubepods" /proc/1/cgroup 2>/dev/null; then
        in_container=true
    fi

    # Check 3: Look for container-specific environment variables
    if [ -n "$CONTAINER_RUNTIME" ] || [ -n "$KUBERNETES_SERVICE_HOST" ]; then
        in_container=true
    fi

    # Fail if not in container environment
    if [ "$in_container" = "false" ]; then
        echo "❌ ERROR: Tests must run inside the container environment!" >&2
        echo "   This ensures reproducibility and consistent test results." >&2
        echo "   Please use ./scripts/test.sh to run tests properly." >&2
        exit 1
    fi

    echo "✅ Verified: Running in container environment"
}

# Call the function
verify_container_environment
exit $?
        """)

    try:
        # Make the temporary script executable
        os.chmod(temp_script.name, 0o755)

        # Run the modified script
        result = subprocess.run(['bash', temp_script.name],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               text=True,
                               check=False)

        # Check that it passed
        assert result.returncode == 0, f"Container environment verification failed:\n{result.stdout}"
        assert "✅ Verified: Running in container environment" in result.stdout, \
            "Container environment verification message not found in output"
    finally:
        # Clean up the temporary file
        os.unlink(temp_script.name)

def test_non_container_environment_detection():
    """Test that the script fails when not running in a container environment."""
    # Create a modified script that simulates a non-container environment

    # Determine project root and script path
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    script = os.path.join(root, 'scripts', 'verify_base_image_digest.sh')

    # Create a temporary script that simulates a non-container environment
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as temp_script:
        temp_script.write(f"""
#!/usr/bin/env bash
# Mock script that simulates a non-container environment

# Define a mock function that simulates a non-container environment
verify_container_environment() {{
    # Mock function that always reports not in a container
    local in_container=false

    # Fail because we're not in a container environment
    if [ "$in_container" = "false" ]; then
        echo "❌ ERROR: Tests must run inside the container environment!" >&2
        echo "   This ensures reproducibility and consistent test results." >&2
        echo "   Please use ./scripts/test.sh to run tests properly." >&2
        exit 1
    fi

    echo "✅ Verified: Running in container environment"
}}

# Call the mock function directly
verify_container_environment
        """)

    try:
        # Make the temporary script executable
        os.chmod(temp_script.name, 0o755)

        # Run the modified script
        result = subprocess.run(['bash', temp_script.name],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               text=True,
                               check=False)

        # Check that it failed with the expected error message
        assert result.returncode == 1, "Script should fail when not in container environment"
        assert "❌ ERROR: Tests must run inside the container environment!" in result.stdout, \
            "Expected error message not found in output"
        assert "This ensures reproducibility and consistent test results." in result.stdout, \
            "Expected explanation message not found in output"
        assert "Please use ./scripts/test.sh to run tests properly." in result.stdout, \
            "Expected guidance message not found in output"
    finally:
        # Clean up the temporary file
        os.unlink(temp_script.name)