#!/usr/bin/env python3
# generate_dockerfile.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
# Script to generate a Dockerfile from a config.yaml file
# This ensures all version pins are centralized in one place

import os
import sys
import yaml
import re
import argparse
from pathlib import Path

# Constants
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_FILE = PROJECT_ROOT / "config.yaml"
TEMPLATE_FILE = PROJECT_ROOT / "Dockerfile.template"
OUTPUT_FILE = PROJECT_ROOT / "Dockerfile"

# Check if optimized template exists, use it if available
OPTIMIZED_TEMPLATE = PROJECT_ROOT / "Dockerfile.template.optimized"
if OPTIMIZED_TEMPLATE.exists():
    TEMPLATE_FILE = OPTIMIZED_TEMPLATE
    print(f"Using optimized Dockerfile template: {OPTIMIZED_TEMPLATE}")

# No pin files are created on the host - they are generated inside the container

def load_config():
    """Load configuration from config.yaml file."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config file: {e}", file=sys.stderr)
        sys.exit(1)

def generate_apt_pins_file(config):
    """Generate apt_pins.conf file from config - now done inside the container."""
    # No longer generating files on the host
    pass

def generate_toolchain_pins_file(config):
    """Generate toolchain_pins.conf file from config - now done inside the container."""
    # No longer generating files on the host
    pass

def generate_python_pins_file(config):
    """Generate python_pins.conf file from config - now done inside the container."""
    # No longer generating files on the host
    pass

def generate_dockerfile(config):
    """Generate Dockerfile from template and config."""
    try:
        with open(TEMPLATE_FILE, 'r') as f:
            template = f.read()

        # Replace placeholders with values from config
        replacements = {
            # Base image
            'BASE_IMAGE_DIGEST': str(config['base_image']['digest']),

            # OS config
            'TZ': str(config['os_config']['timezone']),
            'LC_ALL': str(config['os_config']['locale']),
            'LANG': str(config['os_config']['locale']),
            'PYTHONHASHSEED': str(config['os_config']['python_hash_seed']),

            # Toolchain versions
            'GCC': str(config['toolchain']['gcc']),
            'CMAKE': str(config['toolchain']['cmake']),
            'OBJCOPY': str(config['toolchain']['objcopy']),
            'PYTHON3': str(config['toolchain']['python3']),

            # APT packages
            'CA_CERTIFICATES': str(config['apt_packages']['ca-certificates']),
            'CURL': str(config['apt_packages']['curl']),
            'GNUPG': str(config['apt_packages']['gnupg']),
            'PANDOC': str(config['apt_packages']['pandoc']),
            'PERL': str(config['apt_packages']['perl']),
            'PYTHON3_PIP': str(config['apt_packages']['python3-pip']),
            'PYTHON3_VENV': str(config['apt_packages']['python3-venv']),
            'NODEJS': str(config['apt_packages']['nodejs']),

            # Python packages
            'FLASK': str(config['python_packages']['flask']),
            'FLASK_SOCKETIO': str(config['python_packages']['flask-socketio']),
            'PYTEST': str(config['python_packages']['pytest']),
            'PYTEST_MOCK': str(config['python_packages']['pytest-mock']),
            'PYTEST_SUGAR': str(config['python_packages']['pytest-sugar']),
            'REQUESTS': str(config['python_packages']['requests']),
            'WERKZEUG': str(config['python_packages']['werkzeug']),
            'JINJA2': str(config['python_packages']['jinja2']),
            'ITSDANGEROUS': str(config['python_packages']['itsdangerous']),
            'BLINKER': str(config['python_packages']['blinker']),
            'PYTHON_SOCKETIO': str(config['python_packages']['python-socketio']),
            'PYTHON_ENGINEIO': str(config['python_packages']['python-engineio']),
            'BIDICT': str(config['python_packages']['bidict']),
            'SIMPLE_WEBSOCKET': str(config['python_packages']['simple-websocket']),
            'H11': str(config['python_packages']['h11']),
            'WSPROTO': str(config['python_packages']['wsproto']),
            'PYYAML': str(config['python_packages']['pyyaml']),
            'ESP_IDF_MONITOR': str(config['python_packages']['esp-idf-monitor']),
            'IDF_COMPONENT_MANAGER': str(config['python_packages']['idf-component-manager']),
            'KCONFIGLIB': str(config['python_packages']['kconfiglib']),
        }

        # Replace all placeholders
        for key, value in replacements.items():
            template = template.replace(f"${{{key}}}", value)

        # Check for any remaining placeholders
        remaining_placeholders = re.findall(r'\${([A-Z0-9_]+)}', template)
        if remaining_placeholders:
            print(f"Warning: The following placeholders were not replaced: {', '.join(remaining_placeholders)}", file=sys.stderr)

        # Write the generated Dockerfile
        with open(OUTPUT_FILE, 'w') as f:
            f.write(template)

        print(f"✅ Generated {OUTPUT_FILE}")
    except Exception as e:
        print(f"Error generating Dockerfile: {e}", file=sys.stderr)
        sys.exit(1)

def cleanup():
    """No cleanup needed as we don't create any temporary files."""
    pass

def calculate_md5(file_path):
    """Calculate MD5 hash of a file."""
    import hashlib
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        # Read file in chunks to handle large files efficiently
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

def main():
    """Main function."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Generate Dockerfile from config.yaml")
    parser.add_argument("--force", action="store_true", help="Force regeneration of Dockerfile")
    parser.add_argument("--optimized", action="store_true", help="Use optimized Dockerfile template")
    args = parser.parse_args()

    print("🔄 Generating Dockerfile from config.yaml...")

    try:
        # Check if config.yaml exists
        if not os.path.isfile(CONFIG_FILE):
            print(f"Error: Config file not found at {CONFIG_FILE}", file=sys.stderr)
            sys.exit(1)

        # Check if Dockerfile.template exists
        if not os.path.isfile(TEMPLATE_FILE):
            print(f"Error: Template file not found at {TEMPLATE_FILE}", file=sys.stderr)
            sys.exit(1)

        # Calculate MD5 hash of config.yaml
        config_md5 = calculate_md5(CONFIG_FILE)
        md5_file = os.path.join(PROJECT_ROOT, ".config.yaml.md5")

        # Check if MD5 file exists and compare hashes
        regenerate = args.force  # Force regeneration if --force is specified
        if not regenerate and os.path.isfile(md5_file):
            # Read stored MD5
            with open(md5_file, "r") as f:
                stored_md5 = f.read().strip()

            # Compare MD5 hashes
            if stored_md5 == config_md5:
                print("✅ Config unchanged. Using existing Dockerfile.")
                # Only skip regeneration if Dockerfile exists
                if os.path.isfile(OUTPUT_FILE):
                    regenerate = False
                else:
                    print("🔄 Dockerfile not found. Generating new one...")
                    regenerate = True
            else:
                print("🔄 Config changed. Regenerating Dockerfile...")
                regenerate = True
        else:
            if args.force:
                print("🔄 Forced regeneration of Dockerfile...")
            else:
                print("🔄 MD5 file missing. Regenerating Dockerfile...")
            regenerate = True

        # Return early if no regeneration needed
        if not regenerate:
            return

        # Load config
        config = load_config()

        # Generate Dockerfile only - pin files are generated inside the container
        generate_dockerfile(config)

        # Save MD5 hash to .config.yaml.md5
        with open(md5_file, "w") as f:
            f.write(config_md5)

        print("✅ Dockerfile generated successfully!")
    finally:
        # No cleanup needed
        pass

if __name__ == "__main__":
    main()
