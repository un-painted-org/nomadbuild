#!/usr/bin/env python3
# repro_builder.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
import os
import sys
import argparse
import subprocess
import logging
import logging.handlers
import time
import hashlib
from pathlib import Path

# --- Configuration ---
ENV_DIR_NAME = "build_env"
CONTAINER_APP_DIR = Path("/app")
ESP_MINER_REPO = "https://github.com/bitaxeorg/ESP-Miner.git"
LOG_FILE_NAME = "repro_build.log"

# --- Global Logger ---
logger = logging.getLogger("ReproBuilder")

# --- Helper Functions (Simplified/Adapted) ---

def get_env_dir() -> Path:
    env_dir = CONTAINER_APP_DIR / ENV_DIR_NAME
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
    env_dir = get_env_dir()
    repos_dir = env_dir / "repos"
    repo_path = repos_dir / repo_name
    logger.info(f"Checking repository: {repo_name} at {repo_path}")
    if not (repo_path.exists() and (repo_path / ".git").is_dir()):
        logger.info(f"Cloning {repo_name}...")
        run_command(["git", "clone", repo_url, str(repo_path)], capture_output=False, description="clone repo")
    else:
        logger.info(f"Updating existing clone...") 
        run_command(["git", "fetch", "--tags", "--force", "--prune"], cwd=repo_path, capture_output=False, description="fetch tags")
        # Careful with reset if local changes are ever intended
        # run_command(["git", "reset", "--hard", "origin/master"], cwd=repo_path, capture_output=False, description="reset master") 
        # run_command(["git", "pull"], cwd=repo_path, capture_output=False, description="pull")
        run_command(["git", "clean", "-fdx"], cwd=repo_path, capture_output=False, description="clean repo")
    return repo_path

def checkout_tag(repo_path: Path, tag: str):
    logger.info(f"Checking out tag {tag}...")
    run_command(["git", "checkout", f"tags/{tag}"], cwd=repo_path, capture_output=False, description="checkout tag")
    logger.info("Updating submodules...")
    run_command(["git", "submodule", "update", "--init", "--recursive"], cwd=repo_path, capture_output=False, description="update submodules")
    logger.info(f"Checked out {tag} successfully.")

def _get_commit_timestamp(repo_path: Path, tag: str) -> str | None:
    logger.debug(f"Getting commit timestamp for tag {tag}...")
    try:
        ts_str = run_command(["git", "log", "-1", "--pretty=%ct", tag], cwd=repo_path)
        if ts_str and ts_str.isdigit(): return ts_str
        logger.error(f"Could not parse commit timestamp for tag {tag}. Output: '{ts_str}'")
        return None
    except Exception as e: logger.error(f"Could not get commit timestamp for tag {tag}: {e}"); return None

def _run_idf_clean(miner_repo_path: Path):
    logger.info("Running idf.py fullclean...")
    run_command(["idf.py", "fullclean"], cwd=miner_repo_path, capture_output=False, env={"IDF_TARGET": "esp32s3"})
    logger.info("Clean completed.")

def _run_idf_build(miner_repo_path: Path, commit_timestamp: str) -> bool:
    logger.info("Running idf.py build...")
    build_env = os.environ.copy()
    build_env["IDF_TARGET"] = "esp32s3"
    build_env["SOURCE_DATE_EPOCH"] = commit_timestamp
    try:
        run_command(["idf.py", "build"], cwd=miner_repo_path, env=build_env, capture_output=False, check=True)
        logger.info("Build completed successfully.")
        return True
    except Exception: logger.error("Build failed."); return False

# Runs the merge_bin.sh script to create a generic merged binary.
def _run_merge_script(miner_repo_path: Path, output_filename: str) -> Path | None:
    logger.info(f"Generating Merged Binary: {output_filename}...")
    merge_script = miner_repo_path / "merge_bin.sh"
    output_path = miner_repo_path / "build" / output_filename 
    if not merge_script.exists(): logger.error(f"{merge_script.name} not found."); return None
    output_path.parent.mkdir(parents=True, exist_ok=True)
    merge_cmd = [str(merge_script), str(output_path)]
    try:
        run_command(["/bin/bash"] + merge_cmd, cwd=miner_repo_path, capture_output=False, check=True)
        if output_path.exists(): logger.info("Generated merged binary."); return output_path
        logger.error("Merge script ran but output file not found."); return None
    except Exception as e: logger.error(f"Error running merge script: {e}"); return None

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
def main():
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
    commit_timestamp = _get_commit_timestamp(miner_repo_path, args.tag)
    if not commit_timestamp: sys.exit("Failed to get commit timestamp.")
            
    hash_run1 = None; hash_run2 = None

    # --- Run 1 ---
    logger.info("--- Starting Build Run 1 --- ")
    _run_idf_clean(miner_repo_path)
    if not _run_idf_build(miner_repo_path, commit_timestamp): sys.exit("Build Run 1 Failed.")
    merged_path_1 = _run_merge_script(miner_repo_path, f"merged-{args.tag}-run1.bin")
    hash_run1 = _calculate_hash(merged_path_1)
    logger.info("--- Finished Build Run 1 --- ")

    # --- Run 2 ---
    logger.info("--- Starting Build Run 2 --- ")
    _run_idf_clean(miner_repo_path)
    # IMPORTANT: Need to ensure source state is identical, re-checkout or just rely on clean?
    # Re-checkout is safest to undo any potential build side effects not caught by clean
    checkout_tag(miner_repo_path, args.tag) 
    if not _run_idf_build(miner_repo_path, commit_timestamp): sys.exit("Build Run 2 Failed.")
    merged_path_2 = _run_merge_script(miner_repo_path, f"merged-{args.tag}-run2.bin")
    hash_run2 = _calculate_hash(merged_path_2)
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