# test_custom_repo_info.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
# Test for repository information in build_info.json

import pytest
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.builder.utils import create_and_save_build_info
from src.builder.utils import ESP_MINER_REPO


class TestRepoInfo:
    """Tests for repository information in build_info.json."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary directory for the output files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def mock_artifact_paths(self, temp_output_dir):
        """Create mock artifact paths for testing."""
        # Create some dummy files to use as artifacts
        artifact_paths = []
        for filename in ["esp-miner-v1.0.0.bin", "www-v1.0.0.bin"]:
            file_path = temp_output_dir / filename
            with open(file_path, "wb") as f:
                f.write(b"dummy content")
            artifact_paths.append(file_path)
        return artifact_paths

    def test_custom_repo_info_included(self, temp_output_dir, mock_artifact_paths):
        """Test that custom repository information is included in build_info.json when provided."""
        # Call the function with custom repository information
        custom_url = "https://github.com/custom/repo.git"
        build_info = create_and_save_build_info(
            copied_artifact_paths=mock_artifact_paths,
            built_tag="v1.0.0",
            expected_version="v1.0.0",
            output_dir=temp_output_dir,
            is_custom_repo=True,
            custom_repo_url=custom_url
        )

        # Verify the build_info dictionary contains the repo_url information
        assert "repo_url" in build_info
        assert build_info["repo_url"]["custom"] is True
        assert build_info["repo_url"]["url"] == custom_url

        # Verify the build_info.json file contains the repo_url information
        build_info_path = temp_output_dir / "build_info.json"
        assert build_info_path.exists()

        with open(build_info_path, "r") as f:
            saved_build_info = json.load(f)

        assert "repo_url" in saved_build_info
        assert saved_build_info["repo_url"]["custom"] is True
        assert saved_build_info["repo_url"]["url"] == custom_url

        # Also verify backward compatibility with custom_repo field
        assert "custom_repo" in saved_build_info
        assert saved_build_info["custom_repo"]["used"] is True
        assert saved_build_info["custom_repo"]["url"] == custom_url

    def test_default_repo_info_included(self, temp_output_dir, mock_artifact_paths):
        """Test that default repository information is included in build_info.json when not custom."""
        # Call the function without custom repository information
        build_info = create_and_save_build_info(
            copied_artifact_paths=mock_artifact_paths,
            built_tag="v1.0.0",
            expected_version="v1.0.0",
            output_dir=temp_output_dir
        )

        # Verify the build_info dictionary contains the repo_url information
        assert "repo_url" in build_info
        assert build_info["repo_url"]["custom"] is False
        assert build_info["repo_url"]["url"] == ESP_MINER_REPO

        # Verify the build_info.json file contains the repo_url information
        build_info_path = temp_output_dir / "build_info.json"
        assert build_info_path.exists()

        with open(build_info_path, "r") as f:
            saved_build_info = json.load(f)

        assert "repo_url" in saved_build_info
        assert saved_build_info["repo_url"]["custom"] is False
        assert saved_build_info["repo_url"]["url"] == ESP_MINER_REPO

    def test_validation_fails_when_repo_info_missing(self, temp_output_dir, mock_artifact_paths):
        """Test that validation fails when repository information is missing."""
        # Instead of mocking json.dump, we'll create a custom open function that modifies the data
        original_open = open

        # Keep track of whether we've already modified the file
        modified = False

        def custom_open(*args, **kwargs):
            nonlocal modified
            file_obj = original_open(*args, **kwargs)

            # Only modify the file when it's opened for reading during validation
            if 'r' in args[1] and not modified and args[0].name.endswith('build_info.json'):
                modified = True
                # Return a file-like object with modified content
                class ModifiedFile:
                    def __enter__(self):
                        return self

                    def __exit__(self, *args):
                        pass

                    def read(self):
                        # Return a JSON string without the repo_url field
                        return '{"tag": "v1.0.0", "version": "v1.0.0", "files": [], "custom_repo": {"used": true, "url": "https://github.com/custom/repo.git"}}'

                    def close(self):
                        pass

                return ModifiedFile()

            return file_obj

        # Patch the built-in open function
        with patch('builtins.open', side_effect=custom_open):
            # Call the function with custom repository information
            with pytest.raises(ValueError, match="Repository information .* missing from build_info.json"):
                create_and_save_build_info(
                    copied_artifact_paths=mock_artifact_paths,
                    built_tag="v1.0.0",
                    expected_version="v1.0.0",
                    output_dir=temp_output_dir,
                    is_custom_repo=True,
                    custom_repo_url="https://github.com/custom/repo.git"
                )
