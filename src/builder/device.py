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
    """Verifies target IP, returns device info dict and identified model name."""
    logger.info(f"Verifying target device at {target_ip}...")
    url = f"http://{target_ip}/api/system/info"
    try:
        response = requests.get(url, timeout=API_TIMEOUT)
        response.raise_for_status()
        device_info = response.json()
        logger.debug(f"Received device info: {json.dumps(device_info, indent=2)}")

        if not all(k in device_info for k in ["hostname", "version", "ASICModel"]):
            logger.error(f"Device at {target_ip} does not appear to be a compatible Bitaxe...")
            return None, None

        asic_model = device_info.get("ASICModel", "").upper()
        if "LV" in asic_model:
             logger.error(f"Device ASIC model '{asic_model}' at {target_ip} indicates an unsupported LV type...")
             return None, None

        identified_model = get_identified_model(device_info)
        if identified_model is None:
            logger.error("Unsupported LV miner model detected; aborting flash.")
            return None, None

        # Block unsupported models
        if identified_model.startswith("NerdQAxe"):
            logger.error("NerdQAxe family is currently unsupported; aborting flash to prevent hardware issues.")
            return None, None

        logger.info(f"Verification successful: Found {identified_model} '{device_info.get('hostname')}' (ASIC: {asic_model}, Version: {device_info.get('version')}) at {target_ip}.")
        return device_info, identified_model

    # ... (Exception handling remains same) ...
    except requests.exceptions.Timeout:
        logger.error(f"Connection to {target_ip} timed out ({API_TIMEOUT}s)...")
        return None, None
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error trying to reach {target_ip}: {e}")
        return None, None
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error verifying device {target_ip}: {e.response.status_code}...")
        return None, None
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON response from {target_ip}...")
        return None, None
    except Exception as e:
        logger.exception(f"An unexpected error occurred during device verification...: {e}")
        return None, None

def upload_to_bitaxe(target_ip: str, endpoint: str, file_path: Path, file_description: str) -> bool:
    """Uploads a file to a specified Bitaxe API endpoint."""
    logger.info(f"Attempting to upload {file_description} ({file_path.name}) to {target_ip}{endpoint}...")
    url = f"http://{target_ip}{endpoint}"

    if not file_path.exists():
        logger.error(f"Cannot upload: File not found at {file_path}")
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
            logger.info(f"{file_description.capitalize()} upload request sent successfully.")
            logger.info(f"Device response: {response.text.strip()}")
            success = True
        else:
            logger.error(f"{file_description.capitalize()} upload failed. Status: {response.status_code}...")
            success = False
        return success

    # ... (Exception handling remains same) ...
    except MemoryError:
        logger.error(f"Failed to upload {file_description}: Not enough memory...")
        return False
    except requests.exceptions.Timeout:
        logger.error(f"Upload to {target_ip}{endpoint} timed out ({UPLOAD_TIMEOUT}s)...")
        return False
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error during upload...: {e}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Error during upload request...: {e}")
        return False
    except Exception as e:
        logger.exception(f"An unexpected error occurred during file upload...: {e}")
        return False

def verify_flash_success(target_ip: str, expected_version: str | None):
    """Waits for device to potentially reboot and verifies connection and version."""
    if not expected_version:
        logger.warning(f"Cannot verify version for {target_ip}: Expected version not provided.")
        return False # Return False if verification cannot be done

    # Derive base version by removing potential -sovereign suffix
    expected_base_version = expected_version.split('-sovereign')[0] if expected_version else None
    if not expected_base_version:
         logger.warning(f"Could not extract base version from expected_version '{expected_version}'... Using full string as base.")
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
                logger.warning(f"Device {target_ip} responded but version field missing or empty. Retrying...")
                time.sleep(check_interval)
                elapsed_wait += check_interval
                continue # Go to next iteration of while loop

            # --- Comparison Logic ---
            logger.info(f"Device {target_ip} reported version: '{actual_version}'")
            success = False

            # 1. Check for exact match with full expected version (e.g., v2.6.2-sovereign)
            if actual_version == expected_full_version:
                success = True
            # 2. Check for exact match with base tag only (e.g., v2.6.2)
            elif actual_version == expected_base_version:
                success = True
            # 3. Check if device version STARTS WITH the base tag + hyphen (e.g., v2.6.2-...)
            elif actual_version.startswith(expected_base_version + "-"):
                success = True

            # --- Log Result ---
            if success:
                logger.info(f"SUCCESS: Device {target_ip} online with matching version: '{actual_version}'")
                return True # Explicitly return True on success
            else:
                # Log failure only once if version is present but doesn't match
                logger.error(f"FAILURE: Device {target_ip} online but has WRONG version: '{actual_version}' (Expected: '{expected_full_version}')")
                return False # Explicitly return False on mismatch

        except requests.exceptions.Timeout: logger.debug(f"Timeout connecting to {target_ip}... Retrying...")
        except requests.exceptions.ConnectionError: logger.debug(f"Connection error to {target_ip}... Retrying...")
        except requests.exceptions.RequestException as e: logger.warning(f"HTTP error verifying {target_ip}: {e}... Retrying...")
        except json.JSONDecodeError: logger.warning(f"Invalid JSON response from {target_ip}... Retrying...")
        except Exception as e: logger.warning(f"Unexpected error verifying {target_ip}: {e}... Retrying...")

        time.sleep(check_interval)
        elapsed_wait += check_interval

    logger.error(f"FAILURE: Device {target_ip} did not respond or report correct version within {max_wait} seconds after flashing.")
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
                    # Completed (100%)
                    progress_fn('completed', 'Flash completed successfully.', 100)
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

    if not args.flash_ip:
        # No flashing requested, just show a simple message
        return

    # Display build information at the beginning
    print("\n" + "=" * 60)
    print(f"{Colors.BOLD}{Colors.BRIGHT_GREEN}BUILD INFORMATION{Colors.RESET}")
    print("=" * 60)

    if selected_tag:
        print(f"{Colors.BOLD}Tag:{Colors.RESET}           {Colors.BRIGHT_CYAN}{selected_tag}{Colors.RESET}")
    if expected_version:
        print(f"{Colors.BOLD}Version:{Colors.RESET}       {Colors.BRIGHT_CYAN}{expected_version}{Colors.RESET}")
    print("=" * 60 + "\n")

    target_ips = [ip.strip() for ip in args.flash_ip.split(',') if ip.strip()]
    version_suffix = expected_version or selected_tag
    firmware_file = CONTAINER_OUTPUT_DIR / f"esp-miner-{version_suffix}.bin"
    www_file = CONTAINER_OUTPUT_DIR / f"www-{version_suffix}.bin"

    def cli_confirm(display_name, device_info, target_ip):
        prompt = f"FLASH {display_name} '{device_info.get('hostname', target_ip)}' ({target_ip})? [y/N]: "
        try:
            return input(prompt).strip().lower().startswith('y')
        except EOFError:
            return False

    # Custom progress function that filters out redundant messages
    def cli_progress(status, message, progress=None):
        # Skip the "Flash completed successfully" message as it's redundant
        if status == 'completed' and "Flash completed successfully" in message:
            return

        if status == 'progress':
            logger.info(message)
        elif status == 'warning':
            logger.warning(message)
        elif status == 'error':
            logger.error(message)
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

# Need to import argparse for type hint
import argparse

# ... (rest of the file remains unchanged) ...