# test_builder_gitops.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
import pytest
import sys, os
# Ensure project root is in sys.path for import resolution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from pathlib import Path
from unittest.mock import patch, MagicMock, ANY

from src.builder.build import build_esp_miner, build_cancel_event

@pytest.fixture
def temp_dir(tmp_path):
    """Temporary directory fixture for tests"""
    return tmp_path

@patch('src.builder.build.checkout_tag')
@patch('src.builder.build._find_build_outputs')
@patch('src.builder.build._verify_build_artifacts')
@patch('src.builder.build._run_idf_clean')
@patch('src.builder.build._prepare_source_code')
@patch('src.builder.build._run_idf_build')
@patch('src.builder.utils.run_command')
def test_build_esp_miner_handles_cancellation_gitops(
    mock_run_command,
    mock_run_idf_build,
    mock_prepare,
    mock_clean,
    mock_verify,
    mock_find_outputs,
    mock_checkout,
    temp_dir
):
    """Test that build_esp_miner handles cancellation correctly (Git integration)"""
    # Arrange
    mock_prepare.return_value = ("commit123", "v1.0.0-sovereign")
    mock_find_outputs.return_value = (None, None)
    mock_run_command.return_value = MagicMock(returncode=0, stdout=b'', stderr=b'')
    # Simulate cancellation in build step
    def cancel_build(repo_path, commit_ts, verbose, progress_cb):
        build_cancel_event.set()
        return None
    mock_run_idf_build.side_effect = cancel_build

    # Act
    result = build_esp_miner(temp_dir, "v1.0.0", False, lambda *_: None)

    # Assert
    assert result == (None, None, None, None, None)
    mock_checkout.assert_called_once_with(temp_dir, "v1.0.0", ANY)
    mock_clean.assert_called_once_with(temp_dir, ANY)
    mock_prepare.assert_called_once_with(temp_dir, "v1.0.0", ANY)
    mock_run_idf_build.assert_called_once_with(temp_dir, "commit123", False, ANY)
    mock_verify.assert_not_called()
    mock_find_outputs.assert_not_called()


@patch('src.builder.build.checkout_tag')
@patch('src.builder.build._find_build_outputs')
@patch('src.builder.build._verify_build_artifacts')
@patch('src.builder.build._run_idf_clean')
@patch('src.builder.build._prepare_source_code')
@patch('src.builder.build._run_idf_build')
@patch('src.builder.utils.run_command')
def test_build_esp_miner_handles_success_gitops(
    mock_run_command,
    mock_run_idf_build,
    mock_prepare,
    mock_clean,
    mock_verify,
    mock_find_outputs,
    mock_checkout,
    temp_dir
):
    """Test that build_esp_miner handles successful build (Git integration)"""
    # Arrange
    mock_prepare.return_value = ("commit123", "v1.0.0-sovereign")
    mock_run_idf_build.return_value = "/path/out.bin"
    mock_find_outputs.return_value = (Path("app.bin"), Path("boot.bin"))
    mock_run_command.return_value = MagicMock(returncode=0, stdout=b'', stderr=b'')

    # Act
    build_dir, build_output, partition_csv, flasher_args, version = build_esp_miner(
        temp_dir, "v1.0.0", False, lambda *_: None
    )

    # Assert
    assert build_dir == temp_dir / "build"
    assert build_output == "/path/out.bin"
    assert partition_csv == Path("app.bin")
    assert flasher_args == Path("boot.bin")
    assert version == "v1.0.0-sovereign"
    mock_checkout.assert_called_once_with(temp_dir, "v1.0.0", ANY)
    mock_clean.assert_called_once_with(temp_dir, ANY)
    mock_prepare.assert_called_once_with(temp_dir, "v1.0.0", ANY)
    mock_run_idf_build.assert_called_once_with(temp_dir, "commit123", False, ANY)
    mock_verify.assert_called_once_with(temp_dir / "build", ANY)
    mock_find_outputs.assert_called_once_with(temp_dir, temp_dir / "build", ANY) 