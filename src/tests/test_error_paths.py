import builtins
import errno
import json
import pytest
from pathlib import Path
import src.builder.build as build_mod


def test_prepare_source_code_disk_full(monkeypatch, tmp_path):
    # Stub checkout_tag and run_command to skip git operations
    monkeypatch.setattr(build_mod, "checkout_tag", lambda mp, tag, cb: "commit123")
    monkeypatch.setattr(build_mod, "run_command", lambda *args, **kwargs: None)
    # Monkeypatch open to simulate disk-full on version.txt write
    orig_open = builtins.open
    def fake_open(path, mode='r', *args, **kwargs):
        # Only fail on writing version.txt
        p = str(path)
        if p.endswith("version.txt") and 'w' in mode:
            raise OSError(errno.ENOSPC, "No space left on device")
        return orig_open(path, mode, *args, **kwargs)
    monkeypatch.setattr(builtins, "open", fake_open)
    # Expect RuntimeError when version.txt write fails
    with pytest.raises(RuntimeError) as excinfo:
        build_mod._prepare_source_code(tmp_path, "v1.2.3", None)
    assert "Failed to write version.txt file" in str(excinfo.value)


def test_parse_flasher_args_handles_json_error(tmp_path):
    # Create an invalid JSON file
    flasher_file = tmp_path / "flasher_args.json"
    flasher_file.write_text("{ invalid json }")
    # Call parser; it should not raise and should return default values
    result = build_mod._parse_flasher_args(flasher_file)
    assert isinstance(result, dict)
    # Default sections should be empty dicts
    assert result.get('flash_settings') == {}
    assert result.get('flash_files_from_json') == {}
    assert result.get('flash_offsets_from_json') == {} 