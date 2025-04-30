import subprocess
import os

def test_base_image_digest():
    # Determine project root and script/config paths
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    script = os.path.join(root, 'scripts', 'verify_base_image_digest.sh')
    config = os.path.join(root, 'build', 'toolchain_pins.conf')

    # Ensure the script and config exist
    assert os.path.isfile(script), f"Script not found: {script}"
    assert os.path.isfile(config), f"Config file not found: {config}"

    # Run the verifier
    result = subprocess.run(['bash', script, config], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    # Check exit code
    assert result.returncode == 0, f"Base image digest verification failed:\n{result.stdout}" 