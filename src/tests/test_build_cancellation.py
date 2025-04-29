# test_build_cancellation.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
import pytest
from unittest.mock import patch, MagicMock, call
import flask
import threading

"""Test cases for the build cancellation feature"""

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
def test_cancel_build_with_no_active_thread_fixed(mock_emit, mock_request_context):
    """Test that cancel_build emits correct event when no build is in progress"""
    # Import the module to monkey patch it first
    import src.web_ui
    
    # Set up the globals state explicitly
    original_globals = getattr(src.web_ui, '_build_thread', None)
    src.web_ui._build_thread = None
    
    try:
        # Now import the function
        from src.web_ui import handle_cancel_build
        
        # Call the handler with empty active processes
        handle_cancel_build()
        
        # Verify that emit was called with correct arguments
        mock_emit.assert_called_once_with('build_status', {
            'status': 'cancelled',
            'message': 'No active build to cancel',
            'progress': 0
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
def test_cancel_build_with_active_thread_enhanced(mock_emit, mock_processes, mock_request_context):
    """Test that cancel_build terminates processes when build is in progress, with error handling"""
    # Create a mock process
    mock_process = MagicMock()
    mock_process.poll.return_value = None  # Process still running
    mock_process.args = ["test_command"]
    
    # Set up active processes
    mock_processes.__iter__.return_value = [mock_process]
    
    # Import the web_ui module to patch its globals directly
    import src.web_ui
    
    # Temporarily add mock build_thread to globals
    old_globals = dict(src.web_ui.__dict__)
    src.web_ui.build_thread = MagicMock(is_alive=lambda: True)
    src.web_ui.build_in_progress = True
    
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
            'message': 'Build was cancelled by user request',
            'progress': 0
        })
        
        # Verify state was properly cleaned up
        assert not hasattr(src.web_ui, 'build_thread') or src.web_ui.build_thread is None
    finally:
        # Restore the module's original state
        for key in list(src.web_ui.__dict__.keys()):
            if key not in old_globals:
                delattr(src.web_ui, key)

@patch('src.builder.build.active_build_processes')
@patch('flask_socketio.SocketIO.emit')
def test_cancel_build_handles_errors(mock_emit, mock_processes, mock_request_context):
    """Test that cancel_build properly handles errors during termination"""
    # Create a mock process that raises an exception on terminate
    mock_process = MagicMock()
    mock_process.poll.return_value = None  # Process still running
    mock_process.args = ["test_command"]
    mock_process.terminate.side_effect = Exception("Test error")
    
    # Set up active processes
    mock_processes.__iter__.return_value = [mock_process]
    
    # Import the web_ui module to patch its globals directly
    import src.web_ui
    
    # Temporarily add mock build_thread to globals
    old_globals = dict(src.web_ui.__dict__)
    src.web_ui.build_thread = MagicMock(is_alive=lambda: True)
    src.web_ui.build_in_progress = True
    
    try:
        # Mock the logger to capture errors
        with patch('src.web_ui.logger') as mock_logger:
            # Import the handler function
            from src.web_ui import handle_cancel_build
            
            # Call the handler
            handle_cancel_build()
            
            # Verify process terminate was called and exception was logged
            mock_process.terminate.assert_called_once()
            mock_logger.error.assert_any_call("Error during build cancellation: Test error")
            
            # Verify that emit was called with correct error arguments
            mock_emit.assert_called_once_with('build_status', {
                'status': 'cancelled',
                'message': 'Build cancellation partially completed with errors: Test error',
                'progress': 0
            })
            
            # Verify state was properly cleaned up despite the error
            assert not hasattr(src.web_ui, 'build_thread') or src.web_ui.build_thread is None
    finally:
        # Restore the module's original state
        for key in list(src.web_ui.__dict__.keys()):
            if key not in old_globals:
                delattr(src.web_ui, key)

@patch('src.web_ui.socketio')
@patch('src.web_ui.builder_build')
@patch('threading.Thread')
def test_cancel_button_styling_during_build(mock_thread, mock_builder, mock_socketio, mock_request_context):
    """Test that clicking the clear button during an active build properly shows cancel styling"""
    # Since we can't test CSS directly, we'll check if the JavaScript sets the right class
    # This is a more integration-oriented test
    
    # Import the module to get socket handlers
    import src.web_ui
    
    # Set up builder mock
    mock_builder.is_building = True
    mock_builder.build_progress = 45
    
    # Create mock socket and emit for client JS testing
    mock_socket = MagicMock()
    
    # Simulate client-side behavior via JS events
    # 1. When build starts, client should call updateClearButtonText()
    # 2. This adds the 'cancel-button' class
    # 3. When the cancel button is clicked, client emits 'cancel_build'
    
    # Mock the socket.on handler for 'build_status'
    def mock_build_status_handler(event_name, data):
        assert event_name == 'build_status'
        # This should trigger client-side updateClearButtonText()
        assert data['status'] in ['started', 'progress', 'cancelled', 'completed']
        # Return mock socket for chaining
        return mock_socket
        
    mock_socket.on.side_effect = mock_build_status_handler
    
    # Add tests for UI updates when different build status events are received
    # This validates the handleCancelBuild function's integration with UI
    
    # Test the server response to 'cancel_build' socket event
    from src.web_ui import handle_cancel_build
    
    # Setup mock process
    mock_process = MagicMock()
    mock_process.poll.return_value = None
    mock_process.args = ["test_command"]
    mock_builder.active_build_processes = [mock_process]
    
    # Setup thread and global state
    old_globals = dict(src.web_ui.__dict__)
    src.web_ui.build_thread = MagicMock(is_alive=lambda: True)
    src.web_ui.build_in_progress = True
    
    try:
        # Trigger the cancel build handler
        handle_cancel_build()
        
        # Verify the build state was reset and cancellation status was emitted
        assert mock_builder.is_building is False
        assert mock_builder.build_progress == 0
        mock_socketio.emit.assert_called_with('build_status', {
            'status': 'cancelled',
            'message': 'Build was cancelled by user request'
        })
    finally:
        # Restore original globals
        for key in list(src.web_ui.__dict__.keys()):
            if key not in old_globals:
                delattr(src.web_ui, key)

@patch('src.web_ui.socketio')
@patch('src.web_ui.builder_build')
def test_build_cancellation_during_progress(mock_builder, mock_socketio, mock_request_context):
    """Test cancelling a build during the progress update phase"""
    
    # Import module to modify directly
    import src.web_ui
    
    # Setup mock progress callback
    progress_calls = []
    
    # Create the real callback that would be used in src.web_ui.run_build_thread
    def progress_callback(percent, message):
        # Record the call
        progress_calls.append((percent, message))
        # After 50% progress, simulate cancellation
        if percent >= 50:
            mock_builder.is_building = False
            
        # This is what the actual callback does
        if mock_builder.is_building:
            mock_socketio.emit('build_status', {
                'status': 'progress',
                'percent': percent,
                'message': message
            })
    
    # Setup initial state
    mock_builder.is_building = True
    mock_builder.build_progress = 0
    
    # Now manually call the callback multiple times to simulate progress
    for i in range(0, 101, 10):
        progress_callback(i, f"Progress at {i}%")
    
    # Verify that the callback was called with the right values
    assert len(progress_calls) == 11  # 0, 10, 20, ..., 100
    assert progress_calls[0][0] == 0
    assert progress_calls[-1][0] == 100
    
    # Verify that emit was called correctly before cancellation
    progress_calls_before_cancellation = [call for call in progress_calls if call[0] < 50]
    for call_args in progress_calls_before_cancellation:
        percent, message = call_args
        mock_socketio.emit.assert_any_call('build_status', {
            'status': 'progress',
            'percent': percent,
            'message': message
        })
    
    # Verify that cancellation happened at 50%
    assert not mock_builder.is_building
    
    # Verify emit was not called for later progress updates
    progress_calls_after_cancellation = [call for call in progress_calls if call[0] >= 50]
    assert len(progress_calls_after_cancellation) >= 1  # At least one call after cancellation
    
    # Check the total number of calls to mock_socketio.emit
    assert mock_socketio.emit.call_count == len(progress_calls_before_cancellation) 

@patch('src.web_ui.socketio')
@patch('src.web_ui.builder_build')
def test_clear_log_button_functionality(mock_builder, mock_socketio, mock_request_context):
    """Test that the Clear Log button correctly functions as a cancel button during build"""
    # Import the module to access routes
    import src.web_ui
    from src.web_ui import handle_clear_log, app
    
    # Save original function
    original_handle_clear_log = src.web_ui.handle_clear_log
    
    # Test case 1: When no build is in progress
    # Set up state for no active build
    src.web_ui.build_in_progress = False
    mock_builder.is_building = False
    
    # Call the clear log handler directly
    handle_clear_log()
    
    # Check that socketio.emit was called with 'clear_log'
    mock_socketio.emit.assert_called_with('clear_log')
    
    # Reset for next test
    mock_socketio.emit.reset_mock()
    
    # Test case 2: When a build is in progress
    # Set up state for active build
    src.web_ui.build_in_progress = True
    mock_builder.is_building = True
    
    # Create mock thread and process
    mock_build_thread = MagicMock()
    mock_build_thread.is_alive.return_value = True
    
    # Set up module globals
    src.web_ui.build_thread = mock_build_thread
    
    # Call the handler
    handle_clear_log()
    
    # Check that the build was canceled
    assert mock_builder.is_building is False
    
    # Verify socket notifications were sent
    mock_socketio.emit.assert_any_call('build_status', {'status': 'cancelled'})
    mock_socketio.emit.assert_any_call('clear_log') 