# Backlog Item 105: Implement NerdQAxe Support

## Description

This backlog item focuses on adding support for the NerdQAxe product family to the NomadBuild system. The implementation will include device detection logic, a consolidated UI for device selection, dynamic loading of firmware tags from repositories, and comprehensive testing with NerdQAxe hardware.

## Requirements

1. Add support for the NerdQAxe product family
2. Implement device detection logic
3. Consolidate build UI into "pick your device type" interface
4. Dynamically load latest tags from NerdQAxe/Bitaxe repositories
5. Implement single "pick your desired tag" option for firmware selection
6. Test with NerdQAxe hardware

## Implementation Details

### 1. NerdQAxe Product Family Support

The NerdQAxe product family includes several variants that need to be supported:

- NerdQAxe Basic
- NerdQAxe Pro
- NerdQAxe Ultra
- Future NerdQAxe variants

For each variant, we need to:

- Define device specifications (e.g., memory size, CPU type, peripherals)
- Identify compatible firmware versions
- Specify flashing parameters
- Document device-specific features and limitations

Example device specification:
```python
NERDQAXE_DEVICES = {
    "nerdqaxe_basic": {
        "name": "NerdQAxe Basic",
        "description": "Entry-level NerdQAxe mining device",
        "memory_size": "4MB",
        "cpu": "ESP32-S3",
        "repository": "shufps/nerdqaxe-firmware",
        "compatible_tags": ["v*"],
        "flash_params": {
            "flash_mode": "dio",
            "flash_size": "4MB",
            "flash_freq": "80m"
        }
    },
    "nerdqaxe_pro": {
        "name": "NerdQAxe Pro",
        "description": "Mid-range NerdQAxe mining device",
        "memory_size": "8MB",
        "cpu": "ESP32-S3",
        "repository": "shufps/nerdqaxe-firmware",
        "compatible_tags": ["v*-pro"],
        "flash_params": {
            "flash_mode": "dio",
            "flash_size": "8MB",
            "flash_freq": "80m"
        }
    },
    "nerdqaxe_ultra": {
        "name": "NerdQAxe Ultra",
        "description": "High-end NerdQAxe mining device",
        "memory_size": "16MB",
        "cpu": "ESP32-S3",
        "repository": "shufps/nerdqaxe-firmware",
        "compatible_tags": ["v*-ultra"],
        "flash_params": {
            "flash_mode": "dio",
            "flash_size": "16MB",
            "flash_freq": "80m"
        }
    }
}
```

### 2. Device Detection Logic

Implement logic to detect the connected device type automatically:

- Use a hierarchical approach to device detection:
  1. Check `deviceModel` first (e.g., "NerdQAxe Basic", "NerdQAxe Pro")
  2. If not available, check `minerModel` (e.g., "NerdQAxe")
  3. If not available, check `boardVersion` (e.g., "v1.0", "v2.0")
  4. If not available, check `ASICModel` (e.g., "BM1366", "BM1397")

- Implement fallback mechanisms if automatic detection fails
- Allow manual override of detected device type

Example implementation:
```python
def detect_device_type(device_info):
    """Detect the device type from device information."""
    # Check deviceModel first
    if "deviceModel" in device_info:
        device_model = device_info["deviceModel"].lower()
        if "nerdqaxe basic" in device_model:
            return "nerdqaxe_basic"
        elif "nerdqaxe pro" in device_model:
            return "nerdqaxe_pro"
        elif "nerdqaxe ultra" in device_model:
            return "nerdqaxe_ultra"
    
    # Check minerModel next
    if "minerModel" in device_info:
        miner_model = device_info["minerModel"].lower()
        if "nerdqaxe" in miner_model:
            # Default to basic if we only know it's a NerdQAxe
            return "nerdqaxe_basic"
    
    # Check boardVersion
    if "boardVersion" in device_info:
        board_version = device_info["boardVersion"].lower()
        if "v1.0" in board_version:
            return "nerdqaxe_basic"
        elif "v2.0" in board_version:
            return "nerdqaxe_pro"
        elif "v3.0" in board_version:
            return "nerdqaxe_ultra"
    
    # Check ASICModel as last resort
    if "ASICModel" in device_info:
        asic_model = device_info["ASICModel"].lower()
        if "bm1366" in asic_model:
            return "nerdqaxe_basic"
        elif "bm1397" in asic_model:
            return "nerdqaxe_pro"
    
    # Default to unknown if we can't determine the device type
    return "unknown"
```

### 3. Consolidated Build UI

Redesign the build UI to consolidate the current default build screen into a "pick your device type" interface:

- Create a unified device selection screen
- Group devices by family (Bitaxe, NerdQAxe, etc.)
- Show device details (description, specifications, etc.)
- Provide visual indicators for detected devices
- Allow filtering and searching for devices

Example UI mockup:
```html
<div class="device-selection">
  <h2>Select Your Device</h2>
  
  <div class="device-filters">
    <button class="filter-btn active" data-filter="all">All Devices</button>
    <button class="filter-btn" data-filter="bitaxe">Bitaxe Family</button>
    <button class="filter-btn" data-filter="nerdqaxe">NerdQAxe Family</button>
    <button class="filter-btn" data-filter="detected">Detected Devices</button>
  </div>
  
  <div class="device-grid">
    <!-- Bitaxe Devices -->
    <div class="device-card" data-family="bitaxe">
      <div class="device-icon">
        <img src="/static/img/bitaxe.png" alt="Bitaxe">
      </div>
      <div class="device-info">
        <h3>Bitaxe</h3>
        <p>Original Bitaxe mining device</p>
        <ul>
          <li>Memory: 4MB</li>
          <li>CPU: ESP32</li>
        </ul>
      </div>
      <button class="select-btn">Select</button>
    </div>
    
    <!-- NerdQAxe Devices -->
    <div class="device-card detected" data-family="nerdqaxe">
      <div class="device-icon">
        <img src="/static/img/nerdqaxe_basic.png" alt="NerdQAxe Basic">
        <span class="detected-badge">Detected</span>
      </div>
      <div class="device-info">
        <h3>NerdQAxe Basic</h3>
        <p>Entry-level NerdQAxe mining device</p>
        <ul>
          <li>Memory: 4MB</li>
          <li>CPU: ESP32-S3</li>
        </ul>
      </div>
      <button class="select-btn">Select</button>
    </div>
    
    <div class="device-card" data-family="nerdqaxe">
      <div class="device-icon">
        <img src="/static/img/nerdqaxe_pro.png" alt="NerdQAxe Pro">
      </div>
      <div class="device-info">
        <h3>NerdQAxe Pro</h3>
        <p>Mid-range NerdQAxe mining device</p>
        <ul>
          <li>Memory: 8MB</li>
          <li>CPU: ESP32-S3</li>
        </ul>
      </div>
      <button class="select-btn">Select</button>
    </div>
    
    <div class="device-card" data-family="nerdqaxe">
      <div class="device-icon">
        <img src="/static/img/nerdqaxe_ultra.png" alt="NerdQAxe Ultra">
      </div>
      <div class="device-info">
        <h3>NerdQAxe Ultra</h3>
        <p>High-end NerdQAxe mining device</p>
        <ul>
          <li>Memory: 16MB</li>
          <li>CPU: ESP32-S3</li>
        </ul>
      </div>
      <button class="select-btn">Select</button>
    </div>
  </div>
</div>
```

### 4. Dynamic Tag Loading

Implement functionality to dynamically load the latest tags from the NerdQAxe and Bitaxe repositories:

- Use the GitHub API to fetch tags from repositories
- Filter tags based on device compatibility
- Sort tags by version (newest first)
- Cache tags to reduce API calls
- Handle API rate limiting and errors

Example implementation:
```python
def fetch_repository_tags(repository, cache_duration=3600):
    """Fetch tags from a GitHub repository with caching."""
    cache_key = f"repo_tags_{repository}"
    cached_tags = cache.get(cache_key)
    
    if cached_tags:
        return cached_tags
    
    try:
        # Fetch tags from GitHub API
        url = f"https://api.github.com/repos/{repository}/tags"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Parse tags from response
        tags = []
        for tag in response.json():
            tags.append({
                "name": tag["name"],
                "commit": tag["commit"]["sha"],
                "zipball_url": tag["zipball_url"],
                "tarball_url": tag["tarball_url"]
            })
        
        # Sort tags by version (newest first)
        tags.sort(key=lambda t: parse_version(t["name"]), reverse=True)
        
        # Cache tags
        cache.set(cache_key, tags, cache_duration)
        
        return tags
    except Exception as e:
        logging.error(f"Error fetching tags for {repository}: {str(e)}")
        return []

def get_compatible_tags(device_type):
    """Get compatible tags for a device type."""
    device = NERDQAXE_DEVICES.get(device_type)
    if not device:
        return []
    
    repository = device.get("repository")
    if not repository:
        return []
    
    # Fetch all tags from the repository
    all_tags = fetch_repository_tags(repository)
    
    # Filter tags based on device compatibility
    compatible_tags = []
    for tag in all_tags:
        # Check if tag matches any of the compatible tag patterns
        for pattern in device.get("compatible_tags", []):
            if fnmatch.fnmatch(tag["name"], pattern):
                compatible_tags.append(tag)
                break
    
    return compatible_tags
```

### 5. Tag Selection UI

Implement a single "pick your desired tag" option for firmware selection:

- Show a list of compatible tags for the selected device
- Display tag details (version, release date, etc.)
- Highlight recommended tags
- Allow filtering and searching for tags
- Provide a preview of the firmware features

Example UI mockup:
```html
<div class="tag-selection">
  <h2>Select Firmware Version for NerdQAxe Basic</h2>
  
  <div class="tag-filters">
    <button class="filter-btn active" data-filter="all">All Versions</button>
    <button class="filter-btn" data-filter="stable">Stable Releases</button>
    <button class="filter-btn" data-filter="beta">Beta Releases</button>
    <input type="text" class="search-input" placeholder="Search versions...">
  </div>
  
  <div class="tag-list">
    <div class="tag-item recommended">
      <div class="tag-info">
        <h3>v1.2.0</h3>
        <span class="tag-badge recommended">Recommended</span>
        <p>Released on: May 15, 2023</p>
        <p>Stable release with performance improvements</p>
      </div>
      <button class="select-btn">Select</button>
    </div>
    
    <div class="tag-item">
      <div class="tag-info">
        <h3>v1.1.0</h3>
        <p>Released on: April 2, 2023</p>
        <p>Added support for new mining pools</p>
      </div>
      <button class="select-btn">Select</button>
    </div>
    
    <div class="tag-item">
      <div class="tag-info">
        <h3>v1.0.0</h3>
        <p>Released on: March 10, 2023</p>
        <p>Initial stable release</p>
      </div>
      <button class="select-btn">Select</button>
    </div>
    
    <div class="tag-item beta">
      <div class="tag-info">
        <h3>v1.3.0-beta</h3>
        <span class="tag-badge beta">Beta</span>
        <p>Released on: June 1, 2023</p>
        <p>Beta release with experimental features</p>
      </div>
      <button class="select-btn">Select</button>
    </div>
  </div>
</div>
```

### 6. Testing with NerdQAxe Hardware

Implement comprehensive testing with NerdQAxe hardware:

- Test device detection with various NerdQAxe models
- Verify firmware compatibility with each device type
- Test the build process for NerdQAxe firmware
- Test the flashing process with NerdQAxe devices
- Verify device functionality after flashing

Example test plan:
```
1. Device Detection Tests
   - Test with NerdQAxe Basic
   - Test with NerdQAxe Pro
   - Test with NerdQAxe Ultra
   - Test with unknown device (should default to manual selection)

2. Firmware Compatibility Tests
   - Verify compatible tags for each device type
   - Test with various firmware versions
   - Verify incompatible firmware is filtered out

3. Build Process Tests
   - Test building firmware for each device type
   - Verify build artifacts are correct
   - Test with various build options

4. Flashing Process Tests
   - Test flashing firmware to each device type
   - Verify flashing parameters are correct
   - Test error handling during flashing

5. Functionality Tests
   - Verify device functionality after flashing
   - Test mining performance
   - Test device-specific features
```

## Testing

The changes should be tested by:

1. **Unit Testing**:
   - Test device detection logic
   - Test tag fetching and filtering
   - Test UI components

2. **Integration Testing**:
   - Test the entire workflow from device selection to firmware building
   - Verify integration with existing components
   - Test with various device types and firmware versions

3. **Hardware Testing**:
   - Test with actual NerdQAxe hardware
   - Verify device detection and compatibility
   - Test flashing and functionality

## Acceptance Criteria

- NerdQAxe product family is fully supported
- Device detection logic correctly identifies NerdQAxe devices
- Build UI is consolidated into a "pick your device type" interface
- Latest tags are dynamically loaded from NerdQAxe/Bitaxe repositories
- Single "pick your desired tag" option is implemented for firmware selection
- All tests pass with NerdQAxe hardware
- User can successfully build and flash firmware for NerdQAxe devices
