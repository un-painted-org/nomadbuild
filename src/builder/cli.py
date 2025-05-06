# cli.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
# Command-line interface logic
import logging
import argparse
import sys
import platform
import os # Needed for path joining
import json
import subprocess

# Import functions from other builder modules
from .utils import setup_environment, get_env_dir, LOG_FILE_NAME, CONTAINER_OUTPUT_DIR, BUILD_INFO_FILE # Added constants
from pathlib import Path

# Constants
CONTAINER_APP_DIR = Path("/app")
# Import the specific function we need
from .utils import copy_artifacts_to_output, create_and_save_build_info
# Adjusted import to include the moved function
from . import git_ops as builder_git
from .git_ops import fetch_repo, get_esp_miner_stable_tags, ESP_MINER_REPO, ensure_clean_repo_for_build
from .build import build_esp_miner, analyze_build_output
from .device import _handle_flashing, load_models_config # Import from correct module

# Logger setup: Get the root logger
# Basic config will be overridden in _setup_logging
logging.basicConfig()
# Get the root logger instead of a module-specific one
logger = logging.getLogger() # <-- Get root logger

# --- Functions moved/adapted from main script ---

def _handle_build_or_use_existing(args: argparse.Namespace) -> tuple[str | None, str | None, bool | None, str | None]:
    """Handles logic to either perform a build or use existing artifacts based on args."""
    logger.info("--- Determining Build Action --- ")
    build_info_path = CONTAINER_OUTPUT_DIR / BUILD_INFO_FILE
    selected_tag = args.tag
    expected_version = None
    miner_repo_path = None
    is_custom_repo = False
    custom_repo_url = None
    perform_build = False

    # Determine if a build needs to be performed
    if args.tag or args.force_rebuild:
        perform_build = True
        selected_tag = args.tag
    else:
        logger.info("No specific tag or force-rebuild requested. Checking for existing build info...")
        if build_info_path.exists():
            try:
                with open(build_info_path, 'r') as f:
                    build_info = json.load(f)
                    selected_tag = build_info.get('tag')
                    expected_version = build_info.get('version')
                    if selected_tag and expected_version:
                        logger.info(f"Found existing build info. Will use Tag: '{selected_tag}', Version: '{expected_version}'")
                        perform_build = False
                    else:
                        logger.warning("Existing build_info.json is incomplete. Proceeding to build latest stable tag.")
                        perform_build = True
                        selected_tag = None
            except Exception as e:
                logger.warning(f"Error reading existing build_info.json ({build_info_path}): {e}. Proceeding to build latest stable tag.")
                perform_build = True
                selected_tag = None
        else:
            logger.info("No existing build info found. Proceeding to build the latest stable tag.")
            perform_build = True
            selected_tag = None

    # --- Perform Build OR Load Info ---
    if perform_build:
        logger.info("--- Build Process Required --- ")
        logger.info("Fetching Source Code...")
        miner_repo_path, is_custom_repo, custom_repo_url = builder_git.fetch_repo(ESP_MINER_REPO, "ESP-Miner")
        logger.debug(f"fetch_repo returned: is_custom_repo={is_custom_repo}, custom_repo_url={custom_repo_url}")

        # Print the environment variable for debugging
        env_var = os.environ.get("NOMADBUILD_ESP_MINER_REPO_URL")
        logger.debug(f"NOMADBUILD_ESP_MINER_REPO_URL environment variable: {env_var}")

        if not selected_tag:
            logger.info("Determining latest stable tag...")
            stable_tags = builder_git.get_esp_miner_stable_tags(miner_repo_path)
            if not stable_tags:
                logger.critical("Build failed: No stable tags available and none specified.")
                sys.exit("Build failed: No stable tags available.")
            selected_tag = stable_tags[0]
            logger.info(f"Building latest stable tag: {selected_tag}")
        else:
            logger.info(f"Verifying specified tag: {selected_tag}")
            # Verify that the specified tag exists before attempting to build
            if not builder_git.verify_tag_exists(miner_repo_path, selected_tag):
                # Get available tags to suggest alternatives
                stable_tags = builder_git.get_esp_miner_stable_tags(miner_repo_path)

                # Construct error message with suggestions
                error_msg = f"Tag '{selected_tag}' does not exist in the repository."
                if stable_tags:
                    suggestions = ", ".join(stable_tags[:5])
                    error_msg += f" Available stable tags include: {suggestions}"

                logger.critical(f"Build failed: {error_msg}")
                sys.exit(f"Build failed: {error_msg}")

            logger.info(f"Tag '{selected_tag}' verified. Proceeding with build.")

        logger.info("Cleaning repository before build...")
        # Ensure clean state for the build
        if not ensure_clean_repo_for_build(miner_repo_path):
             logger.warning("Repository cleaning failed, proceeding with caution.")
        else:
             logger.info("Repository cleaned successfully.")

        logger.info("\n--- Starting Build Phase --- ")
        # build_esp_miner now returns: (build_dir, commit_hash, partition_csv_path, flasher_args_path, expected_version)
        verbose_build = getattr(args, 'verbose_build', False)  # Default to False if attribute doesn't exist
        build_dir, commit_hash, partition_csv_path, flasher_args_path, expected_version = build_esp_miner(miner_repo_path, selected_tag, verbose_build)

        # Check if build was cancelled (indicated by None return values)
        if build_dir is None: # Check the first element which should be Path or None
            logger.warning("Build was cancelled or failed upstream. Aborting build handling.")
            # Exit or raise? Let's exit cleanly if cancelled, maybe raise otherwise?
            # For now, assuming None means cancellation.
            sys.exit("Build process cancelled or failed.")

        # Validate required paths after successful build
        if not all([build_dir, partition_csv_path, flasher_args_path, expected_version]):
            logger.critical("Build result tuple missing expected values after successful build.")
            sys.exit("Build failed due to incomplete build results.")

        logger.info(f"Build successful for tag {selected_tag}. Expected version: {expected_version}")
        # Pass the correct build_dir (Path object) to analyze_build_output
        analyze_build_output(build_dir, flasher_args_path, partition_csv_path)

        logger.info("Copying build artifacts to output directory...")
        copied_artifact_paths = copy_artifacts_to_output(
            firmware_build_path=build_dir, # Pass the correct build_dir
            built_tag=selected_tag,
            expected_version=expected_version
        )
        if not copied_artifact_paths:
            logger.error("No build artifacts were successfully copied. Cannot proceed.")
            sys.exit("Build artifact copying failed.")

        logger.info("Creating build information file...")
        logger.debug(f"Calling create_and_save_build_info with is_custom_repo={is_custom_repo}, custom_repo_url={custom_repo_url}")
        try:
            build_info = create_and_save_build_info(
                copied_artifact_paths=copied_artifact_paths,
                built_tag=selected_tag,
                expected_version=expected_version,
                output_dir=CONTAINER_OUTPUT_DIR,
                is_custom_repo=is_custom_repo,
                custom_repo_url=custom_repo_url
            )
        except ValueError as e:
            logger.critical(f"Failed to create build information file: {e}")
            sys.exit(f"Build failed: {e}")
        except Exception as e:
            logger.critical(f"Unexpected error creating build information file: {e}")
            sys.exit(f"Build failed due to unexpected error: {e}")
        if not build_info:
            logger.error("Failed to create or save build information.")
            sys.exit("Build information creation failed.")
        else:
            logger.info(f"Build information saved successfully for version {build_info.get('version', 'N/A')}.")
            logger.debug(f"Build Info Contents: {build_info}")

        # Add a clear completion message
        logger.info("")
        logger.info("--- Build Process Complete ---")

    else: # Not performing build, using existing info loaded earlier
        logger.info(f"Using existing build artifacts for Tag: {selected_tag}, Version: {expected_version}")
        # No action needed here, vars selected_tag and expected_version are already set

    # --- Final Check & Return ---
    if not selected_tag or not expected_version:
        # After fallback logic, we must have determined the build target
        logger.critical(f"Internal logic error: Could not determine selected tag ({selected_tag}) or expected version ({expected_version}). Aborting.")
        sys.exit("Failed to establish build target due to internal logic error.")
    return selected_tag, expected_version, is_custom_repo, custom_repo_url

def _parse_arguments():
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(description="NomadBuild Local Builder & Flasher (Containerized CLI)")
    parser.add_argument("--tag", help="Specific ESP-Miner git tag to build")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress INFO messages in console output")
    parser.add_argument("--log-level", default="DEBUG", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Set file logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    parser.add_argument("--force-rebuild", action="store_true", help="Force rebuild even if artifacts exist")


    # Create a mutually exclusive group for flash targets
    flash_group = parser.add_mutually_exclusive_group()
    flash_group.add_argument("--flash-ip", help="IP address of a single device to flash")
    flash_group.add_argument("--flash-csv", help="Path to CSV file containing IP addresses of devices to flash (one per line)")

    parser.add_argument("--skip-firmware", action="store_true", help="Skip flashing main firmware during update")
    parser.add_argument("--skip-www", action="store_true", help="Skip flashing web UI during update")
    parser.add_argument("--force-flash", action="store_true", help="Force flashing without confirmation for each device")
    parser.add_argument("--verbose-build", action="store_true", help="Stream idf.py output during build process")
    # Add reproducibility command options
    parser.add_argument("--repro", action="store_true", help="Run reproducibility check for a specific tag")
    return parser.parse_args()

def _setup_logging(args: argparse.Namespace):
    """Configures file and console logging for the root logger based on arguments."""
    from .color_formatter import ColoredFormatter

    log_dir = get_env_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = log_dir / LOG_FILE_NAME
    log_level_file = getattr(logging, args.log_level.upper(), logging.DEBUG)
    log_level_console = logging.WARNING if args.quiet else logging.INFO

    # Configure the root logger
    root_logger = logging.getLogger() # Get root logger again just to be explicit
    root_logger.setLevel(logging.DEBUG) # Set lowest level to capture everything initially

    # Remove existing handlers attached to the root logger (e.g., from basicConfig)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()

    # File Handler
    fh = logging.FileHandler(log_file_path, mode='w')
    fh.setLevel(log_level_file)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s') # Include logger name in file
    fh.setFormatter(file_formatter)
    root_logger.addHandler(fh)

    # Console Handler with colored output
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(log_level_console)
    console_formatter = ColoredFormatter('%(levelname)s: %(message)s') # Colored formatter
    ch.setFormatter(console_formatter)
    root_logger.addHandler(ch)

    # Log the completion message using the configured root logger
    root_logger.debug(f"Root logger setup complete. File Level: {logging.getLevelName(log_level_file)}, Console Level: {logging.getLevelName(log_level_console)}")

def _handle_reproducibility_check(args: argparse.Namespace):
    """Handles reproducibility check logic."""
    if not args.tag:
        logger.error("Reproducibility check requires a tag. Use --tag <VERSION>")
        sys.exit(1)

    logger.info(f"Running reproducibility check for tag: {args.tag}")

    # Call the run_repro_check.sh script
    run_repro_script_path = CONTAINER_APP_DIR / "scripts" / "run_repro_check.sh"
    if not run_repro_script_path.exists():
        logger.error(f"Reproducibility check script not found at {run_repro_script_path}")
        sys.exit(1)

    # Make sure the script is executable
    try:
        os.chmod(run_repro_script_path, 0o755)
    except Exception as e:
        logger.warning(f"Could not make script executable: {e}")

    # Use run_command from utils to run the script
    from .utils import run_command

    cmd = ["/bin/bash", str(run_repro_script_path), "--tag", args.tag]

    try:
        logger.info("Starting reproducibility check...")
        # Set check=False to handle the exit code ourselves
        result = run_command(cmd, check=False, stream_output=True)

        # Check the exit code
        if result is None or result.returncode != 0:
            logger.error(f"Reproducibility check failed with exit code {result.returncode if result else 'unknown'}")
            sys.exit(result.returncode if result else 1)
        else:
            logger.info("Reproducibility check completed successfully.")
    except Exception as e:
        logger.error(f"Error running reproducibility check: {e}")
        sys.exit(1)



def _display_build_summary(selected_tag, expected_version, args, is_custom_repo=False, custom_repo_url=None):
    """Displays a user-friendly summary of the build results."""
    from .color_formatter import Colors

    # Always show build summary, regardless of whether flashing is requested

    # Get the output directory
    output_dir = CONTAINER_OUTPUT_DIR

    # Check if build_info.json exists
    build_info_path = output_dir / BUILD_INFO_FILE
    build_info = None
    if build_info_path.exists():
        try:
            with open(build_info_path, 'r') as f:
                build_info = json.load(f)
        except Exception as e:
            logger.debug(f"Could not read build info: {e}")

    # Print a visually distinct summary section
    print("\n" + "=" * 60)
    print(f"{Colors.BOLD}{Colors.BRIGHT_GREEN}BUILD SUMMARY{Colors.RESET}")
    print("=" * 60)

    # Build information
    if selected_tag:
        print(f"{Colors.BOLD}Tag:{Colors.RESET}           {Colors.BRIGHT_CYAN}{selected_tag}{Colors.RESET}")
    if expected_version:
        print(f"{Colors.BOLD}Version:{Colors.RESET}       {Colors.BRIGHT_CYAN}{expected_version}{Colors.RESET}")

    # Display warning if using a custom repository
    if is_custom_repo and custom_repo_url:
        print("")
        print(f"{Colors.BRIGHT_YELLOW}⚠️  CUSTOM REPOSITORY WARNING{Colors.RESET}")
        print(f"{Colors.BRIGHT_YELLOW}   Using custom ESP-Miner repository: {custom_repo_url}{Colors.RESET}")
        print(f"{Colors.BRIGHT_YELLOW}   This is an advanced feature and may affect reproducibility{Colors.RESET}")

    # Files information
    if build_info and 'files' in build_info:
        print(f"\n{Colors.BOLD}Build Artifacts:{Colors.RESET}")
        for file in build_info['files']:
            file_path = output_dir / file
            if file_path.exists():
                size = file_path.stat().st_size
                size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"
                print(f"  {Colors.BRIGHT_GREEN}✓{Colors.RESET} {file} ({size_str})")

    print("=" * 60 + "\n")

def _display_flash_summary(selected_tag, expected_version, args):
    """Displays a simplified summary after flashing."""
    # This function is intentionally empty to prevent displaying a summary after flashing
    pass



def main():
    """Main entry point for the CLI application."""
    args = _parse_arguments()
    _setup_logging(args) # Setup root logger

    # Now subsequent logger calls (including those in imported modules) will use the root config
    logger.info("--- NomadBuild Local Builder & Flasher (CLI) --- ")
    logger.debug(f"Command line arguments: {args}")
    logger.info(f"Platform: {platform.system()} {platform.machine()}")

    load_models_config()
    setup_environment()



    # Handle reproducibility commands
    if args.repro:
        _handle_reproducibility_check(args)
        return

    # Normal build and flash flow
    selected_tag, expected_version, is_custom_repo, custom_repo_url = _handle_build_or_use_existing(args)

    # Display a user-friendly build summary before flashing
    _display_build_summary(selected_tag, expected_version, args, is_custom_repo, custom_repo_url)

    # Pass necessary args to _handle_flashing (from device.py)
    # Note: _handle_flashing doesn't need the custom repo info
    _handle_flashing(args, selected_tag, expected_version)

if __name__ == "__main__":
    # Basic config might run before _setup_logging, but _setup_logging will remove its handlers
    main()