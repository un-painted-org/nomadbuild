# test_cli_mutually_exclusive.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
# Tests for mutually exclusive CLI arguments
import pytest
import sys
import argparse
from unittest.mock import patch
from src.builder.cli import _parse_arguments

def test_mutually_exclusive_flash_params():
    """Test that --flash-ip and --flash-csv are mutually exclusive."""
    # Test with only --flash-ip
    with patch('sys.argv', ['nomadbuild.py', '--flash-ip', '192.168.1.100']):
        args = _parse_arguments()
        assert args.flash_ip == '192.168.1.100'
        assert args.flash_csv is None
    
    # Test with only --flash-csv
    with patch('sys.argv', ['nomadbuild.py', '--flash-csv', 'devices.csv']):
        args = _parse_arguments()
        assert args.flash_csv == 'devices.csv'
        assert args.flash_ip is None
    
    # Test with both parameters (should raise an error)
    with patch('sys.argv', ['nomadbuild.py', '--flash-ip', '192.168.1.100', '--flash-csv', 'devices.csv']):
        with pytest.raises(SystemExit):
            _parse_arguments()
