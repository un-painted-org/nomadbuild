#!/usr/bin/env python3
# repro_builder.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
# Reproducible build checker for ESP-Miner
import os
import sys
import argparse
import subprocess
import logging
import logging.handlers
import time
import hashlib
import shutil
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any

# --- Configuration ---
ENV_DIR_NAME = "build_env"
CONTAINER_APP_DIR = Path("/app")
CONTAINER_ONLY_DIR = Path("/container_only")
ESP_MINER_REPO = "https://github.com/bitaxeorg/ESP-Miner.git"
LOG_FILE_NAME = "repro_build.log"

# Define the path to the correct Python interpreter for ESP-IDF builds
ESP_IDF_PYTHON = "/opt/esp/python_env/idf5.4_py3.12_env/bin/python"
# Define the full path to the idf.py script
IDF_PY_SCRIPT = "/opt/esp/idf/tools/idf.py"

# --- Global Logger ---
logger = logging.getLogger("ReproBuilder")

# --- Helper Functions (Simplified/Adapted) ---

def get_env_dir() -> Path:
    # Use /container_only instead of /app to ensure it's not mounted to the host
    container_only_dir = CONTAINER_ONLY_DIR

    # Create the container_only directory if it doesn't exist
    if not container_only_dir.exists():
        container_only_dir.mkdir(parents=True, exist_ok=True)

    # Create the build environment directory inside the container_only directory
    env_dir = container_only_dir / ENV_DIR_NAME
    return env_dir

def setup_environment():
    env_dir = get_env_dir()
    log_dir = env_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (env_dir / "repos").mkdir(exist_ok=True)
    logger.debug(f"Using build environment directory: {env_dir}")

def run_command(cmd_list, cwd=None, env=None, capture_output=True, check=True, description=None):
    log_desc = f" ({description})" if description else ""
    logger.debug(f"Running command{log_desc}: {' '.join(cmd_list)} {'in ' + str(cwd) if cwd else ''}")
    try:
        process_env = os.environ.copy()
        if env: process_env.update(env)
        stdout_setting = subprocess.PIPE if capture_output else subprocess.DEVNULL
        stderr_setting = subprocess.PIPE if capture_output else subprocess.DEVNULL
        process = subprocess.run(cmd_list, check=check, cwd=cwd, env=process_env, text=True, stdout=stdout_setting, stderr=stderr_setting)
        stdout_content = process.stdout.strip() if process.stdout else ""
        stderr_content = process.stderr.strip() if process.stderr else ""
        if stdout_content: logger.debug(f"Captured Stdout{log_desc}:\n{stdout_content[:500]}...")
        if stderr_content: logger.debug(f"Captured Stderr{log_desc}:\n{stderr_content[:500]}...")
        logger.debug(f"Command finished successfully: {' '.join(cmd_list)}")
        return stdout_content if capture_output else None
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running command: {' '.join(cmd_list)}")
        logger.error(f"Exit Code: {e.returncode}")
        stdout_content = e.stdout.strip() if e.stdout else "<no stdout>"
        stderr_content = e.stderr.strip() if e.stderr else "<no stderr>"
        logger.error(f"Stdout:\n{stdout_content}")
        logger.error(f"Stderr:\n{stderr_content}")
        logger.critical(f"Command failed. Check log file.")
        sys.exit(f"Command failed with exit code {e.returncode}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred running {' '.join(cmd_list)}: {e}")
        sys.exit(1)

def fetch_repo(repo_url: str, repo_name: str) -> Path:
    """Fetches or updates a Git repository."""
    env_dir = get_env_dir()
    repos_dir = env_dir / "repos"
    repo_path = repos_dir / repo_name

    logger.info(f"Checking repository: {repo_name} at {repo_path}")

    try:
        if not (repo_path.exists() and (repo_path / ".git").is_dir()):
            # Clone the repository
            logger.info(f"Cloning {repo_name}...")
            clone_cmd = ["git", "clone", repo_url, str(repo_path)]
            logger.debug(f"Executing: {' '.join(clone_cmd)}")

            process = subprocess.run(
                clone_cmd,
                env=os.environ.copy(),
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        else:
            # Update the existing repository
            logger.info(f"Updating existing clone...")

            # Fetch tags
            fetch_cmd = ["git", "fetch", "--tags", "--force", "--prune"]
            logger.debug(f"Executing: {' '.join(fetch_cmd)} in {repo_path}")

            process = subprocess.run(
                fetch_cmd,
                cwd=repo_path,
                env=os.environ.copy(),
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Clean the repository
            clean_cmd = ["git", "clean", "-fdx"]
            logger.debug(f"Executing: {' '.join(clean_cmd)} in {repo_path}")

            process = subprocess.run(
                clean_cmd,
                cwd=repo_path,
                env=os.environ.copy(),
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

        return repo_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed with exit code {e.returncode}")
        if e.stderr:
            logger.error(f"Git stderr: {e.stderr[:500]}...")
        raise RuntimeError(f"Failed to fetch repository {repo_name}")
    except Exception as e:
        logger.error(f"Unexpected error during repository fetch: {e}")
        raise RuntimeError(f"Failed to fetch repository {repo_name}")

def checkout_tag(repo_path: Path, tag: str):
    """Checks out a specific tag in the repository and updates submodules."""
    logger.info(f"Checking out tag {tag}...")

    try:
        # Checkout the tag
        checkout_cmd = ["git", "checkout", f"tags/{tag}"]
        logger.debug(f"Executing: {' '.join(checkout_cmd)} in {repo_path}")

        process = subprocess.run(
            checkout_cmd,
            cwd=repo_path,
            env=os.environ.copy(),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Update submodules
        logger.info("Updating submodules...")
        submodule_cmd = ["git", "submodule", "update", "--init", "--recursive"]
        logger.debug(f"Executing: {' '.join(submodule_cmd)} in {repo_path}")

        process = subprocess.run(
            submodule_cmd,
            cwd=repo_path,
            env=os.environ.copy(),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        logger.info(f"Checked out {tag} successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed with exit code {e.returncode}")
        if e.stderr:
            logger.error(f"Git stderr: {e.stderr[:500]}...")
        raise RuntimeError(f"Failed to checkout tag {tag}")
    except Exception as e:
        logger.error(f"Unexpected error during checkout: {e}")
        raise RuntimeError(f"Failed to checkout tag {tag}")

def _get_commit_timestamp(repo_path: Path, tag: str) -> str | None:
    """Gets the commit timestamp for a specific tag."""
    logger.debug(f"Getting commit timestamp for tag {tag}...")

    try:
        # Get the commit timestamp
        command = ["git", "log", "-1", "--pretty=%ct", tag]
        logger.debug(f"Executing: {' '.join(command)} in {repo_path}")

        process = subprocess.run(
            command,
            cwd=repo_path,
            env=os.environ.copy(),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        ts_str = process.stdout.strip()

        if ts_str and ts_str.isdigit():
            return ts_str

        logger.error(f"Could not parse commit timestamp for tag {tag}. Output: '{ts_str}'")
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed with exit code {e.returncode}")
        if e.stderr:
            logger.error(f"Git stderr: {e.stderr[:500]}...")
        return None
    except Exception as e:
        logger.error(f"Could not get commit timestamp for tag {tag}: {e}")
        return None

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
    command = [ESP_IDF_PYTHON, IDF_PY_SCRIPT, "fullclean"]
    logger.info(f"Executing: {' '.join(command)} in {miner_repo_path}")

    try:
        # Use subprocess.run directly for better control
        process = subprocess.run(
            command,
            cwd=miner_repo_path,
            env=idf_env,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logger.info("Clean completed successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Clean failed with exit code {e.returncode}")
        if e.stderr:
            logger.error(f"Clean stderr: {e.stderr[:500]}...")
        raise RuntimeError(f"idf.py fullclean failed with exit code {e.returncode}")
    except Exception as e:
        logger.error(f"Clean failed with exception: {e}")
        raise RuntimeError(f"Unexpected error during clean: {e}")



def _run_idf_build(miner_repo_path: Path, commit_timestamp: str) -> bool:
    """Runs the IDF build command using the correct Python interpreter and IDF script."""
    logger.info("Running idf.py build...")

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
    build_env["IDF_TARGET"] = "esp32s3"
    build_env["SOURCE_DATE_EPOCH"] = commit_timestamp

    # Execute idf.py build using the ESP-IDF Python interpreter for deterministic environment
    command = [ESP_IDF_PYTHON, IDF_PY_SCRIPT, "build"]
    logger.info(f"Executing: {' '.join(command)} in {miner_repo_path}")

    # Log relevant env vars being used by the subprocess
    logger.info(f"  Env (Selected): {{'IDF_TARGET': '{build_env.get('IDF_TARGET')}', 'SOURCE_DATE_EPOCH': '{build_env.get('SOURCE_DATE_EPOCH', 'N/A')}'}}")

    try:
        # Use subprocess.run directly for better control
        process = subprocess.run(
            command,
            cwd=miner_repo_path,
            env=build_env,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logger.info("Build completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Build failed with exit code {e.returncode}")
        if e.stdout:
            logger.debug(f"Build stdout: {e.stdout[:500]}...")
        if e.stderr:
            logger.error(f"Build stderr: {e.stderr[:500]}...")
        return False
    except Exception as e:
        logger.error(f"Build failed with exception: {e}")
        return False

# Runs the merge_bin.sh script to create a generic merged binary.
def _run_merge_script(miner_repo_path: Path, output_filename: str) -> Path | None:
    """Runs the merge_bin.sh script to create a generic merged binary."""
    logger.info(f"Generating Merged Binary: {output_filename}...")
    merge_script = miner_repo_path / "merge_bin.sh"
    output_path = miner_repo_path / "build" / output_filename

    if not merge_script.exists():
        logger.error(f"{merge_script.name} not found.")
        return None

    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = ["/bin/bash", str(merge_script), str(output_path)]

    try:
        # Use subprocess.run directly for better control
        process = subprocess.run(
            command,
            cwd=miner_repo_path,
            env=os.environ.copy(),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if output_path.exists():
            logger.info("Generated merged binary.")
            return output_path

        logger.error("Merge script ran but output file not found.")
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"Merge script failed with exit code {e.returncode}")
        if e.stderr:
            logger.error(f"Merge script stderr: {e.stderr[:500]}...")
        return None
    except Exception as e:
        logger.error(f"Error running merge script: {e}")
        return None

# Calculates SHA256 hash for a single file path.
def _calculate_hash(image_path: Path | None) -> str | None:
    if not image_path or not image_path.exists(): logger.warning(f"File not found for hashing: {image_path}"); return None
    logger.info(f"Calculating SHA256 hash for {image_path.name}...")
    hasher = hashlib.sha256(); buffer_size = 65536
    try:
        with open(image_path, 'rb') as f:
            while chunk := f.read(buffer_size): hasher.update(chunk)
        hex_digest = hasher.hexdigest()
        logger.debug(f"  - Hash: {hex_digest}")
        return hex_digest
    except Exception as e: logger.error(f"Error hashing {image_path}: {e}"); return None

def _setup_logging(args: argparse.Namespace):
    log_dir = get_env_dir() / "logs"; log_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = log_dir / LOG_FILE_NAME
    log_level_file = getattr(logging, args.log_level.upper(), logging.DEBUG)
    log_level_console = logging.WARNING if args.quiet else logging.INFO
    logger.setLevel(logging.DEBUG)
    for handler in logger.handlers[:]: logger.removeHandler(handler); handler.close()
    fh = logging.FileHandler(log_file_path, mode='w')
    fh.setLevel(log_level_file); fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')); logger.addHandler(fh)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(log_level_console); ch.setFormatter(logging.Formatter('%(levelname)s: %(message)s')); logger.addHandler(ch)
    logger.info(f"Logging initialized. Log file: {log_file_path}")

# --- Main Logic ---
def main(args=None):
    if args is None:
        parser = argparse.ArgumentParser(description="Bitaxe Reproducible Build Checker (Internal)")
        parser.add_argument("--tag", required=True, help="ESP-Miner git tag to build and check.")
        parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Log level for file.")
        parser.add_argument("-q", "--quiet", action="store_true", help="Suppress INFO on console.")
        args = parser.parse_args()

    _setup_logging(args)
    setup_environment()

    logger.info(f"--- Starting Internal Reproducibility Check for Tag: {args.tag} ---")

    miner_repo_path = fetch_repo(ESP_MINER_REPO, "ESP-Miner")
    # Prepare source only once (checkout)
    checkout_tag(miner_repo_path, args.tag)

    # --- Repro Hardening: verify clean tree & canonicalize mtimes ---
    # 1) Abort if the upstream repo is dirty (should never happen in CI)
    try:
        logger.info("Checking if repository is clean...")
        status_cmd = ["git", "status", "--porcelain"]
        logger.debug(f"Executing: {' '.join(status_cmd)} in {miner_repo_path}")

        process = subprocess.run(
            status_cmd,
            cwd=miner_repo_path,
            env=os.environ.copy(),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        dirty_status = process.stdout.strip()
        if dirty_status:
            logger.error("Upstream repository has uncommitted changes; aborting for reproducibility.")
            logger.error(f"Git status output: {dirty_status}")
            sys.exit(1)

        # 2) Ensure all file mtimes equal the commit timestamp (SOURCE_DATE_EPOCH)
        logger.info("Normalizing file timestamps...")
        commit_ts_cmd = ["bash", "-c", "find . -exec touch -hcd @$(git log -1 --pretty=%ct) {} +"]
        logger.debug(f"Executing: {commit_ts_cmd} in {miner_repo_path}")

        process = subprocess.run(
            commit_ts_cmd,
            cwd=miner_repo_path,
            env=os.environ.copy(),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}")
        if e.stderr:
            logger.error(f"Command stderr: {e.stderr[:500]}...")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during repository check: {e}")
        sys.exit(1)

    commit_timestamp = _get_commit_timestamp(miner_repo_path, args.tag)
    if not commit_timestamp: sys.exit("Failed to get commit timestamp.")

    hash_run1 = None; hash_run2 = None

    # --- Run 1 ---
    logger.info("--- Starting Build Run 1 --- ")
    _run_idf_clean(miner_repo_path)
    if not _run_idf_build(miner_repo_path, commit_timestamp): sys.exit("Build Run 1 Failed.")
    merged_path_1 = _run_merge_script(miner_repo_path, f"merged-{args.tag}-run1.bin")
    hash_run1 = _calculate_hash(merged_path_1)

    # Copy the binary file to the firmware directory for easier access
    firmware_dir = Path("/app/firmware")
    firmware_dir.mkdir(parents=True, exist_ok=True)
    if merged_path_1 and merged_path_1.exists():
        firmware_path_1 = firmware_dir / f"merged-{args.tag}-run1.bin"
        logger.info(f"Copying binary file to {firmware_path_1}")
        shutil.copy2(merged_path_1, firmware_path_1)

    logger.info("--- Finished Build Run 1 --- ")

    # --- Run 2 ---
    logger.info("--- Starting Build Run 2 --- ")
    _run_idf_clean(miner_repo_path)
    # IMPORTANT: Need to ensure source state is identical, re-checkout or just rely on clean?
    # Re-checkout is safest to undo any potential build side effects not caught by clean
    # Add extra git clean for good measure before checkout
    logger.info("Cleaning source tree again before Run 2 checkout...")
    try:
        clean_cmd = ["git", "clean", "-fdx"]
        logger.debug(f"Executing: {' '.join(clean_cmd)} in {miner_repo_path}")

        process = subprocess.run(
            clean_cmd,
            cwd=miner_repo_path,
            env=os.environ.copy(),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Git clean failed with exit code {e.returncode}")
        if e.stderr:
            logger.error(f"Git clean stderr: {e.stderr[:500]}...")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during git clean: {e}")
        sys.exit(1)

    checkout_tag(miner_repo_path, args.tag)
    # Also re-normalize timestamps after checkout for Run 2
    logger.info("Normalizing file timestamps again before Run 2 build...")
    try:
        commit_ts_cmd = ["bash", "-c", "find . -exec touch -hcd @$(git log -1 --pretty=%ct) {} +"]
        logger.debug(f"Executing: {commit_ts_cmd} in {miner_repo_path}")

        process = subprocess.run(
            commit_ts_cmd,
            cwd=miner_repo_path,
            env=os.environ.copy(),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to normalize timestamps with exit code {e.returncode}")
        if e.stderr:
            logger.error(f"Command stderr: {e.stderr[:500]}...")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during timestamp normalization: {e}")
        sys.exit(1)

    # Run the build again with the same timestamp
    if not _run_idf_build(miner_repo_path, commit_timestamp): sys.exit("Build Run 2 Failed.")
    merged_path_2 = _run_merge_script(miner_repo_path, f"merged-{args.tag}-run2.bin")
    hash_run2 = _calculate_hash(merged_path_2)

    # Copy the binary file to the firmware directory for easier access
    if merged_path_2 and merged_path_2.exists():
        firmware_path_2 = firmware_dir / f"merged-{args.tag}-run2.bin"
        logger.info(f"Copying binary file to {firmware_path_2}")
        shutil.copy2(merged_path_2, firmware_path_2)

    logger.info("--- Finished Build Run 2 --- ")

    # --- Comparison ---
    logger.info("--- Comparing Build Outputs (Merged Binary Hash) --- ")
    reproducible = False
    if hash_run1 is None or hash_run2 is None: logger.error("Cannot compare: Hash missing from one or both runs.")
    elif hash_run1 == hash_run2: logger.info(f"MATCH: Merged Binary Hash: {hash_run1}"); reproducible = True
    else: logger.warning(f"MISMATCH: Merged Binary - Run 1: {hash_run1} | Run 2: {hash_run2}")

    # --- Final Result ---
    logger.info("--- Reproducibility Check Result ---")
    if reproducible: logger.info("SUCCESS: Build is reproducible!"); print("RESULT: Reproducible"); sys.exit(0)
    else: logger.error(f"FAILURE: Build is NOT reproducible."); print("RESULT: Not Reproducible"); sys.exit(1)

if __name__ == "__main__":
    main()