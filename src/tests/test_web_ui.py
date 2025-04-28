# test_web_ui.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
import pytest
from unittest.mock import patch, MagicMock
import flask
import sys
import threading

"""Test cases for the web_ui module"""

@pytest.fixture
def mock_request_context():
    """Create a mock Flask request context."""
    app = flask.Flask(__name__)
    with app.test_request_context():
        # Set up a fake request.sid
        flask.request.sid = 'test_sid'
        yield

@patch('src.builder.build.active_build_processes', [])
@patch('flask_socketio.SocketIO.emit')
def test_cancel_build_with_no_active_thread(mock_emit, mock_request_context):
    """Test that cancel_build emits correct event when no build is in progress"""
    # Import the module first to set up globals properly
    import src.web_ui
    
    # Ensure _build_thread is either not present or None
    original_globals = getattr(src.web_ui, '_build_thread', None)
    src.web_ui._build_thread = None
    
    try:
        # Import the function after setting up globals
        from src.web_ui import handle_cancel_build
        
        # Call the handler with empty active processes
        handle_cancel_build()
        
        # Verify that emit was called with correct arguments
        mock_emit.assert_called_once_with('build_status', {
            'status': 'cancelled',
            'message': 'No active build to cancel'
        })
    finally:
        # Restore original state
        if original_globals is None:
            if hasattr(src.web_ui, '_build_thread'):
                delattr(src.web_ui, '_build_thread')
        else:
            src.web_ui._build_thread = original_globals

@patch('src.builder.build.active_build_processes')
@patch('flask_socketio.SocketIO.emit')
def test_cancel_build_with_active_thread(mock_emit, mock_processes, mock_request_context):
    """Test that cancel_build terminates processes when build is in progress"""
    # Create a mock process
    mock_process = MagicMock()
    mock_process.poll.return_value = None  # Process still running
    mock_process.args = ["test_command"]
    
    # Set up active processes
    mock_processes.__iter__.return_value = [mock_process]
    
    # Add build_thread to the globals space
    mock_thread = MagicMock()
    mock_thread.is_alive.return_value = True
    
    # Import the web_ui module to patch its globals directly
    import src.web_ui
    
    # Temporarily add mock build_thread to globals
    old_globals = dict(src.web_ui.__dict__)
    src.web_ui.build_thread = mock_thread
    
    try:
        # Import the handler function
        from src.web_ui import handle_cancel_build
        
        # Call the handler
        handle_cancel_build()
        
        # Verify process was terminated
        mock_process.terminate.assert_called_once()
        
        # Verify that emit was called with correct arguments
        mock_emit.assert_called_once_with('build_status', {
            'status': 'cancelled',
            'message': 'Build was cancelled by user request'
        })
    finally:
        # Restore the module's original state
        for key in list(src.web_ui.__dict__.keys()):
            if key not in old_globals:
                delattr(src.web_ui, key)

@patch('src.web_ui.logger')
def test_check_build_status_when_building(mock_logger, mock_request_context):
    """Test check_build_status when a build is in progress"""
    # Import here to avoid circular import
    from src.web_ui import handle_check_build_status
    
    # Mock builder_build.is_building
    with patch('src.web_ui.builder_build') as mock_builder:
        # Set up the build status
        mock_builder.is_building = True
        mock_builder.current_tag = 'v1.0.0'
        mock_builder.build_progress = 50
        
        # Mock emit function
        with patch('src.web_ui.emit') as mock_emit:
            # Call the handler
            handle_check_build_status()
            
            # Verify that emit was called with correct arguments
            mock_emit.assert_called_once_with('build_status', {
                'status': 'building',
                'message': 'Building firmware for tag v1.0.0',
                'progress': 50
            })
            
            # Verify that logger was called
            mock_logger.info.assert_any_call('Build is in progress, sending current status')

@patch('src.web_ui.logger')
def test_check_build_status_when_idle(mock_logger, mock_request_context):
    """Test check_build_status when no build is in progress"""
    # Import here to avoid circular import
    from src.web_ui import handle_check_build_status
    
    # Mock builder_build.is_building
    with patch('src.web_ui.builder_build') as mock_builder:
        # Set up the build status
        mock_builder.is_building = False
        
        # Mock emit function
        with patch('src.web_ui.emit') as mock_emit:
            # Call the handler
            handle_check_build_status()
            
            # Verify that emit was called with correct arguments
            mock_emit.assert_called_once_with('build_status', {
                'status': 'idle',
                'message': 'No build in progress'
            })
            
            # Verify that logger was called
            mock_logger.info.assert_any_call('No build in progress')

@patch('src.web_ui.socketio')
@patch('src.web_ui.builder_build')
@patch('src.web_ui.ensure_clean_repo_for_build')
def test_cancel_build_properly_resets_state(mock_clean_repo, mock_builder, mock_socketio, mock_request_context):
    """Test that cancelling a build properly resets all state"""
    from src.web_ui import handle_cancel_build
    
    # Set up active processes with a mock process
    mock_process = MagicMock()
    mock_process.poll.return_value = None  # Process still running
    mock_builder.active_build_processes = [mock_process]
    
    # Set up build_thread in the module
    import src.web_ui
    old_globals = dict(src.web_ui.__dict__)
    src.web_ui.build_thread = MagicMock(is_alive=lambda: True)
    
    try:
        # Call the handler to cancel the build
        handle_cancel_build()
        
        # Verify the state was properly reset
        assert mock_builder.is_building is False
        assert mock_builder.build_progress == 0
        assert src.web_ui.build_thread is None
        
        # Verify process was terminated
        mock_process.terminate.assert_called_once()
        
        # Verify the correct status was emitted
        mock_socketio.emit.assert_called_once_with('build_status', {
            'status': 'cancelled',
            'message': 'Build was cancelled by user request'
        })
    finally:
        # Clean up
        for key in list(src.web_ui.__dict__.keys()):
            if key not in old_globals:
                delattr(src.web_ui, key)

@patch('src.web_ui.socketio')
@patch('src.web_ui.builder_build')
@patch('src.web_ui.ensure_clean_repo_for_build')
@patch('threading.Thread')
def test_start_build_resets_state_before_starting(mock_thread, mock_clean_repo, mock_builder, mock_socketio, mock_request_context):
    """Test that starting a build properly resets state from any previous build"""
    from src.web_ui import start_build
    
    # Set up state as if a previous build had been cancelled
    mock_builder.is_building = False
    mock_builder.build_progress = 30
    mock_builder.active_build_processes = [MagicMock()]
    
    # Set up a mock thread
    mock_thread_instance = MagicMock()
    mock_thread.return_value = mock_thread_instance
    
    # Set up build_thread in the module with a previous thread
    import src.web_ui
    old_globals = dict(src.web_ui.__dict__)
    src.web_ui.build_thread = MagicMock()
    
    try:
        # Call start_build with some tag
        build_data = {"tag": "v1.0.0"}
        start_build(build_data)
        
        # Verify state was reset before starting
        assert mock_builder.is_building is False
        assert mock_builder.build_progress == 0
        assert len(mock_builder.active_build_processes) == 0
        
        # Verify clean repo was called
        mock_clean_repo.assert_called_once_with(force_deep_clean=True)
        
        # Verify a new thread was created and started
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()
        
        # Verify the build thread was stored and message was emitted
        assert src.web_ui.build_thread == mock_thread_instance
        mock_socketio.emit.assert_called_once_with('build_status', {
            'status': 'started',
            'tag': 'v1.0.0',
            'message': 'Starting build for v1.0.0'
        })
    finally:
        # Clean up
        for key in list(src.web_ui.__dict__.keys()):
            if key not in old_globals:
                delattr(src.web_ui, key)

@patch('src.web_ui.ensure_clean_repo_for_build')
@patch('src.web_ui.run_build_thread')
@patch('threading.Thread')
def test_build_after_cancellation_starts_cleanly(mock_thread, mock_run_build, mock_clean_repo, mock_request_context):
    """Test that starting a build after cancellation works correctly"""
    # Import necessary functions
    from src.web_ui import start_build, handle_cancel_build
    
    # Setup web_ui module state for testing
    import src.web_ui
    old_globals = dict(src.web_ui.__dict__)
    
    # Set up builder module mocks
    with patch('src.web_ui.builder_build') as mock_builder:
        with patch('src.web_ui.socketio') as mock_socketio:
            try:
                # 1. Simulate an active build
                src.web_ui.build_in_progress = True
                mock_builder.is_building = True
                mock_builder.build_progress = 50
                mock_process = MagicMock()
                mock_process.poll.return_value = None
                mock_builder.active_build_processes = [mock_process]
                src.web_ui.build_thread = MagicMock(is_alive=lambda: True)
                
                # 2. Cancel the build
                handle_cancel_build()
                
                # Verify cancellation state
                assert mock_builder.is_building is False
                assert mock_builder.build_progress == 0
                assert mock_process.terminate.called
                assert mock_socketio.emit.call_count == 1
                
                # Reset mocks for the start build part
                mock_socketio.emit.reset_mock()
                mock_clean_repo.reset_mock()
                
                # 3. Start a new build
                mock_thread_instance = MagicMock()
                mock_thread.return_value = mock_thread_instance
                
                # Call start_build with a tag
                start_build({"tag": "v1.0.0"})
                
                # Verify new build started cleanly
                assert mock_clean_repo.called  # Repository was cleaned
                assert mock_thread.called  # New thread was created
                assert mock_thread_instance.start.called  # Thread was started
                assert src.web_ui.build_thread == mock_thread_instance  # Thread was stored
                
                # Verify correct status messages were emitted
                mock_socketio.emit.assert_called_once_with('build_status', {
                    'status': 'started',
                    'tag': 'v1.0.0',
                    'message': 'Starting build for v1.0.0'
                })
                
            finally:
                # Clean up - restore module state
                for key in list(src.web_ui.__dict__.keys()):
                    if key not in old_globals:
                        delattr(src.web_ui, key)

@patch('src.web_ui.socketio')
@patch('src.web_ui.builder_build')
@patch('threading.Thread')
def test_run_build_thread_handles_cancelled_state(mock_thread, mock_builder, mock_socketio, mock_request_context):
    """Test that run_build_thread properly handles cancellation during execution"""
    from src.web_ui import run_build_thread
    
    # Import the module to manipulate globals
    import src.web_ui
    
    # Set up a mock for progress_callback
    def progress_callback_mock(percent, message):
        # Simulate build cancellation after some progress
        if percent > 50:
            mock_builder.is_building = False
    
    # Mock the builder_utils functions used inside run_build_thread
    with patch('src.web_ui.builder_utils') as mock_utils:
        with patch('src.web_ui.builder_git') as mock_git:
            # Setup repository and tag verification
            mock_git.ESP_MINER_REPO = '/mock/repo/path'
            mock_utils.run_command.return_value = 'v1.0.0'
            
            # Setup initial build state
            mock_builder.is_building = True
            mock_builder.build_progress = 0
            
            # Run the build thread with our test tag
            run_build_thread('v1.0.0')
            
            # Verify final build state is reset
            assert mock_builder.is_building is False
            assert mock_builder.build_progress == 0
            
            # Verify status message sequences
            assert mock_socketio.emit.call_count >= 1
            # First call should be starting message
            first_call_args = mock_socketio.emit.call_args_list[0][0]
            assert first_call_args[0] == 'build_status'
            assert first_call_args[1]['status'] == 'progress'
            assert first_call_args[1]['percent'] == 0

@patch('src.web_ui.socketio')
@patch('src.web_ui.builder_build')
@patch('threading.Thread')
def test_clear_button_cancels_active_build(mock_thread, mock_builder, mock_socketio, mock_request_context):
    """Test that clicking the clear button during an active build properly cancels the build"""
    from src.web_ui import handle_clear_log
    
    # Import module to manipulate globals
    import src.web_ui
    old_globals = dict(src.web_ui.__dict__)
    
    try:
        # Set up state as if a build is in progress
        src.web_ui.build_in_progress = True
        mock_builder.is_building = True
        mock_builder.build_progress = 45
        mock_builder.current_tag = 'v1.0.0'
        
        # Create mock process for active_build_processes
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process still running
        mock_builder.active_build_processes = [mock_process]
        
        # Set up build_thread in the module
        src.web_ui.build_thread = MagicMock()
        src.web_ui.build_thread.is_alive.return_value = True
        
        # Call the clear log handler (which should now cancel the build)
        handle_clear_log()
        
        # Verify the build was cancelled
        assert mock_builder.is_building is False
        
        # Verify the correct status was emitted
        mock_socketio.emit.assert_any_call('build_status', {
            'status': 'cancelled'
        })
        
        # Verify the log was cleared
        mock_socketio.emit.assert_any_call('clear_log')
        
    finally:
        # Clean up
        for key in list(src.web_ui.__dict__.keys()):
            if key not in old_globals:
                delattr(src.web_ui, key)

@patch('src.web_ui.socketio')
@patch('src.web_ui.builder_build')
def test_clear_button_only_clears_log_when_no_build(mock_builder, mock_socketio, mock_request_context):
    """Test that clicking the clear button when no build is active simply clears the log"""
    from src.web_ui import handle_clear_log
    
    # Import module to manipulate globals
    import src.web_ui
    old_globals = dict(src.web_ui.__dict__)
    
    try:
        # Set up state as if no build is in progress
        src.web_ui.build_in_progress = False
        src.web_ui.build_thread = None
        mock_builder.is_building = False
        mock_builder.active_build_processes = []
        
        # Call the clear log handler
        handle_clear_log()
        
        # Verify only the clear_log event was emitted, no cancellation
        # We only check that clear_log was called, not that it was the only call
        mock_socketio.emit.assert_any_call('clear_log')
        # Make sure no cancel status was emitted
        for call in mock_socketio.emit.call_args_list:
            args, kwargs = call
            if args and args[0] == 'build_status':
                if isinstance(args[1], dict) and args[1].get('status') == 'cancelled':
                    pytest.fail("Cancellation status was emitted when no build was in progress")
    finally:
        # Clean up
        for key in list(src.web_ui.__dict__.keys()):
            if key not in old_globals:
                delattr(src.web_ui, key) 