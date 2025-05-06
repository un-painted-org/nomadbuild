#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for CLI tag verification integration.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import argparse

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from builder.cli import _handle_build_or_use_existing


class TestCLITagVerification(unittest.TestCase):
    """Test cases for CLI tag verification integration."""

    @patch('builder.cli.builder_git')
    @patch('builder.cli.ensure_clean_repo_for_build')
    @patch('builder.cli.build_esp_miner')
    @patch('builder.cli.analyze_build_output')
    @patch('builder.cli.copy_artifacts_to_output')
    @patch('builder.cli.create_and_save_build_info')
    @patch('builder.cli.sys.exit')
    def test_handle_build_with_valid_tag(self, mock_exit, mock_create_build_info, mock_copy_artifacts,
                                         mock_analyze_build, mock_build_esp_miner, mock_ensure_clean, mock_git):
        """Test that _handle_build_or_use_existing proceeds with a valid tag."""
        # Setup mocks
        args = argparse.Namespace(tag="v2.7.0", force_rebuild=True)
        mock_git.fetch_repo.return_value = (Path("/fake/repo"), False, "https://github.com/esp-miner/esp-miner.git")
        mock_git.verify_tag_exists.return_value = True
        mock_ensure_clean.return_value = True
        mock_build_esp_miner.return_value = (Path("/fake/build"), "abcdef", Path("/fake/partition.csv"),
                                            Path("/fake/flasher_args.json"), "2.7.0")
        mock_copy_artifacts.return_value = ["firmware.bin", "www.bin"]
        mock_create_build_info.return_value = {"version": "2.7.0"}

        # Call the function
        result = _handle_build_or_use_existing(args)

        # Verify the function proceeded with the build
        self.assertEqual(result, ("v2.7.0", "2.7.0", False, "https://github.com/esp-miner/esp-miner.git"))
        mock_git.verify_tag_exists.assert_called_once_with(Path("/fake/repo"), "v2.7.0")
        mock_exit.assert_not_called()  # sys.exit should not be called

    @patch('builder.cli.builder_git')
    @patch('builder.cli.sys.exit')
    @patch('builder.cli.build_esp_miner')
    def test_handle_build_with_invalid_tag(self, mock_build_esp_miner, mock_exit, mock_git):
        """Test that _handle_build_or_use_existing exits when tag doesn't exist."""
        # Setup mocks
        args = argparse.Namespace(tag="v9.9.9", force_rebuild=True)
        mock_git.fetch_repo.return_value = (Path("/fake/repo"), False, "https://github.com/esp-miner/esp-miner.git")
        mock_git.verify_tag_exists.return_value = False
        mock_git.get_esp_miner_stable_tags.return_value = ["v2.7.0", "v2.6.0", "v2.5.0"]

        # Configure sys.exit to raise an exception to prevent further execution
        mock_exit.side_effect = SystemExit

        # Call the function and expect it to raise SystemExit
        with self.assertRaises(SystemExit):
            _handle_build_or_use_existing(args)

        # Verify the function exited with an error
        mock_git.verify_tag_exists.assert_called_once_with(Path("/fake/repo"), "v9.9.9")
        mock_exit.assert_called_once()  # sys.exit should be called
        # Check that the error message contains the tag and suggestions
        self.assertIn("Tag 'v9.9.9' does not exist", mock_exit.call_args[0][0])
        self.assertIn("Available stable tags include: v2.7.0, v2.6.0, v2.5.0", mock_exit.call_args[0][0])
        # Verify that build_esp_miner was not called
        mock_build_esp_miner.assert_not_called()

    @patch('builder.cli.builder_git')
    @patch('builder.cli.sys.exit')
    @patch('builder.cli.build_esp_miner')
    def test_handle_build_with_invalid_tag_no_suggestions(self, mock_build_esp_miner, mock_exit, mock_git):
        """Test that _handle_build_or_use_existing exits when tag doesn't exist and no suggestions are available."""
        # Setup mocks
        args = argparse.Namespace(tag="v9.9.9", force_rebuild=True)
        mock_git.fetch_repo.return_value = (Path("/fake/repo"), False, "https://github.com/esp-miner/esp-miner.git")
        mock_git.verify_tag_exists.return_value = False
        mock_git.get_esp_miner_stable_tags.return_value = []

        # Configure sys.exit to raise an exception to prevent further execution
        mock_exit.side_effect = SystemExit

        # Call the function and expect it to raise SystemExit
        with self.assertRaises(SystemExit):
            _handle_build_or_use_existing(args)

        # Verify the function exited with an error
        mock_git.verify_tag_exists.assert_called_once_with(Path("/fake/repo"), "v9.9.9")
        mock_exit.assert_called_once()  # sys.exit should be called
        # Check that the error message contains the tag but no suggestions
        self.assertIn("Tag 'v9.9.9' does not exist", mock_exit.call_args[0][0])
        self.assertNotIn("Available stable tags include", mock_exit.call_args[0][0])
        # Verify that build_esp_miner was not called
        mock_build_esp_miner.assert_not_called()


if __name__ == '__main__':
    unittest.main()
