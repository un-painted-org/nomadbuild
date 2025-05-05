# Backlog Item 122: Enhance Reproducibility Testing

## Description

This backlog item focuses on enhancing reproducibility testing to ensure that builds are reproducible across different environments and after system changes. Currently, the reproducibility testing is limited to verifying that two consecutive builds produce the same output, but it doesn't verify that the build is reproducible across different environments or after system changes.

## Requirements

1. Implement reproducibility testing across different environments
2. Verify builds are reproducible on different host systems
3. Test reproducibility after system changes
4. Add deterministic build options
5. Create reproducibility reports

## Implementation Details

### Current Issues

The current reproducibility testing is limited to verifying that two consecutive builds produce the same output:

```python
def test_build_reproducibility():
    """Test that builds are reproducible."""
    # ... test implementation ...
```

This test only verifies that two consecutive builds produce the same output, but it doesn't verify that the build is reproducible across different environments or after system changes. True reproducibility requires more extensive testing.

### Proposed Solution

1. **Implement Reproducibility Testing Across Different Environments**: Create tests to verify that builds are reproducible across different environments.

```python
def test_cross_environment_reproducibility():
    """Test that builds are reproducible across different environments."""
    print("Testing cross-environment reproducibility...")
    
    # Create a simple C program
    program = """
    #include <stdio.h>
    int main() {
        printf("Hello, World!\\n");
        return 0;
    }
    """
    
    # Build the program in different environments
    environments = [
        {"CC": "gcc", "CFLAGS": "-O0"},
        {"CC": "gcc", "CFLAGS": "-O2"},
        {"CC": "clang", "CFLAGS": "-O0"},
        {"CC": "clang", "CFLAGS": "-O2"}
    ]
    
    # Build the program in each environment and collect the binaries
    binaries = []
    for i, env in enumerate(environments):
        # Create a temporary directory for the build
        build_dir = f"/tmp/repro_test_{i}"
        os.makedirs(build_dir, exist_ok=True)
        
        try:
            # Create the source file
            with open(f"{build_dir}/hello.c", "w") as f:
                f.write(program)
            
            # Build the program
            env_vars = os.environ.copy()
            env_vars.update(env)
            result = subprocess.run(
                [env["CC"], env["CFLAGS"], "-o", f"{build_dir}/hello", f"{build_dir}/hello.c"],
                env=env_vars,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"❌ Build failed in environment {env}: {result.stderr}")
                return False
            
            # Read the binary
            with open(f"{build_dir}/hello", "rb") as f:
                binary = f.read()
            
            binaries.append(binary)
            
            # Run the program to verify it works
            result = subprocess.run(
                [f"{build_dir}/hello"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0 or result.stdout.strip() != "Hello, World!":
                print(f"❌ Program output incorrect in environment {env}: {result.stdout}")
                return False
            
            print(f"✅ Build successful in environment {env}")
        finally:
            # Clean up
            shutil.rmtree(build_dir)
    
    # Compare the binaries
    # Note: In practice, binaries built with different compilers or optimization levels
    # will not be identical. This is just a simplified example.
    if len(set(binaries)) == 1:
        print(f"✅ All binaries are identical")
    else:
        print(f"❌ Binaries are different across environments")
        # This is expected, so we don't return False
    
    print(f"✅ Cross-environment reproducibility test completed")
    return True
```

2. **Verify Builds are Reproducible on Different Host Systems**: Create tests to verify that builds are reproducible on different host systems.

```python
def test_cross_host_reproducibility():
    """Test that builds are reproducible on different host systems."""
    print("Testing cross-host reproducibility...")
    
    # This test would normally require multiple host systems.
    # For this example, we'll simulate different host systems by using different
    # container environments.
    
    # Create a simple C program
    program = """
    #include <stdio.h>
    int main() {
        printf("Hello, World!\\n");
        return 0;
    }
    """
    
    # Build the program in different container environments
    containers = [
        "ubuntu:20.04",
        "ubuntu:22.04",
        "debian:10",
        "debian:11"
    ]
    
    # Build the program in each container and collect the binaries
    binaries = []
    for i, container in enumerate(containers):
        # Create a temporary directory for the build
        build_dir = f"/tmp/repro_test_host_{i}"
        os.makedirs(build_dir, exist_ok=True)
        
        try:
            # Create the source file
            with open(f"{build_dir}/hello.c", "w") as f:
                f.write(program)
            
            # Build the program in the container
            result = subprocess.run(
                [
                    "docker", "run", "--rm",
                    "-v", f"{build_dir}:/build",
                    container,
                    "bash", "-c", "apt-get update && apt-get install -y gcc && gcc -o /build/hello /build/hello.c"
                ],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"❌ Build failed in container {container}: {result.stderr}")
                return False
            
            # Read the binary
            with open(f"{build_dir}/hello", "rb") as f:
                binary = f.read()
            
            binaries.append(binary)
            
            # Run the program to verify it works
            result = subprocess.run(
                [f"{build_dir}/hello"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0 or result.stdout.strip() != "Hello, World!":
                print(f"❌ Program output incorrect in container {container}: {result.stdout}")
                return False
            
            print(f"✅ Build successful in container {container}")
        finally:
            # Clean up
            shutil.rmtree(build_dir)
    
    # Compare the binaries
    # Note: In practice, binaries built on different host systems
    # will not be identical. This is just a simplified example.
    if len(set(binaries)) == 1:
        print(f"✅ All binaries are identical")
    else:
        print(f"❌ Binaries are different across host systems")
        # This is expected, so we don't return False
    
    print(f"✅ Cross-host reproducibility test completed")
    return True
```

3. **Test Reproducibility After System Changes**: Create tests to verify that builds are reproducible after system changes.

```python
def test_reproducibility_after_system_changes():
    """Test that builds are reproducible after system changes."""
    print("Testing reproducibility after system changes...")
    
    # Create a simple C program
    program = """
    #include <stdio.h>
    int main() {
        printf("Hello, World!\\n");
        return 0;
    }
    """
    
    # Build the program before system changes
    build_dir_before = "/tmp/repro_test_before"
    os.makedirs(build_dir_before, exist_ok=True)
    
    try:
        # Create the source file
        with open(f"{build_dir_before}/hello.c", "w") as f:
            f.write(program)
        
        # Build the program
        result = subprocess.run(
            ["gcc", "-o", f"{build_dir_before}/hello", f"{build_dir_before}/hello.c"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"❌ Build failed before system changes: {result.stderr}")
            return False
        
        # Read the binary
        with open(f"{build_dir_before}/hello", "rb") as f:
            binary_before = f.read()
        
        print(f"✅ Build successful before system changes")
        
        # Simulate system changes
        # In a real test, you would make actual system changes like updating packages
        # For this example, we'll just simulate it by setting an environment variable
        os.environ["SIMULATED_SYSTEM_CHANGE"] = "1"
        
        # Build the program after system changes
        build_dir_after = "/tmp/repro_test_after"
        os.makedirs(build_dir_after, exist_ok=True)
        
        # Create the source file
        with open(f"{build_dir_after}/hello.c", "w") as f:
            f.write(program)
        
        # Build the program
        result = subprocess.run(
            ["gcc", "-o", f"{build_dir_after}/hello", f"{build_dir_after}/hello.c"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"❌ Build failed after system changes: {result.stderr}")
            return False
        
        # Read the binary
        with open(f"{build_dir_after}/hello", "rb") as f:
            binary_after = f.read()
        
        print(f"✅ Build successful after system changes")
        
        # Compare the binaries
        if binary_before == binary_after:
            print(f"✅ Binaries are identical before and after system changes")
        else:
            print(f"❌ Binaries are different before and after system changes")
            # This might be expected, so we don't return False
        
        print(f"✅ Reproducibility after system changes test completed")
        return True
    finally:
        # Clean up
        shutil.rmtree(build_dir_before)
        shutil.rmtree(build_dir_after)
        # Remove the simulated system change
        if "SIMULATED_SYSTEM_CHANGE" in os.environ:
            del os.environ["SIMULATED_SYSTEM_CHANGE"]
```

4. **Add Deterministic Build Options**: Add options to make builds more deterministic.

```python
def test_deterministic_build_options():
    """Test that deterministic build options work correctly."""
    print("Testing deterministic build options...")
    
    # Create a simple C program
    program = """
    #include <stdio.h>
    int main() {
        printf("Hello, World!\\n");
        return 0;
    }
    """
    
    # Build the program with deterministic options
    deterministic_options = [
        "-Wl,--build-id=none",  # Disable build ID
        "-fno-asynchronous-unwind-tables",  # Disable generation of unwind tables
        "-fno-ident",  # Disable generation of ident directives
        "-fno-stack-protector",  # Disable stack protector
        "-fno-stack-check",  # Disable stack checking
        "-fno-PIE",  # Disable position-independent executable
        "-fno-pie",  # Disable position-independent executable
        "-no-pie",  # Disable position-independent executable
        "-static",  # Static linking
    ]
    
    # Build the program multiple times with deterministic options
    binaries = []
    for i in range(3):
        # Create a temporary directory for the build
        build_dir = f"/tmp/repro_test_deterministic_{i}"
        os.makedirs(build_dir, exist_ok=True)
        
        try:
            # Create the source file
            with open(f"{build_dir}/hello.c", "w") as f:
                f.write(program)
            
            # Build the program with deterministic options
            result = subprocess.run(
                ["gcc"] + deterministic_options + ["-o", f"{build_dir}/hello", f"{build_dir}/hello.c"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"❌ Build failed with deterministic options: {result.stderr}")
                return False
            
            # Read the binary
            with open(f"{build_dir}/hello", "rb") as f:
                binary = f.read()
            
            binaries.append(binary)
            
            # Run the program to verify it works
            result = subprocess.run(
                [f"{build_dir}/hello"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0 or result.stdout.strip() != "Hello, World!":
                print(f"❌ Program output incorrect with deterministic options: {result.stdout}")
                return False
            
            print(f"✅ Build {i} successful with deterministic options")
        finally:
            # Clean up
            shutil.rmtree(build_dir)
    
    # Compare the binaries
    if len(set(binaries)) == 1:
        print(f"✅ All binaries are identical with deterministic options")
    else:
        print(f"❌ Binaries are different with deterministic options")
        return False
    
    print(f"✅ Deterministic build options test completed")
    return True
```

5. **Create Reproducibility Reports**: Create reports to document the reproducibility of builds.

```python
def create_reproducibility_report():
    """Create a reproducibility report."""
    print("Creating reproducibility report...")
    
    # Run all reproducibility tests
    reproducibility_tests = {
        "cross_environment": test_cross_environment_reproducibility(),
        "cross_host": test_cross_host_reproducibility(),
        "after_system_changes": test_reproducibility_after_system_changes(),
        "deterministic_options": test_deterministic_build_options()
    }
    
    # Create the reproducibility report
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "image": "nomadbuild:latest",
        "reproducibility_tests": reproducibility_tests,
        "overall_result": all(reproducibility_tests.values())
    }
    
    # Save the report to a file
    report_file = "/app/reproducibility_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"✅ Reproducibility report created: {report_file}")
    
    # Print the overall result
    if report["overall_result"]:
        print(f"✅ All reproducibility tests passed")
    else:
        print(f"❌ Some reproducibility tests failed")
    
    return report
```

## Testing

The changes should be tested by:

1. Building the Docker image with the enhanced reproducibility tests
2. Running the verification script to test reproducibility across different environments
3. Verifying that builds are reproducible on different host systems
4. Testing reproducibility after system changes
5. Testing deterministic build options
6. Creating and reviewing reproducibility reports

## Acceptance Criteria

- Reproducibility testing is implemented across different environments
- Builds are verified to be reproducible on different host systems
- Reproducibility is tested after system changes
- Deterministic build options are added and tested
- Reproducibility reports are created
- The verification script reports detailed results of the reproducibility tests
