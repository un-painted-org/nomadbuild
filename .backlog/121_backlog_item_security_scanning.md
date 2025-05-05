# Backlog Item 121: Add Security Scanning for Docker Images

## Description

This backlog item focuses on implementing security scanning for Docker images to identify and mitigate potential security vulnerabilities. Currently, there's no security scanning to verify that the optimization doesn't introduce security vulnerabilities, which is especially important when modifying the Dockerfile and changing the packages included in the image.

## Requirements

1. Implement security scanning for Docker images
2. Check for known vulnerabilities in packages
3. Verify minimal attack surface in optimized image
4. Scan for sensitive information in the image
5. Create security reports for each build

## Implementation Details

### Current Issues

There's currently no security scanning to verify that the optimization doesn't introduce security vulnerabilities. This is especially important when modifying the Dockerfile and changing the packages included in the image.

### Proposed Solution

1. **Implement Security Scanning**: Use tools like Trivy, Clair, or Docker Scout to scan Docker images for vulnerabilities.

```python
def scan_image_with_trivy():
    """Scan the Docker image with Trivy."""
    print("Scanning Docker image with Trivy...")
    
    # Get the image name
    image_name = "nomadbuild:latest"
    
    # Run Trivy scan
    result = subprocess.run(
        ["trivy", "image", "--severity", "HIGH,CRITICAL", image_name],
        capture_output=True,
        text=True
    )
    
    # Check for vulnerabilities
    if "Total: 0" in result.stdout:
        print(f"✅ No HIGH or CRITICAL vulnerabilities found")
        return True
    else:
        print(f"❌ Vulnerabilities found:")
        print(result.stdout)
        return False
```

2. **Check for Known Vulnerabilities**: Check for known vulnerabilities in packages installed in the image.

```python
def check_package_vulnerabilities():
    """Check for known vulnerabilities in packages."""
    print("Checking for known vulnerabilities in packages...")
    
    # Get the list of installed packages
    result = subprocess.run(
        ["apt", "list", "--installed"],
        capture_output=True,
        text=True
    )
    
    # Parse the list of installed packages
    installed_packages = []
    for line in result.stdout.splitlines():
        if "/" in line:
            package = line.split("/")[0]
            installed_packages.append(package)
    
    # Check each package for known vulnerabilities
    vulnerable_packages = []
    for package in installed_packages:
        # Use a vulnerability database API to check for vulnerabilities
        # This is a simplified example; in practice, you would use a real vulnerability database
        if is_package_vulnerable(package):
            vulnerable_packages.append(package)
    
    if vulnerable_packages:
        print(f"❌ Vulnerable packages found:")
        for package in vulnerable_packages:
            print(f"  {package}")
        return False
    
    print(f"✅ No known vulnerabilities found in installed packages")
    return True

def is_package_vulnerable(package):
    """Check if a package is vulnerable."""
    # This is a simplified example; in practice, you would use a real vulnerability database
    # For now, we'll just return False for all packages
    return False
```

3. **Verify Minimal Attack Surface**: Verify that the optimized image has a minimal attack surface.

```python
def verify_minimal_attack_surface():
    """Verify that the optimized image has a minimal attack surface."""
    print("Verifying minimal attack surface...")
    
    # Check for unnecessary packages
    unnecessary_packages = [
        "gcc", "g++", "make", "cmake", "ninja",
        "gdb", "valgrind", "strace", "ltrace",
        "netcat", "nmap", "telnet", "ftp"
    ]
    
    # Check if any unnecessary packages are installed
    installed_unnecessary_packages = []
    for package in unnecessary_packages:
        result = subprocess.run(
            ["which", package],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            installed_unnecessary_packages.append(package)
    
    if installed_unnecessary_packages:
        print(f"❌ Unnecessary packages found:")
        for package in installed_unnecessary_packages:
            print(f"  {package}")
        return False
    
    # Check for unnecessary open ports
    result = subprocess.run(
        ["netstat", "-tulpn"],
        capture_output=True,
        text=True
    )
    
    # Parse the list of open ports
    open_ports = []
    for line in result.stdout.splitlines():
        if "LISTEN" in line:
            port = line.split()[3].split(":")[-1]
            open_ports.append(port)
    
    # Check for unnecessary open ports
    unnecessary_open_ports = []
    for port in open_ports:
        if port != "9090":  # The only port that should be open is 9090
            unnecessary_open_ports.append(port)
    
    if unnecessary_open_ports:
        print(f"❌ Unnecessary open ports found:")
        for port in unnecessary_open_ports:
            print(f"  {port}")
        return False
    
    print(f"✅ Image has minimal attack surface")
    return True
```

4. **Scan for Sensitive Information**: Scan the image for sensitive information like API keys, passwords, or private keys.

```python
def scan_for_sensitive_information():
    """Scan the image for sensitive information."""
    print("Scanning for sensitive information...")
    
    # Patterns to look for
    patterns = [
        r"password\s*=\s*['\"]([^'\"]+)['\"]",
        r"api[_-]?key\s*=\s*['\"]([^'\"]+)['\"]",
        r"secret\s*=\s*['\"]([^'\"]+)['\"]",
        r"-----BEGIN PRIVATE KEY-----",
        r"-----BEGIN RSA PRIVATE KEY-----",
        r"-----BEGIN DSA PRIVATE KEY-----",
        r"-----BEGIN EC PRIVATE KEY-----"
    ]
    
    # Files to exclude from scanning
    exclude_files = [
        "/app/src/tests",
        "/app/docs"
    ]
    
    # Scan the filesystem for sensitive information
    sensitive_files = []
    for root, dirs, files in os.walk("/"):
        # Skip excluded directories
        if any(root.startswith(exclude) for exclude in exclude_files):
            continue
        
        for file in files:
            # Skip binary files
            if file.endswith((".so", ".pyc", ".pyo", ".bin", ".exe")):
                continue
            
            file_path = os.path.join(root, file)
            
            try:
                # Try to read the file as text
                with open(file_path, "r") as f:
                    content = f.read()
                
                # Check for sensitive information
                for pattern in patterns:
                    if re.search(pattern, content):
                        sensitive_files.append(file_path)
                        break
            except:
                # Skip files that can't be read as text
                pass
    
    if sensitive_files:
        print(f"❌ Sensitive information found in {len(sensitive_files)} files:")
        for file in sensitive_files[:10]:  # Show only the first 10 files
            print(f"  {file}")
        if len(sensitive_files) > 10:
            print(f"  ... and {len(sensitive_files) - 10} more")
        return False
    
    print(f"✅ No sensitive information found")
    return True
```

5. **Create Security Reports**: Create security reports for each build.

```python
def create_security_report():
    """Create a security report for the build."""
    print("Creating security report...")
    
    # Run all security checks
    security_checks = {
        "trivy_scan": scan_image_with_trivy(),
        "package_vulnerabilities": check_package_vulnerabilities(),
        "minimal_attack_surface": verify_minimal_attack_surface(),
        "sensitive_information": scan_for_sensitive_information()
    }
    
    # Create the security report
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "image": "nomadbuild:latest",
        "security_checks": security_checks,
        "overall_result": all(security_checks.values())
    }
    
    # Save the report to a file
    report_file = "/app/security_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"✅ Security report created: {report_file}")
    
    # Print the overall result
    if report["overall_result"]:
        print(f"✅ All security checks passed")
    else:
        print(f"❌ Some security checks failed")
    
    return report
```

## Testing

The changes should be tested by:

1. Building the Docker image with the security scanning tools
2. Running the verification script to scan the image for vulnerabilities
3. Checking for known vulnerabilities in packages
4. Verifying that the image has a minimal attack surface
5. Scanning for sensitive information in the image
6. Creating and reviewing security reports

## Acceptance Criteria

- Security scanning is implemented for Docker images
- Known vulnerabilities in packages are checked
- The image is verified to have a minimal attack surface
- Sensitive information is scanned for in the image
- Security reports are created for each build
- The verification script reports detailed results of the security scanning
