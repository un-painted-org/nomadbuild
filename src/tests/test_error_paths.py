import errno
import json
import pytest
from pathlib import Path
import src.builder.build as build_mod
import subprocess
from unittest.mock import MagicMock

# Import the module containing the functions to test
from src.builder import build as build_mod
from src.builder.build import (
    build_esp_miner,
    _prepare_source_code,
    BuildFailedError
)

# Helper to simulate build failure
def mock_run_build_failure(*args, **kwargs):
    raise subprocess.CalledProcessError(1, cmd=["mock_cmd"], stderr="Build failed simulation")

def test_prepare_source_code_disk_full_correct(monkeypatch, tmp_path):
    """Test handling of disk full error during version.txt write."""
    monkeypatch.setattr(build_mod, "checkout_tag", lambda mp, tag, cb: "commit123")
    monkeypatch.setattr(build_mod, "run_command", lambda *args, **kwargs: None)
    monkeypatch.setattr(build_mod, "get_commit_timestamp", lambda *a, **k: "12345") # Also mock timestamp
    
    orig_write_text = build_mod.Path.write_text
    def fake_write_text(self, data, encoding=None, errors=None):
        if self.name == "version.txt":
            raise OSError(errno.ENOSPC, "No space left on device")
        return orig_write_text(self, data, encoding=encoding, errors=errors)
    monkeypatch.setattr(build_mod.Path, "write_text", fake_write_text)
    
    with pytest.raises(RuntimeError) as excinfo:
        # Use tmp_path fixture
        _prepare_source_code(tmp_path, "v1.2.3", None)
    assert "Failed to write version file" in str(excinfo.value)
    assert "due to OS error" in str(excinfo.value)

def test_parse_flasher_args_handles_json_error(tmp_path):
    flasher_file = tmp_path / "flasher_args.json"
    flasher_file.write_text("{ invalid json }")
    # Assuming _parse_flasher_args exists in build_mod for this test context
    result = build_mod._parse_flasher_args(flasher_file) 
    assert isinstance(result, dict)
    assert result.get('flash_settings') == {}
    assert result.get('flash_files_from_json') == {}
    assert result.get('flash_offsets_from_json') == {} 

def test_prepare_source_code_tag_not_found(mocker):
    """Test _prepare_source_code when checkout_tag raises ValueError."""
    mocker.patch('src.builder.build.checkout_tag', side_effect=ValueError("Tag not found"))
    mock_repo = MagicMock(spec=Path)
    with pytest.raises(ValueError) as excinfo:
        _prepare_source_code(mock_repo, "nonexistent_tag", None)
    assert "Tag not found" in str(excinfo.value)

def test_prepare_source_code_submodule_fail(mocker, tmp_path: Path):
    """Test _prepare_source_code when submodule update fails."""
    mocker.patch('src.builder.build.checkout_tag', return_value="commit_hash")
    mocker.patch('src.builder.build.run_command', side_effect=subprocess.CalledProcessError(1, "git submodule update"))
    with pytest.raises(RuntimeError) as excinfo:
        # Use tmp_path fixture
        _prepare_source_code(tmp_path, "v1.2.3", None)
    assert "Submodule update failed" in str(excinfo.value)

def test_build_esp_miner_clean_fail(mocker):
    """Test build_esp_miner fails if _run_idf_clean fails."""
    mocker.patch('src.builder.build._prepare_source_code', return_value=("h", "v", "t")) 
    mocker.patch('src.builder.build._run_idf_clean', side_effect=BuildFailedError("Clean failed"))
    with pytest.raises(BuildFailedError) as excinfo:
        build_esp_miner(Path("/fake/repo"), "v1.0.0", False, None)
    assert "Clean failed" in str(excinfo.value)

def test_run_build_failure(mocker):
    """Test build_esp_miner fails if _run_idf_build fails."""
    mocker.patch('src.builder.build._run_idf_clean')
    mocker.patch('src.builder.build._prepare_source_code', return_value=("h", "v", "t"))
    mocker.patch('src.builder.build._run_idf_build', side_effect=mock_run_build_failure)
    with pytest.raises(BuildFailedError) as excinfo:
        build_esp_miner(Path("/fake/repo"), "v1.0.0", False, None)
    assert "Build command failed" in str(excinfo.value)
    assert "(Exit Code: 1)" in str(excinfo.value) 