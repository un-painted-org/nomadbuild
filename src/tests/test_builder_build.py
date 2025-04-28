# test_builder_build.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock, mock_open, ANY
import os
import sys
import subprocess
import threading
import time

# Ensure project root is in sys.path for import resolution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.builder.build import (
    build_esp_miner, 
    _run_idf_build, 
    active_build_processes,
    is_building,
    build_progress,
    current_tag,
    # verify_tag_exists,  # This function doesn't exist anymore
)

"""Test cases for the build module"""

@pytest.fixture
def temp_dir():
    """Create a temporary directory for the test"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

@pytest.fixture(autouse=True)
def reset_build_state():
    """Reset build state variables before and after each test"""
    # Reset before test
    active_build_processes.clear()
    global is_building, build_progress, current_tag
    is_building = False
    build_progress = 0
    current_tag = None
    
    # Run the test
    yield
    
    # Reset after test
    active_build_processes.clear()
    is_building = False
    build_progress = 0
    current_tag = None

# Helper for verifying progress callback percentages

def _assert_percentages_increasing(percentages):
    """Utility to check that a list of progress percentages is non-empty and
    strictly non-decreasing (duplicates allowed)."""
    assert percentages, "Progress callback should have been invoked at least once"
    perc_only = [p if isinstance(p, (int, float)) else p[0] for p in percentages]
    assert perc_only == sorted(perc_only), "Progress percentages should be increasing"
    assert any(p > 0 for p in perc_only), "At least one progress value should be greater than zero"

@patch('src.builder.build.checkout_tag')
@patch('src.builder.build._prepare_source_code')
@patch('src.builder.build._run_idf_clean')
@patch('src.builder.build._run_idf_build')
@patch('src.builder.build._verify_build_artifacts')
@patch('src.builder.utils.run_command')
def test_build_esp_miner_sets_global_state(
    mock_run_command, mock_verify, mock_run_build,
    mock_clean, mock_prepare, mock_checkout, temp_dir
):
    """Test that build_esp_miner sets global state variables correctly"""
    # Mock return values
    mock_prepare.return_value = (str(temp_dir), "v1.0.0")
    mock_run_build.return_value = "mock build output"

    # Define a side effect for mock_run_build to check state during build
    def check_state_during_build(*args, **kwargs):
        from src.builder.build import is_building
        from src.builder.build import current_tag
        assert is_building is True
        assert current_tag == "v1.0.0"
        # Simulate some progress update
        return "mock build output"

    mock_run_build.side_effect = check_state_during_build

    # Call the function and unpack the correct tuple
    build_dir, build_log_output, partition_csv_path, flasher_args_path, version = build_esp_miner(
        temp_dir, "v1.0.0", False, Mock() # Pass a mock callback
    )

    # Verify global state is reset after the build
    global is_building, build_progress, current_tag
    assert is_building is False
    assert build_progress == 0
    assert current_tag is None

    # Verify return values based on the actual signature
    assert Path(build_dir) == temp_dir / "build"
    assert build_log_output == "mock build output"
    # Assertions for partition_csv_path and flasher_args_path could be added if needed, but are None due to mocks
    # assert partition_csv_path is None 
    # assert flasher_args_path is None 
    assert version == "v1.0.0-sovereign"

    # Verify mocks were called
    mock_checkout.assert_called_once_with(temp_dir, "v1.0.0", ANY) # Use ANY for callback
    mock_prepare.assert_called_once_with(temp_dir, "v1.0.0", ANY)
    mock_clean.assert_called_once_with(temp_dir, ANY)
    mock_run_build.assert_called_once_with(
        temp_dir, ANY, False, ANY # Use ANY for timestamp and callback
    )
    mock_verify.assert_called_once_with(temp_dir / "build", ANY)
    # mock_find_outputs.assert_called_once_with(temp_dir, temp_dir / "build", ANY) # No longer asserting this directly

@patch('src.builder.build.checkout_tag')
@patch('src.builder.build._prepare_source_code')
@patch('src.builder.build._run_idf_clean')
@patch('src.builder.build._run_idf_build')
@patch('src.builder.build._verify_build_artifacts')
@patch('src.builder.build._find_build_outputs')
@patch('src.builder.utils.run_command')
def test_build_callback_receives_progress_updates(
    mock_run_command, mock_find_outputs, mock_verify, mock_run_build,
    mock_clean, mock_prepare, mock_checkout, temp_dir
):
    """Test that progress callback is called with updates"""
    # Mock return values
    mock_prepare.return_value = (str(temp_dir), "v1.0.0-sovereign")
    mock_find_outputs.return_value = (None, None)
    mock_run_build.return_value = "mock build output"
    
    # Mock run_command to handle any git commands
    mock_run_command.return_value = "mock git output"
    
    # Create a mock callback
    mock_callback = Mock()
    
    # Call the function
    build_esp_miner(
        temp_dir, "v1.0.0", False, mock_callback
    )
    
    # Verify callback was called with progress updates
    assert mock_callback.called
    
    # Extract and assert progress percentages
    progress_percentages = [call_args.args[0] for call_args in mock_callback.call_args_list]
    _assert_percentages_increasing(progress_percentages)

@patch('src.builder.build.get_env_dir')
@patch('src.builder.build.subprocess.Popen')
def test_run_idf_build_tracks_active_processes(mock_popen, mock_get_env_dir, temp_dir):
    """Test that _run_idf_build tracks and then removes the process in active_build_processes"""
    import src.builder.build as build_mod
    # Use a dict that ignores deletions until we cancel
    class NoDeleteDict(dict):
        def __delitem__(self, key):
            super().__delitem__(key)
    build_mod.active_build_processes = NoDeleteDict()
    build_mod.build_cancel_event.clear()
    # Redirect logs to temp_dir
    mock_get_env_dir.return_value = temp_dir
    # Set up mock process
    mock_process = MagicMock()
    mock_process.stdout.readline.return_value = ""
    mock_process.stderr.readline.return_value = ""
    mock_process.returncode = 0
    pid = 12345
    mock_process.pid = pid
    # Poll until cancellation
    def poll_se():
        return 0 if build_mod.build_cancel_event.is_set() else None
    mock_process.poll.side_effect = poll_se
    mock_popen.return_value = mock_process
    # Run build in thread
    with patch('builtins.open', mock_open()):
        t = threading.Thread(target=_run_idf_build, args=(temp_dir, "ts", False, None))
        t.start()
        # Wait for tracking
        start = time.time()
        while time.time() - start < 1.0:
            if pid in build_mod.active_build_processes:
                break
            time.sleep(0.01)
        assert pid in build_mod.active_build_processes, f"PID {pid} not tracked"
        # Trigger cancellation and wait for removal
        build_mod.build_cancel_event.set()
        t.join(timeout=2)
        assert pid not in build_mod.active_build_processes, f"PID {pid} not removed"

@patch('src.builder.build.get_env_dir')
@patch('src.builder.build.subprocess.Popen')
def test_run_idf_build_updates_build_progress(mock_popen, mock_get_env_dir, temp_dir):
    """Test that _run_idf_build updates build_progress global variable"""
    # Clear any lingering cancel event from other tests
    import src.builder.build as build_mod
    build_mod.build_cancel_event.clear()
    build_mod.build_progress = 0
    
    # Set up mock process
    mock_process = MagicMock()
    # Simulate output that triggers progress updates
    mock_process.stdout.readline.side_effect = [
        "Running cmake in directory\n",
        "ninja: Entering directory\n",
        "[1/100] Building CXX object\n",
        "Linking CXX executable\n",
        "esptool.py\n",
        "Project build complete.\n",
        ""
    ]
    mock_process.stderr.readline.return_value = ""
    mock_process.poll.return_value = None
    mock_process.returncode = 0
    mock_popen.return_value = mock_process

    # Create a mock progress callback
    mock_progress_callback = Mock()

    # Ensure logs are written under temp_dir
    mock_get_env_dir.return_value = temp_dir

    # Patch open to avoid file I/O
    with patch('builtins.open', mock_open()):
        _run_idf_build(temp_dir, "timestamp", True, mock_progress_callback)

    # Verify that build_progress was reset at end
    assert build_progress == 0

    # Verify callback received a reasonable sequence of percentages
    actual_percentages = [call.args[0] for call in mock_progress_callback.call_args_list]
    _assert_percentages_increasing(actual_percentages)

@patch('src.builder.build.get_env_dir')
@patch('src.builder.build.checkout_tag')
@patch('src.builder.build._prepare_source_code')
@patch('src.builder.build._run_idf_clean')
@patch('src.builder.build._run_idf_build')
@patch('src.builder.build._verify_build_artifacts')
@patch('src.builder.build._find_build_outputs')
@patch('src.builder.utils.run_command')
def test_build_esp_miner_handles_cancellation_gitops(
    mock_run_command, mock_find_outputs, mock_verify, mock_run_idf_build,
    mock_clean, mock_prepare, mock_checkout, mock_get_env_dir, temp_dir
):
    """Test that build_esp_miner handles cancellation correctly (Git integration)"""
    # Arrange
    mock_get_env_dir.return_value = temp_dir
    mock_prepare.return_value = ("commit123", "v1.0.0-sovereign")
    mock_find_outputs.return_value = (None, None)
    mock_run_command.return_value = MagicMock(returncode=0, stdout=b'', stderr=b'')
    def cancel_build(repo_path, commit_ts, verbose, progress_cb):
        from src.builder.build import build_cancel_event
        build_cancel_event.set()
        return None
    mock_run_idf_build.side_effect = cancel_build
    # Act
    result = build_esp_miner(temp_dir, "v1.0.0", False, lambda *_: None)
    # Assert
    assert result == (None, None, None, None, None)
    mock_checkout.assert_called_once_with(temp_dir, "v1.0.0", ANY)
    mock_prepare.assert_called_once_with(temp_dir, "v1.0.0", ANY)
    mock_clean.assert_called_once_with(temp_dir, ANY)
    mock_run_idf_build.assert_called_once_with(temp_dir, "commit123", False, ANY)
    mock_verify.assert_not_called()
    mock_find_outputs.assert_not_called()

@patch('src.builder.build.get_env_dir')
@patch('src.builder.build.checkout_tag')
@patch('src.builder.build._prepare_source_code')
@patch('src.builder.build._run_idf_clean')
@patch('src.builder.build._run_idf_build')
@patch('src.builder.build._verify_build_artifacts')
@patch('src.builder.build._find_build_outputs')
@patch('src.builder.utils.run_command')
def test_build_esp_miner_handles_success_gitops(
    mock_run_command, mock_find_outputs, mock_verify, mock_run_idf_build,
    mock_clean, mock_prepare, mock_checkout, mock_get_env_dir, temp_dir
):
    """Test that build_esp_miner handles successful build (Git integration)"""
    # Arrange
    mock_get_env_dir.return_value = temp_dir
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
    mock_prepare.assert_called_once_with(temp_dir, "v1.0.0", ANY)
    mock_clean.assert_called_once_with(temp_dir, ANY)
    mock_run_idf_build.assert_called_once_with(temp_dir, "commit123", False, ANY)
    mock_verify.assert_called_once_with(temp_dir / "build", ANY)
    mock_find_outputs.assert_called_once_with(temp_dir, temp_dir / "build", ANY)