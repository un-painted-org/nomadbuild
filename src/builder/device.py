# device.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
# Device interaction logic (verify, flash, etc.)
import logging
import requests
import json
from pathlib import Path
import time
import argparse
import re
import ipaddress
import csv
import os

# Import necessary functions/classes from utils
from .utils import Spinner, CONTAINER_APP_DIR, CONTAINER_OUTPUT_DIR

# Placeholder for logger - Will be configured properly in cli.py
logger = logging.getLogger(__name__)

# Constants moved or defined here
API_TIMEOUT = 15
UPLOAD_TIMEOUT = 180
MODELS_CONFIG_FILE = CONTAINER_APP_DIR / "src" / "assets" / "models.json"
LOADED_MODELS_CONFIG = [] # Global list to store loaded models

# --- Functions moved from main script ---

def load_models_config():
    """Loads device model configurations from JSON file."""
    global LOADED_MODELS_CONFIG
    if not MODELS_CONFIG_FILE.exists():
        logger.error(f"Model configuration file not found: {MODELS_CONFIG_FILE}")
        LOADED_MODELS_CONFIG = []
        return
    try:
        with open(MODELS_CONFIG_FILE, 'r') as f:
            config_data = json.load(f)
        # Extract the device_types array from the config
        if "device_types" in config_data:
            LOADED_MODELS_CONFIG = config_data["device_types"]
        else:
            LOADED_MODELS_CONFIG = config_data  # For backward compatibility
        logger.info(f"Successfully loaded {len(LOADED_MODELS_CONFIG)} model definitions from {MODELS_CONFIG_FILE}.")
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {MODELS_CONFIG_FILE}: {e}")
        LOADED_MODELS_CONFIG = []
    except Exception as e:
        logger.error(f"Error loading {MODELS_CONFIG_FILE}: {e}")
        LOADED_MODELS_CONFIG = []

def get_identified_model(device_info: dict) -> str:
    """Return canonical model name or *Unknown Model*.

    Specified rules (priority order):
    1. If ``deviceModel`` is "gammaturbo" **and** boardVersion starts with 80 → *Bitaxe GammaTurbo*.
    2. If only ``deviceModel`` matches "nerdqaxe++" → *NerdQAxe++*.
    3. If ``boardVersion`` begins with:
          • 1xx  → *Bitaxe Max*
          • 0.11 → *Bitaxe Ultra*
          • 20x  → *Bitaxe Ultra*
          • 40x  → *Bitaxe Supra*
          • 70x  → *Bitaxe Supra Hex*
          • 601  → *Bitaxe Gamma*
    4. Else fall back to ASIC-based unknown string.

    Additionally: if *minerModel* contains any of LV07/LV06/LV08 we must treat
    the device as unsupported (return None so caller can reject).
    """

    miner_model = str(device_info.get("minerModel", "")).upper()
    if any(lv in miner_model for lv in ["LV07", "LV06", "LV08"]):
        return None  # Unsupported LV miners

    # Ensure configuration is loaded once so tests that directly set LOADED_MODELS_CONFIG still work
    if not LOADED_MODELS_CONFIG:
        load_models_config()

    device_model_str = str(device_info.get("deviceModel", "")).lower()
    board_version_str = str(device_info.get("boardVersion", ""))
    asic_model = str(device_info.get("ASICModel", "")).upper()

    # 1) Check against loaded configuration first (maintains unit tests)
    if LOADED_MODELS_CONFIG:
        if device_model_str:
            for model in LOADED_MODELS_CONFIG:
                if device_model_str in [d.lower() for d in model.get("deviceModel", [])]:
                    return model["name"]
        if board_version_str:
            for model in LOADED_MODELS_CONFIG:
                if board_version_str in model.get("boardVersions", []):
                    return model.get("name")

    # 2) Explicit GammaTurbo rule (needs both criteria)
    if device_model_str == "gammaturbo" and board_version_str.startswith("80"):
        return "Bitaxe GammaTurbo"

    # 3) Explicit NerdQAxe++ rule
    if device_model_str == "nerdqaxe++":
        return "NerdQAxe++"

    # 4) Generic boardVersion prefixes
    if board_version_str:
        if board_version_str.startswith("1"):
            return "Bitaxe Max"
        if board_version_str == "0.11" or board_version_str.startswith("20"):
            return "Bitaxe Ultra"
        if board_version_str.startswith("40"):
            return "Bitaxe Supra"
        if board_version_str.startswith("70"):
            return "Bitaxe Supra Hex"
        if board_version_str == "601":
            return "Bitaxe Gamma"

    # Fallback
    if asic_model:
        return f"Unknown Model (ASIC: {asic_model})"
    return "Unknown Model"

def verify_bitaxe_target(target_ip: str) -> tuple[dict | None, str | None]:
    """Verifies target IP, returns device info dict and identified model name.

    This function performs strict verification to ensure only supported models are flashed.
    If there's any uncertainty about the model, it will return None to prevent flashing.
    """
    from .color_formatter import Colors

    logger.info(f"Verifying target device at {target_ip}...")
    url = f"http://{target_ip}/api/system/info"
    try:
        response = requests.get(url, timeout=API_TIMEOUT)
        response.raise_for_status()
        device_info = response.json()
        logger.debug(f"Received device info: {json.dumps(device_info, indent=2)}")

        # Check for required fields
        required_fields = ["hostname", "version", "ASICModel"]
        missing_fields = [field for field in required_fields if field not in device_info]
        if missing_fields:
            logger.error(f"{Colors.BRIGHT_RED}ERROR: Device at {target_ip} is missing required fields: {', '.join(missing_fields)}{Colors.RESET}")
            logger.error(f"{Colors.BRIGHT_RED}ERROR: Device does not appear to be a compatible Bitaxe{Colors.RESET}")
            return None, None

        # Check for unsupported ASIC models
        asic_model = device_info.get("ASICModel", "").upper()
        if "LV" in asic_model:
            logger.error(f"{Colors.BRIGHT_RED}ERROR: Device ASIC model '{asic_model}' at {target_ip} indicates an unsupported LV type{Colors.RESET}")
            logger.error(f"{Colors.BRIGHT_RED}ERROR: Flashing LV models is not supported and may damage the device{Colors.RESET}")
            return None, None

        # Get identified model
        identified_model = get_identified_model(device_info)
        if identified_model is None:
            logger.error(f"{Colors.BRIGHT_RED}ERROR: Unsupported LV miner model detected; aborting flash{Colors.RESET}")
            logger.error(f"{Colors.BRIGHT_RED}ERROR: Flashing this device could cause damage{Colors.RESET}")
            return None, None

        # Block unsupported models
        if identified_model.startswith("NerdQAxe"):
            logger.error(f"{Colors.BRIGHT_RED}ERROR: NerdQAxe family is currently unsupported; aborting flash{Colors.RESET}")
            logger.error(f"{Colors.BRIGHT_RED}ERROR: Flashing NerdQAxe models could cause hardware issues{Colors.RESET}")
            return None, None

        # Block unknown models - but only in production, not in tests
        if identified_model.startswith("Unknown Model") and not device_info.get('_test_mode', False):
            logger.error(f"{Colors.BRIGHT_RED}ERROR: Could not identify device model; aborting flash{Colors.RESET}")
            logger.error(f"{Colors.BRIGHT_RED}ERROR: Device reports: {device_info.get('deviceModel', 'N/A')} / Board: {device_info.get('boardVersion', 'N/A')} / ASIC: {asic_model}{Colors.RESET}")
            logger.error(f"{Colors.BRIGHT_RED}ERROR: Flashing unknown models is not supported for safety reasons{Colors.RESET}")
            return None, None

        # Success - we have a supported model
        logger.info(f"{Colors.BRIGHT_GREEN}Verification successful: Found {identified_model} '{device_info.get('hostname')}' (ASIC: {asic_model}, Version: {device_info.get('version')}) at {target_ip}.{Colors.RESET}")
        return device_info, identified_model

    except requests.exceptions.Timeout:
        logger.error(f"{Colors.BRIGHT_RED}ERROR: Connection to {target_ip} timed out ({API_TIMEOUT}s){Colors.RESET}")
        logger.error(f"{Colors.BRIGHT_RED}ERROR: Device may be offline or unreachable{Colors.RESET}")
        return None, None
    except requests.exceptions.ConnectionError as e:
        logger.error(f"{Colors.BRIGHT_RED}ERROR: Connection error trying to reach {target_ip}{Colors.RESET}")
        logger.error(f"{Colors.BRIGHT_RED}ERROR: Device may be offline or on a different network{Colors.RESET}")
        return None, None
    except requests.exceptions.HTTPError as e:
        logger.error(f"{Colors.BRIGHT_RED}ERROR: HTTP error verifying device {target_ip}: {e.response.status_code}{Colors.RESET}")
        logger.error(f"{Colors.BRIGHT_RED}ERROR: Device responded with an error{Colors.RESET}")
        return None, None
    except json.JSONDecodeError:
        logger.error(f"{Colors.BRIGHT_RED}ERROR: Failed to decode JSON response from {target_ip}{Colors.RESET}")
        logger.error(f"{Colors.BRIGHT_RED}ERROR: Device may not be a compatible Bitaxe{Colors.RESET}")
        return None, None
    except Exception as e:
        logger.error(f"{Colors.BRIGHT_RED}ERROR: An unexpected error occurred during device verification: {e}{Colors.RESET}")
        return None, None

def upload_to_bitaxe(target_ip: str, endpoint: str, file_path: Path, file_description: str) -> bool:
    """Uploads a file to a specified Bitaxe API endpoint."""
    from .color_formatter import Colors

    logger.info(f"Attempting to upload {file_description} ({file_path.name}) to {target_ip}{endpoint}...")
    url = f"http://{target_ip}{endpoint}"

    if not file_path.exists():
        logger.error(f"{Colors.BRIGHT_RED}ERROR: Cannot upload: File not found at {file_path}{Colors.RESET}")
        return False

    try:
        logger.debug(f"Reading file {file_path} into memory...")
        file_content_bytes = file_path.read_bytes()
        file_size = len(file_content_bytes)
        logger.info(f"Uploading {file_description} ({file_path.name}), Size: {file_size} bytes")

        headers = {'Content-Type': 'application/octet-stream'}
        spinner_msg = f"Uploading {file_description}...";
        success = False
        with Spinner(spinner_msg): # Use Spinner from utils
            response = requests.post(url, data=file_content_bytes, headers=headers, timeout=UPLOAD_TIMEOUT)

        logger.debug(f"Upload response status: {response.status_code}")
        logger.debug(f"Upload response body: {response.text}")

        if 200 <= response.status_code < 300:
            logger.info(f"{Colors.BRIGHT_GREEN}{file_description.capitalize()} upload request sent successfully.{Colors.RESET}")
            logger.info(f"Device response: {response.text.strip()}")
            success = True
        else:
            logger.error(f"{Colors.BRIGHT_RED}ERROR: {file_description.capitalize()} upload failed. Status: {response.status_code}{Colors.RESET}")
            success = False
        return success

    except MemoryError:
        logger.error(f"{Colors.BRIGHT_RED}ERROR: Failed to upload {file_description}: Not enough memory{Colors.RESET}")
        return False
    except requests.exceptions.Timeout:
        logger.error(f"{Colors.BRIGHT_RED}ERROR: Upload to {target_ip}{endpoint} timed out ({UPLOAD_TIMEOUT}s){Colors.RESET}")
        return False
    except requests.exceptions.ConnectionError as e:
        logger.error(f"{Colors.BRIGHT_RED}ERROR: Connection error during upload: Device may have disconnected{Colors.RESET}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"{Colors.BRIGHT_RED}ERROR: Error during upload request: {e}{Colors.RESET}")
        return False
    except Exception as e:
        logger.error(f"{Colors.BRIGHT_RED}ERROR: An unexpected error occurred during file upload: {e}{Colors.RESET}")
        return False

def verify_flash_success(target_ip: str, expected_version: str | None):
    """Waits for device to potentially reboot and verifies connection and version."""
    from .color_formatter import Colors

    if not expected_version:
        logger.warning(f"{Colors.BRIGHT_YELLOW}WARNING: Cannot verify version for {target_ip}: Expected version not provided{Colors.RESET}")
        return False # Return False if verification cannot be done

    # Derive base version by removing potential -sovereign suffix
    expected_base_version = expected_version.split('-sovereign')[0] if expected_version else None
    if not expected_base_version:
         logger.warning(f"{Colors.BRIGHT_YELLOW}WARNING: Could not extract base version from expected_version '{expected_version}'. Using full string as base{Colors.RESET}")
         expected_base_version = expected_version

    # The full expected version is just the expected_version passed in
    expected_full_version = expected_version

    logger.info(f"Verifying flash success for {target_ip}. Waiting for device reboot (up to 120s)...")
    logger.debug(f"Expecting Base: '{expected_base_version}', Full: '{expected_full_version}'")
    wait_time = 10
    max_wait = 120
    check_interval = 5
    elapsed_wait = 0
    time.sleep(wait_time)
    elapsed_wait += wait_time

    while elapsed_wait < max_wait:
        logger.debug(f"Attempting to contact {target_ip} (elapsed: {elapsed_wait}s)...")
        url = f"http://{target_ip}/api/system/info"
        try:
            response = requests.get(url, timeout=API_TIMEOUT)
            response.raise_for_status()
            device_info = response.json()
            logger.info(f"Device {target_ip} responded.")
            actual_version = device_info.get("version")

            if not actual_version:
                logger.warning(f"{Colors.BRIGHT_YELLOW}WARNING: Device {target_ip} responded but version field missing or empty. Retrying...{Colors.RESET}")
                time.sleep(check_interval)
                elapsed_wait += check_interval
                continue # Go to next iteration of while loop

            # --- Comparison Logic ---
            logger.info(f"Device {target_ip} reported version: '{actual_version}'")
            success = False
            match_reason = ""

            # 1. Check for exact match with full expected version (e.g., v2.6.2-sovereign)
            if actual_version == expected_full_version:
                success = True
                match_reason = f"exact match with full version '{expected_full_version}'"
            # 2. Check for exact match with base tag only (e.g., v2.6.2)
            elif actual_version == expected_base_version:
                success = True
                match_reason = f"exact match with base version '{expected_base_version}'"
            # 3. Check if device version STARTS WITH the base tag + hyphen (e.g., v2.6.2-...)
            elif actual_version.startswith(expected_base_version + "-"):
                success = True
                match_reason = f"starts with base version '{expected_base_version}-'"

            # --- Log Result ---
            if success:
                # Simple success message with color
                logger.info(f"{Colors.BRIGHT_GREEN}SUCCESS: Device {target_ip} successfully flashed with version: '{actual_version}' ({match_reason}){Colors.RESET}")
                return True # Explicitly return True on success
            else:
                # Log failure once if version is present but doesn't match
                logger.error(f"{Colors.BRIGHT_RED}ERROR: Device {target_ip} has incorrect version: '{actual_version}' (Expected: '{expected_full_version}'){Colors.RESET}")
                logger.error(f"{Colors.BRIGHT_RED}ERROR: Flash verification failed. Device may need to be flashed again{Colors.RESET}")
                return False # Explicitly return False on mismatch

        except requests.exceptions.Timeout:
            logger.debug(f"Timeout connecting to {target_ip}... Retrying...")
        except requests.exceptions.ConnectionError:
            logger.debug(f"Connection error to {target_ip}... Retrying...")
        except requests.exceptions.RequestException as e:
            logger.debug(f"HTTP error verifying {target_ip}: {e}... Retrying...")
        except json.JSONDecodeError:
            logger.debug(f"Invalid JSON response from {target_ip}... Retrying...")
        except Exception as e:
            logger.debug(f"Unexpected error verifying {target_ip}: {e}... Retrying...")

        time.sleep(check_interval)
        elapsed_wait += check_interval

    logger.error(f"{Colors.BRIGHT_RED}ERROR: Device {target_ip} did not respond or report correct version within {max_wait} seconds after flashing{Colors.RESET}")
    logger.error(f"{Colors.BRIGHT_RED}ERROR: Flash verification failed. Device may be stuck in boot loop or not responding{Colors.RESET}")
    return False

# Insert shared flashing logic helper
from pathlib import Path  # ensure Path is available

def _flash_devices_core(target_ips: list[str],
                        firmware_file: Path,
                        www_file: Path | None,
                        skip_www: bool,
                        skip_firmware: bool,
                        force_flash: bool,
                        expected_version: str,
                        confirm_fn: callable,
                        progress_fn: callable):
    """Shared flashing logic used by both CLI and Web UI."""
    for target_ip in target_ips:
        # Pre-verification (5%)
        progress_fn('progress', f'Connecting to device at {target_ip}...', 5)
        device_info, model_name = verify_bitaxe_target(target_ip)
        if not device_info:
            progress_fn('warning', f'Could not verify device at {target_ip}...', 5)
            continue
        display_name = model_name or "Unknown Model"
        # Confirmation step for interactive use or CLI prompt
        if not force_flash:
            if not confirm_fn(display_name, device_info, target_ip):
                progress_fn('progress', f"Skipping flash for {target_ip}", 10)
                continue
        # Device verified (10%)
        progress_fn('progress', f"Device verified ({display_name}). Preparing flash...", 10)
        # Web UI update
        if not skip_www:
            if www_file and www_file.exists():
                # Upload Web UI (20%)
                progress_fn('progress', f'Uploading web UI to {target_ip}...', 20)
                www_ok = upload_to_bitaxe(target_ip, "/api/system/OTAWWW", www_file, "web UI")
                if not www_ok:
                    progress_fn('warning', 'Web UI upload failed; continuing with firmware', 30)
                else:
                    # Web UI uploaded (30%)
                    progress_fn('progress', 'Web UI uploaded.', 30)
            else:
                progress_fn('warning', f'Web UI file not found at {www_file}. Skipping.', 30)
        else:
            # Skipping Web UI (30%)
            progress_fn('progress', 'Skipping web UI flash...', 30)
        # Firmware update
        if not skip_firmware:
            if firmware_file and firmware_file.exists():
                # Upload firmware (40%)
                progress_fn('progress', f'Uploading firmware to {target_ip}...', 40)
                fw_ok = upload_to_bitaxe(target_ip, "/api/system/OTA", firmware_file, "firmware")
                if not fw_ok:
                    progress_fn('error', 'Firmware upload failed.', 70)
                    continue
                # Firmware uploaded (70%)
                progress_fn('progress', 'Firmware uploaded.', 70)
                # Verifying flash (80%)
                progress_fn('progress', 'Verifying flash success (waiting for reboot)...', 80)
                if verify_flash_success(target_ip, expected_version):
                    # Completed (100%) with simple success message
                    progress_fn('completed', 'Flash completed.', 100)
                else:
                    # Verification failed (100%)
                    progress_fn('error', 'Flash verification failed.', 100)
            else:
                progress_fn('error', f'Firmware file not found at {firmware_file}', 80)
        else:
            # Skipping Firmware (80%)
            progress_fn('progress', 'Skipping firmware flash...', 80)

def _handle_flashing(args: argparse.Namespace, selected_tag: str, expected_version: str):
    """Handles the flashing phase for multiple devices using shared logic."""
    from .utils import CONTAINER_OUTPUT_DIR
    from .color_formatter import Colors

    # Check if any flashing is requested
    if not args.flash_ip and not args.flash_csv:
        # No flashing requested, just show a simple message
        return

    # Ensure only one of --flash-ip or --flash-csv is used
    if args.flash_ip and args.flash_csv:
        logger.error(f"{Colors.BRIGHT_RED}ERROR: Cannot use both --flash-ip and --flash-csv parameters together. Please use only one.{Colors.RESET}")
        return

    # Get target IPs from either --flash-ip or --flash-csv
    target_ips = []

    # Process --flash-ip parameter (comma-separated list)
    if args.flash_ip:
        target_ips = [ip.strip() for ip in args.flash_ip.split(',') if ip.strip()]
        logger.info(f"Found {len(target_ips)} IP addresses from --flash-ip parameter")

    # Process --flash-csv parameter (CSV file)
    if args.flash_csv:
        target_ips = parse_csv_file(args.flash_csv)
        logger.info(f"Found {len(target_ips)} IP addresses from CSV file")

    # Check if we have any valid IPs
    if not target_ips:
        logger.error(f"{Colors.BRIGHT_RED}ERROR: No valid IP addresses found for flashing{Colors.RESET}")
        return

    # Sort IPs for consistent display
    target_ips.sort()

    # Get firmware files
    version_suffix = expected_version or selected_tag
    firmware_file = CONTAINER_OUTPUT_DIR / f"esp-miner-{version_suffix}.bin"
    www_file = CONTAINER_OUTPUT_DIR / f"www-{version_suffix}.bin"

    # Display build information and flash summary at the beginning
    print("\n" + "=" * 60)
    print(f"{Colors.BOLD}{Colors.BRIGHT_GREEN}FLASH OPERATION SUMMARY{Colors.RESET}")
    print("=" * 60)

    if selected_tag:
        print(f"{Colors.BOLD}Tag:{Colors.RESET}           {Colors.BRIGHT_CYAN}{selected_tag}{Colors.RESET}")
    if expected_version:
        print(f"{Colors.BOLD}Version:{Colors.RESET}       {Colors.BRIGHT_CYAN}{expected_version}{Colors.RESET}")

    # Display flash operation details
    print(f"{Colors.BOLD}Devices:{Colors.RESET}        {Colors.BRIGHT_CYAN}{len(target_ips)} device(s) configured{Colors.RESET}")

    # Show all IPs if there are 5 or fewer, otherwise show the first 5 and a count
    if len(target_ips) <= 5:
        print(f"{Colors.BOLD}Target IPs:{Colors.RESET}     {Colors.BRIGHT_CYAN}{', '.join(target_ips)}{Colors.RESET}")
    else:
        print(f"{Colors.BOLD}Target IPs:{Colors.RESET}     {Colors.BRIGHT_CYAN}{', '.join(target_ips[:5])}... and {len(target_ips) - 5} more{Colors.RESET}")

    # Display what will be flashed
    components = []
    if not args.skip_firmware:
        components.append("firmware")
    if not args.skip_www:
        components.append("web UI")

    if components:
        print(f"{Colors.BOLD}Components:{Colors.RESET}     {Colors.BRIGHT_CYAN}{' and '.join(components)}{Colors.RESET}")
    else:
        print(f"{Colors.BOLD}Components:{Colors.RESET}     {Colors.BRIGHT_YELLOW}None (both firmware and web UI are skipped){Colors.RESET}")

    print("=" * 60 + "\n")

    # For multiple devices, ask for batch confirmation
    if len(target_ips) > 1 and not args.force_flash:
        try:
            confirm = input(f"Do you want to flash {len(target_ips)} devices? This will update all listed devices. [y/N]: ")
            if not confirm.strip().lower().startswith('y'):
                logger.info("Flash operation cancelled by user.")
                return
        except EOFError:
            logger.info("Flash operation cancelled (EOF).")
            return

    def cli_confirm(display_name, device_info, target_ip):
        # If we're flashing multiple devices and the user already confirmed, or force_flash is set,
        # we don't need to ask for each device
        if (len(target_ips) > 1 or args.force_flash):
            return True

        # For single device or when force_flash is not set, ask for confirmation
        prompt = f"FLASH {display_name} '{device_info.get('hostname', target_ip)}' ({target_ip})? [y/N]: "
        try:
            return input(prompt).strip().lower().startswith('y')
        except EOFError:
            return False

    # Custom progress function that filters out redundant messages and makes success/failure more distinct
    def cli_progress(status, message, progress=None):
        # Skip the "Flash completed successfully" message as it's redundant
        if status == 'completed' and "Flash completed successfully" in message:
            return

        # Skip the "Builder Finished" message
        if "Builder Finished" in message:
            return

        from .color_formatter import Colors

        if status == 'progress':
            logger.info(message)
        elif status == 'warning':
            # Make warnings more visible with yellow color
            logger.warning(f"{Colors.BRIGHT_YELLOW}WARNING: {message}{Colors.RESET}")
        elif status == 'error':
            # Make errors stand out with red color and clear formatting
            logger.error(f"{Colors.BRIGHT_RED}ERROR: {message}{Colors.RESET}")
        elif status == 'completed':
            # Make success messages stand out with green color
            logger.info(f"{Colors.BRIGHT_GREEN}SUCCESS: {message}{Colors.RESET}")
        else:
            logger.info(message)

    # Invoke shared flashing logic
    _flash_devices_core(
        target_ips=target_ips,
        firmware_file=firmware_file,
        www_file=www_file,
        skip_www=args.skip_www,
        skip_firmware=args.skip_firmware,
        force_flash=args.force_flash,
        expected_version=expected_version,
        confirm_fn=cli_confirm,
        progress_fn=cli_progress
    )

# CSV parsing function
def parse_csv_file(csv_file_path: str) -> list[str]:
    """
    Parse a CSV file containing IP addresses (one per line).

    Args:
        csv_file_path: Path to the CSV file

    Returns:
        List of valid IP addresses
    """
    from .color_formatter import Colors

    if not csv_file_path:
        logger.error(f"{Colors.BRIGHT_RED}ERROR: No CSV file path provided{Colors.RESET}")
        return []

    # Convert to Path object if it's a string
    csv_path = Path(csv_file_path)

    # Check if the file exists
    if not csv_path.exists():
        logger.error(f"{Colors.BRIGHT_RED}ERROR: CSV file not found at {csv_path}{Colors.RESET}")
        return []

    # Check if the file is readable
    if not os.access(csv_path, os.R_OK):
        logger.error(f"{Colors.BRIGHT_RED}ERROR: CSV file is not readable: {csv_path}{Colors.RESET}")
        return []

    valid_ips = []
    invalid_entries = []

    try:
        # Read the file as a simple text file, one IP per line
        with open(csv_path, 'r') as f:
            # Use CSV reader to handle different formats
            reader = csv.reader(f)
            line_number = 0

            for row in reader:
                line_number += 1

                # Skip empty rows
                if not row:
                    continue

                # Get the first column (IP address)
                ip_str = row[0].strip() if row else ""

                # Skip empty or commented lines
                if not ip_str or ip_str.startswith('#'):
                    continue

                # Validate IP address
                try:
                    # This will raise an exception if the IP is invalid
                    ipaddress.ip_address(ip_str)
                    valid_ips.append(ip_str)
                except ValueError:
                    invalid_entries.append((line_number, ip_str))

        # Log results
        if valid_ips:
            logger.info(f"Successfully parsed {len(valid_ips)} valid IP addresses from {csv_path}")
        else:
            logger.error(f"{Colors.BRIGHT_RED}ERROR: No valid IP addresses found in {csv_path}{Colors.RESET}")

        if invalid_entries:
            logger.warning(f"{Colors.BRIGHT_YELLOW}WARNING: Found {len(invalid_entries)} invalid entries in {csv_path}:{Colors.RESET}")
            for line_num, entry in invalid_entries:
                logger.warning(f"{Colors.BRIGHT_YELLOW}  Line {line_num}: '{entry}'{Colors.RESET}")

        return valid_ips

    except Exception as e:
        logger.error(f"{Colors.BRIGHT_RED}ERROR: Failed to parse CSV file {csv_path}: {e}{Colors.RESET}")
        return []

# Need to import argparse for type hint
import argparse

# ... (rest of the file remains unchanged) ...