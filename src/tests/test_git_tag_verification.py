#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for git tag verification functionality.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from builder.git_ops import verify_tag_exists


class TestGitTagVerification(unittest.TestCase):
    """Test cases for git tag verification."""

    @patch('builder.git_ops.run_command')
    def test_verify_tag_exists_local_success(self, mock_run_command):
        """Test that verify_tag_exists returns True when tag exists locally."""
        # Mock the run_command function to return a successful fetch and tag exists locally
        mock_run_command.side_effect = [
            None,  # git fetch
            "v2.7.0"  # git tag -l v2.7.0
        ]

        result = verify_tag_exists(Path("/fake/repo"), "v2.7.0")
        self.assertTrue(result)
        
        # Verify that run_command was called with the correct arguments
        mock_run_command.assert_any_call(["git", "fetch", "--tags", "--force"], cwd=Path("/fake/repo"))
        mock_run_command.assert_any_call(["git", "tag", "-l", "v2.7.0"], cwd=Path("/fake/repo"), capture_output=True)

    @patch('builder.git_ops.run_command')
    def test_verify_tag_exists_remote_success(self, mock_run_command):
        """Test that verify_tag_exists returns True when tag exists in remote but not locally."""
        # Mock the run_command function to return a successful fetch, tag doesn't exist locally but exists in remote
        mock_run_command.side_effect = [
            None,  # git fetch
            "",  # git tag -l v2.7.0 (not found locally)
            "abcdef1234567890 refs/tags/v2.7.0"  # git ls-remote (found in remote)
        ]

        result = verify_tag_exists(Path("/fake/repo"), "v2.7.0")
        self.assertTrue(result)
        
        # Verify that run_command was called with the correct arguments
        mock_run_command.assert_any_call(["git", "fetch", "--tags", "--force"], cwd=Path("/fake/repo"))
        mock_run_command.assert_any_call(["git", "tag", "-l", "v2.7.0"], cwd=Path("/fake/repo"), capture_output=True)
        mock_run_command.assert_any_call(
            ["git", "ls-remote", "--tags", "origin", "refs/tags/v2.7.0"], 
            cwd=Path("/fake/repo"), 
            capture_output=True
        )

    @patch('builder.git_ops.run_command')
    def test_verify_tag_does_not_exist(self, mock_run_command):
        """Test that verify_tag_exists returns False when tag doesn't exist."""
        # Mock the run_command function to return a successful fetch, tag doesn't exist locally or in remote
        mock_run_command.side_effect = [
            None,  # git fetch
            "",  # git tag -l v2.7.0 (not found locally)
            ""  # git ls-remote (not found in remote)
        ]

        result = verify_tag_exists(Path("/fake/repo"), "v2.7.0")
        self.assertFalse(result)
        
        # Verify that run_command was called with the correct arguments
        mock_run_command.assert_any_call(["git", "fetch", "--tags", "--force"], cwd=Path("/fake/repo"))
        mock_run_command.assert_any_call(["git", "tag", "-l", "v2.7.0"], cwd=Path("/fake/repo"), capture_output=True)
        mock_run_command.assert_any_call(
            ["git", "ls-remote", "--tags", "origin", "refs/tags/v2.7.0"], 
            cwd=Path("/fake/repo"), 
            capture_output=True
        )

    @patch('builder.git_ops.run_command')
    def test_verify_tag_exists_fetch_fails(self, mock_run_command):
        """Test that verify_tag_exists handles fetch failures gracefully."""
        # Mock the run_command function to fail on fetch but succeed on local tag check
        mock_run_command.side_effect = [
            Exception("Network error"),  # git fetch fails
            "v2.7.0"  # git tag -l v2.7.0 (found locally)
        ]

        result = verify_tag_exists(Path("/fake/repo"), "v2.7.0")
        self.assertTrue(result)
        
        # Verify that run_command was called with the correct arguments
        mock_run_command.assert_any_call(["git", "fetch", "--tags", "--force"], cwd=Path("/fake/repo"))
        mock_run_command.assert_any_call(["git", "tag", "-l", "v2.7.0"], cwd=Path("/fake/repo"), capture_output=True)

    @patch('builder.git_ops.run_command')
    def test_verify_tag_exists_all_checks_fail(self, mock_run_command):
        """Test that verify_tag_exists returns False when all checks fail."""
        # Mock the run_command function to fail on all checks
        mock_run_command.side_effect = [
            Exception("Network error"),  # git fetch fails
            Exception("Git error"),  # git tag -l fails
            Exception("Remote error")  # git ls-remote fails
        ]

        result = verify_tag_exists(Path("/fake/repo"), "v2.7.0")
        self.assertFalse(result)
        
        # Verify that run_command was called with the correct arguments
        mock_run_command.assert_any_call(["git", "fetch", "--tags", "--force"], cwd=Path("/fake/repo"))
        mock_run_command.assert_any_call(["git", "tag", "-l", "v2.7.0"], cwd=Path("/fake/repo"), capture_output=True)
        mock_run_command.assert_any_call(
            ["git", "ls-remote", "--tags", "origin", "refs/tags/v2.7.0"], 
            cwd=Path("/fake/repo"), 
            capture_output=True
        )


if __name__ == '__main__':
    unittest.main()
