# test_builder_utils.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
import pytest
import subprocess
from unittest.mock import patch, MagicMock

from src.builder import utils

# ----------------------
# run_command utility tests (item 68)
# ----------------------

@patch('src.builder.utils.subprocess.run')
def test_run_command_capture_stdout(mock_sub_run):
    """run_command should return captured stdout when command succeeds."""
    mock_completed = MagicMock()
    mock_completed.stdout = "hello world\n"
    mock_completed.stderr = ""
    mock_sub_run.return_value = mock_completed

    result = utils.run_command(["echo", "hello"], capture_output=True)
    assert result == "hello world"
    mock_sub_run.assert_called_once()

@patch('src.builder.utils.subprocess.run')
def test_run_command_check_raises_on_failure(mock_sub_run):
    """When check=True and command fails, run_command should raise the CalledProcessError."""
    cpe = subprocess.CalledProcessError(returncode=1, cmd=["false"])
    cpe.stdout = "out"
    cpe.stderr = "err"
    mock_sub_run.side_effect = cpe

    with pytest.raises(subprocess.CalledProcessError):
        utils.run_command(["false"], check=True)

@patch('src.builder.utils.subprocess.run')
def test_run_command_returns_none_on_filenotfound(mock_sub_run):
    """If underlying command is missing, run_command returns None when check=False."""
    mock_sub_run.side_effect = FileNotFoundError()
    result = utils.run_command(["nonexistent"], check=False)
    assert result is None

@patch('src.builder.utils.subprocess.run')
def test_run_command_timeout_returns_none(mock_sub_run):
    """TimeoutExpired should be caught and return None when check=False."""
    mock_sub_run.side_effect = subprocess.TimeoutExpired(cmd=["sleep"], timeout=1)
    result = utils.run_command(["sleep", "2"], check=False)
    assert result is None 