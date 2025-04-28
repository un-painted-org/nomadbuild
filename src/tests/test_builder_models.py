# test_builder_models.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
import pytest
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.builder.device import load_models_config, verify_bitaxe_target, get_identified_model, LOADED_MODELS_CONFIG

@pytest.fixture(autouse=True)
def mock_config_dir(monkeypatch):
    """Create a temp directory for config files and mock the model config path."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        # Create the config directory
        config_dir = temp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        # Create a mock models.json
        models_json = config_dir / "models.json"
        with open(models_json, "w") as f:
            json.dump({
                "device_types": [
                    {
                        "name": "Bitaxe 1.x",
                        "identifier": "bitaxe",
                        "deviceModel": ["bitaxe v1"],
                        "boardVersions": ["1.0"],
                        "version_regex": "BITAXE\\s+V?([0-9.]+)"
                    },
                    {
                        "name": "Bitaxe Shell",
                        "identifier": "bitaxeshell",
                        "deviceModel": ["bitaxeshell"],
                        "boardVersions": ["shell"],
                        "version_regex": "BITAXESHELL\\s+V?([0-9.]+)"
                    }
                ]
            }, f)
        
        # Patch the model config path
        monkeypatch.setattr(
            "src.builder.device.MODELS_CONFIG_FILE", 
            models_json
        )
        
        # Also set the global LOADED_MODELS_CONFIG - Fix: Use device_types array directly
        mock_configs = [
            {
                "name": "Bitaxe 1.x",
                "identifier": "bitaxe",
                "deviceModel": ["bitaxe v1"],
                "boardVersions": ["1.0"]
            },
            {
                "name": "Bitaxe Shell",
                "identifier": "bitaxeshell",
                "deviceModel": ["bitaxeshell"],
                "boardVersions": ["shell"]
            }
        ]
        monkeypatch.setattr("src.builder.device.LOADED_MODELS_CONFIG", mock_configs)
        
        yield temp_path

@pytest.fixture
def setup_models_config(monkeypatch):
    """Force load_models_config to return proper values for testing"""
    # After load_models_config is called, ensure LOADED_MODELS_CONFIG has proper structure
    mock_configs = [
        {
            "name": "Bitaxe 1.x",
            "identifier": "bitaxe",
            "deviceModel": ["bitaxe v1"],
            "boardVersions": ["1.0"]
        },
        {
            "name": "Bitaxe Shell",
            "identifier": "bitaxeshell",
            "deviceModel": ["bitaxeshell"],
            "boardVersions": ["shell"]
        }
    ]
    monkeypatch.setattr("src.builder.device.LOADED_MODELS_CONFIG", mock_configs)
    
    # Create a mock json.load function
    def mock_json_load(*args, **kwargs):
        return {"device_types": mock_configs}
    
    # Replace the open and json.load calls
    monkeypatch.setattr("json.load", mock_json_load)
    monkeypatch.setattr("builtins.open", MagicMock())
    
    yield mock_configs

@patch("json.load")
@patch("builtins.open", new_callable=MagicMock)
def test_load_models_config(mock_open, mock_json_load, monkeypatch):
    """Test models configuration loading."""
    # Set up the test to return our mock data
    mock_json_load.return_value = {
        "device_types": [
            {
                "name": "Bitaxe 1.x",
                "identifier": "bitaxe",
                "deviceModel": ["bitaxe v1"],
                "boardVersions": ["1.0"]
            },
            {
                "name": "Bitaxe Shell",
                "identifier": "bitaxeshell",
                "deviceModel": ["bitaxeshell"],
                "boardVersions": ["shell"]
            }
        ]
    }
    
    # Before loading, ensure we don't have old config data
    monkeypatch.setattr("src.builder.device.LOADED_MODELS_CONFIG", [])
    
    # Execute the function
    load_models_config()
    
    # Assert that open was called
    mock_open.assert_called_once()
    
    # Verify the data was loaded
    from src.builder.device import LOADED_MODELS_CONFIG
    assert LOADED_MODELS_CONFIG is not None
    # The value should be the device_types list, not the whole object
    assert LOADED_MODELS_CONFIG == mock_json_load.return_value["device_types"]

@patch("src.builder.device.requests.get")
def test_verify_bitaxe_target_success(mock_get, setup_models_config):
    """Test successful device verification."""
    # Mock successful response with a valid Bitaxe device
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "hostname": "bitaxe123",
        "version": "1.0.0",
        "ASICModel": "BM1366",
        "deviceModel": "bitaxe v1"
    }
    mock_get.return_value = mock_response
    
    device_info, model_name = verify_bitaxe_target("192.168.1.100")
    
    assert device_info is not None
    assert device_info["hostname"] == "bitaxe123"
    assert device_info["ASICModel"] == "BM1366"
    assert model_name is not None
    assert "Bitaxe" in model_name

@patch("src.builder.device.requests.get")
def test_verify_bitaxe_target_connection_error(mock_get):
    """Test device verification when connection fails."""
    # Mock a connection error
    mock_get.side_effect = Exception("Connection failed")
    
    device_info, model_name = verify_bitaxe_target("192.168.1.100")
    
    assert device_info is None
    assert model_name is None

def test_get_identified_model(setup_models_config):
    """Test model identification."""
    # Test identifying a Bitaxe 1.x device
    device_info = {
        "deviceModel": "bitaxe v1",
        "boardVersion": "1.0",
        "ASICModel": "BM1366"
    }
    model_name = get_identified_model(device_info)
    assert model_name == "Bitaxe 1.x"
    
    # Test identifying a Bitaxe Shell device
    device_info = {
        "deviceModel": "bitaxeshell",
        "boardVersion": "shell",
        "ASICModel": "BM1366"
    }
    model_name = get_identified_model(device_info)
    assert model_name == "Bitaxe Shell"
    
    # Test unknown device model
    device_info = {
        "deviceModel": "unknown",
        "boardVersion": "unknown",
        "ASICModel": "BM1366"
    }
    model_name = get_identified_model(device_info)
    assert "Unknown Model" in model_name
    assert "ASIC: BM1366" in model_name