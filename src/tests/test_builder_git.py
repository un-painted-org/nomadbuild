# test_builder_git.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.builder.git_ops import fetch_repo, get_esp_miner_stable_tags, ESP_MINER_REPO

# --- Tests for clone_repo ---

@pytest.fixture
def temp_dir():
    """Create a temporary directory for the tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

def test_fetch_repo_new_clone(temp_dir, mocker):
    """Test repo cloning when directory doesn't exist."""
    # Mock git to avoid actual cloning
    mock_run = mocker.patch('src.builder.git_ops.run_command')
    # Mock get_env_dir to return our temp directory
    mocker.patch('src.builder.git_ops.get_env_dir', return_value=temp_dir)
    
    # Call with defaults
    repo_path = fetch_repo(ESP_MINER_REPO, "ESP-Miner")
    
    # Verify git clone command was called with expected arguments
    mock_run.assert_called_once()
    clone_cmd = mock_run.call_args[0][0]
    assert "git" in clone_cmd
    assert "clone" in clone_cmd
    assert ESP_MINER_REPO in clone_cmd
    assert str(temp_dir / "repos" / "ESP-Miner") in str(repo_path)

def test_fetch_repo_existing(temp_dir, mocker):
    """Test repo update when directory already exists."""
    # Set up existing repo structure
    repo_dir = temp_dir / "repos" / "ESP-Miner"
    repo_dir.mkdir(parents=True)
    (repo_dir / ".git").mkdir(parents=True)
    
    # Mock git to avoid actual operations
    mock_run = mocker.patch('src.builder.git_ops.run_command')
    # Mock get_env_dir to return our temp directory
    mocker.patch('src.builder.git_ops.get_env_dir', return_value=temp_dir)
    
    # Call function
    repo_path = fetch_repo(ESP_MINER_REPO, "ESP-Miner")
    
    # Verify fetch was called instead of clone
    assert mock_run.call_count == 1
    fetch_cmd = mock_run.call_args[0][0]
    assert "git" in fetch_cmd
    assert "fetch" in fetch_cmd
    assert "--tags" in fetch_cmd

# --- Tests for _get_esp_miner_stable_tags ---

def test_get_stable_tags(mocker):
    """Test parsing and sorting of git tags."""
    mock_repo_path = Path("/mock/repo")
    # Simulate git tag output
    git_output = """
v2.5.0
v2.6.0b1
v2.6.1
v2.6.2
v2.6.3
v3.0.0-alpha
latest
v2.4.5
"""
    # Mock run_command
    mock_run = mocker.patch('src.builder.git_ops.run_command')
    mock_run.return_value = git_output.strip()
    
    # Call the function
    stable_tags = get_esp_miner_stable_tags(mock_repo_path)
    
    # Verify the result contains only stable tags in correct order
    assert len(stable_tags) >= 4  # At least 4 stable tags from our test data
    assert stable_tags[0] == "v2.6.3"  # Most recent should be first
    assert stable_tags[1] == "v2.6.2"
    assert "v2.6.0b1" not in stable_tags  # Beta should be excluded
    assert "v3.0.0-alpha" not in stable_tags  # Alpha should be excluded

def test_get_stable_tags_none_found(mocker):
    """Test when no stable tags match the pattern."""
    mock_repo_path = Path("/mock/repo")
    git_output = "v3.0.0-alpha\nlatest\nrc-1"
    
    # Mock run_command
    mock_run = mocker.patch('src.builder.git_ops.run_command')
    mock_run.return_value = git_output.strip()
    
    # Call the function
    stable_tags = get_esp_miner_stable_tags(mock_repo_path)
    
    # Verify empty result when no stable tags found
    assert len(stable_tags) == 0 