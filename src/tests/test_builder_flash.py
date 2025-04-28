# test_builder_flash.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
import pytest
from pathlib import Path
from src.builder.device import _flash_devices_core


def test_flash_full_success(tmp_path, monkeypatch):
    # Prepare dummy firmware and web UI files
    firmware_file = tmp_path / "esp-miner-v1.0.0.bin"
    www_file = tmp_path / "www-v1.0.0.bin"
    firmware_file.write_text("dummy")
    www_file.write_text("dummy")

    # Capture progress events
    events = []
    def mock_progress(status, message, progress):
        events.append((status, message, progress))

    # Always confirm for CLI (not used when force_flash=True)
    def mock_confirm(name, info, ip):
        return True

    # Mock device interactions
    monkeypatch.setattr('src.builder.device.verify_bitaxe_target', lambda ip: ({'hostname': 'dev'}, 'ModelX'))
    def mock_upload(ip, endpoint, file_path, desc):
        return True
    monkeypatch.setattr('src.builder.device.upload_to_bitaxe', mock_upload)
    monkeypatch.setattr('src.builder.device.verify_flash_success', lambda ip, ver: True)

    # Run flashing helper
    _flash_devices_core(
        target_ips=["1.2.3.4"],
        firmware_file=firmware_file,
        www_file=www_file,
        skip_www=False,
        skip_firmware=False,
        force_flash=True,
        expected_version="v1.0.0",
        confirm_fn=mock_confirm,
        progress_fn=mock_progress
    )

    # Verify ordered progress updates and completion
    assert events[0] == ('progress', 'Connecting to device at 1.2.3.4...', 5)
    assert events[1] == ('progress', 'Device verified (ModelX). Preparing flash...', 10)
    assert events[2] == ('progress', 'Uploading web UI to 1.2.3.4...', 20)
    assert events[3] == ('progress', 'Web UI uploaded.', 30)
    assert events[4] == ('progress', 'Uploading firmware to 1.2.3.4...', 40)
    assert events[5] == ('progress', 'Firmware uploaded.', 70)
    assert events[6] == ('progress', 'Verifying flash success (waiting for reboot)...', 80)
    assert events[7] == ('completed', 'Flash completed successfully.', 100)


def test_flash_skip_confirmation(tmp_path, monkeypatch):
    # Prepare dummy firmware file
    firmware_file = tmp_path / "esp-miner-v1.0.0.bin"
    firmware_file.write_text("dummy")

    events = []
    def mock_progress(status, message, progress):
        events.append((status, message, progress))

    # Reject confirmation
    def mock_confirm(name, info, ip):
        return False

    monkeypatch.setattr('src.builder.device.verify_bitaxe_target', lambda ip: ({'hostname': 'dev'}, 'ModelX'))
    monkeypatch.setattr('src.builder.device.upload_to_bitaxe', lambda *args, **kwargs: True)
    monkeypatch.setattr('src.builder.device.verify_flash_success', lambda ip, ver: True)

    _flash_devices_core(
        target_ips=["1.2.3.4"],
        firmware_file=firmware_file,
        www_file=None,
        skip_www=True,
        skip_firmware=True,
        force_flash=False,
        expected_version="v1.0.0",
        confirm_fn=mock_confirm,
        progress_fn=mock_progress
    )

    # Only connecting and skip flash events
    assert events == [
        ('progress', 'Connecting to device at 1.2.3.4...', 5),
        ('progress', 'Skipping flash for 1.2.3.4', 10)
    ]


def test_flash_firmware_failure(tmp_path, monkeypatch):
    # Prepare dummy firmware and (missing) www file
    firmware_file = tmp_path / "esp-miner-v1.0.0.bin"
    firmware_file.write_text("dummy")

    events = []
    def mock_progress(status, message, progress):
        events.append((status, message, progress))

    def mock_confirm(name, info, ip):
        return True

    monkeypatch.setattr('src.builder.device.verify_bitaxe_target', lambda ip: ({'hostname': 'dev'}, 'ModelX'))
    # Web UI succeeds, firmware fails
    def mock_upload(ip, endpoint, fp, desc):
        return not endpoint.endswith('/OTA')
    monkeypatch.setattr('src.builder.device.upload_to_bitaxe', mock_upload)
    monkeypatch.setattr('src.builder.device.verify_flash_success', lambda ip, ver: True)

    _flash_devices_core(
        target_ips=["1.2.3.4"],
        firmware_file=firmware_file,
        www_file=tmp_path / "www.bin",
        skip_www=False,
        skip_firmware=False,
        force_flash=True,
        expected_version="v1.0.0",
        confirm_fn=mock_confirm,
        progress_fn=mock_progress
    )

    # Expect firmware error at 70%
    assert ('error', 'Firmware upload failed.', 70) in events 