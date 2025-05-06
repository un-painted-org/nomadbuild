# utils.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
# Shared utility functions (command execution, env setup, artifact copy, spinner)
import logging
import os
import sys
import subprocess
import shutil
import platform
import time
import itertools
import hashlib
import json
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Callable

# Import ESP_MINER_REPO directly to avoid circular imports
ESP_MINER_REPO = "https://github.com/bitaxeorg/ESP-Miner.git"
import threading
import webbrowser
import random
import socket
import datetime
from typing import Callable, Optional

# Placeholder for logger - Will be configured properly in cli.py
logger = logging.getLogger(__name__)

# --- Constants moved from main script ---
ENV_DIR_NAME = "build_env" # Should this be configurable?
CONTAINER_APP_DIR = Path("/app")
CONTAINER_OUTPUT_DIR = Path("/firmware")
LOG_FILE_NAME = "build.log"
IDF_BUILD_LOG_FILENAME = "idf_build_output.log"
BUILD_INFO_FILE = "build_info.json"

# --- Spinner Class ---
class Spinner:
    """Context manager for displaying a simple CLI spinner."""
    def __init__(self, message="Processing...", delay=0.1):
        self.spinner = itertools.cycle(['-', '/', '|', '\\'])
        self.delay = delay
        self.message = message
        self.running = False
        self.spinner_thread = None

    def _spin(self):
        while self.running:
            # Write directly to stdout to avoid logger formatting/levels for spinner
            sys.stdout.write(f'\r{self.message} {next(self.spinner)}')
            sys.stdout.flush()
            time.sleep(self.delay)

    def __enter__(self):
        # Only show spinner if console is INFO or below
        # Use the logger instance configured in cli.py
        if logger.getEffectiveLevel() <= logging.INFO:
            self.running = True
            self.spinner_thread = threading.Thread(target=self._spin)
            self.spinner_thread.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.spinner_thread:
            self.running = False
            self.spinner_thread.join()
            # Clear the spinner line
            sys.stdout.write('\r' + ' ' * (len(self.message) + 2) + '\r')
            sys.stdout.flush()

# --- Helper Functions moved from main script ---

def get_env_dir() -> Path:
    """Gets the path to the container-only build environment directory.

    This directory is created inside the container and should never be mounted
    to the host system. It's used for temporary files during the build process.
    """
    # Use /container_only instead of /app to ensure it's not mounted to the host
    container_only_dir = Path("/container_only")

    # Create the container_only directory if it doesn't exist
    if not container_only_dir.exists():
        container_only_dir.mkdir(parents=True, exist_ok=True)

    # Create the build environment directory inside the container_only directory
    env_dir = container_only_dir / ENV_DIR_NAME
    return env_dir

def setup_environment():
    """Creates the container-only build environment directory and log directory.

    This function ensures that all directories are created inside the container
    and not on the host system. It uses the /container_only directory which is
    not mounted from the host system.
    """
    # Use get_env_dir() which now returns a path in /container_only
    env_dir = get_env_dir()
    log_dir = env_dir / "logs"
    log_file_path = log_dir / LOG_FILE_NAME

    # Create directories
    if not env_dir.exists():
        logger.info(f"Creating container-only build environment directory: {env_dir}")
        env_dir.mkdir(parents=True, exist_ok=True)
    else:
        logger.info(f"Using existing container-only build environment directory: {env_dir}")

    log_dir.mkdir(exist_ok=True)
    (env_dir / "repos").mkdir(exist_ok=True)

    # Log file is cleared by FileHandler mode 'w' during logger setup in main()
    logger.debug(f"Log file path: {log_file_path}")

    # Return the environment directory path for use by other functions
    return env_dir

def run_command(cmd_list, cwd=None, env=None, capture_output=True, check=False, stream_output: bool = False):
    """Runs a command, logs details, handles potential errors, and returns stdout if captured.
    If check=True, raises subprocess.CalledProcessError on failure.
    """
    logger.debug(f"Running command: {' '.join(cmd_list)} {'in ' + str(cwd) if cwd else ''}")
    try:
        process_env = os.environ.copy()
        if env:
            logger.debug(f"Adding custom environment variables: {env}")
            process_env.update(env)

        if stream_output:
            stdout_setting = sys.stdout
            stderr_setting = sys.stderr
            capture_output = False # Cannot capture if streaming to console
            check = False # Cannot use check=True reliably with streaming pipes? Better to handle manually.
            logger.debug("Streaming command output directly to console...")
        elif capture_output:
            stdout_setting = subprocess.PIPE
            stderr_setting = subprocess.PIPE
        else:
            stdout_setting = subprocess.DEVNULL
            stderr_setting = subprocess.DEVNULL

        process = subprocess.run(
            cmd_list,
            check=check, # Pass the check argument to subprocess.run
            cwd=cwd,
            env=process_env,
            text=True,
            stdout=stdout_setting,
            stderr=stderr_setting,
        )

        # Capture output after process completes if not streaming
        stdout_content = None
        stderr_content = None
        if capture_output and process.stdout:
            stdout_content = process.stdout.strip()
        if capture_output and process.stderr:
             stderr_content = process.stderr.strip()

        if stdout_content:
                logger.debug(f"Captured Stdout:\n{stdout_content[:500]}{'...' if len(stdout_content)>500 else ''}")
        # Only log stderr if it contains content, to reduce noise
        if stderr_content:
                logger.debug(f"Captured Stderr:\n{stderr_content[:500]}{'...' if len(stderr_content)>500 else ''}")

        logger.debug(f"Command finished successfully: {' '.join(cmd_list)}")

        # Return stdout if captured, the process object if streaming, otherwise None
        if capture_output:
            return stdout_content
        elif stream_output:
            return process
        else:
            return None

    except subprocess.CalledProcessError as e:
        # This block is only reached if check=True was passed to subprocess.run and the command failed
        logger.error(f"Error running command (check=True): {' '.join(cmd_list)}")
        logger.error(f"Exit Code: {e.returncode}")
        # Capture output from the exception object itself
        stdout_content = e.stdout.strip() if e.stdout else "<no stdout captured>"
        stderr_content = e.stderr.strip() if e.stderr else "<no stderr captured>"
        logger.error(f"Stdout:\n{stdout_content}")
        logger.error(f"Stderr:\n{stderr_content}")
        logger.critical(f"Command failed: {' '.join(cmd_list)}. Raising CalledProcessError.")
        raise # Re-raise the error as requested by check=True

    except FileNotFoundError as e:
        logger.critical(f"Error: Command not found: {cmd_list[0]}")
        logger.critical(f"Please ensure the command is installed and in the system PATH.")
        if check: # Also raise if check=True was requested
             raise
        else:
             return None

    except Exception as e:
        logger.exception(f"An unexpected error occurred running {' '.join(cmd_list)}: {e}")
        if check: # Also raise if check=True was requested
            raise
        else:
            return None

def run_long_command_with_spinner(cmd_list, cwd=None, env=None, check=True):
    """Runs a potentially long command, capturing output, showing spinner (optional), and returning stdout."""
    stdout_content = run_command(cmd_list, cwd=cwd, env=env, capture_output=True, check=check)
    return stdout_content

def copy_artifacts_to_output(firmware_build_path: Path, built_tag: str, expected_version: str | None) -> list[Path]:
    """Copies verified build artifacts and build info to the output volume.
    Returns a list of Path objects for the successfully copied artifact files.
    """
    logger.info("--- Copying Artifacts to Output Volume --- ")
    output_dir = CONTAINER_OUTPUT_DIR
    output_dir.mkdir(exist_ok=True)
    firmware_build_path = Path(firmware_build_path)
    logger.debug(f"Source build artifact path for copying: {firmware_build_path}")

    logger.info(f"Cleaning previous build artifacts from {output_dir}...")
    cleaned_count = 0
    keep_files = [IDF_BUILD_LOG_FILENAME, BUILD_INFO_FILE]
    for item in output_dir.iterdir():
        if item.name not in keep_files:
            if item.is_file():
                item.unlink()
                cleaned_count += 1
            elif item.is_dir():
                shutil.rmtree(item)
                cleaned_count += 1
    logger.info(f"Cleaned {cleaned_count} previous artifact(s).")

    version_suffix = expected_version if expected_version else built_tag
    artifacts_to_copy = {
        "esp-miner.bin": f"esp-miner-{version_suffix}.bin",
        Path("bootloader") / "bootloader.bin": f"bootloader-{version_suffix}.bin",
        Path("partition_table") / "partition-table.bin": f"partition-table-{version_suffix}.bin",
        "www.bin": f"www-{version_suffix}.bin",
        "flasher_args.json": f"flasher_args-{version_suffix}.json"
    }

    logger.info(f"Copying artifacts from {firmware_build_path} to {output_dir}...")
    copied_files_paths = []
    file_manifest = {}
    for src_rel_path, dest_filename in artifacts_to_copy.items():
        src_full_path = firmware_build_path / src_rel_path
        dest_full_path = output_dir / dest_filename
        if src_full_path.exists():
            try:
                shutil.copy2(src_full_path, dest_full_path)
                file_size = dest_full_path.stat().st_size
                file_hash = hashlib.sha256(dest_full_path.read_bytes()).hexdigest()
                file_manifest[dest_filename] = {"size": file_size, "sha256": file_hash}
                logger.debug(f"Copied {src_full_path} to {dest_full_path} ({file_size} bytes)")
                copied_files_paths.append(dest_full_path)
            except Exception as e:
                logger.error(f"Error copying {src_full_path} to {dest_full_path}: {e}")
        else:
            if src_rel_path != "flasher_args.json" and not str(src_rel_path).startswith("www") :
                 logger.error(f"CRITICAL Error: Source artifact not found, skipping copy: {src_full_path}")
            else:
                 logger.warning(f"Source artifact not found, skipping copy: {src_full_path}")

    # --- COMMENT OUT Build Info Saving ---
    # info_file_path = output_dir / BUILD_INFO_FILE
    # build_info = {
    #     'built_tag': built_tag,
    #     'expected_version': expected_version,
    #     'build_timestamp_utc': time.time(),
    #     'artifacts': file_manifest,
    #     'platform': f\"{platform.system()} {platform.machine()}\"
    # }
    # try:
    #     with open(info_file_path, 'w') as f:
    #         json.dump(build_info, f, indent=4)
    #     logger.info(f\"Saved build info to {info_file_path} with expected_version: '{expected_version}\'\")
    # except Exception as e:
    #     logger.error(f\"Error saving build info to {info_file_path}: {e}\")
    # --- END COMMENT OUT ---

    idf_log_src = get_env_dir() / "logs" / IDF_BUILD_LOG_FILENAME
    idf_log_dest = output_dir / IDF_BUILD_LOG_FILENAME
    if idf_log_src.exists():
        try:
            shutil.copy2(idf_log_src, idf_log_dest)
            logger.info(f"Saved full idf.py build log to {idf_log_dest}")
        except Exception as e:
            logger.error(f"Could not copy {idf_log_src} to {idf_log_dest}: {e}")
    else:
        logger.warning(f"IDF build log not found at {idf_log_src}")

    logger.info(f"Artifact copying complete. ({len(copied_files_paths)} essential files copied to {output_dir})")
    return copied_files_paths

# --- New Function for Build Info ---
def create_and_save_build_info(copied_artifact_paths: list[Path],
                               built_tag: str,
                               expected_version: str,
                               output_dir: Path,
                               is_custom_repo: bool = False,
                               custom_repo_url: str = None) -> dict:
    """Calculates hashes, identifies key binaries, creates build_info dict, and saves it.

    Args:
        copied_artifact_paths: List of Path objects pointing to the copied artifacts
        built_tag: The tag that was built
        expected_version: The expected version string
        output_dir: The directory to save the build_info.json file
        is_custom_repo: Whether a custom repository URL was used
        custom_repo_url: The custom repository URL if used

    Returns:
        dict: The build information dictionary

    Raises:
        ValueError: If custom repository information is missing from the saved file
                               in the output directory.
        built_tag: The specific git tag that was built.
        expected_version: The full version string (e.g., tag + suffix).
        output_dir: The Path object for the output directory (e.g., /firmware).

    Returns:
        The created build_info dictionary.
    """
    logger.info("--- Creating and Saving Build Information --- ")
    esp_miner_rel_path = None
    www_bin_rel_path = None
    firmware_hashes = {}
    firmware_relative_files = []

    if not output_dir or not isinstance(output_dir, Path):
        logger.error("create_and_save_build_info: Invalid output_dir provided.")
        return {} # Return empty dict on error

    if not copied_artifact_paths:
        logger.warning("create_and_save_build_info: No artifact paths provided. Build info will be incomplete.")
        # Continue to create a potentially empty/partial info file

    for file_path in copied_artifact_paths:
        if not file_path.is_file():
            logger.warning(f"Skipping non-file item during build info creation: {file_path}")
            continue
        try:
            # Ensure paths are absolute before calculating relative path
            abs_file_path = file_path.resolve()
            abs_output_dir = output_dir.resolve()
            relative_path_str = str(abs_file_path.relative_to(abs_output_dir))
            firmware_relative_files.append(relative_path_str)
            file_name = file_path.name

            # Identify specific binaries based on naming convention used in copy_artifacts_to_output
            # Assuming format: <type>-<version>.bin
            if file_name.startswith("esp-miner-") and file_name.endswith(".bin"):
                esp_miner_rel_path = relative_path_str
            elif file_name.startswith("www-") and file_name.endswith(".bin"):
                www_bin_rel_path = relative_path_str

            # Calculate hash
            with open(file_path, 'rb') as f:
                file_content = f.read()
                hash_value = hashlib.sha256(file_content).hexdigest()
                # Use filename as key for consistency with previous logic
                firmware_hashes[file_name] = hash_value
            logger.debug(f"Processed for build info: {file_name}, Hash: {hash_value[:8]}...")

        except ValueError as e:
            logger.error(f"Error calculating relative path for {file_path} against {output_dir}: {e}")
        except OSError as e:
            logger.error(f"Error reading file {file_path} for hashing: {e}")
        except Exception as e:
            logger.error(f"Unexpected error processing file {file_path} for build info: {e}", exc_info=True)

    # Construct the build_info dictionary
    build_info = {
        'tag': built_tag, # Renamed from 'built_tag' for consistency
        'version': expected_version,
        'build_time': datetime.datetime.now(datetime.timezone.utc).isoformat(), # Use UTC
        'files': firmware_relative_files, # The list of all relative paths
        'esp_miner_bin_rel_path': esp_miner_rel_path, # Specific relative path
        'www_bin_rel_path': www_bin_rel_path,         # Specific relative path
        'sha256_hashes': firmware_hashes,
    }

    # Add repo_url field with the new format
    repo_url = custom_repo_url if is_custom_repo else ESP_MINER_REPO
    build_info['repo_url'] = {
        'custom': bool(is_custom_repo),
        'url': repo_url
    }

    # Log the repository information with more details
    logger.info(f"Adding repository information to build_info dictionary:")
    logger.info(f"  - Repository URL: {repo_url}")
    logger.info(f"  - Custom repository: {bool(is_custom_repo)}")
    logger.debug(f"  - Full repo_url field: {build_info['repo_url']}")

    # For backward compatibility, also include the custom_repo field if using a custom repo
    if is_custom_repo and custom_repo_url:
        build_info['custom_repo'] = {
            'used': True,
            'url': custom_repo_url
        }
        logger.debug(f"  - Added backward compatibility custom_repo field: {build_info['custom_repo']}")

    # Define the path for build_info.json
    build_info_path = output_dir / BUILD_INFO_FILE

    # Save the dictionary to build_info.json (incorporating logic from web_ui.save_last_build_info)
    try:
        # Ensure output directory exists (should already exist from copy_artifacts)
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Saving build info to {build_info_path}...")
        # Log the keys in the build_info dictionary to help with debugging
        logger.debug(f"Keys in build_info dictionary before saving: {list(build_info.keys())}")

        # Verify that repo_url is in the dictionary before saving
        if 'repo_url' not in build_info:
            logger.error("repo_url field is missing from build_info dictionary before saving!")
            # Add it again if it's somehow missing
            repo_url = custom_repo_url if is_custom_repo else ESP_MINER_REPO
            build_info['repo_url'] = {
                'custom': bool(is_custom_repo),
                'url': repo_url
            }
            logger.info(f"Re-added repo_url field to build_info dictionary: {build_info['repo_url']}")

        # Use ensure_ascii=False for potentially non-ASCII characters in paths/tags
        # Use indent=4 for readability
        with open(build_info_path, 'w', encoding='utf-8') as f:
            json.dump(build_info, f, indent=4, ensure_ascii=False)

        # Verify the file was written correctly
        if build_info_path.exists():
            file_size = build_info_path.stat().st_size
            logger.info(f"Successfully saved build info to {build_info_path} ({file_size} bytes).")
        else:
            logger.error(f"Failed to save build info to {build_info_path}! File does not exist after writing.")

        # Validate that repository information is included
        # Read the file back to verify the information was saved
        logger.info("Validating repository information in saved build_info.json file...")
        try:
            with open(build_info_path, 'r', encoding='utf-8') as f:
                saved_build_info = json.load(f)

            # Log the keys in the saved build_info dictionary
            logger.debug(f"Keys in saved build_info dictionary: {list(saved_build_info.keys())}")

            # Check for repo_url field
            if 'repo_url' not in saved_build_info:
                error_msg = "Repository information (repo_url field) missing from build_info.json"
                logger.error(error_msg)
                # Log the entire saved build_info for debugging
                logger.error(f"Content of saved build_info: {saved_build_info}")
                raise ValueError(error_msg)

            # Log the repo_url field from the saved file
            logger.debug(f"repo_url field in saved build_info: {saved_build_info.get('repo_url')}")

            expected_url = custom_repo_url if is_custom_repo else ESP_MINER_REPO
            if saved_build_info['repo_url'].get('url') != expected_url:
                error_msg = f"Repository URL mismatch in build_info.json: expected '{expected_url}', got '{saved_build_info['repo_url'].get('url')}'"
                logger.error(error_msg)
                raise ValueError(error_msg)

            if saved_build_info['repo_url'].get('custom') != bool(is_custom_repo):
                error_msg = f"Repository custom flag mismatch in build_info.json: expected '{bool(is_custom_repo)}', got '{saved_build_info['repo_url'].get('custom')}'"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Also check for backward compatibility with custom_repo field if using a custom repo
            if is_custom_repo and custom_repo_url:
                if 'custom_repo' not in saved_build_info:
                    logger.warning("Legacy custom_repo field missing from build_info.json for custom repository")
                else:
                    if saved_build_info['custom_repo'].get('url') != expected_url:
                        logger.warning(f"Legacy custom_repo URL mismatch in build_info.json: expected '{expected_url}', got '{saved_build_info['custom_repo'].get('url')}'")

                    if saved_build_info['custom_repo'].get('used') != True:
                        logger.warning(f"Legacy custom_repo used flag mismatch in build_info.json: expected 'True', got '{saved_build_info['custom_repo'].get('used')}'")

            logger.info("Repository information successfully validated in build_info.json")
        except json.JSONDecodeError as e:
            error_msg = f"Error decoding JSON from build_info.json: {e}"
            logger.error(error_msg)
            # Try to read the raw file content for debugging
            try:
                with open(build_info_path, 'r', encoding='utf-8') as f:
                    raw_content = f.read()
                logger.error(f"Raw content of build_info.json (first 500 chars): {raw_content[:500]}")
            except Exception as read_err:
                logger.error(f"Could not read raw content of build_info.json: {read_err}")
            raise ValueError(error_msg)

    except TypeError as e:
        logger.exception(f"Error serializing build info to JSON for {build_info_path}: {e}. Data: {build_info}")
        raise
    except OSError as e:
        logger.exception(f"Error writing build info file {build_info_path}: {e}")
        raise
    except ValueError as e:
        # This is raised by our validation code
        logger.exception(f"Validation error for build_info.json: {e}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error saving build info file {build_info_path}: {e}")
        raise

    return build_info

def calculate_sha256(file_path):
    """Calculate SHA256 checksum for a file."""
    # Ensure file_path is a Path object
    file_path = Path(file_path)
    if not file_path.is_file():
        logger.error(f"Cannot calculate SHA256: File not found at {file_path}")
        return None

    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            # Read and update hash string value in blocks of 4K
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        hex_digest = sha256_hash.hexdigest()
        logger.debug(f"Calculated SHA256 for {file_path.name}: {hex_digest}")
        return hex_digest
    except OSError as e:
        logger.error(f"Error reading file {file_path} for SHA256 calculation: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error calculating SHA256 for {file_path}: {e}")
        return None

# Need to import argparse for type hint in _handle_flashing if it remains here
# import argparse
# def _handle_flashing(...): # This function is defined in device.py

# calculate_sha256 was defined as a method before, needs adjustment if needed as standalone
# def calculate_sha256(file_path):
#     """Calculate SHA256 checksum for a file."""
#     sha256_hash = hashlib.sha256()
#     with open(file_path, "rb") as f:
#         for byte_block in iter(lambda: f.read(4096), b""):
#             sha256_hash.update(byte_block)
#     return sha256_hash.hexdigest()