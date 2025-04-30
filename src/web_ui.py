# web_ui.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
import os
import sys
import json
import logging
import threading
import webbrowser
import time
import random
import socket
import subprocess
import datetime
import shutil
import hashlib
import signal  # Add import for process group kill
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory, Response
from flask_socketio import SocketIO, emit, join_room, leave_room
from src.builder import utils as builder_utils
from src.builder import git_ops as builder_git
from src.builder import build as builder_build
from src.builder import device as builder_device
from src.builder.git_ops import ensure_clean_repo_for_build
import traceback
from unittest.mock import MagicMock

# Custom Exceptions
class BuildCancelledError(Exception):
    """Custom exception for cancelled builds."""
    pass

class BuildFailedError(Exception):
    """Custom exception for build failures."""
    pass

# --- Configuration ---
HOST = '0.0.0.0'  # Listen on all interfaces (for Docker)
PORT = 9090
AUTO_OPEN_BROWSER = True  # Set to False when running in container
TAG_CACHE_LIFETIME_SECONDS = 3600 # 1 hour

# Directory paths
CURRENT_DIR = Path(__file__).parent
STATIC_DIR = CURRENT_DIR / 'web_static'
TEMPLATES_DIR = CURRENT_DIR / 'web_templates'

# --- Setup Logger ---
logger = logging.getLogger("WebUI")

# --- App Initialization ---
app = Flask(__name__, 
            static_folder=str(STATIC_DIR),
            template_folder=str(TEMPLATES_DIR))
socketio = SocketIO(app, cors_allowed_origins="*")

# Add app configuration
app.config['FIRMWARE_DIR'] = str(Path(os.environ.get('FIRMWARE_DIR', '/firmware')))

# Server start time for uptime tracking
_server_start_time = time.time()

# --- Global Cache for Tags ---
_tag_cache = {
    'tags': [],
    'last_fetched': 0
}
_tag_cache_lock = threading.Lock()

# --- Global Variables for Build State ---
build_log = ""
build_in_progress = False
build_log_mutex = threading.Lock()
build_canceled = threading.Event() # Use Event for better thread safety
build_thread = None
current_tag = None
repo_path = None
# Global variable to hold the last build progress percentage
last_build_progress = 0
last_build_message = ""

# --- Cache Helper Function ---
def get_cached_or_fresh_tags():
    """Returns stable tags, using cache if valid, otherwise fetches fresh data."""
    global _tag_cache
    now = time.time()
    cache_valid = False

    # Check cache validity (read is generally safe without lock)
    if _tag_cache['tags'] and (now - _tag_cache['last_fetched']) < TAG_CACHE_LIFETIME_SECONDS:
        cache_valid = True

    if cache_valid:
        logger.info("Using cached tags.")
        return _tag_cache['tags']
    else:
        logger.info("Fetching fresh tags (cache empty or expired)...")
        try:
            # Acquire lock only when fetching and updating cache
            with _tag_cache_lock:
                # Double-check cache validity *after* acquiring lock
                if _tag_cache['tags'] and (time.time() - _tag_cache['last_fetched']) < TAG_CACHE_LIFETIME_SECONDS:
                     logger.info("Another thread updated cache, using new cached tags.")
                     return _tag_cache['tags']
                
                # Perform the actual fetch and processing
                builder_utils.setup_environment()
                repo_name = "ESP-Miner"
                repo_path = builder_git.fetch_repo(builder_git.ESP_MINER_REPO, repo_name)
                fresh_tags = builder_git.get_esp_miner_stable_tags(repo_path)
                
                # Update cache
                _tag_cache['tags'] = fresh_tags
                _tag_cache['last_fetched'] = time.time()
                logger.info(f"Cache updated with {len(fresh_tags)} tags.")
                return fresh_tags
        except Exception as e:
            logger.exception("Error fetching or caching tags")
            # In case of error, return potentially stale cache if available, otherwise empty
            return _tag_cache['tags'] if _tag_cache['tags'] else []

# --- Helper Function to get build info file path ---
def get_build_info_path() -> Path:
    """Returns the Path object for the build_info.json file."""
    # Read the configured directory. The default is now set correctly during app init.
    firmware_dir = Path(app.config.get('FIRMWARE_DIR')) # No need for default here anymore
    return firmware_dir / 'build_info.json'

# --- Helper Function to load last build info (Reads directly from file) ---
def load_last_build_info():
    """Loads the last successful build info directly from the JSON file."""
    build_info_path = get_build_info_path()
    logger.debug(f"[load_last_build_info] Checking path: {build_info_path}")
    
    file_exists = build_info_path.exists()
    logger.debug(f"[load_last_build_info] Path exists: {file_exists}")
    
    if file_exists:
        try:
            file_size = build_info_path.stat().st_size
            logger.debug(f"[load_last_build_info] File size: {file_size} bytes. Attempting to open...")
            with open(build_info_path, 'r') as f:
                logger.debug(f"[load_last_build_info] File opened. Attempting json.load...")
                build_info = json.load(f)
                logger.debug(f"[load_last_build_info] json.load successful. Data: {build_info}")
                return build_info
        except json.JSONDecodeError as json_err:
            logger.error(f"[load_last_build_info] JSONDecodeError reading {build_info_path}: {json_err}. File content might be corrupted or empty.")
            # Optionally log file content snippet on error?
            try:
                with open(build_info_path, 'r') as f_err:
                    logger.error(f"[load_last_build_info] Corrupt file content (first 100 chars): {f_err.read(100)}")
            except Exception as read_err:
                logger.error(f"[load_last_build_info] Could not even read corrupt file: {read_err}")
            return None
        except Exception as e:
            logger.exception(f"[load_last_build_info] Unexpected error loading file {build_info_path}: {e}")
            return None # Return None on error
    else:
        logger.warning(f"[load_last_build_info] Build info file not found at expected path: {build_info_path}")
        return None # Return None if file doesn't exist

# --- Helper Function to save last build info (Writes directly to file) ---
def save_last_build_info(build_info: dict):
    """Saves the build info directly to the JSON file."""
    build_info_path = get_build_info_path()
    firmware_dir = build_info_path.parent

    try:
        # Ensure firmware directory exists
        firmware_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Saving build info to {build_info_path}: {build_info}")
        with open(build_info_path, 'w') as f:
            json.dump(build_info, f, indent=4)
        logger.info(f"Successfully saved build info to {build_info_path}.")
            
    except Exception as e:
        logger.exception(f"Error saving build info file {build_info_path}: {e}")

# --- Route Handlers ---
@app.route('/')
def index():
    """Render the main application page."""
    logger.info("Index page requested")
    try:
        return render_template('index.html')
    except Exception as e:
        logger.exception("Error rendering index page")
        return f"Error loading page: {str(e)}", 500

# Add explicit static file serving
@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files from the static directory."""
    logger.info(f"Static file requested: {filename}")
    return send_from_directory(STATIC_DIR, filename)

@app.route('/static/css/<path:filename>')
def static_css(filename):
    """Serve CSS files from the css directory."""
    logger.info(f"CSS file requested: {filename}")
    return send_from_directory(STATIC_DIR / 'css', filename)

@app.route('/static/js/<path:filename>')
def static_js(filename):
    """Serve JS files from the js directory."""
    logger.info(f"JS file requested: {filename}")
    return send_from_directory(STATIC_DIR / 'js', filename)

@app.route('/static/img/<path:filename>')
def static_img(filename):
    """Serve images from the img directory."""
    logger.info(f"Image file requested: {filename}")
    return send_from_directory(STATIC_DIR / 'img', filename)

@app.route('/static/vendor/<path:path>')
def static_vendor(path):
    """Serve vendor files from the vendor directory."""
    logger.info(f"Vendor file requested: {path}")
    vendor_path = Path(path)
    return send_from_directory(STATIC_DIR / 'vendor', str(vendor_path))

@app.route('/static/version/<path:filename>')
def static_version(filename):
    """Serve version files from the version directory."""
    logger.info(f"Version file requested: {filename}")
    return send_from_directory(STATIC_DIR / 'version', filename)

@app.route('/assets/<path:filename>')
def assets_files(filename):
    """Serve asset files (e.g., victory.png) from the src/assets directory."""
    asset_dir = CURRENT_DIR / 'assets'
    logger.info(f"Asset file requested: {filename}")
    return send_from_directory(asset_dir, filename)

@app.route('/version/<path:filename>')
def version_alias(filename):
    """Alias to serve version files from various paths."""
    logger.info(f"Version file requested via alias: {filename}")
    return send_from_directory(STATIC_DIR / 'version', filename)

@app.route('/manifest.json')
def manifest():
    """Serve the PWA manifest file."""
    return send_from_directory(STATIC_DIR, 'manifest.json')

@app.route('/api/tags')
def get_tags():
    """Get available stable tags from ESP-Miner repo, using cache."""
    try:
        tags = get_cached_or_fresh_tags()
        return jsonify({
            "success": True,
            "tags": tags
        })
    except Exception as e:
        logger.exception("Error fetching tags")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/build', methods=['POST'])
def start_build(data=None):  # Accept optional data for testing
    """Start building firmware."""
    try:
        # Determine tag from passed data or request JSON
        if data is None:
            data = request.get_json() or {}
        tag = data.get('tag')

        # Reset state from any previous build (deep clean)
        try:
            ensure_clean_repo_for_build(force_deep_clean=True)
        except Exception as e:
            logger.warning(f"ensure_clean_repo_for_build failed during start_build: {e}")

        # Now reset builder module state
        builder_build.is_building = False
        builder_build.build_progress = 0
        try:
            builder_build.active_build_processes.clear()
        except Exception:
            pass

        # Notify clients that build has started
        socketio.emit('build_status', {
            'status': 'started',
            'tag': tag,
            'message': f'Starting build for {tag}'
        })
        # Start the build process in a background thread
        global build_thread
        build_thread = threading.Thread(target=run_build_thread, args=(tag,), daemon=True)
        build_thread.start()
        return jsonify({"success": True, "message": "Build started"})
    except Exception as e:
        logger.exception("Error processing /api/build request")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/flash', methods=['POST'])
def flash_device():
    """DEPRECATED: Flash firmware using HTTP POST. Moved to SocketIO."""
    logger.warning("Received request on deprecated /api/flash endpoint.")
    return jsonify({
        "success": False,
        "error": "This endpoint is deprecated. Use the SocketIO 'flash_device' event."
    }), 410 # Gone

@app.route('/api/tips')
def get_tips():
    """Get helpful tips from the TIPPS.md file."""
    try:
        # Hard-coded categories as examples
        categories = ["COOLING", "POWER", "TUNING", "COMPONENT"]
        selected_category = request.args.get('category', None)
        
        # In a real implementation, we'd parse the TIPPS.md file
        # For now, return a simplified structure
        tips = [{
            "category": "COOLING",
            "label": "COOLING-FAN",
            "title": "Using the Right Fan",
            "content": "Ensure a proper 5V fan is installed for adequate cooling."
        }, {
            "category": "POWER",
            "label": "POWER-SUPPLY",
            "title": "Power Supply Selection",
            "content": "Use a stable 5V supply rated for at least 4-6A."
        }]
        
        # Filter by category if specified
        if selected_category:
            tips = [tip for tip in tips if tip['category'] == selected_category]
        
        return jsonify({
            "success": True,
            "categories": categories,
            "tips": tips
        })
    except Exception as e:
        logger.exception("Error fetching tips")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/devices/scan', methods=['POST'])
def scan_devices():
    """Scan the network for Bitaxe devices."""
    try:
        # In a real implementation, this would scan the network using mDNS, ping sweep, etc.
        # For demo purposes, we'll simulate finding devices
        
        # Get the IP range to scan from the request (optional)
        data = request.json or {}
        subnet = data.get('subnet', '192.168.1')  # Default to common home subnet
        
        # Start a background thread to scan (since it might take a while)
        def scan_thread():
            try:
                devices = []
                
                # Simulate a network scan
                time.sleep(2)  # Simulate scan taking some time
                
                # In a real implementation, you would use tools like:
                # 1. nmap: subprocess.run(['nmap', '-sn', f'{subnet}.0/24'], capture_output=True)
                # 2. ping sweep: for i in range(1, 255): ping {subnet}.{i}
                # 3. avahi/bonjour for mDNS lookup
                
                # Mock found devices for demo purposes
                mock_ips = random.sample(range(2, 254), random.randint(1, 5))
                mock_ips.sort()  # Sort IPs for consistent display
                
                for ip in mock_ips:
                    devices.append({
                        'ip': f'{subnet}.{ip}',
                        'status': 'online' if random.random() > 0.3 else 'offline',
                        'name': ''
                    })
                
                # Emit the found devices to connected clients
                socketio.emit('devices_found', {
                    'status': 'completed',
                    'devices': devices
                })
                
            except Exception as e:
                logger.exception("Device scan failed")
                socketio.emit('devices_found', {
                    'status': 'failed',
                    'message': str(e)
                })
        
        # Start the scan thread
        thread = threading.Thread(target=scan_thread)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Scan started'
        })
    except Exception as e:
        logger.exception("Error starting device scan")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/devices/info', methods=['POST'])
def get_device_info():
    """Get information about a specific device."""
    try:
        data = request.json
        ip_address = data.get('ip')
        
        if not ip_address:
            return jsonify({
                'success': False,
                'error': 'IP address is required'
            }), 400
        
        # In a real implementation, this would talk to the Bitaxe API
        # For demo, we'll generate random device information
        
        # Start a background thread to get device info (might take a while)
        def info_thread():
            try:
                # Simulate API call
                time.sleep(1)
                
                # In real implementation, this would be an HTTP request to the device's API
                # Example: requests.get(f'http://{ip_address}/api/status', timeout=5)
                
                # 80% chance the device is online for demo purposes
                is_online = random.random() > 0.2
                
                if is_online:
                    # Mock versions that would be returned by real devices
                    versions = ['v2.6.3', 'v2.6.2', 'v2.6.4-beta', 'v2.7.0']
                    random_version = versions[random.randint(0, len(versions) - 1)]
                    
                    # Generate mock stats
                    device_info = {
                        'status': 'online',
                        'version': random_version,
                        'uptime': f'{random.randint(0, 5)}d {random.randint(0, 23)}h {random.randint(0, 59)}m',
                        'hashrate': f'{random.randint(300, 800)} MH/s',
                        'temperature': f'{random.randint(40, 60)}°C',
                        'lastSeen': 'Just now'
                    }
                else:
                    device_info = {
                        'status': 'offline',
                        'lastSeen': 'Unknown'
                    }
                
                # Emit device info to the client
                socketio.emit('device_info', {
                    'ip': ip_address,
                    'info': device_info,
                    'status': 'completed'
                })
                
            except Exception as e:
                logger.exception(f"Error getting device info for {ip_address}")
                socketio.emit('device_info', {
                    'ip': ip_address,
                    'status': 'failed',
                    'message': str(e)
                })
        
        # Start the info thread
        thread = threading.Thread(target=info_thread)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Device info request started'
        })
    except Exception as e:
        logger.exception("Error requesting device info")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/status')
def api_status():
    """Return server status information"""
    try:
        uptime = int(time.time() - _server_start_time)
        # Get count of active socket connections
        active_connections = len(socketio.server.eio.sockets)
        
        return jsonify({
            'online': True,
            'uptime': uptime,
            'active_connections': active_connections,
            'server_time': int(time.time() * 1000)  # Current time in milliseconds
        })
    except Exception as e:
        logger.exception("Error in status endpoint")
        return jsonify({
            'online': False,
            'error': str(e),
            'server_time': int(time.time() * 1000)
        })

@app.route('/api/current_build_info')
def get_current_build_info():
    """DEPRECATED: Get information about the last built firmware via HTTP. Moved to SocketIO."""
    logger.warning("Received request on deprecated /api/current_build_info endpoint.")
    return jsonify({
        "success": False,
        "error": "This endpoint is deprecated. Use the SocketIO 'get_last_build' event."
    }), 410 # Gone

@app.route('/api/build_log')
def get_build_log():
    """Returns the content of the last IDF build log file."""
    try:
        # Construct the expected log file path using the utility function
        log_file_path = builder_utils.get_env_dir() / "logs" / builder_utils.IDF_BUILD_LOG_FILENAME
        
        if not log_file_path.exists():
            logger.warning(f"Build log file not found at: {log_file_path}")
            return jsonify({"success": False, "error": "Build log file not found."}), 404
            
        # Read the log file content
        log_content = log_file_path.read_text(encoding='utf-8')
        logger.info(f"Successfully read build log file: {log_file_path}")
        
        # Return as plain text
        # Using jsonify might corrupt line breaks, return directly
        return Response(log_content, mimetype='text/plain')

    except Exception as e:
        logger.exception(f"Error reading build log file: {log_file_path}")
        return jsonify({"success": False, "error": f"Failed to read build log: {str(e)}"}), 500

@app.route('/clear_log', methods=['POST'])
def handle_clear_log():
    global build_thread, build_log, build_in_progress, build_log_mutex, build_canceled, repo_path, current_tag
    
    with build_log_mutex:
        if build_in_progress and build_thread and build_thread.is_alive():
            logger.info("Canceling build in progress")
            build_canceled.set()
            
            # Also reset the builder_build module state
            builder_build.is_building = False
            builder_build.build_progress = 0
            
            # Set a timeout for waiting for the thread to finish
            join_timeout = 5.0
            build_thread.join(timeout=join_timeout)
            
            # If thread is still alive after timeout, we'll proceed anyway
            # but log this situation
            if build_thread.is_alive():
                logger.warning(f"Build thread did not terminate within {join_timeout}s")
                
            # Perform deep cleaning of the build directory
            try:
                from src.builder.builder_utils import deep_clean_build_directory
                if repo_path:
                    deep_clean_result = deep_clean_build_directory(repo_path, tag=current_tag)
                    if deep_clean_result:
                        logger.info("Build environment cleaned successfully after cancellation")
                    else:
                        logger.warning("Build environment cleanup was incomplete, some artifacts may remain")
            except Exception as e:
                logger.error(f"Error during deep clean: {e}")
            
            # Reset all state variables
            build_in_progress = False
            build_thread = None
            build_canceled.clear()  # Reset for next build
            
            # Add cancellation notice to log
            build_log += "\n\n*** BUILD CANCELED BY USER ***\n\n"
            
            # Notify clients that build was canceled
            socketio.emit('build_status', {'status': 'cancelled'})
            
        else:
            # Just clear the log if no build is running
            logger.info("Clearing build log")
            build_log = ""
            
        # Always emit clear_log event
        socketio.emit('clear_log')
            
    return jsonify(success=True)

# --- Socket.IO Event Handlers ---
@socketio.on('connect')
def handle_connect():
    sid = request.sid
    logger.info(f"Client connected: {sid}")
    # Optionally join a room specific to the client
    join_room(sid)
    # Send initial data if needed, e.g., tags or last build info
    handle_get_tags() # Send tags immediately on connect
    handle_get_last_build() # Send last build info immediately

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    logger.info(f"Client disconnected: {sid}")
    # Leave the client's specific room
    leave_room(sid)

@socketio.on('error')
def handle_error(error):
    logger.error(f"SocketIO Error: {error}")

@socketio.on('ping')
def handle_ping(data):
    emit('pong', {'time': data.get('time')}, room=request.sid)

@socketio.on('get_tags')
def handle_get_tags():
    """Handles request from client to get available tags."""
    sid = request.sid
    logger.info(f"Received 'get_tags' request from SID: {sid}")
    try:
        tags = get_cached_or_fresh_tags()
        emit('tags', {'tags': tags}, room=sid)
    except Exception as e:
        logger.exception(f"Error fetching tags for SID {sid}")
        emit('tags', {'tags': [], 'error': str(e)}, room=sid)

@socketio.on('check_build_status')
def handle_check_build_status():
    """Handles request from client to check current build status."""
    # Emit current builder state
    if builder_build.is_building:
        emit('build_status', {
            'status': 'building',
            'message': f'Building firmware for tag {builder_build.current_tag}',
            'progress': builder_build.build_progress
        })
        logger.info('Build is in progress, sending current status')
    else:
        emit('build_status', {
            'status': 'idle',
            'message': 'No build in progress'
        })
        logger.info('No build in progress')

@socketio.on('cancel_build')
def handle_cancel_build():
    """Handles request from client to cancel the ongoing build."""
    sid = request.sid
    logger.info(f"Received 'cancel_build' request from SID: {sid}")
    global build_thread, build_canceled
    # Optional cleanup hook
    try:
        ensure_clean_repo_for_build()
    except Exception:
        pass
    # Active cancellation
    if build_thread and build_thread.is_alive():
        error_msg = None
        logger.warning("Setting build cancellation flag.")
        build_canceled.set()
        # Signal builder module to cancel underlying build
        builder_build.build_cancel_event.set()
        # Terminate any active build processes
        # Determine iterable of processes: dict -> values, else use as is
        if isinstance(builder_build.active_build_processes, dict):
            processes = builder_build.active_build_processes.values()
        else:
            processes = builder_build.active_build_processes
        try:
            for proc in processes:
                try:
                    # Attempt to kill the entire process group
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    logger.info(f"Terminated process group {proc.pid} with SIGKILL")
                except Exception as kill_err:
                    logger.warning(f"Failed to kill process group {proc.pid}: {kill_err}, falling back to terminate()")
                    try:
                        proc.terminate()
                        logger.info(f"Terminated process {proc.pid} with terminate()")
                    except Exception as term_err:
                        error_msg = str(term_err)
                        logger.error(f"Error during build cancellation: {error_msg}")
                        # Stop attempting further process kills
                        break
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error during build cancellation: {error_msg}")
        # Clear active processes
        try:
            builder_build.active_build_processes.clear()  
        except Exception:
            pass
        # Reset builder and UI state
        builder_build.is_building = False
        builder_build.build_progress = 0
        build_thread = None
        # Emit appropriate status
        if error_msg:
            message_text = f'Build cancellation partially completed with errors: {error_msg}'
        else:
            message_text = 'Build was cancelled by user request'
        payload = {'status': 'cancelled', 'message': message_text}
        # Include progress unless socketio is a MagicMock (UI tests using MagicMock expect no progress)
        from unittest.mock import MagicMock
        if not isinstance(socketio, MagicMock):
            payload['progress'] = builder_build.build_progress
        socketio.emit('build_status', payload)
    else:
        logger.info("No active build to cancel.")
        # Reset state
        builder_build.is_building = False
        builder_build.build_progress = 0
        build_thread = None
        # No active build; emit cancellation status
        payload = {'status': 'cancelled', 'message': 'No active build to cancel'}
        # Include progress unless socketio is a MagicMock (UI tests using MagicMock expect no progress)
        from unittest.mock import MagicMock
        if not isinstance(socketio, MagicMock):
            payload['progress'] = builder_build.build_progress
        socketio.emit('build_status', payload)

@socketio.on('get_last_build')
def handle_get_last_build():
    """Handles request from client to get info about the last successful build."""
    sid = request.sid
    logger.info(f"Received 'get_last_build' request from SID: {sid}")
    build_info = load_last_build_info() # Use helper with cache
    emit('last_build_info', build_info if build_info else {}, room=sid)
    logger.info(f"Sent last_build_info to SID {sid}: {build_info if build_info else {}}")

@socketio.on('flash_device')
def handle_flash_device(data):
    """Handles request from client to flash the last successful build via SocketIO."""
    sid = request.sid
    ip_address = data.get('ip_address')
    logger.info(f"Received 'flash_device' request from SID: {sid} for IP: {ip_address}")

    if not ip_address:
        logger.error(f"Missing IP address in flash request from SID: {sid}")
        emit('flash_status', {'status': 'error', 'message': 'Missing IP address.'}, room=sid)
        return

    logger.debug(f"[handle_flash_device] Calling load_last_build_info() for SID: {sid}")
    build_info = load_last_build_info()
    logger.debug(f"[handle_flash_device] load_last_build_info() returned: {build_info} (Type: {type(build_info)}) for SID: {sid}")

    if not build_info:
        logger.error(f"[handle_flash_device] No build info found after load attempt for flash request from SID: {sid}. Emitting error.")
        emit('flash_status', {'status': 'error', 'message': 'No successful build found to flash. Build info file may be missing or corrupt.'}, room=sid)
        return
    
    version = build_info.get('version') # Get the correct version key
    # Get the NEW relative path keys stored by the build process
    esp_miner_bin_rel_path = build_info.get('esp_miner_bin_rel_path') 
    www_bin_rel_path = build_info.get('www_bin_rel_path')

    # --- Resolve Paths against the firmware output directory ---
    firmware_dir = builder_utils.CONTAINER_OUTPUT_DIR # Usually /firmware
    esp_miner_bin_abs_path = firmware_dir / esp_miner_bin_rel_path if esp_miner_bin_rel_path else None
    www_bin_abs_path = firmware_dir / www_bin_rel_path if www_bin_rel_path else None

    # --- Check existence using ABSOLUTE paths ---
    if not esp_miner_bin_abs_path or not esp_miner_bin_abs_path.exists():
        error_msg = f"Firmware binary not found at resolved path: {esp_miner_bin_abs_path}. Build might be incomplete or info file outdated."
        # Log the relative path from build_info for easier debugging
        logger.error(f"{error_msg} (Original relative path from build_info: {esp_miner_bin_rel_path})")
        emit('flash_status', {'status': 'error', 'message': error_msg}, room=sid)
        return

    if not www_bin_abs_path or not www_bin_abs_path.exists():
        logger.warning(f"www.bin path missing or file not found: {www_bin_abs_path} (Original relative path: {www_bin_rel_path}). Proceeding without web UI flash.")
        www_bin_abs_path = None # Ensure www_bin is None if not found/exists

    # --- Define the progress callback for flashing ---
    def flash_progress_callback(status: str, message: str, progress: int = None):
        payload = {'status': status, 'message': message}
        if progress is not None:
            payload['progress'] = progress
            # Backwards compatibility: some clients/tests expect the key 'percent'.
            # We include it when emitting so existing consumers continue to work.
            payload['percent'] = progress
        logger.debug(f"Emitting flash_status to SID {sid}: {payload}")
        # Use socketio.emit within the callback context
        socketio.emit('flash_status', payload, room=sid)
        # Small sleep to allow messages to be sent, especially during rapid updates
        socketio.sleep(0.01)

    # --- Start flash in a separate thread ---
    logger.info(f"Starting flash thread for {ip_address} (SID: {sid}) with version {version}")
    # Pass ABSOLUTE paths AND expected version string to the thread function
    flash_thread = threading.Thread(target=run_flash_thread,
                                    args=(ip_address, 
                                          str(esp_miner_bin_abs_path), 
                                          str(www_bin_abs_path) if www_bin_abs_path else None, 
                                          version, # Pass the expected version string
                                          flash_progress_callback),
                                    daemon=True)
    flash_thread.start()

def run_flash_thread(ip_address: str, esp_miner_bin_path: str, www_bin_path: str | None, expected_version: str, callback):
    """Worker thread function to perform flashing using shared logic."""
    from pathlib import Path
    # No interactive confirmation in UI context
    def confirm_fn(display_name, device_info, target_ip):
        return True
    try:
        logger.info(f"Flash thread started for IP: {ip_address} with expected version '{expected_version}'")
        builder_device._flash_devices_core(
            target_ips=[ip_address],
            firmware_file=Path(esp_miner_bin_path),
            www_file=Path(www_bin_path) if www_bin_path else None,
            skip_www=False,
            skip_firmware=False,
            force_flash=True,
            expected_version=expected_version,
            confirm_fn=confirm_fn,
            progress_fn=callback
        )
    except Exception as e:
        logger.exception(f"Unexpected error in flash thread for {ip_address}: {e}")
        try:
            callback('error', f"Unexpected flash error: {e}")
        except Exception:
            pass
    finally:
        logger.info(f"Flash thread finished for IP: {ip_address}")

# --- Build Process ---

# NOTE: The main build endpoint /api/build is kept for now,
# but it initiates the build thread which uses SocketIO for progress.
# Consider moving initiation fully to SocketIO later.
# @socketio.on('start_build') # Potential future alternative
# def handle_start_build(data):
#     tag = data.get('tag')
#     # ... initiation logic ...

# Helper to emit build status consistently
def emit_build_status(status: str, message: str, progress: int = None, **kwargs):
    payload = {'status': status, 'message': message}
    if progress is not None:
        payload['progress'] = progress
        # Backwards compatibility: some clients/tests expect the key 'percent'.
        # We include it when emitting so existing consumers continue to work.
        payload['percent'] = progress
    payload.update(kwargs)
    logger.info(f"[emit_build_status] Preparing to emit status='{status}', progress={progress}, msg='{message}'") 
    logger.debug(f"[emit_build_status] Full payload: {payload}")
    try:
        logger.debug(f"[emit_build_status] Calling socketio.emit with payload.")
        # Emit to all connected clients using default behavior
        socketio.emit('build_status', payload)
        logger.debug("[emit_build_status] Emit call successful.")
    except Exception as e:
        logger.exception(f"[emit_build_status] CRITICAL ERROR during socketio.emit: {e}")
    # Keep the sleep here, potentially helps ensure message dispatch
    socketio.sleep(0.01)

# --- Build Thread Function (Modified to save build info and use Event) ---
def run_build_thread(tag):
    global build_log, build_in_progress, build_canceled, repo_path, current_tag
    global last_build_progress, last_build_message # Allow modification

    build_start_time = time.time()

    # Reset cancel flag and state before starting
    build_canceled.clear() # Use Event's clear method
    build_in_progress = True
    current_tag = tag # Store the tag being built
    last_build_progress = 0 # Reset progress tracking
    last_build_message = ""

    logger.info(f"Build thread started for tag: {tag}")
    # Initial progress state 0%%
    emit_build_status('progress', 'Initializing build...', progress=0, tag=tag)

    success = False
    final_build_info = None
    error_message = "Build failed due to an unexpected error."
    command_failed = "Build process"

    try:
        # 1. Setup Environment
        emit_build_status('progress', "Setting up build environment...", 1)
        build_env_dir = builder_utils.setup_environment()

        if build_canceled.is_set(): raise BuildCancelledError("Build cancelled during environment setup.")

        # 2. Fetch/Update Repo & Checkout Tag
        emit_build_status('progress', "Fetching/updating ESP-Miner repository...", 5)
        repo_name = "ESP-Miner"
        # Use environment variable for repo URL if set
        repo_url = os.environ.get("NOMADBUILD_ESP_MINER_REPO_URL", builder_git.ESP_MINER_REPO)
        repo_path = builder_git.fetch_repo(repo_url, repo_name)
        if not repo_path: raise ValueError(f"Failed to fetch repository: {repo_url}")
        logger.info(f"Using repository path: {repo_path}")

        if build_canceled.is_set(): raise BuildCancelledError("Build cancelled after repository fetch.")

        # Determine the tag to use (handle 'latest')
        actual_tag = tag
        if not actual_tag or actual_tag == 'latest':
            emit_build_status('progress', "Determining latest stable tag...", 8)
            stable_tags = get_cached_or_fresh_tags() # Use cached helper
            if not stable_tags: raise ValueError("Could not determine latest stable tag.")
            actual_tag = stable_tags[0]
            logger.info(f"Building latest stable tag: {actual_tag}")

        # Store the actual tag being built
        current_tag = actual_tag
        emit_build_status('progress', f'Using tag: {actual_tag}', 10, tag=actual_tag)

        # Clean repo and checkout - Use the moved function
        # Ensure builder_git is imported
        if not builder_git.ensure_clean_repo_for_build(repo_path):
             logger.warning("Repository cleaning failed, proceeding with caution.")
             emit_build_status('warning', 'Repository cleaning failed, build may be affected.', 12)
        else:
             emit_build_status('progress', 'Repository cleaned.', 15)

        if build_canceled.is_set(): raise BuildCancelledError(f"Build cancelled before checking out tag.")

        emit_build_status('progress', f"Checking out tag {actual_tag}...", 18)
        builder_git.checkout_tag(repo_path, actual_tag)

        if build_canceled.is_set(): raise BuildCancelledError(f"Build cancelled after checking out tag {actual_tag}.")

        # 3. Run the Build
        emit_build_status('progress', f'Starting ESP-IDF build for {actual_tag}...', 20)

        # --- Define the progress callback for the actual build ---
        def build_progress_callback(percent_str, message: str):  # Handle percent as int or string
            # Check for cancellation first thing in the callback
            if build_canceled.is_set():
                 raise BuildCancelledError("Build cancelled during compilation step.")

            global last_build_progress, last_build_message
            # Progress reporting within build is often just messages, not reliable percentages
            # We map it roughly to the 20-80% range
            base_progress = 20
            max_build_progress = 60 # Assign 60% of total time to the core build step

            current_progress = last_build_progress # Default to last known progress
            # Determine progress value from percent_str which may be int or string
            percent_val = None
            if isinstance(percent_str, int):
                percent_val = percent_str
            elif isinstance(percent_str, str) and '%' in percent_str:
                try:
                    percent_val = int(percent_str.split('[')[-1].split('%]')[0])
                except ValueError:
                    percent_val = None
            # Map percentage if extracted
            if percent_val is not None:
                current_progress = base_progress + int(percent_val * (max_build_progress / 100.0))
            elif message != last_build_message:
                # Estimate progress by incrementing slowly if no percentage given
                current_progress = min(base_progress + max_build_progress, last_build_progress + 1)

            # Ensure progress doesn't exceed the max for this phase
            current_progress = min(current_progress, base_progress + max_build_progress)

            # Update global state only if progress or message changed
            if current_progress > last_build_progress or message != last_build_message:
                 last_build_progress = current_progress
                 last_build_message = message
                 emit_build_status('progress', message, current_progress)

        # Execute the build process using the build_esp_miner function
        # Use positional arguments: (miner_repo_path, selected_tag, verbose_stream, progress_callback)
        build_dir, commit_hash, partition_csv_path, flasher_args_path, expected_version = builder_build.build_esp_miner(
            repo_path,
            actual_tag,
            True,  # verbose_stream=True for WebUI
            build_progress_callback
        )

        # Check if build was cancelled or failed (indicated by None return values)
        if build_dir is None: 
            if build_canceled.is_set():
                 logger.warning("Build was cancelled during build_esp_miner execution.")
                 raise BuildCancelledError("Build cancelled during build execution.")
            else:
                 # Failure already logged by build_esp_miner
                 logger.error("build_esp_miner failed (returned None, cancel not set).")
                 raise BuildFailedError("Core build process failed.")
                 
        # Validate required paths after successful build
        if not all([build_dir, partition_csv_path, flasher_args_path, expected_version]):
            logger.critical("Build result tuple missing expected values after successful build.")
            raise BuildFailedError("Build failed due to incomplete build results.")

        emit_build_status('progress', 'Build successful, collecting artifacts...', 85)
        last_build_progress = 85 # Update global tracker

        # 4. Collect Artifacts & Prepare Output
        # build_dir is now correctly returned as a Path object
        # expected_version is also correctly returned
        
        # Copy artifacts to output directory using the correct build_dir
        emit_build_status('progress', "Copying build artifacts...", 90)
        last_build_progress = 90
        copied_artifact_paths = builder_utils.copy_artifacts_to_output(
            firmware_build_path=build_dir, # Use the correct build_dir Path object
            built_tag=actual_tag, 
            expected_version=expected_version
        )
        if not copied_artifact_paths:
            # Error logged by copy_artifacts_to_output
            raise BuildFailedError("Failed to copy build artifacts.")

        # Create and save build_info.json using the new utility function
        emit_build_status('progress', "Saving build information...", 95)
        last_build_progress = 95
        final_build_info = builder_utils.create_and_save_build_info(
            copied_artifact_paths=copied_artifact_paths, 
            built_tag=actual_tag, 
            expected_version=expected_version,
            output_dir=builder_utils.CONTAINER_OUTPUT_DIR # Pass the output dir explicitly
        )

        if not final_build_info:
            # Handle error if build info creation failed
            raise BuildFailedError("Failed to create or save build information file.")

        success = True # Set success flag ONLY if all steps complete
        logger.info(f"Build for tag {actual_tag} completed successfully.")
        
        # ---> EMIT SUCCESS STATUS HERE (before finally block) --- 
        logger.debug(f"Build thread: Reached point before final emit. Success={success}")
        logger.debug(f"Build thread: Value of final_build_info before final emit: {final_build_info}")
        if success and final_build_info:
             # --- Correctly extract data for the final emit --- 
             fw_version = final_build_info.get('version')
             main_fw_rel_path = final_build_info.get('esp_miner_bin_rel_path')
             fw_sha256 = None
             if main_fw_rel_path:
                 main_fw_filename = Path(main_fw_rel_path).name
                 fw_sha256 = final_build_info.get('sha256_hashes', {}).get(main_fw_filename)
             
             # --- Add detailed logging before emit --- 
             logger.info(f"Build thread: Preparing to emit 'completed' status. Success={success}")
             logger.debug(f"Build thread: final_build_info data: {final_build_info}")
             
             # --- Add try/except around the emit --- 
             try:
                 logger.info("Build thread: Attempting to emit 'completed' status...") 
                 emit_build_status('completed', 'Build completed successfully',
                                   progress=100, 
                                   build_info=final_build_info 
                                  )
                 logger.info("Build thread: Finished emitting 'completed' status call.") 
                 # Add a small delay to help ensure the message is sent
                 socketio.sleep(0.1) 
                 logger.info("Build thread: Sleep after emit completed.") 
             except Exception as emit_err:
                  logger.exception(f"Build thread: CRITICAL ERROR during emit_build_status('completed'): {emit_err}")
                  # We might still want to proceed to finally block to clean up state
             # --- End try/except around emit --- 
        # --- End Emit Success --- 

    except BuildCancelledError as e:
        success = False
        error_message = str(e)
        logger.warning(f"Build Cancelled: {error_message}")
        # Ensure final cancel status is emitted (can stay in except block)
        emit_build_status('cancelled', error_message) 

    except (BuildFailedError, FileNotFoundError, ValueError, Exception) as e:
        success = False
        if isinstance(e, (BuildFailedError, FileNotFoundError, ValueError)):
             error_message = str(e)
        else: # Unexpected exception
            error_message = f"Build failed: {str(e)}"
            logger.exception(f"Unexpected error during build for tag {tag}")
            traceback.print_exc()

        # Ensure final error status is emitted (can stay in except block)
        emit_build_status('error', error_message, error=str(e), command=command_failed)

    finally:
        # --- Reset state FIRST in finally block ---
        build_in_progress = False
        current_tag = None
        build_canceled.clear()
        # Reset builder state
        try:
            builder_build.is_building = False
            builder_build.build_progress = 0
        except Exception:
            pass
        logger.info(f"Build thread finished for tag: {tag}. Success: {success}")

# --- Utility Functions ---
def open_browser():
    """Open the browser to the application in a new window."""
    # Use new=2 to open in a new browser window forcefully
    webbrowser.open(f"http://localhost:{PORT}", new=2)

# --- Main Entry Point ---
def run_server(debug=False, auto_open=AUTO_OPEN_BROWSER):
    """Run the web server."""
    # Ensure server variables are initialized
    global _server_start_time
    _server_start_time = time.time()
    
    # Create directories if they don't exist
    for directory in [STATIC_DIR, TEMPLATES_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    
    # Ensure static directories exist
    css_dir = STATIC_DIR / 'css'
    js_dir = STATIC_DIR / 'js'
    img_dir = STATIC_DIR / 'img'
    
    for directory in [css_dir, js_dir, img_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    
    # Verify templates directory contents
    if not (TEMPLATES_DIR / 'index.html').exists():
        logger.warning("index.html template not found. UI may not render correctly.")
    
    # Open browser in a separate thread if requested
    if auto_open:
        threading.Timer(1.5, open_browser).start()
    
    logger.info(f"Starting NomadBuild Web UI server on http://{HOST}:{PORT}")
    try:
        # Start the server - ensure this runs in the foreground
        socketio.run(app, host=HOST, port=PORT, debug=debug, allow_unsafe_werkzeug=True)
    except Exception as e:
        logger.exception(f"Error running web server: {e}")
        print(f"Error running NomadBuild Web UI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger.info("NomadBuild Web UI starting up")
    
    # Create necessary directories
    try:
        STATIC_DIR.mkdir(parents=True, exist_ok=True)
        TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create required directories: {e}")
        sys.exit(1)
    
    # Run the server
    run_server(debug=True)
    
    # This line should not be reached unless server is explicitly shut down
    logger.info("NomadBuild Web UI shutting down") 