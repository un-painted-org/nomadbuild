# test_flash_verification_failure.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
import pytest
from pathlib import Path
from src.builder.device import _flash_devices_core


def test_flash_verification_failure(tmp_path, monkeypatch):
    """Test flashing when verification after flashing fails."""
    # Prepare dummy firmware file
    firmware_file = tmp_path / "esp-miner-v1.0.0.bin"
    firmware_file.write_text("dummy")
    
    # Capture progress events
    events = []
    def mock_progress(status, message, progress):
        events.append((status, message, progress))
    
    # Always confirm for CLI
    def mock_confirm(name, info, ip):
        return True
    
    # Mock device verification to succeed
    monkeypatch.setattr('src.builder.device.verify_bitaxe_target', lambda ip: ({'hostname': 'dev'}, 'ModelX'))
    
    # Mock upload to succeed
    monkeypatch.setattr('src.builder.device.upload_to_bitaxe', lambda ip, endpoint, file_path, desc: True)
    
    # Mock verification after flashing to fail
    monkeypatch.setattr('src.builder.device.verify_flash_success', lambda ip, ver: False)
    
    # Run flashing helper
    _flash_devices_core(
        target_ips=["1.2.3.4"],
        firmware_file=firmware_file,
        www_file=None,
        skip_www=True,
        skip_firmware=False,
        force_flash=True,
        expected_version="v1.0.0",
        confirm_fn=mock_confirm,
        progress_fn=mock_progress
    )
    
    # Verify that an error event was generated
    assert any(status == 'error' and 'verification failed' in message.lower() for status, message, _ in events)
