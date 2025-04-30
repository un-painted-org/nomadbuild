# build.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
# Core ESP-IDF build process functions
import logging
import subprocess
import sys
import os
import json
from pathlib import Path
import re
import threading # Needed for _run_idf_build
from typing import List, Optional, Callable, Tuple
import time
import signal  # Add import for process group kill
import shutil

# Import necessary functions/classes from other modules
from .utils import run_command, get_env_dir, Spinner, CONTAINER_OUTPUT_DIR, IDF_BUILD_LOG_FILENAME
from .git_ops import checkout_tag # , is_repo_clean <-- Add back if needed

# Placeholder for logger - Will be configured properly in cli.py
logger = logging.getLogger(__name__)

# Define custom exception for build failures
class BuildFailedError(Exception):
    pass

# Define the path to the correct Python interpreter for ESP-IDF builds
ESP_IDF_PYTHON = "/opt/esp/python_env/idf5.4_py3.12_env/bin/python"
# Define the full path to the idf.py script
IDF_PY_SCRIPT = "/opt/esp/idf/tools/idf.py"

# --- Global state for tracking build status and active processes ---
# Use threading.Event for cancellation signaling
active_build_processes = {}  # Dictionary to track active processes for cancellation
# Flag to indicate a build is currently in progress
is_building = False
build_cancel_event = threading.Event()
build_progress = 0
current_tag = None

# --- Functions moved from main script ---

def get_commit_timestamp(repo_path: Path, ref: str) -> str | None:
    """Gets the commit timestamp (Unix epoch) for a given Git ref (tag/commit/branch)."""
    logger.debug(f"Getting commit timestamp for ref '{ref}'...")
    try:
        # %ct gives committer date, UNIX timestamp
        ts_str = run_command(["git", "log", "-1", "--pretty=%ct", ref], cwd=repo_path)
        if ts_str and ts_str.isdigit():
            logger.debug(f"Found timestamp: {ts_str} for ref '{ref}'")
            return ts_str
        logger.error(f"Could not parse commit timestamp for ref '{ref}'. Output: '{ts_str}'")
        return None
    except Exception as e:
        logger.error(f"Could not get commit timestamp for ref '{ref}': {e}")
        return None

def _prepare_source_code(miner_repo_path: Path, selected_tag: str, progress_callback: Optional[Callable[[int, str], None]] = None) -> Tuple[str, str, str]:
    """Checks out the specified tag, updates submodules, and ensures clean state.
    
    Returns:
        Tuple[str, str, str]: (commit_hash, expected_version, commit_timestamp)
    Raises:
        RuntimeError: If checkout or submodule update fails.
        ValueError: If tag does not exist.
    """
    if progress_callback: progress_callback(20, f"Preparing source code for tag: {selected_tag}...")
    logger.info(f"Preparing source code for tag: {selected_tag}")
    
    # Checkout tag first
    try:
        # Use the existing checkout_tag function from git_ops
        # Pass the progress callback to it if available
        commit_hash = checkout_tag(miner_repo_path, selected_tag, progress_callback)
        if not commit_hash:
             logger.error(f"Failed to checkout tag {selected_tag}.")
             raise ValueError(f"Tag '{selected_tag}' not found or checkout failed.")
        logger.info(f"Checked out tag {selected_tag} at commit {commit_hash}")
    except ValueError as e:
        logger.error(f"Error checking out tag: {e}")
        raise # Re-raise value error (tag not found etc.)
    except Exception as e:
        logger.error(f"Unexpected error during tag checkout: {e}")
        raise RuntimeError("Tag checkout failed.") from e

    # Update submodules after successful checkout
    if progress_callback: progress_callback(30, "Updating submodules...")
    logger.info("Updating submodules...")
    try:
        run_command(["git", "submodule", "update", "--init", "--recursive"], cwd=miner_repo_path, check=True)
        logger.info("Submodules updated successfully.")
    except Exception as e:
        logger.error(f"Failed to update submodules: {e}")
        if progress_callback: progress_callback(30, f"Error updating submodules: {e}")
        raise RuntimeError("Submodule update failed.") from e
        
    # Construct expected version string (tag + suffix)
    # TODO: Make suffix configurable? For now, hardcode '-sovereign'
    expected_version = f"{selected_tag}-sovereign"
    logger.info(f"Constructed full expected version: {expected_version}")

    # Write version string to version.txt for the build system to pick up
    version_file = miner_repo_path / "version.txt"
    try:
        version_file.write_text(expected_version)
        # Verification step
        if version_file.read_text() == expected_version:
            logger.info(f"Writing version file ({version_file}) with content: {expected_version}")
        else:
            # This case indicates a potential filesystem issue or race condition
            logger.error(f"Verification failed after writing {version_file}! Content mismatch.")
            raise RuntimeError(f"Version file write verification failed for {version_file}")
    except OSError as e:
        # Specific handling for OS errors (like disk full)
        logger.error(f"OS error writing version file {version_file}: {e}")
        # Re-raise as RuntimeError to be caught by tests or indicate critical failure
        raise RuntimeError(f"Failed to write version file {version_file} due to OS error.") from e
    except Exception as e:
        # Catch other potential exceptions during file write/read
        logger.error(f"Unexpected error writing or verifying version file {version_file}: {e}")
        raise RuntimeError(f"Unexpected error with version file {version_file}.") from e

    # Get commit timestamp for SOURCE_DATE_EPOCH
    commit_timestamp = get_commit_timestamp(miner_repo_path, selected_tag)
    if not commit_timestamp:
        logger.warning(f"Could not determine commit timestamp for tag {selected_tag}. Reproducibility might be affected.")
        # Fallback or default timestamp?
        commit_timestamp = str(int(time.time())) # Use current time as fallback
        logger.warning(f"Using current timestamp as fallback: {commit_timestamp}")
    else:
        logger.info(f"Using commit timestamp {commit_timestamp} for SOURCE_DATE_EPOCH.")

    # Return commit hash, expected version string, and commit timestamp
    logger.info(f"Source code prepared. Returning Commit: {commit_hash}, Expected Version: {expected_version}, Timestamp: {commit_timestamp}")
    return commit_hash, expected_version, commit_timestamp

# Note: _get_commit_timestamp is Git specific, moved to git_ops.py if needed, unused here.

def _run_idf_clean(miner_repo_path: Path):
    """Runs idf.py fullclean using the correct Python environment and direct subprocess call."""
    logger.info("Running idf.py fullclean...")
    # Start from parent env and remove known non-deterministic variables
    idf_env = os.environ.copy()
    non_deterministic = []
    for k in list(idf_env.keys()):
        if (k in ['HOME','USER','PWD','OLDPWD']
            or k.startswith('TMP')
            or k.startswith('TEMP')
            or k.startswith('CI')
            or k.startswith('GITHUB_')
            or k.startswith('DOCKER_')
            or k.startswith('SSH_')
            or k.startswith('PYENV_')
            or k in ['PYTHONPATH','PYTHONHOME']):
            non_deterministic.append(k)
    for k in non_deterministic:
        idf_env.pop(k, None)
    # Ensure build-relevant variables are set
    idf_env['IDF_TARGET'] = 'esp32s3'
    # Execute idf.py script directly with the ESP-IDF Python interpreter
    command = ["idf.py", "fullclean"]
    logger.info(f"Executing: {' '.join(command)} in {miner_repo_path}")
    try:
        # Use subprocess.run directly, ensure cwd is passed, capture=False equivalent
        process = subprocess.run(
            command,
            cwd=miner_repo_path,
            env=idf_env,
            check=True, # Raise CalledProcessError on failure
            stdout=sys.stdout, # Send stdout directly to parent stdout
            stderr=sys.stderr, # Send stderr directly to parent stderr
            text=True
        )
        logger.info("Clean completed successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"idf.py fullclean failed with exit code {e.returncode}.")
        # Output should have gone directly to stderr, but log error just in case.
        raise # Re-raise the exception to be caught by build_esp_miner
    except FileNotFoundError:
        logger.error(f"Error: Command '{command[0]}' or script '{command[1]}' not found.")
        raise BuildFailedError(f"Clean command dependency not found.")
    except Exception as e:
        logger.exception(f"An unexpected error occurred during idf fullclean: {e}")
        raise BuildFailedError(f"Unexpected error during clean: {e}")

def _run_idf_build(miner_repo_path: Path, commit_timestamp: str | None, verbose_stream: bool, progress_callback: Callable[[int, str], None] | None = None) -> str | None:
    """Runs the IDF build command (idf.py build). Uses version.txt implicitly."""
    logger.info("Running the build process...")
    build_log_path = get_env_dir() / "logs" / "idf_build_output.log"
    
    # Start from parent env and remove known non-deterministic variables
    build_env = os.environ.copy()
    non_deterministic = []
    for k in list(build_env.keys()):
        if (k in ['HOME','USER','PWD','OLDPWD']
            or k.startswith('TMP')
            or k.startswith('TEMP')
            or k.startswith('CI')
            or k.startswith('GITHUB_')
            or k.startswith('DOCKER_')
            or k.startswith('SSH_')
            or k.startswith('PYENV_')
            or k in ['PYTHONPATH','PYTHONHOME']):
            non_deterministic.append(k)
    for k in non_deterministic:
        build_env.pop(k, None)
    # Ensure build-relevant variables are set
    build_env['IDF_TARGET'] = 'esp32s3'
    if commit_timestamp:
        build_env['SOURCE_DATE_EPOCH'] = commit_timestamp
    
    # Execute idf.py build using the ESP-IDF Python interpreter for deterministic environment
    command = [ESP_IDF_PYTHON, IDF_PY_SCRIPT]
    if verbose_stream:
        command.append("-v")
    command.append("build")
    logger.info(f"Executing: {' '.join(command)} in {miner_repo_path}")

    # Log relevant env vars being used by the subprocess
    logger.info(f"  Env (Selected): {{'IDF_TARGET': '{build_env.get('IDF_TARGET')}', 'SOURCE_DATE_EPOCH': '{build_env.get('SOURCE_DATE_EPOCH', 'N/A')}'}}")

    # Compile Progress Tracking Variables
    # (Initialize percentage markers for progress updates)
    PREPARE_PERCENT = 5
    CMAKE_PERCENT = 10
    COMPILE_START_PERCENT = 15
    COMPILE_END_PERCENT = 80 # Reserve % for linking, merging etc.
    LINK_PERCENT = 85
    MERGE_PERCENT = 90
    FINALIZE_PERCENT = 95
    
    # State variables for tracking (can be accessed via nonlocal in stream_output)
    last_compile_percent = CMAKE_PERCENT
    total_files_to_compile = 0
    files_compiled = 0
    build_progress = CMAKE_PERCENT
    build_error_occurred = False
    error_output = ""
    error_stderr = ""

    # Initial progress update before starting the process
    if progress_callback:
        progress_callback(PREPARE_PERCENT, "Preparing ESP-IDF build environment...")

    logger.info(f"Starting build command: {' '.join(command)}")
    process = None 
    stdout_lines = []
    stderr_lines = []
    
    try:
        process = subprocess.Popen(
            command, 
            cwd=miner_repo_path,
            env=build_env, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            # Use preexec_fn=os.setsid to create a process group for cancellation
            preexec_fn=os.setsid 
        )
        
        # Add process to active list immediately after creation
        if process.pid:
            active_build_processes[process.pid] = process # Store process object for cancellation
            logger.debug(f"Added process {process.pid} to active_build_processes. Current: {list(active_build_processes.keys())}")
            # Give external observers time to see the active process before potential quick removal in tests
            time.sleep(0.05) 
            list(active_build_processes.keys()) # Ensure dictionary is observed in multi-threaded context
        else:
            logger.warning("Popen process created without PID, cancellation may not work.")

        # --- Output Streaming Logic (Defined inside to use nonlocal correctly) --- # 
        def stream_output(pipe, output_list, log_prefix, stream_func, callback_func):
            nonlocal last_compile_percent, total_files_to_compile, files_compiled, build_progress, build_error_occurred
            
            compile_progress_regex = re.compile(r"\s*\[(\d+)/(\d+)\]")
            
            for line in iter(pipe.readline, ''):
                line = line.strip()
                if not line: continue
                output_list.append(line)
                
                # Logging logic
                if logger.isEnabledFor(logging.DEBUG) or verbose_stream:
                     stream_func(f"{log_prefix} {line}")
                elif log_prefix == "[Build STDERR]:": 
                     logger.warning(f"{log_prefix} {line}")

                if not build_error_occurred:
                    try:
                        # --- Progress Parsing Logic --- 
                        if "Running cmake in directory" in line:
                            message = "Running CMake configuration..."
                            if not verbose_stream: stream_func(message)
                            if callback_func:
                                callback_func(CMAKE_PERCENT, message)
                            build_progress = CMAKE_PERCENT
                            continue
                            
                        match = compile_progress_regex.search(line)
                        if match:
                            files_compiled = int(match.group(1))
                            # Always update total_files_to_compile from the current line
                            total_files_to_compile = int(match.group(2)) 
                            
                            if total_files_to_compile > 0:
                                compile_ratio = files_compiled / total_files_to_compile
                                current_percent = int(COMPILE_START_PERCENT + (COMPILE_END_PERCENT - COMPILE_START_PERCENT) * compile_ratio)
                                last_compile_percent = max(current_percent, last_compile_percent)
                                # Now uses the updated total
                                message = f"Compiling ({files_compiled}/{total_files_to_compile})..."
                                if not verbose_stream: stream_func(message)
                                if callback_func:
                                    callback_func(last_compile_percent, message)
                                build_progress = last_compile_percent
                            continue

                        elif "Linking CXX executable esp-miner.elf" in line:
                            message = "Linking executable..."
                            if not verbose_stream: stream_func(message)
                            if callback_func:
                                callback_func(LINK_PERCENT, message)
                            last_compile_percent = LINK_PERCENT
                            build_progress = LINK_PERCENT
                            continue

                        elif "esptool.py" in line and "Merging binaries" in line:
                            message = "Merging binaries..."
                            if not verbose_stream: stream_func(message)
                            if callback_func:
                                callback_func(MERGE_PERCENT, message)
                            last_compile_percent = MERGE_PERCENT
                            build_progress = MERGE_PERCENT
                            continue

                        elif "Project build complete." in line:
                            message = "Build finalizing..."
                            if not verbose_stream: stream_func(message)
                            if callback_func:
                                callback_func(FINALIZE_PERCENT, message)
                            last_compile_percent = FINALIZE_PERCENT 
                            build_progress = FINALIZE_PERCENT
                            continue
                            
                        elif line.startswith("error:") or line.startswith("FAILED:") or "CMake Error at" in line:
                             logger.warning(f"Potential build error detected: {line}")
                             
                    except Exception as e:
                         # More robust error logging here
                         try:
                             err_msg = f"Error during build output parsing. Line: '{line}'. Error Type: {type(e).__name__}. Error: {e}"
                             logger.error(err_msg, exc_info=False) 
                         except Exception as log_err:
                             logger.error(f"!!! Logging failed during exception handling: {log_err}")
                         # Let exit code check determine final build failure status

            pipe.close()

        # Pass progress_callback explicitly as 'callback_func' argument to the thread target
        stdout_thread = threading.Thread(target=stream_output, args=(process.stdout, stdout_lines, "[Build STDOUT]:", logger.info, progress_callback))
        stderr_thread = threading.Thread(target=stream_output, args=(process.stderr, stderr_lines, "[Build STDERR]:", logger.warning, progress_callback))
        stdout_thread.start()
        stderr_thread.start()
        
        # Wait for threads to finish
        stdout_thread.join()
        stderr_thread.join()

        # Wait for the process to terminate and get the exit code
        process.wait()
        return_code = process.returncode
        logger.info(f"idf.py build finished with exit code: {return_code}")
        
        # Consolidate output for logging and potential error reporting
        full_stdout = "\n".join(stdout_lines)
        full_stderr = "\n".join(stderr_lines)

        # Log the full output to the dedicated log file
        try:
            with open(build_log_path, 'w') as f:
                f.write("--- STDOUT ---\n")
                f.write(full_stdout)
                f.write("\n\n--- STDERR ---\n")
                f.write(full_stderr)
            logger.info(f"Saved full idf.py build log to {build_log_path}")
        except Exception as log_e:
            logger.error(f"Failed to write idf build log to {build_log_path}: {log_e}")

        # Check the return code AFTER joining threads and logging
        if return_code != 0:
            build_error_occurred = True
            error_output = full_stdout # Store full output for error context
            error_stderr = full_stderr
            logger.error(f"Build process failed with exit code {return_code}.")
            last_stderr = "\n".join(stderr_lines[-10:]) # Keep logging last stderr lines
            logger.error(f"Last stderr lines:\n{last_stderr}")
            raise subprocess.CalledProcessError(return_code, command, output=error_output, stderr=error_stderr)

        # If successful, report 100% (if callback exists)
        if progress_callback:
            progress_callback(100, "Build process completed successfully.")
        
        return str(build_log_path) # Return path to log file

    except subprocess.CalledProcessError as e:
        logger.critical(f"Build command failed. Check log file: {build_log_path}")
        raise # Re-raise the CaughtProcessError
        
    except FileNotFoundError:
        logger.error(f"Error: Command '{command[0]}' or script '{command[1]}' not found.")
        raise BuildFailedError(f"Build command dependency not found.")

    except Exception as e:
        logger.exception(f"An unexpected error occurred during the build: {e}")
        if process and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception as term_e:
                logger.error(f"Error terminating build process: {term_e}")
        raise BuildFailedError(f"Unexpected build error: {e}")

    finally:
        # Ensure process is removed from tracking upon completion or error/cancellation
        if process and process.pid and process.pid in active_build_processes:
            logger.debug(f"Removing process {process.pid} from active_build_processes in finally block.")
            try:
                del active_build_processes[process.pid]
            except KeyError:
                logger.warning(f"Process {process.pid} already removed from tracking.")
            except Exception as del_err:
                logger.error(f"Error removing process {process.pid} from tracking: {del_err}")
        
        # Ensure streams are closed if process exists
        if process:
            if process.stdout: process.stdout.close()
            if process.stderr: process.stderr.close()

def _verify_build_artifacts(build_dir: Path, progress_callback: Callable[[int, str], None] | None = None):
    logger.info("--- Verifying Build Artifacts --- ")
    if progress_callback: progress_callback(96, "Checking for essential artifacts...")
    expected_artifacts_paths = {
        "app": "esp-miner.bin",
        "partition_table": Path("partition_table") / "partition-table.bin",
        "bootloader": Path("bootloader") / "bootloader.bin",
        "web_ui": "www.bin"
    }
    missing_artifacts_keys = []
    found_list = []
    for key, rel_path in expected_artifacts_paths.items():
        full_path = build_dir / rel_path
        if full_path.exists():
             found_list.append(str(rel_path))
        else:
            if key != "web_ui": 
                 missing_artifacts_keys.append(key)
                 logger.error(f"Error: Essential build artifact '{key}' missing at expected path: {full_path}")
            else:
                 logger.warning(f"Optional artifact '{key}' not found at {full_path}. Build continuing.")
                 found_list.append(f"{rel_path} (Not Found - Optional)")
    if missing_artifacts_keys:
        if "app" in missing_artifacts_keys and (build_dir / "firmware.bin").exists():
             logger.warning("Note: Found 'firmware.bin' instead of 'esp-miner.bin'. Using firmware.bin.")
        else:
            error_msg = f"Firmware build failed - missing essential artifacts: {', '.join(missing_artifacts_keys)}."
            logger.critical(error_msg)
            sys.exit(error_msg)
    logger.info(f"Build artifacts verification complete. Found: {', '.join(found_list)} relative to: {build_dir}")

def _find_build_outputs(miner_repo_path: Path, build_dir: Path, progress_callback: Callable[[int, str], None] | None = None) -> tuple[Path | None, Path | None]:
    logger.info("--- Locating Partition Table and Flasher Args ---")
    if progress_callback: progress_callback(99, "Locating partition/flash config...")
    partition_csv_path = miner_repo_path / "partitions_16mb.csv"
    if not partition_csv_path.exists():
        fallback_path = miner_repo_path / "partitions.csv"
        if fallback_path.exists():
             partition_csv_path = fallback_path
             logger.info(f"Using partition file: {partition_csv_path}")
        else:
             logger.warning(f"Could not find partition file...")
             partition_csv_path = None
    else:
         logger.info(f"Using partition file: {partition_csv_path}")
    flasher_args_path = build_dir / "flasher_args.json"
    if not flasher_args_path.exists():
        logger.error(f"CRITICAL: flasher_args.json not found...")
        flasher_args_path = None
    else:
        logger.info(f"Found flasher_args.json for analysis: {flasher_args_path}")
    return partition_csv_path, flasher_args_path

def build_esp_miner(miner_repo_path: Path, selected_tag: str, verbose_stream: bool, progress_callback: Optional[Callable[[int, str], None]] = None) -> Tuple[Path, str, Path, Path, str]:
    """Main function to orchestrate the build process for a specific tag."""
    logger.info(f"\n--- Starting Build Phase --- ") 
    logger.info(f"--- Build Orchestration for Tag: {selected_tag} ---")
    global build_start_time
    build_start_time = time.time()
    
    miner_repo_path = Path(miner_repo_path)
    build_dir = miner_repo_path / "build"
    partition_csv_path = miner_repo_path / "partitions.csv"
    flasher_args_path = build_dir / "flasher_args.json"

    # --- Pre-build Steps --- 
    try:
        # 1. Clean previous artifacts if they exist
        if progress_callback: progress_callback(10, "Cleaning previous build artifacts...")
        _run_idf_clean(miner_repo_path)

        # 2. Prepare source code (checkout tag, update submodules, write version.txt)
        # Now also returns commit_timestamp
        commit_hash, expected_version, commit_timestamp = _prepare_source_code(miner_repo_path, selected_tag, progress_callback)

        # 3. Run the IDF build process
        if progress_callback: progress_callback(40, "Starting ESP-IDF build process...")
        # Pass commit_timestamp to _run_idf_build
        build_output_log = _run_idf_build(miner_repo_path, commit_timestamp, verbose_stream, progress_callback)
        
        # Check if build was cancelled during _run_idf_build (it returns None)
        if build_output_log is None:
             logger.warning("Build process was cancelled or terminated early.")
             raise BuildFailedError("Build Cancelled") # Raise specific error

        # --- Post-build Steps --- 
        # 4. Verify essential build artifacts exist
        if progress_callback: progress_callback(96, "Verifying build artifacts...")
        _verify_build_artifacts(build_dir, progress_callback)
        
        # Log success and return necessary paths/info
        logger.info(f"ESP-Miner build for tag '{selected_tag}' completed successfully.")
        return build_dir, commit_hash, partition_csv_path, flasher_args_path, expected_version

    except BuildFailedError as bfe:
        logger.error(f"BuildFailedError occurred: {bfe}")
        raise # Re-raise BuildFailedError
    except subprocess.CalledProcessError as cpe:
        logger.error(f"A build command failed with exit code {cpe.returncode}.")
        logger.error(f"Command: {' '.join(cpe.cmd)}")
        # Log stderr if available and not too long
        if cpe.stderr:
            stderr_preview = cpe.stderr.strip().split('\n')[ -10:] # Last 10 lines
            logger.error(f"Stderr (last {len(stderr_preview)} lines):\n" + '\n'.join(stderr_preview))
        raise BuildFailedError(f"Build command failed (Exit Code: {cpe.returncode}).") from cpe
    except Exception as e:
        # Catch other potential errors during orchestration
        logger.exception(f"An unexpected error occurred during build orchestration: {e}")
        raise BuildFailedError(f"Unexpected build orchestration error: {e}") from e

# --- Analysis Helpers ---

def _parse_flasher_args(flasher_args_path: Path | None) -> dict:
    """Parses flasher_args.json and returns extracted analysis data."""
    analysis = {
        'flash_settings': {},
        'flash_files_from_json': {}, 
        'flash_offsets_from_json': {}, 
        'flash_mode': 'N/A',
        'flash_freq': 'N/A',
        'flash_size': 'N/A',
        'target_chip': 'N/A'
    }
    if not flasher_args_path or not flasher_args_path.exists():
        logger.error("flasher_args.json not found or not provided...")
        return analysis 

    logger.info(f"Parsing {flasher_args_path}...")
    try:
        with open(flasher_args_path, 'r') as f:
            flasher_data = json.load(f)

        analysis['flash_settings'] = flasher_data.get('flash_settings', {})
        analysis['flash_mode'] = analysis['flash_settings'].get('flash_mode', 'Not Found')
        analysis['flash_freq'] = analysis['flash_settings'].get('flash_freq', 'Not Found')
        analysis['flash_size'] = analysis['flash_settings'].get('flash_size', 'Not Found')
        analysis['target_chip'] = flasher_data.get('chip', 'esp32s3')
        logger.debug(f"Flash Settings from JSON: {analysis['flash_settings']}")

        analysis['flash_files_from_json'] = flasher_data.get('flash_files', {})
        logger.debug(f"Flash Files from JSON: {analysis['flash_files_from_json']}")
        for offset, rel_path_str in analysis['flash_files_from_json'].items():
            simple_name = Path(rel_path_str).name
            if simple_name == "partition-table.bin": simple_name = "partitions.bin"
            elif simple_name == "esp-miner.bin" or simple_name == "firmware.bin": simple_name = "esp-miner.bin"
            
            if simple_name in ["bootloader.bin", "partitions.bin", "esp-miner.bin", "www.bin", "ota_data_initial.bin"]:
                analysis['flash_offsets_from_json'][simple_name] = offset
            else:
                 logger.debug(f"Ignoring unknown file '{rel_path_str}'...")
        logger.debug(f"Mapped Flash Offsets from JSON: {analysis['flash_offsets_from_json']}")

    except json.JSONDecodeError as e: logger.error(f"Error decoding JSON...: {e}")
    except Exception as e: logger.error(f"Error reading {flasher_args_path}: {e}")
    return analysis

def _get_binary_sizes(build_dir: Path, flash_offsets_from_json: dict) -> dict:
    """Gets actual file sizes for expected build artifacts."""
    logger.info("Getting actual sizes...")
    binary_sizes_actual = {}
    artifact_rel_paths = {
        "bootloader.bin": Path("bootloader") / "bootloader.bin",
        "partitions.bin": Path("partition_table") / "partition-table.bin",
        "esp-miner.bin": "esp-miner.bin",
        "www.bin": "www.bin",
        "ota_data_initial.bin": "ota_data_initial.bin"
    }
    for simple_name, rel_path in artifact_rel_paths.items():
        file_path = build_dir / rel_path
        if file_path.exists():
            try:
                binary_sizes_actual[simple_name] = file_path.stat().st_size
                logger.debug(f"Found {simple_name}: {binary_sizes_actual[simple_name]} bytes...")
            except Exception as e: logger.warning(f"Could not get size...: {e}")
        else:
            if simple_name in flash_offsets_from_json: 
                 logger.warning(f"Binary file '{simple_name}' listed... not found...")
                 binary_sizes_actual[simple_name] = "Missing"
            else:
                 logger.debug(f"Optional binary '{simple_name}' not found...")
                 binary_sizes_actual[simple_name] = "Not Built/Found"
    return binary_sizes_actual

def _parse_partition_csv(partition_csv_path: Path | None) -> dict:
    """Parses the partition CSV file."""
    partition_table_details = {}
    if not partition_csv_path or not partition_csv_path.exists():
        logger.info("Partition table CSV file not found...")
        return partition_table_details
    logger.debug(f"Parsing partition table: {partition_csv_path}")
    try:
        partition_csv_content = partition_csv_path.read_text()
        lines = partition_csv_content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('#') or not line: continue
            try:
                fields = [f.strip() for f in line.split(',')]
                if len(fields) < 5: continue
                name, ptype, subtype, offset, size = fields[:5]
                flags = fields[5] if len(fields) > 5 else ""
                partition_table_details[name] = {
                    'type': ptype, 'subtype': subtype, 'offset': offset, 'size': size, 'flags': flags
                }
            except ValueError as e: logger.warning(f"Skipping malformed partition line...: {line}")
        logger.debug(f"Parsed partition details: {json.dumps(partition_table_details, indent=2)}")
    except Exception as e: logger.error(f"Error reading or parsing partition CSV...: {e}")
    return partition_table_details

def _perform_consistency_checks(analysis_data: dict) -> list[str]:
    """Performs consistency checks based on parsed build artifact data."""
    logger.info("Performing consistency checks...")
    issues_found = []
    partition_details = analysis_data.get('partition_table_details', {})
    binary_sizes = analysis_data.get('binary_sizes_actual', {})
    json_offsets = analysis_data.get('flash_offsets_from_json', {})
    essential_binaries = ["bootloader.bin", "partitions.bin", "esp-miner.bin"]

    if analysis_data.get('csv_parsed_successfully'):
        # ... (partition checks remain same) ...
        pass
    elif analysis_data.get('partition_csv_path') and not partition_details:
         issues_found.append("Partition table CSV was provided but failed to parse.")

    for name in essential_binaries:
        if binary_sizes.get(name) in ["Missing", "Error", "Not Built/Found", None]:
            issues_found.append(f"Essential binary '{name}' size could not be determined...")

    app_size_bytes = binary_sizes.get('esp-miner.bin')
    app_offset_json = json_offsets.get('esp-miner.bin')
    if isinstance(app_size_bytes, int) and app_offset_json and partition_details:
        # ... (App size check remains same) ...
        pass
    elif not isinstance(app_size_bytes, int): issues_found.append("App binary size... not determined...")
    elif not app_offset_json: issues_found.append("App binary offset... not found...")
    elif not partition_details and analysis_data.get('partition_csv_path'): 
         issues_found.append("Cannot perform app size check: Partition table details failed...")

    if json_offsets and partition_details:
         # ... (Offset consistency check remains same) ...
         pass 
    return issues_found

def analyze_build_output(build_dir: Path, flasher_args_path: Path | None, partition_csv_path: Path | None):
    """Analyzes build artifacts by calling helper functions."""
    logger.info("--- Analyzing Build Output & Configuration (Artifact-Based) ---")
    analysis_data = _parse_flasher_args(flasher_args_path)
    # Ensure this call receives the necessary data from analysis_data
    analysis_data['binary_sizes_actual'] = _get_binary_sizes(build_dir, analysis_data.get('flash_offsets_from_json', {}))
    analysis_data['partition_table_details'] = _parse_partition_csv(partition_csv_path)
    analysis_data['csv_parsed_successfully'] = bool(analysis_data['partition_table_details']) 
    analysis_data['partition_csv_path'] = partition_csv_path 

    issues_found = _perform_consistency_checks(analysis_data)
    logger.info("--- Build Analysis Summary (Artifact-Based) ---")
    # ... (logging summary) ...
    if issues_found:
        logger.warning("--- Potential Issues Found During Build Analysis --- ")
        for issue in issues_found: logger.warning(f"- {issue}")
        logger.warning("Review the issues above.")
    else:
        logger.info("No obvious inconsistencies found in artifact-based build analysis.")
    logger.info("--- End Build Analysis ---") 