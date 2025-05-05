# Backlog Item 120: Implement Stress and Performance Testing

## Description

This backlog item focuses on implementing stress and performance testing to verify container behavior under load and ensure that the optimization doesn't impact performance. Currently, there are no stress tests to verify the container's behavior under load or performance tests to measure build times.

## Requirements

1. Add stress tests to verify container behavior under load
2. Test with multiple simultaneous builds
3. Measure and compare build times before and after optimization
4. Test memory usage under load
5. Verify resource cleanup after stress tests

## Implementation Details

### Current Issues

The current verification script includes basic functionality tests but no stress tests to verify the container's behavior under load or performance tests to measure build times. This is critical for ensuring the optimization doesn't impact performance.

### Proposed Solution

1. **Add Stress Tests**: Create stress tests to verify container behavior under load.

```python
def test_container_stress():
    """Test container behavior under load."""
    print("Testing container behavior under load...")
    
    # Number of simultaneous processes to run
    num_processes = 10
    
    # Create multiple processes to run CPU-intensive tasks
    processes = []
    for i in range(num_processes):
        process = multiprocessing.Process(
            target=cpu_intensive_task,
            args=(i,)
        )
        processes.append(process)
        process.start()
    
    # Wait for all processes to complete
    for process in processes:
        process.join()
    
    print(f"✅ Container handled {num_processes} simultaneous CPU-intensive tasks")
    return True

def cpu_intensive_task(process_id):
    """Run a CPU-intensive task."""
    print(f"Process {process_id} starting CPU-intensive task...")
    
    # Calculate prime numbers up to 100,000
    primes = []
    for num in range(2, 100000):
        is_prime = True
        for i in range(2, int(num ** 0.5) + 1):
            if num % i == 0:
                is_prime = False
                break
        if is_prime:
            primes.append(num)
    
    print(f"Process {process_id} found {len(primes)} prime numbers")
```

2. **Test Multiple Simultaneous Builds**: Test the container with multiple simultaneous builds.

```python
def test_multiple_builds():
    """Test the container with multiple simultaneous builds."""
    print("Testing multiple simultaneous builds...")
    
    # Number of simultaneous builds to run
    num_builds = 3
    
    # Create multiple processes to run builds
    processes = []
    for i in range(num_builds):
        process = multiprocessing.Process(
            target=run_build,
            args=(i,)
        )
        processes.append(process)
        process.start()
    
    # Wait for all processes to complete
    for process in processes:
        process.join()
    
    print(f"✅ Container handled {num_builds} simultaneous builds")
    return True

def run_build(build_id):
    """Run a build process."""
    print(f"Build {build_id} starting...")
    
    # Create a temporary directory for the build
    build_dir = f"/tmp/build_{build_id}"
    os.makedirs(build_dir, exist_ok=True)
    
    try:
        # Create a simple C program
        with open(f"{build_dir}/hello.c", "w") as f:
            f.write("""
            #include <stdio.h>
            int main() {
                printf("Hello, World!\\n");
                return 0;
            }
            """)
        
        # Compile the program
        result = subprocess.run(
            ["gcc", "-o", f"{build_dir}/hello", f"{build_dir}/hello.c"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"❌ Build {build_id} failed: {result.stderr}")
            return False
        
        # Run the program
        result = subprocess.run(
            [f"{build_dir}/hello"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0 or result.stdout.strip() != "Hello, World!":
            print(f"❌ Build {build_id} output incorrect: {result.stdout}")
            return False
        
        print(f"✅ Build {build_id} completed successfully")
        return True
    finally:
        # Clean up
        shutil.rmtree(build_dir)
```

3. **Measure Build Times**: Measure and compare build times before and after optimization.

```python
def measure_build_times():
    """Measure and compare build times."""
    print("Measuring build times...")
    
    # Number of builds to run
    num_builds = 5
    
    # Run multiple builds and measure the time
    build_times = []
    for i in range(num_builds):
        start_time = time.time()
        run_build(i)
        end_time = time.time()
        build_time = end_time - start_time
        build_times.append(build_time)
        print(f"Build {i} took {build_time:.2f} seconds")
    
    # Calculate average build time
    avg_build_time = sum(build_times) / len(build_times)
    print(f"Average build time: {avg_build_time:.2f} seconds")
    
    # Compare with previous build times (if available)
    previous_build_times_file = "/app/previous_build_times.json"
    if os.path.exists(previous_build_times_file):
        with open(previous_build_times_file, "r") as f:
            previous_build_times = json.load(f)
        
        previous_avg_build_time = sum(previous_build_times) / len(previous_build_times)
        print(f"Previous average build time: {previous_avg_build_time:.2f} seconds")
        
        # Calculate percentage change
        percentage_change = (avg_build_time - previous_avg_build_time) / previous_avg_build_time * 100
        print(f"Build time change: {percentage_change:.2f}%")
    
    # Save current build times for future comparison
    with open(previous_build_times_file, "w") as f:
        json.dump(build_times, f)
    
    return build_times
```

4. **Test Memory Usage**: Test memory usage under load.

```python
def test_memory_usage():
    """Test memory usage under load."""
    print("Testing memory usage under load...")
    
    # Get initial memory usage
    initial_memory = get_memory_usage()
    print(f"Initial memory usage: {initial_memory:.2f} MB")
    
    # Run memory-intensive tasks
    memory_intensive_tasks()
    
    # Get peak memory usage
    peak_memory = get_memory_usage()
    print(f"Peak memory usage: {peak_memory:.2f} MB")
    
    # Wait for memory to be released
    time.sleep(5)
    
    # Get final memory usage
    final_memory = get_memory_usage()
    print(f"Final memory usage: {final_memory:.2f} MB")
    
    # Check for memory leaks
    if final_memory > initial_memory * 1.1:  # Allow for 10% increase
        print(f"❌ Possible memory leak: {final_memory - initial_memory:.2f} MB not released")
        return False
    
    print(f"✅ Memory usage under load is acceptable")
    return True

def get_memory_usage():
    """Get current memory usage in MB."""
    # Use /proc/self/status to get memory usage
    with open("/proc/self/status", "r") as f:
        for line in f:
            if line.startswith("VmRSS:"):
                # Extract the memory usage in kB
                memory_kb = int(line.split()[1])
                # Convert to MB
                memory_mb = memory_kb / 1024
                return memory_mb
    
    return 0

def memory_intensive_tasks():
    """Run memory-intensive tasks."""
    # Create large arrays in memory
    arrays = []
    for i in range(10):
        # Create a 100MB array
        array = bytearray(100 * 1024 * 1024)
        arrays.append(array)
        print(f"Created array {i} of size 100MB")
    
    # Use the arrays to prevent optimization
    for i, array in enumerate(arrays):
        array[0] = i
        print(f"Used array {i}")
    
    # Release the arrays
    arrays = None
```

5. **Verify Resource Cleanup**: Verify that resources are properly cleaned up after stress tests.

```python
def verify_resource_cleanup():
    """Verify that resources are properly cleaned up after stress tests."""
    print("Verifying resource cleanup...")
    
    # Check for leftover processes
    result = subprocess.run(
        ["ps", "aux"],
        capture_output=True,
        text=True
    )
    
    # Look for processes that might have been left behind
    leftover_processes = []
    for line in result.stdout.splitlines():
        if "gcc" in line or "g++" in line or "make" in line or "cmake" in line:
            leftover_processes.append(line)
    
    if leftover_processes:
        print(f"❌ Leftover processes found:")
        for process in leftover_processes:
            print(f"  {process}")
        return False
    
    # Check for leftover temporary files
    temp_files = []
    for root, dirs, files in os.walk("/tmp"):
        for file in files:
            if file.startswith("build_") or file.startswith("test_"):
                temp_files.append(os.path.join(root, file))
    
    if temp_files:
        print(f"❌ Leftover temporary files found:")
        for file in temp_files:
            print(f"  {file}")
        return False
    
    print(f"✅ All resources were properly cleaned up")
    return True
```

## Testing

The changes should be tested by:

1. Building the Docker image with the stress and performance tests
2. Running the verification script to test container behavior under load
3. Testing with multiple simultaneous builds
4. Measuring and comparing build times before and after optimization
5. Testing memory usage under load
6. Verifying resource cleanup after stress tests

## Acceptance Criteria

- Stress tests verify container behavior under load
- Multiple simultaneous builds are tested
- Build times are measured and compared before and after optimization
- Memory usage under load is tested
- Resources are verified to be properly cleaned up after stress tests
- The verification script reports detailed results of the stress and performance tests
