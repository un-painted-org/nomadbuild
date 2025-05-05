import subprocess
import os
import tempfile
import shutil
import pytest

def test_base_image_digest_negative():
    """Test that base image digest verification fails when digests don't match."""
    # Determine project root and script path
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    script = os.path.join(root, 'scripts', 'verify_base_image_digest.sh')

    # Ensure the script exists
    assert os.path.isfile(script), f"Script not found: {script}"

    # Create a temporary directory for the test
    temp_dir = tempfile.mkdtemp()
    temp_config_path = os.path.join(temp_dir, 'toolchain_pins.conf')

    # Create a config file with a different digest
    with open(temp_config_path, 'w') as temp_config:
        # Use a different digest than the one in the Dockerfile
        modified_digest = 'sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
        temp_config.write(f"base_image={modified_digest}\n")

    # Set up environment to use our temporary directory
    env = os.environ.copy()
    env['NOMADBUILD_CONFIG_DIR'] = temp_dir

    try:
        # Run the verifier with our environment pointing to the modified config
        result = subprocess.run(['bash', script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)

        # Check that the verifier FAILS (non-zero exit code) with mismatch
        assert result.returncode != 0, f"Base image digest verification incorrectly succeeded with mismatched digests:\n{result.stdout}"

        # Check that the output contains an informative error message
        assert "Dockerfile FROM not pinned to" in result.stdout or "❌ Dockerfile FROM not pinned to" in result.stdout, f"Error message does not indicate digest mismatch:\n{result.stdout}"
        assert "❌" in result.stdout, f"Error indicator not found in output:\n{result.stdout}"

    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)