# test_builder_args.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
import pytest
import argparse
from src.builder import cli

# Helper to run parser with args list
def parse_args(mocker, arg_list):
    mocker.patch('sys.argv', ['cli.py'] + arg_list)
    return cli._parse_arguments()

# --- Tests for _parse_arguments ---

def test_args_defaults(mocker):
    args = parse_args(mocker, [])
    assert args.tag is None
    assert args.flash_ip is None
    assert not args.quiet
    assert args.log_level == "DEBUG"  # Default is DEBUG based on inspection
    assert not args.force_rebuild
    assert not args.skip_firmware
    assert not args.skip_www
    assert not args.force_flash
    # Removed checks for vanilla/compare

def test_args_tag(mocker):
    args = parse_args(mocker, ['--tag', 'v2.5.0'])
    assert args.tag == 'v2.5.0'

def test_args_flash_ip_single(mocker):
    args = parse_args(mocker, ['--flash-ip', '192.168.1.100'])
    assert args.flash_ip == '192.168.1.100'

# This test is no longer valid since --flash-ip now only accepts a single IP address
# The shell script will reject comma-separated IPs before they reach the Python code
def test_args_flash_ip_multiple(mocker):
    # Now we expect the parser to get a single IP, not a comma-separated list
    args = parse_args(mocker, ['--flash-ip', '1.1.1.1'])
    assert args.flash_ip == '1.1.1.1'

def test_args_flags(mocker):
    args = parse_args(mocker, [
        '--quiet',
        '--force-rebuild',
        '--skip-firmware',
        '--skip-www',
        '--force-flash'
    ])
    assert args.quiet
    assert args.force_rebuild
    assert args.skip_firmware
    assert args.skip_www
    assert args.force_flash

def test_args_log_level(mocker):
    args = parse_args(mocker, ['--log-level', 'INFO'])
    assert args.log_level == 'INFO'

def test_args_invalid_log_level(mocker):
    """Supplying an unsupported log level should cause argparse to exit."""
    with pytest.raises(SystemExit):
        parse_args(mocker, ['--log-level', 'INVALID'])

def test_args_unknown_flag(mocker):
    """Unknown flags should trigger argparse error and SystemExit."""
    with pytest.raises(SystemExit):
        parse_args(mocker, ['--nonexistent'])