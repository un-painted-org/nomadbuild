# test_web_ui_git_integration.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import flask
import threading

"""Test cases for the web_ui module's git integration"""

@pytest.fixture
def mock_request_context():
    """Create a mock Flask request context."""
    app = flask.Flask(__name__)
    with app.test_request_context():
        # Set up a fake request.sid
        flask.request.sid = 'test_sid'
        yield

@patch('src.web_ui.builder_git')
def test_get_cached_or_fresh_tags_handles_fetch_repo_tuple(mock_git, mock_request_context):
    """Test that get_cached_or_fresh_tags correctly unpacks the tuple returned by fetch_repo"""
    # Import the module
    import src.web_ui

    # Set up the mock for fetch_repo to return a tuple
    mock_repo_path = Path('/mock/repo/path')
    mock_git.fetch_repo.return_value = (mock_repo_path, False, 'https://github.com/example/repo.git')

    # Set up the mock for get_esp_miner_stable_tags
    mock_git.get_esp_miner_stable_tags.return_value = ['v1.0.0', 'v0.9.0']

    # Mock the Path.exists method to return True for our mock path
    with patch.object(Path, 'exists', return_value=True):
        # Mock builder_utils.setup_environment
        with patch('src.web_ui.builder_utils') as mock_utils:
            # Reset the tag cache to force a fresh fetch
            src.web_ui._tag_cache = {'tags': [], 'last_fetched': 0}

            # Call the function
            tags = src.web_ui.get_cached_or_fresh_tags()

            # Verify the function correctly unpacked the tuple
            mock_git.fetch_repo.assert_called_once()
            mock_git.get_esp_miner_stable_tags.assert_called_once_with(mock_repo_path)

            # Verify the function returned the expected tags
            assert tags == ['v1.0.0', 'v0.9.0']

@patch('src.web_ui.builder_git')
@patch('src.web_ui.builder_utils')
@patch('src.web_ui.emit_build_status')
def test_run_build_thread_handles_fetch_repo_tuple(mock_emit, mock_utils, mock_git, mock_request_context):
    """Test that run_build_thread correctly unpacks the tuple returned by fetch_repo"""
    # Import the module
    import src.web_ui

    # Set up the mock for fetch_repo to return a tuple
    mock_repo_path = Path('/mock/repo/path')
    mock_git.fetch_repo.return_value = (mock_repo_path, False, 'https://github.com/example/repo.git')

    # Set up other mocks needed for run_build_thread
    mock_git.ESP_MINER_REPO = 'https://github.com/example/repo.git'
    mock_git.ensure_clean_repo_for_build.return_value = True
    mock_git.checkout_tag.return_value = 'abcdef123456'

    # Mock builder_build.build_esp_miner to return a successful build
    with patch('src.web_ui.builder_build') as mock_builder:
        mock_builder.build_esp_miner.return_value = (
            Path('/mock/build/dir'),  # build_dir
            'abcdef123456',           # commit_hash
            Path('/mock/partition.csv'),  # partition_csv_path
            Path('/mock/flasher_args.json'),  # flasher_args_path
            'v1.0.0'                  # expected_version
        )

        # Mock copy_artifacts_to_output
        mock_utils.copy_artifacts_to_output.return_value = [Path('/firmware/esp-miner-v1.0.0.bin')]

        # Mock create_and_save_build_info
        mock_utils.create_and_save_build_info.return_value = {
            'version': 'v1.0.0',
            'tag': 'v1.0.0',
            'esp_miner_bin_rel_path': 'esp-miner-v1.0.0.bin'
        }

        # Mock CONTAINER_OUTPUT_DIR
        mock_utils.CONTAINER_OUTPUT_DIR = Path('/firmware')

        # Set up the global state for run_build_thread
        src.web_ui.build_in_progress = True
        src.web_ui.build_canceled = threading.Event()
        src.web_ui.current_tag = None
        src.web_ui.last_build_progress = 0
        src.web_ui.last_build_message = ""

        # Call run_build_thread with a tag
        src.web_ui.run_build_thread('v1.0.0')

        # Verify fetch_repo was called correctly
        mock_git.fetch_repo.assert_called_once()

        # Verify ensure_clean_repo_for_build was called with the correct repo_path
        mock_git.ensure_clean_repo_for_build.assert_called_once_with(mock_repo_path)

        # Verify checkout_tag was called with the correct repo_path and tag
        mock_git.checkout_tag.assert_called_once_with(mock_repo_path, 'v1.0.0')

        # Verify build_esp_miner was called with the correct repo_path
        mock_builder.build_esp_miner.assert_called_once()
        args, _ = mock_builder.build_esp_miner.call_args
        assert args[0] == mock_repo_path  # First arg should be repo_path
        assert args[1] == 'v1.0.0'        # Second arg should be tag

        # Verify the build completed successfully
        assert mock_emit.call_count > 0
        # Find the completed status call
        completed_call = None
        for call in mock_emit.call_args_list:
            args, kwargs = call
            if args and args[0] == 'completed':
                completed_call = call
                break

        assert completed_call is not None, "No 'completed' status was emitted"
