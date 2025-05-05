# Backlog Item: Implement CSV-Based Multi-Device Flashing

## Description
Implement a feature to allow flashing multiple devices by specifying a CSV file with IP addresses using the `--flash-csv` parameter.

## Requirements
1. Add a new command-line parameter `--flash-csv` that accepts a path to a CSV file
2. The CSV file should contain one IP address per line
3. Display the number of configured IP addresses before flashing starts
4. Ask the user interactively if they want to update all devices automatically
5. For each device, verify that it's one of the supported models before flashing
6. Skip flashing and do not make any changes if the device model cannot be verified
7. Show update details for each device as they are happening
8. Make the update/flash progress foolproof and user-friendly
9. Ensure success and failure messages are easily distinguishable
10. Implement comprehensive test cases for the CSV parsing functionality

## Implementation Details

### CSV File Format
- Simple format with one IP address per line
- No headers required
- Example:
  ```
  192.168.1.100
  192.168.1.101
  192.168.1.102
  ```

### Command-Line Interface
- Add `--flash-csv` parameter to `_parse_arguments()` in `src/builder/cli.py`
- Update `nomadbuild.sh` to pass the parameter to the Docker container

### CSV Parsing
- Create a new function to parse the CSV file and extract IP addresses
- Validate IP addresses for correct format
- Handle potential errors (file not found, invalid format, etc.)

### Flashing Process
- Modify `_handle_flashing()` in `src/builder/device.py` to handle both `--flash-ip` and `--flash-csv` parameters
- Display the number of devices to be flashed and ask for confirmation
- Implement batch confirmation to avoid asking for each device
- Maintain the existing device verification logic for each IP address
- Ensure clear progress reporting for each device

### Testing
- Add unit tests for CSV parsing
- Add integration tests for the flashing process with multiple devices
- Test error handling for various edge cases

## Acceptance Criteria
1. User can specify a CSV file with IP addresses using `--flash-csv`
2. The number of devices to be flashed is displayed before flashing starts
3. User is asked for confirmation before flashing multiple devices
4. Each device is verified before flashing
5. Update details are shown for each device during the flashing process
6. Success and failure messages are clearly distinguishable
7. All tests pass, including new tests for CSV parsing and multi-device flashing

## Example Test Cases

### CSV Parsing Tests
```python
def test_parse_csv_file_valid():
    """Test parsing a valid CSV file with IP addresses."""
    # Create a temporary CSV file with valid IP addresses
    csv_file = create_temp_csv_file(["192.168.1.100", "192.168.1.101"])
    
    # Parse the CSV file
    ip_addresses = parse_csv_file(csv_file)
    
    # Verify the parsed IP addresses
    assert len(ip_addresses) == 2
    assert "192.168.1.100" in ip_addresses
    assert "192.168.1.101" in ip_addresses

def test_parse_csv_file_invalid_ip():
    """Test parsing a CSV file with invalid IP addresses."""
    # Create a temporary CSV file with invalid IP addresses
    csv_file = create_temp_csv_file(["192.168.1.100", "invalid_ip"])
    
    # Parse the CSV file
    ip_addresses = parse_csv_file(csv_file)
    
    # Verify that only valid IP addresses are returned
    assert len(ip_addresses) == 1
    assert "192.168.1.100" in ip_addresses
```

### Multi-Device Flashing Tests
```python
def test_flash_multiple_devices_success(monkeypatch):
    """Test flashing multiple devices successfully."""
    # Mock device verification and flashing functions
    monkeypatch.setattr('src.builder.device.verify_bitaxe_target', lambda ip: ({'hostname': f'device-{ip}'}, 'ModelX'))
    monkeypatch.setattr('src.builder.device.upload_to_bitaxe', lambda ip, endpoint, file_path, desc: True)
    monkeypatch.setattr('src.builder.device.verify_flash_success', lambda ip, ver: True)
    
    # Create a temporary CSV file with IP addresses
    csv_file = create_temp_csv_file(["192.168.1.100", "192.168.1.101"])
    
    # Mock user confirmation
    monkeypatch.setattr('builtins.input', lambda _: 'y')
    
    # Flash the devices
    result = flash_devices_from_csv(csv_file, "firmware.bin", "www.bin", "v1.0.0")
    
    # Verify the result
    assert result.success_count == 2
    assert result.failure_count == 0

def test_flash_multiple_devices_with_failures(monkeypatch):
    """Test flashing multiple devices with some failures."""
    # Mock device verification and flashing functions
    def mock_verify(ip):
        if ip == "192.168.1.100":
            return ({'hostname': f'device-{ip}'}, 'ModelX')
        return None, None
    
    monkeypatch.setattr('src.builder.device.verify_bitaxe_target', mock_verify)
    monkeypatch.setattr('src.builder.device.upload_to_bitaxe', lambda ip, endpoint, file_path, desc: True)
    monkeypatch.setattr('src.builder.device.verify_flash_success', lambda ip, ver: True)
    
    # Create a temporary CSV file with IP addresses
    csv_file = create_temp_csv_file(["192.168.1.100", "192.168.1.101"])
    
    # Mock user confirmation
    monkeypatch.setattr('builtins.input', lambda _: 'y')
    
    # Flash the devices
    result = flash_devices_from_csv(csv_file, "firmware.bin", "www.bin", "v1.0.0")
    
    # Verify the result
    assert result.success_count == 1
    assert result.failure_count == 1
```
