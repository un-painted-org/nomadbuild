# git_ops.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
# Git operations (clone, fetch tags, checkout)
import logging
import re
import shutil
import os
import sys
import subprocess
from pathlib import Path
from typing import Callable, Optional

# Import necessary functions/classes from other modules
from .utils import run_command, get_env_dir # Import run_command and get_env_dir from utils

# Placeholder for logger - Will be configured properly in cli.py
logger = logging.getLogger(__name__)

# Constants
ESP_MINER_REPO = "https://github.com/bitaxeorg/ESP-Miner.git"
MAX_STABLE_TAGS_TO_SHOW = 5

# --- Functions moved from main script ---

def fetch_repo(repo_url_default: str, repo_name: str) -> Path:
    """Clones or updates a Git repository. Allows override via environment variable."""
    repo_url_override = os.environ.get("NOMADBUILD_ESP_MINER_REPO_URL")
    repo_url = repo_url_override if repo_url_override else repo_url_default
    
    if repo_url != repo_url_default:
        logger.info(f"Using overridden repository URL from environment: {repo_url}")
    else:
        logger.info(f"Using default repository URL: {repo_url}")
            
    logger.info(f"--- Preparing Source Code Repository via Git Clone: {repo_name} --- ")
    env_dir = get_env_dir()
    repo_base_dir = env_dir / "repos"
    target_repo_path = repo_base_dir / repo_name
    repo_base_dir.mkdir(parents=True, exist_ok=True)

    if not target_repo_path.exists() or not (target_repo_path / ".git").is_dir():
        if target_repo_path.exists():
             logger.warning(f"Target path {target_repo_path} exists but is not a valid Git repo. Removing for fresh clone.")
             shutil.rmtree(target_repo_path)
        logger.info(f"Repository {repo_name} not found or invalid. Cloning fresh copy...")
        run_command(["git", "clone", repo_url, str(target_repo_path)])
        logger.info(f"{repo_name} cloned to {target_repo_path}.")
    else:
        logger.info(f"Repository {repo_name} found at {target_repo_path}. Assuming usable, fetching updates...")
        try:
             run_command(["git", "fetch", "--prune", "--tags", "--force"], cwd=target_repo_path)
             logger.info("Git fetch completed.")
        except Exception as e:
             logger.error(f"Git fetch failed for {target_repo_path}: {e}. Build might use stale data.")

    return target_repo_path

def get_esp_miner_stable_tags(repo_path: Path) -> list[str]:
    logger.info(f"[GIT] Fetching tags from {repo_path}...")
    run_command(["git", "fetch", "--tags", "--force"], cwd=repo_path)
    logger.debug("[GIT] Getting available tags...")
    tag_output = run_command(["git", "tag", "-l"], cwd=repo_path, capture_output=True)
    all_tags = tag_output.splitlines() if tag_output else []
    stable_tag_pattern = re.compile(r"^v\d+\.\d+\.\d+$")
    stable_tags = sorted([tag for tag in all_tags if stable_tag_pattern.match(tag)], reverse=True)
    limited_tags = stable_tags[:MAX_STABLE_TAGS_TO_SHOW]
    logger.info(f"[GIT] Found latest {len(limited_tags)} stable tags (of {len(stable_tags)} total stable): {limited_tags}")
    if not limited_tags: logger.warning("[GIT] No stable release tags found matching pattern vX.Y.Z")
    return limited_tags

def checkout_tag(repo_path: Path, tag: str, progress_callback: Callable[[int, str], None] | None = None) -> str | None:
    """Checks out a specific git tag and returns the commit hash."""
    logger.info(f"[GIT] Checking out tag '{tag}' in {repo_path}...")
    if not tag:
        logger.error("[GIT] Cannot checkout: Tag is empty.")
        return None
    try:
        # Fetch tags first to ensure we have the latest, handle potential interruptions
        fetch_cmd = ["git", "fetch", "--tags", "--force"]
        logger.debug(f"[GIT] Executing: {' '.join(fetch_cmd)}")
        run_command(fetch_cmd, cwd=repo_path, check=True) # Use check=True to raise on error
        logger.info("[GIT] Fetched tags.")
        if progress_callback: progress_callback(7, "Fetched latest tags.")
        
        # Check if the tag exists locally now
        check_tag_cmd = ["git", "tag", "-l", tag]
        logger.debug(f"[GIT] Executing: {' '.join(check_tag_cmd)}")
        tag_exists_output = run_command(check_tag_cmd, cwd=repo_path, capture_output=True)
        if not tag_exists_output or tag not in tag_exists_output.split():
             logger.error(f"[GIT] Tag '{tag}' not found in repository after fetch.")
             if progress_callback: progress_callback(7, f"Error: Tag '{tag}' not found.")
             return None

        # Checkout the specific tag
        checkout_cmd = ["git", "checkout", f"tags/{tag}"]
        logger.debug(f"[GIT] Executing: {' '.join(checkout_cmd)}")
        run_command(checkout_cmd, cwd=repo_path, check=True) # Use check=True
        logger.info(f"[GIT] Successfully checked out tag '{tag}'.")
        if progress_callback: progress_callback(10, f"Checked out tag '{tag}'.")

        # Get the commit hash for the checked-out tag
        hash_cmd = ["git", "rev-parse", "HEAD"]
        logger.debug(f"[GIT] Executing: {' '.join(hash_cmd)}")
        commit_hash = run_command(hash_cmd, cwd=repo_path, capture_output=True)
        
        if commit_hash:
            commit_hash = commit_hash.strip() # Ensure no extra whitespace
            logger.info(f"[GIT] Current HEAD commit hash: {commit_hash}")
            return commit_hash # Return the commit hash on success
        else:
             logger.error("[GIT] Failed to get commit hash after checkout.")
             return None

    except subprocess.CalledProcessError as e:
        stderr_output = e.stderr.strip() if e.stderr else "No stderr"
        logger.error(f"[GIT] Error during tag checkout ('{tag}'): {e}. Stderr: {stderr_output}")
        if progress_callback: progress_callback(10, f"Error checking out tag: {stderr_output}")
        return None
    except FileNotFoundError:
        logger.error(f"[GIT] Error: 'git' command not found. Is Git installed and in PATH?")
        return None
    except InterruptedError: # Catch potential cancellation during run_command
         logger.warning(f"[GIT] Git operation interrupted during checkout of tag '{tag}'.")
         # Should we raise this or return None? Returning None seems consistent.
         return None
    except Exception as e:
        logger.exception(f"[GIT] An unexpected error occurred during checkout of tag '{tag}': {e}")
        return None

    # This part should ideally not be reached if the logic above is correct
    logger.error(f"[GIT] Reached end of checkout_tag for '{tag}' without returning hash or error.")
    return None

# --- Moved function from web_ui.py ---

def ensure_clean_repo_for_build(repo_path: Path | None = None, force_deep_clean=False):
    """Cleans the Git repository before a build.

    Args:
        repo_path: Path to the repository to clean. If *None*, this helper will
            resolve the default ESP-Miner repo location inside the build
            environment directory (``$ENV_DIR/repos/ESP-Miner``). This keeps
            backward-compatibility with older call-sites that invoked the
            function without explicitly passing the path.
        force_deep_clean: Whether to perform additional cleanup such as
            removing ``sdkconfig`` or other artefacts.
    """

    # If the caller did not specify a path, fall back to the canonical one so
    # that legacy call-sites (e.g. WebUI) keep working.
    if repo_path is None:
        try:
            env_dir = get_env_dir()
            repo_path = env_dir / "repos" / "ESP-Miner"
        except Exception:
            # If even determining the env dir fails, log and bail out.
            logger.error("Could not determine default repo path for cleaning; aborting ensure_clean_repo_for_build.")
            return False

    # Logger is already defined at module level
    logger.info(f"Ensuring clean repository state at {repo_path}")
    try:
        # Reset any uncommitted changes first
        # Use the imported builder_utils correctly
        run_command(["git", "reset", "--hard", "HEAD"], cwd=repo_path)

        # Clean untracked files and directories (-fdx)
        clean_cmd = ["git", "clean", "-fdx"]
        if (repo_path / 'vendors').exists():
             clean_cmd.append("--exclude=vendors/")
        run_command(clean_cmd, cwd=repo_path)

        # Optionally perform a deeper clean
        if force_deep_clean:
            sdkconfig_path = repo_path / 'sdkconfig'
            if sdkconfig_path.exists():
                try:
                    sdkconfig_path.unlink()
                    logger.info("Removed existing sdkconfig file.")
                except OSError as e_unlink:
                    logger.warning(f"Could not remove sdkconfig during deep clean: {e_unlink}")
            # Add more deep clean steps if needed

        # Checkout main/master branch first to ensure we're not starting from a tag detached head
        checked_out_default = False
        for branch in ["main", "master"]:
             try:
                 run_command(["git", "checkout", branch], cwd=repo_path)
                 run_command(["git", "pull"], cwd=repo_path) # Pull latest changes
                 checked_out_default = True
                 logger.info(f"Checked out and pulled default branch '{branch}'.")
                 break
             except Exception:
                 logger.debug(f"Could not checkout/pull branch '{branch}'.")
        if not checked_out_default:
             logger.warning("Could not checkout 'main' or 'master'. Continuing with current branch.")

        # Force-delete any existing version.txt file to ensure it's recreated by build
        version_file = repo_path / "version.txt"
        if version_file.exists():
            try:
                version_file.unlink()
                logger.info("Removed existing version.txt file before build.")
            except OSError as e:
                logger.warning(f"Could not remove existing version.txt: {e}")

        logger.info("Repository cleaned successfully.")
        return True

    except Exception as e:
        logger.exception(f"Error during repository cleanup: {e}")
        return False 