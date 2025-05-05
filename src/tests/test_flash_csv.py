# test_flash_csv.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
# Tests for CSV-based flashing functionality
import pytest
import tempfile
import os
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
        args.flash_ip = "192.168.1.102,192.168.1.103"
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
