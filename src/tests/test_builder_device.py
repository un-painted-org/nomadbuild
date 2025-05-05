# test_builder_device.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

import types

import src.builder.device as device_mod
import requests as real_requests

# ----------------------
# Helpers / Fixtures
# ----------------------

class DummyResponse:
    """Simple stand-in for requests.Response."""
    def __init__(self, status_code: int = 200, json_data: dict | None = None, text: str = "OK"):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise device_mod.requests.exceptions.HTTPError(response=self)

    def json(self):
        return self._json


# Stub Spinner so tests run instantly
class DummySpinner:
    def __init__(self, *_a, **_kw):
        pass
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        return False


# ----------------------
# verify_bitaxe_target
# ----------------------

@patch('src.builder.device.requests')
def test_verify_bitaxe_target_unknown_model_rejected(mock_requests):
    # This test verifies that devices with unknown models are rejected for safety
    info = {"hostname": "axe001", "version": "v1.0", "ASICModel": "BM1366"}
    mock_requests.get.return_value = DummyResponse(200, info)
    # ensure LOADED_MODELS_CONFIG empty to test fallback
    device_mod.LOADED_MODELS_CONFIG = []
    dev_info, model = device_mod.verify_bitaxe_target("192.0.2.1")
    # With our enhanced verification, unknown models should be rejected
    assert dev_info is None and model is None

@patch('src.builder.device.requests')
def test_verify_bitaxe_target_success(mock_requests):
    # This test verifies that devices with proper identification are accepted
    info = {"hostname": "axe001", "version": "v1.0", "ASICModel": "BM1366", "boardVersion": "401"}
    mock_requests.get.return_value = DummyResponse(200, info)
    # ensure LOADED_MODELS_CONFIG empty to test fallback
    device_mod.LOADED_MODELS_CONFIG = []
    dev_info, model = device_mod.verify_bitaxe_target("192.0.2.1")
    # With proper board version, it should be identified as a Bitaxe Supra
    assert dev_info == info
    assert model == "Bitaxe Supra"

@patch('src.builder.device.requests')
def test_verify_bitaxe_target_missing_fields(mock_requests):
    mock_requests.get.return_value = DummyResponse(200, {"hostname": "axe001"})
    dev_info, model = device_mod.verify_bitaxe_target("198.51.100.1")
    assert dev_info is None and model is None

@patch('src.builder.device.requests')
def test_verify_bitaxe_target_lv_rejected(mock_requests):
    info = {"hostname": "axe001", "version": "v1.0", "ASICModel": "BM1366LV"}
    mock_requests.get.return_value = DummyResponse(200, info)
    dev_info, model = device_mod.verify_bitaxe_target("203.0.113.5")
    assert dev_info is None and model is None

@patch('src.builder.device.requests')
def test_verify_bitaxe_target_timeout(mock_requests):
    mock_requests.exceptions.Timeout = real_requests.exceptions.Timeout
    mock_requests.get.side_effect = real_requests.exceptions.Timeout
    dev_info, model = device_mod.verify_bitaxe_target("203.0.113.6")
    assert dev_info is None and model is None

# ----------------------
# upload_to_bitaxe
# ----------------------

@patch('src.builder.device.Spinner', DummySpinner)
@patch('src.builder.device.requests')
def test_upload_to_bitaxe_success(mock_requests, tmp_path):
    bin_file = tmp_path / "fw.bin"
    bin_file.write_bytes(b'abc')
    mock_requests.post.return_value = DummyResponse(200, text="flashed")
    ok = device_mod.upload_to_bitaxe("192.0.2.2", "/flash", bin_file, "firmware")
    assert ok is True

@patch('src.builder.device.Spinner', DummySpinner)
@patch('src.builder.device.requests')
def test_upload_to_bitaxe_non2xx(mock_requests, tmp_path):
    bin_file = tmp_path / "fw.bin"
    bin_file.write_bytes(b'abc')
    mock_requests.post.return_value = DummyResponse(500, text="fail")
    ok = device_mod.upload_to_bitaxe("192.0.2.3", "/flash", bin_file, "firmware")
    assert ok is False

@patch('src.builder.device.Spinner', DummySpinner)
def test_upload_to_bitaxe_missing_file(tmp_path):
    missing = tmp_path / "nofile.bin"
    ok = device_mod.upload_to_bitaxe("192.0.2.4", "/flash", missing, "firmware")
    assert ok is False

# ----------------------
# get_identified_model
# ----------------------

def test_get_identified_model_from_config():
    device_mod.LOADED_MODELS_CONFIG = [
        {"name": "Bitaxe S3", "deviceModel": ["bitaxe_s3"]}
    ]
    device_info = {"deviceModel": "bitaxe_s3", "ASICModel": "BM1366"}
    model_name = device_mod.get_identified_model(device_info)
    assert model_name == "Bitaxe S3"