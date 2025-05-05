#!/usr/bin/env python3
# test_cli_reproducibility.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
# Unit tests for reproducibility commands in the CLI module

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, call
import tempfile
from pathlib import Path
import subprocess
import argparse

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the modules to test
from builder.cli import _handle_reproducibility_check


class TestCLIReproducibilityCommands(unittest.TestCase):
    """Test cases for reproducibility commands in the CLI module."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        # Create mock script paths
        self.mock_repro_script = self.temp_path / "run_repro_check.sh"

        # Create mock script files
        self.mock_repro_script.touch(mode=0o755)

        # Create mock args
        self.args = argparse.Namespace()
        self.args.tag = "v2.7.0"

        # Set up patches
        self.path_exists_patcher = patch('pathlib.Path.exists')
        self.mock_path_exists = self.path_exists_patcher.start()
        self.mock_path_exists.return_value = True

        self.chmod_patcher = patch('os.chmod')
        self.mock_chmod = self.chmod_patcher.start()

        self.run_command_patcher = patch('builder.utils.run_command')
        self.mock_run_command = self.run_command_patcher.start()

        # Mock process result
        self.mock_process = MagicMock()
        self.mock_process.returncode = 0
        self.mock_run_command.return_value = self.mock_process

    def tearDown(self):
        """Tear down test fixtures."""
        self.path_exists_patcher.stop()
        self.chmod_patcher.stop()
        self.run_command_patcher.stop()
        self.temp_dir.cleanup()

    @patch('builder.cli.CONTAINER_APP_DIR', Path("/app"))
    @patch('builder.cli.logger')
    def test_handle_reproducibility_check_success(self, mock_logger):
        """Test successful reproducibility check."""
        # Set up
        self.args.tag = "v2.7.0"

        # Execute
        with patch('builder.cli.Path') as mock_path:
            mock_path.return_value = self.mock_repro_script
            _handle_reproducibility_check(self.args)

        # Verify
        mock_logger.info.assert_any_call("Running reproducibility check for tag: v2.7.0")
        mock_logger.info.assert_any_call("Starting reproducibility check...")
        mock_logger.info.assert_any_call("Reproducibility check completed successfully.")

        # Verify run_command was called with correct arguments
        self.mock_run_command.assert_called_once()
        args, kwargs = self.mock_run_command.call_args
        self.assertEqual(args[0][0], "/bin/bash")
        self.assertEqual(args[0][2], "--tag")
        self.assertEqual(args[0][3], "v2.7.0")
        self.assertEqual(kwargs["check"], False)
        self.assertEqual(kwargs["stream_output"], True)

    @patch('builder.cli.CONTAINER_APP_DIR', Path("/app"))
    @patch('builder.cli.logger')
    @patch('builder.cli.sys.exit')
    def test_handle_reproducibility_check_failure(self, mock_exit, mock_logger):
        """Test failed reproducibility check."""
        # Set up
        self.args.tag = "v2.7.0"
        self.mock_process.returncode = 1

        # Execute
        with patch('builder.cli.Path') as mock_path:
            mock_path.return_value = self.mock_repro_script
            _handle_reproducibility_check(self.args)

        # Verify
        mock_logger.error.assert_any_call("Reproducibility check failed with exit code 1")
        mock_exit.assert_called_once_with(1)

    @patch('builder.cli.CONTAINER_APP_DIR', Path("/app"))
    @patch('builder.cli.logger')
    @patch('builder.cli.sys.exit')
    def test_handle_reproducibility_check_no_tag(self, mock_exit, mock_logger):
        """Test reproducibility check with no tag."""
        # Set up
        self.args.tag = None

        # Execute
        _handle_reproducibility_check(self.args)

        # Verify
        mock_logger.error.assert_called_once_with("Reproducibility check requires a tag. Use --tag <VERSION>")
        mock_exit.assert_called_once_with(1)



    @patch('builder.cli.CONTAINER_APP_DIR', Path("/app"))
    @patch('builder.cli.logger')
    @patch('builder.cli.sys.exit')
    def test_handle_reproducibility_check_script_not_found(self, mock_exit, mock_logger):
        """Test reproducibility check with script not found."""
        # Set up
        self.args.tag = "v2.7.0"
        self.mock_path_exists.return_value = False

        # Execute
        _handle_reproducibility_check(self.args)

        # Verify
        mock_logger.error.assert_any_call("Reproducibility check script not found at /app/scripts/run_repro_check.sh")
        mock_exit.assert_called_once_with(1)



    @patch('builder.cli.CONTAINER_APP_DIR', Path("/app"))
    @patch('builder.cli.logger')
    @patch('builder.cli.sys.exit')
    def test_handle_reproducibility_check_exception(self, mock_exit, mock_logger):
        """Test reproducibility check with exception."""
        # Set up
        self.args.tag = "v2.7.0"
        self.mock_run_command.side_effect = Exception("Test exception")

        # Execute
        with patch('builder.cli.Path') as mock_path:
            mock_path.return_value = self.mock_repro_script
            _handle_reproducibility_check(self.args)

        # Verify
        mock_logger.error.assert_any_call("Error running reproducibility check: Test exception")
        mock_exit.assert_called_once_with(1)




if __name__ == '__main__':
    unittest.main()
