# test_builder_git_ops.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import src.builder.git_ops as git_mod

# ----------------------
# get_esp_miner_stable_tags
# ----------------------

@patch('src.builder.git_ops.run_command')
def test_get_esp_miner_stable_tags_filters_and_limits(mock_run_cmd, tmp_path):
    # First call is fetch, second call is tag list
    mock_run_cmd.side_effect = ["", "v2.0.0\nv1.1.0\nv1.0.0-rc1\nv0.9.0"]
    tags = git_mod.get_esp_miner_stable_tags(tmp_path)
    # Should only include vX.Y.Z pattern and sorted desc
    assert tags == ["v2.0.0", "v1.1.0", "v0.9.0"]
    # Ensure fetch and tag list commands invoked
    assert mock_run_cmd.call_count == 2

# ----------------------
# checkout_tag
# ----------------------

@patch('src.builder.git_ops.verify_tag_exists')
@patch('src.builder.git_ops.run_command')
def test_checkout_tag_success(mock_run_cmd, mock_verify_tag, tmp_path):
    # Mock verify_tag_exists to return True
    mock_verify_tag.return_value = True

    # simulate sequence of git commands
    mock_run_cmd.side_effect = [
        "",          # fetch tags
        "",          # checkout
        "deadbeef\n" # rev-parse
    ]
    commit = git_mod.checkout_tag(tmp_path, "v1.2.3")
    assert commit == "deadbeef"
    # Ensure commands executed in order
    cmds = [call.args[0][:2] for call in mock_run_cmd.call_args_list]
    assert [c[0] for c in cmds][:2] == ["git", "git"]

@patch('src.builder.git_ops.get_esp_miner_stable_tags')
@patch('src.builder.git_ops.verify_tag_exists')
def test_checkout_tag_missing(mock_verify_tag, mock_get_stable_tags, tmp_path):
    # Mock verify_tag_exists to return False
    mock_verify_tag.return_value = False
    # Mock get_esp_miner_stable_tags to return some tags
    mock_get_stable_tags.return_value = ["v2.7.0", "v2.6.0"]

    commit = git_mod.checkout_tag(tmp_path, "v9.9.9")
    assert commit is None
    # Verify that verify_tag_exists was called
    mock_verify_tag.assert_called_once_with(tmp_path, "v9.9.9")
    # Verify that get_esp_miner_stable_tags was called
    mock_get_stable_tags.assert_called_once_with(tmp_path)

# ----------------------
# fetch_repo
# ----------------------

@patch('src.builder.git_ops.get_env_dir')
@patch('src.builder.git_ops.run_command')
def test_fetch_repo_clone_when_missing(mock_run_cmd, mock_get_env_dir, tmp_path):
    mock_get_env_dir.return_value = tmp_path
    repo_dir, is_custom_repo, repo_url = git_mod.fetch_repo("https://example.com/repo.git", "Repo")
    # Since directory absent, first command should be git clone
    first_cmd = mock_run_cmd.call_args_list[0].args[0]
    assert first_cmd[:2] == ["git", "clone"]
    expected_path = tmp_path / 'repos' / 'Repo'
    assert repo_dir == expected_path
    assert is_custom_repo is False
    assert repo_url == "https://example.com/repo.git"

# ----------------------
# ensure_clean_repo_for_build
# ----------------------

@patch('src.builder.git_ops.run_command')
def test_ensure_clean_repo_success(mock_run_cmd, tmp_path):
    tmp_path.mkdir(exist_ok=True)
    # Provide .git directory to simulate repo
    (tmp_path / '.git').mkdir()
    ok = git_mod.ensure_clean_repo_for_build(tmp_path)
    assert ok is True