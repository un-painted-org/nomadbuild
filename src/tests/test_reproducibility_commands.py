#!/usr/bin/env python3
# test_reproducibility_commands.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#

import os
import unittest
import tempfile
import shutil
from pathlib import Path

class TestReproducibilityCommands(unittest.TestCase):
    """Test suite for reproducibility commands in nomadbuild.sh."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Find the project root directory
        cls.script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        cls.project_root = cls.script_dir.parent.parent

        # Path to scripts
        cls.nomadbuild_script = cls.project_root / "nomadbuild.sh"

        # Ensure scripts are executable
        os.chmod(cls.nomadbuild_script, 0o755)

        # Create test binary files
        cls.temp_dir = tempfile.mkdtemp()
        cls.create_test_binary_files()

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        shutil.rmtree(cls.temp_dir)

    @classmethod
    def create_test_binary_files(cls):
        """Create test binary files for testing."""
        # Create identical binary files
        cls.identical_binary1 = Path(cls.temp_dir) / "identical1.bin"
        cls.identical_binary2 = Path(cls.temp_dir) / "identical2.bin"

        with open(cls.identical_binary1, "wb") as f:
            f.write(b"This is a test binary file for reproducibility testing.")

        shutil.copy(cls.identical_binary1, cls.identical_binary2)

        # Create different binary files
        cls.different_binary1 = Path(cls.temp_dir) / "different1.bin"
        cls.different_binary2 = Path(cls.temp_dir) / "different2.bin"

        with open(cls.different_binary1, "wb") as f:
            f.write(b"This is a test binary file for reproducibility testing.")

        with open(cls.different_binary2, "wb") as f:
            f.write(b"This is a modified test binary file for reproducibility testing.")

    def test_script_files_exist(self):
        """Test that required script files exist and are executable."""
        # Test nomadbuild.sh
        self.assertTrue(self.nomadbuild_script.exists(),
                       "nomadbuild.sh script should exist")
        self.assertTrue(os.access(self.nomadbuild_script, os.X_OK),
                       "nomadbuild.sh script should be executable")

    def test_nomadbuild_help_includes_reproducibility_options(self):
        """Test that nomadbuild.sh help includes reproducibility options."""
        with open(self.nomadbuild_script, 'r') as f:
            help_text = f.read()

        # Check for reproducibility options in help text
        self.assertIn("--repro", help_text,
                     "Help text should include --repro option")
        self.assertIn("--tag", help_text,
                     "Help text should include --tag option")



    def test_nomadbuild_script_container_integration(self):
        """Test that nomadbuild.sh correctly integrates with the container."""
        with open(self.nomadbuild_script, 'r') as f:
            script_content = f.read()

        # Check for Docker integration
        self.assertIn("docker run", script_content,
                     "Script should use docker run to execute commands in the container")

        # Check for volume mounting
        self.assertIn("-v", script_content,
                     "Script should mount volumes for container access")

        # Check for reproducibility commands
        self.assertIn("--repro", script_content,
                     "Script should handle --repro option")

        # Check for tag handling
        self.assertIn("--tag", script_content,
                     "Script should handle --tag option")

if __name__ == "__main__":
    unittest.main()
