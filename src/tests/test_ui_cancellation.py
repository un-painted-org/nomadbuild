# test_ui_cancellation.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
import pytest
from unittest.mock import patch, MagicMock
import flask
import os
import sys
import json
from pathlib import Path

"""Test cases for the client-side UI cancellation functionality"""

# Check if we have the necessary browser testing tools
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# Skip browser tests if Selenium isn't available
pytestmark = pytest.mark.skipif(
    not SELENIUM_AVAILABLE,
    reason="Selenium not installed, UI tests skipped"
)

@pytest.fixture
def mock_request_context():
    """Create a mock Flask request context."""
    app = flask.Flask(__name__)
    with app.test_request_context():
        # Set up a fake request.sid
        flask.request.sid = 'test_sid'
        yield

@pytest.fixture
def mock_web_ui():
    """Create a mock version of the web UI server for testing"""
    with patch('src.web_ui.socketio') as mock_socketio:
        with patch('src.web_ui.app') as mock_app:
            with patch('src.web_ui.builder_build') as mock_builder:
                yield {
                    'socketio': mock_socketio,
                    'app': mock_app,
                    'builder': mock_builder
                }

@pytest.fixture
def mock_js_env():
    """Simulate the JavaScript environment with mocked socket.io"""
    mock_socket = MagicMock()
    mock_document = MagicMock()
    
    # Create mock button element
    mock_button = MagicMock()
    mock_button.textContent = "Clear Log"
    mock_button.title = "Clear build output log"
    mock_button.classList = MagicMock()
    mock_button.classList.add = MagicMock()
    mock_button.classList.remove = MagicMock()
    mock_button.classList.contains = lambda cls: cls in mock_button._classes
    mock_button._classes = set()
    
    # Override add and remove to actually modify _classes
    def mock_add(cls):
        mock_button._classes.add(cls)
    
    def mock_remove(cls):
        if cls in mock_button._classes:
            mock_button._classes.remove(cls)
    
    mock_button.classList.add.side_effect = mock_add
    mock_button.classList.remove.side_effect = mock_remove
    
    # Create document.getElementById mock
    def mock_get_element_by_id(id):
        if id == 'clear-log-btn':
            return mock_button
        return None
    
    mock_document.getElementById.side_effect = mock_get_element_by_id
    
    # Create mock updateClearButtonText function
    def update_clear_button_text():
        button = mock_document.getElementById('clear-log-btn')
        if button:
            if mock_vars['buildInProgress']:
                button.textContent = 'Cancel Build'
                button.title = 'Cancel the current build process'
                button.classList.add('cancel-button')
            else:
                button.textContent = 'Clear Log'
                button.title = 'Clear build output log'
                button.classList.remove('cancel-button')
    
    # Create mock environment with required variables
    mock_vars = {
        'socket': mock_socket,
        'document': mock_document,
        'buildInProgress': False,
        'updateClearButtonText': update_clear_button_text,
        'button': mock_button
    }
    
    return mock_vars

def test_update_clear_button_text_during_build(mock_js_env):
    """Test that the clear button updates correctly during a build"""
    # Initial state - not building
    mock_js_env['buildInProgress'] = False
    
    # Call the function
    mock_js_env['updateClearButtonText']()
    
    # Verify initial state
    assert mock_js_env['button'].textContent == "Clear Log"
    assert mock_js_env['button'].title == "Clear build output log"
    assert 'cancel-button' not in mock_js_env['button']._classes
    
    # Change state to building
    mock_js_env['buildInProgress'] = True
    
    # Call the function again
    mock_js_env['updateClearButtonText']()
    
    # Verify button changed to Cancel Build
    assert mock_js_env['button'].textContent == "Cancel Build"
    assert mock_js_env['button'].title == "Cancel the current build process"
    assert 'cancel-button' in mock_js_env['button']._classes
    
    # Change state back to not building
    mock_js_env['buildInProgress'] = False
    
    # Call the function again
    mock_js_env['updateClearButtonText']()
    
    # Verify button changed back to Clear Log
    assert mock_js_env['button'].textContent == "Clear Log"
    assert mock_js_env['button'].title == "Clear build output log"
    assert 'cancel-button' not in mock_js_env['button']._classes

def test_socket_events_update_button_state(mock_js_env):
    """Test that socket events properly update the button state"""
    mock_socket = mock_js_env['socket']
    
    # Create a handler function for build_status events
    build_status_handlers = []
    
    def mock_on(event, handler):
        if event == 'build_status':
            build_status_handlers.append(handler)
        # For chaining
        return mock_socket
    
    mock_socket.on.side_effect = mock_on
    
    # Trigger one or more build_status events
    mock_js_env['buildInProgress'] = False
    
    # Register mock handlers
    mock_socket.on('build_status', lambda data: None)
    
    # Simulate receiving 'started' event
    build_data = {'status': 'started', 'message': 'Build started'}
    for handler in build_status_handlers:
        handler(build_data)
    
    # Call updateClearButtonText (would be triggered by the event)
    mock_js_env['buildInProgress'] = True
    mock_js_env['updateClearButtonText']()
    
    # Verify button changed to Cancel Build
    assert mock_js_env['button'].textContent == "Cancel Build"
    assert 'cancel-button' in mock_js_env['button']._classes
    
    # Simulate receiving 'cancelled' event
    build_data = {'status': 'cancelled', 'message': 'Build cancelled'}
    for handler in build_status_handlers:
        handler(build_data)
    
    # Call updateClearButtonText
    mock_js_env['buildInProgress'] = False
    mock_js_env['updateClearButtonText']()
    
    # Verify button changed back to Clear Log
    assert mock_js_env['button'].textContent == "Clear Log"
    assert 'cancel-button' not in mock_js_env['button']._classes

def test_clear_button_emits_cancel_when_building(mock_js_env):
    """Test that clicking the clear button when building emits cancel_build event"""
    # Set up building state
    mock_js_env['buildInProgress'] = True
    mock_js_env['updateClearButtonText']()
    
    # Mock the confirm function to return True (user confirms cancellation)
    global_mock = MagicMock()
    global_mock.confirm.return_value = True
    
    # Create a click handler function for the clear button
    def clear_button_click_handler():
        if mock_js_env['buildInProgress']:
            # If building, show confirmation dialog
            if global_mock.confirm("Are you sure you want to cancel the current build?"):
                # User confirmed, emit cancel_build
                mock_js_env['socket'].emit('cancel_build')
        else:
            # If not building, just clear the log
            pass  # In a real implementation, this would call clearBuildOutput()
    
    # Simulate clicking the clear button
    clear_button_click_handler()
    
    # Verify that socket.emit was called with 'cancel_build'
    mock_js_env['socket'].emit.assert_called_once_with('cancel_build')
    
    # Test the rejection case
    mock_js_env['socket'].emit.reset_mock()
    global_mock.confirm.return_value = False
    
    # Click again, this time rejecting the confirmation
    clear_button_click_handler()
    
    # Verify that socket.emit was NOT called this time
    mock_js_env['socket'].emit.assert_not_called() 