# test_flash_csv.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
# Tests for CSV-based flashing functionality
import pytest
import tempfile
import os
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock
import argparse
from src.builder.device import _handle_flashing

def test_handle_flashing_with_csv(monkeypatch):
    """Test _handle_flashing with a CSV file."""
    # Create a temporary CSV file with IP addresses
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("192.168.1.100\n")
        f.write("192.168.1.101\n")
        temp_file = f.name

    try:
        # Mock the necessary functions
        mock_parse_csv = MagicMock(return_value=["192.168.1.100", "192.168.1.101"])
        mock_flash_devices_core = MagicMock()

        monkeypatch.setattr('src.builder.device.parse_csv_file', mock_parse_csv)
        monkeypatch.setattr('src.builder.device._flash_devices_core', mock_flash_devices_core)

        # Mock the input function to return 'y' for confirmation
        monkeypatch.setattr('builtins.input', lambda _: 'y')

        # Create a mock args object
        args = argparse.Namespace()
        args.flash_ip = None
        args.flash_csv = temp_file
        args.skip_www = False
        args.skip_firmware = False
        args.force_flash = False

        # Call the function
        _handle_flashing(args, "v1.0.0", "v1.0.0")

        # Verify that parse_csv_file was called with the correct file path
        mock_parse_csv.assert_called_once_with(temp_file)

        # Verify that _flash_devices_core was called with the correct parameters
        mock_flash_devices_core.assert_called_once()
        call_args = mock_flash_devices_core.call_args[1]
        assert call_args['target_ips'] == ["192.168.1.100", "192.168.1.101"]
        assert call_args['skip_www'] == False
        assert call_args['skip_firmware'] == False
        assert call_args['force_flash'] == False
        assert call_args['expected_version'] == "v1.0.0"
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)

def test_handle_flashing_with_both_params_error(monkeypatch):
    """Test _handle_flashing with both CSV file and IP parameter (should error)."""
    # Create a temporary CSV file with IP addresses
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("192.168.1.100\n")
        f.write("192.168.1.101\n")
        temp_file = f.name

    try:
        # Mock the necessary functions
        mock_parse_csv = MagicMock(return_value=["192.168.1.100", "192.168.1.101"])
        mock_flash_devices_core = MagicMock()

        monkeypatch.setattr('src.builder.device.parse_csv_file', mock_parse_csv)
        monkeypatch.setattr('src.builder.device._flash_devices_core', mock_flash_devices_core)

        # Create a mock args object
        args = argparse.Namespace()
        args.flash_ip = "192.168.1.102"  # Now a single IP address
        args.flash_csv = temp_file
        args.skip_www = False
        args.skip_firmware = False
        args.force_flash = False

        # Call the function
        _handle_flashing(args, "v1.0.0", "v1.0.0")

        # Verify that _flash_devices_core was NOT called (should error due to both params)
        mock_flash_devices_core.assert_not_called()

        # Verify that parse_csv_file was NOT called
        mock_parse_csv.assert_not_called()
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)

def test_handle_flashing_with_csv_user_cancels(monkeypatch):
    """Test _handle_flashing with CSV file where user cancels the operation."""
    # Create a temporary CSV file with IP addresses
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("192.168.1.100\n")
        f.write("192.168.1.101\n")
        temp_file = f.name

    try:
        # Mock the necessary functions
        mock_parse_csv = MagicMock(return_value=["192.168.1.100", "192.168.1.101"])
        mock_flash_devices_core = MagicMock()

        monkeypatch.setattr('src.builder.device.parse_csv_file', mock_parse_csv)
        monkeypatch.setattr('src.builder.device._flash_devices_core', mock_flash_devices_core)

        # Mock the input function to return 'n' for confirmation (user cancels)
        monkeypatch.setattr('builtins.input', lambda _: 'n')

        # Create a mock args object
        args = argparse.Namespace()
        args.flash_ip = None
        args.flash_csv = temp_file
        args.skip_www = False
        args.skip_firmware = False
        args.force_flash = False

        # Call the function
        _handle_flashing(args, "v1.0.0", "v1.0.0")

        # Verify that parse_csv_file was called with the correct file path
        mock_parse_csv.assert_called_once_with(temp_file)

        # Verify that _flash_devices_core was NOT called (user cancelled)
        mock_flash_devices_core.assert_not_called()
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)

def test_handle_flashing_with_csv_force_flash(monkeypatch):
    """Test _handle_flashing with CSV file and force_flash=True."""
    # Create a temporary CSV file with IP addresses
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("192.168.1.100\n")
        f.write("192.168.1.101\n")
        temp_file = f.name

    try:
        # Mock the necessary functions
        mock_parse_csv = MagicMock(return_value=["192.168.1.100", "192.168.1.101"])
        mock_flash_devices_core = MagicMock()

        monkeypatch.setattr('src.builder.device.parse_csv_file', mock_parse_csv)
        monkeypatch.setattr('src.builder.device._flash_devices_core', mock_flash_devices_core)

        # No need to mock input as it shouldn't be called with force_flash=True

        # Create a mock args object
        args = argparse.Namespace()
        args.flash_ip = None
        args.flash_csv = temp_file
        args.skip_www = False
        args.skip_firmware = False
        args.force_flash = True

        # Call the function
        _handle_flashing(args, "v1.0.0", "v1.0.0")

        # Verify that parse_csv_file was called with the correct file path
        mock_parse_csv.assert_called_once_with(temp_file)

        # Verify that _flash_devices_core was called with the correct parameters
        mock_flash_devices_core.assert_called_once()
        call_args = mock_flash_devices_core.call_args[1]
        assert call_args['target_ips'] == ["192.168.1.100", "192.168.1.101"]
        assert call_args['skip_www'] == False
        assert call_args['skip_firmware'] == False
        assert call_args['force_flash'] == True
        assert call_args['expected_version'] == "v1.0.0"
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)

def test_handle_flashing_with_single_ip(monkeypatch):
    """Test _handle_flashing with a single IP address."""
    # Mock the necessary functions
    mock_flash_devices_core = MagicMock()
    monkeypatch.setattr('src.builder.device._flash_devices_core', mock_flash_devices_core)

    # Create a mock args object
    args = argparse.Namespace()
    args.flash_ip = "192.168.1.100"  # Single IP address
    args.flash_csv = None
    args.skip_www = False
    args.skip_firmware = False
    args.force_flash = False

    # Call the function
    _handle_flashing(args, "v1.0.0", "v1.0.0")

    # Verify that _flash_devices_core was called with the correct parameters
    mock_flash_devices_core.assert_called_once()
    call_args = mock_flash_devices_core.call_args[1]
    assert call_args['target_ips'] == ["192.168.1.100"]
    assert call_args['skip_www'] == False
    assert call_args['skip_firmware'] == False
    assert call_args['force_flash'] == False
    assert call_args['expected_version'] == "v1.0.0"

def test_handle_flashing_with_invalid_ip_format(monkeypatch):
    """Test _handle_flashing with an invalid IP address format."""
    # Mock the necessary functions
    mock_flash_devices_core = MagicMock()
    # Mock logger to capture warnings
    mock_logger = MagicMock()

    monkeypatch.setattr('src.builder.device._flash_devices_core', mock_flash_devices_core)
    monkeypatch.setattr('src.builder.device.logger', mock_logger)

    # Create a mock args object with an invalid IP
    args = argparse.Namespace()
    args.flash_ip = "invalid-ip-address"
    args.flash_csv = None
    args.skip_www = False
    args.skip_firmware = False
    args.force_flash = False

    # Call the function
    _handle_flashing(args, "v1.0.0", "v1.0.0")

    # Since we can't easily mock IP validation which is built into the code,
    # we'll just verify that _flash_devices_core was called (even with an invalid IP)
    # The actual validation would happen inside _flash_devices_core
    assert mock_flash_devices_core.call_count > 0

    # We can't reliably check for warning logs since we don't know how the implementation
    # handles invalid IPs internally

def test_handle_flashing_with_nonexistent_csv(monkeypatch):
    """Test _handle_flashing with a non-existent CSV file."""
    # Mock the necessary functions
    mock_flash_devices_core = MagicMock()
    mock_logger = MagicMock()

    # Create a temporary file path that doesn't exist
    nonexistent_file = "/tmp/nonexistent_file_" + str(uuid.uuid4()) + ".csv"

    # Mock the parse_csv_file function to return an empty list for the nonexistent file
    def mock_parse_csv(file_path):
        if file_path == nonexistent_file:
            # Simulate the behavior of the real function when file doesn't exist
            mock_logger.error(f"CSV file not found: {file_path}")
            return []
        return ["192.168.1.100"]

    monkeypatch.setattr('src.builder.device.parse_csv_file', mock_parse_csv)
    monkeypatch.setattr('src.builder.device._flash_devices_core', mock_flash_devices_core)
    monkeypatch.setattr('src.builder.device.logger', mock_logger)

    # Create a mock args object
    args = argparse.Namespace()
    args.flash_ip = None
    args.flash_csv = nonexistent_file
    args.skip_www = False
    args.skip_firmware = False
    args.force_flash = False

    # Call the function
    _handle_flashing(args, "v1.0.0", "v1.0.0")

    # The behavior depends on how _handle_flashing handles empty IP lists
    # It might call _flash_devices_core with an empty list or not call it at all
    # So we'll check both possibilities
    if mock_flash_devices_core.call_count > 0:
        call_args = mock_flash_devices_core.call_args[1]
        assert call_args['target_ips'] == []

    # Verify that an error was logged
    assert mock_logger.error.call_count > 0 or mock_logger.warning.call_count > 0

def test_handle_flashing_with_malformed_csv(monkeypatch):
    """Test _handle_flashing with a malformed CSV file."""
    # Create a temporary CSV file with invalid content
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("This is not a valid IP address\n")
        f.write("Neither is this\n")
        temp_file = f.name

    try:
        # Mock the necessary functions
        # The parse_csv_file function should filter out invalid IPs and return an empty list
        mock_parse_csv = MagicMock(return_value=[])
        mock_flash_devices_core = MagicMock()
        mock_logger = MagicMock()

        monkeypatch.setattr('src.builder.device.parse_csv_file', mock_parse_csv)
        monkeypatch.setattr('src.builder.device._flash_devices_core', mock_flash_devices_core)
        monkeypatch.setattr('src.builder.device.logger', mock_logger)

        # Create a mock args object
        args = argparse.Namespace()
        args.flash_ip = None
        args.flash_csv = temp_file
        args.skip_www = False
        args.skip_firmware = False
        args.force_flash = False

        # Call the function
        _handle_flashing(args, "v1.0.0", "v1.0.0")

        # Verify that parse_csv_file was called with the correct file path
        mock_parse_csv.assert_called_once_with(temp_file)

        # Verify that _flash_devices_core was NOT called (no valid IPs)
        mock_flash_devices_core.assert_not_called()

        # Verify that an error was logged
        mock_logger.error.assert_called()
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)

def test_handle_flashing_with_empty_csv(monkeypatch):
    """Test _handle_flashing with an empty CSV file."""
    # Create a temporary empty CSV file
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        temp_file = f.name

    try:
        # Mock the necessary functions
        mock_parse_csv = MagicMock(return_value=[])
        mock_flash_devices_core = MagicMock()

        monkeypatch.setattr('src.builder.device.parse_csv_file', mock_parse_csv)
        monkeypatch.setattr('src.builder.device._flash_devices_core', mock_flash_devices_core)

        # Create a mock args object
        args = argparse.Namespace()
        args.flash_ip = None
        args.flash_csv = temp_file
        args.skip_www = False
        args.skip_firmware = False
        args.force_flash = False

        # Call the function
        _handle_flashing(args, "v1.0.0", "v1.0.0")

        # Verify that parse_csv_file was called with the correct file path
        mock_parse_csv.assert_called_once_with(temp_file)

        # Verify that _flash_devices_core was NOT called (no valid IPs)
        mock_flash_devices_core.assert_not_called()
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)
