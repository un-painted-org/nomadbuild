import pytest
import subprocess
import os
from pathlib import Path

SCRIPT_PATH = Path(__file__).parent.parent.parent / "scripts" / "verify_pinned_versions.sh"

@pytest.fixture
def create_config_file(tmp_path):
    """Fixture to create a temporary config file"""
    def _create_config(content):
        config_file = tmp_path / "apt_pins.conf"
        config_file.write_text(content)
        return config_file
    return _create_config

# Simplified helper just to run the script
def run_verify_script(config_path: Path | str):
    env = os.environ.copy()

    process = subprocess.run(
        ["bash", str(SCRIPT_PATH), str(config_path)],
        capture_output=True,
        text=True,
        check=False, # We check returncode manually
        env=env # Pass environment in case needed by script itself
    )
    print(f"Script stdout:\n{process.stdout}")
    print(f"Script stderr:\n{process.stderr}")
    return process

# --- Test Cases ---

def test_comments_and_blanks_ignored(create_config_file, tmp_path):
    """Test that comments and blank lines in the config are ignored.

    Note: This test assumes the underlying dpkg-query/node commands
    will succeed in the environment where the test runs. It primarily tests
    the parsing logic of the script.
    """
    config_content = """
# This is a comment
curl=8.5.0-2ubuntu10.6

# Another comment
nodejs=22.15.0-1nodesource1
    """
    config_file = create_config_file(config_content)

    # We run this without mocking. If dpkg/node aren't installed where
    # pytest runs, the script might report mismatches, but it shouldn't
    # crash due to parsing errors, and the return code might vary.
    # We mainly check that it *attempts* to process the valid lines.
    result = run_verify_script(config_file)

    # We don't assert success/failure here, just that it processed lines
    assert "Checking curl..." in result.stdout
    assert "Checking nodejs..." in result.stdout

def test_invalid_config_path():
    """Test that the script now handles invalid paths gracefully by creating a default config."""
    invalid_path = Path("/non/existent/path/apt_pins.conf")
    # Use simplified helper
    result = run_verify_script(invalid_path)

    # The script should now succeed even with an invalid path
    # because it creates a default config in a container-only directory
    assert result.returncode == 0
    assert "Verification SUCCESS" in result.stdout

def test_no_config_path_arg():
    """Test that the script now handles missing arguments gracefully by creating a default config."""
    # Call script directly without config path arg
    process = subprocess.run(
        ["bash", str(SCRIPT_PATH)], # No argument
        capture_output=True,
        text=True,
        check=False
    )
    print(f"Script stdout (no arg):\n{process.stdout}")
    print(f"Script stderr (no arg):\n{process.stderr}")

    # The script should now succeed even without an argument
    # because it creates a default config in a container-only directory
    assert process.returncode == 0
    assert "Verification SUCCESS" in process.stdout