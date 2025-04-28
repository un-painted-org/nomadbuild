# builder_utils.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
def deep_clean_build_directory(repo_path, tag=None):
    """
    Performs a deep clean of the build directory, removing all build artifacts,
    killing any lingering processes, and resetting the git repository state.
    This is used after build cancellation to ensure a clean state.
    
    Args:
        repo_path: Path to the ESP-Miner repository
        tag: Optional tag name that was being built (for targeted cleanup)
    
    Returns:
        bool: True if cleaning was successful, False otherwise
    """
    import psutil
    import os
    import shutil
    import time
    import glob
    from pathlib import Path
    
    logger.info(f"Performing deep clean of build directory: {repo_path}")
    
    try:
        # 1. Kill any lingering processes that might be related to the build
        build_related_processes = ["idf.py", "cmake", "ninja", "python", "make", "gcc", "cc"]
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Check if any of the process command line arguments contain the repo path
                # or if the process name matches build-related processes
                cmdline = " ".join(proc.cmdline()) if proc.cmdline() else ""
                if (str(repo_path) in cmdline and 
                    any(build_proc in proc.name().lower() for build_proc in build_related_processes)):
                    logger.warning(f"Terminating lingering build process: {proc.pid} - {proc.name()}")
                    proc.terminate()
                    # Give it a moment to terminate gracefully
                    try:
                        proc.wait(timeout=3)
                    except psutil.TimeoutExpired:
                        logger.warning(f"Process {proc.pid} did not terminate gracefully, forcing...")
                        proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                logger.warning(f"Error while checking process: {e}")
                continue
    
        # 2. Wait a moment to ensure processes have exited
        time.sleep(1)
        
        # 3. Clean build directories
        build_dirs = []
        
        # Main build directory
        build_dir = Path(repo_path) / "build"
        if build_dir.exists():
            build_dirs.append(build_dir)
            
        # Handle any temporary build directories that might exist
        tmp_build_dirs = list(Path(repo_path).glob("build-*"))
        build_dirs.extend(tmp_build_dirs)
        
        # Remove all identified build directories
        for bd in build_dirs:
            logger.info(f"Removing build directory: {bd}")
            try:
                # Use robust removal with retries
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        if bd.exists():
                            shutil.rmtree(bd)
                        break
                    except (PermissionError, OSError) as e:
                        if attempt < max_retries - 1:
                            logger.warning(f"Error removing {bd}, retrying in 1s: {e}")
                            time.sleep(1)
                        else:
                            raise
            except Exception as e:
                logger.error(f"Failed to remove build directory {bd}: {e}")
                # Continue with other cleanup even if one directory fails
        
        # 4. Reset Git repository state
        try:
            # Clean untracked files
            run_command(["git", "clean", "-fdx"], cwd=repo_path, check=True)
            
            # Reset any uncommitted changes
            run_command(["git", "reset", "--hard"], cwd=repo_path, check=True)
            
            # If a specific tag was provided, ensure we're back on that tag
            if tag:
                run_command(["git", "checkout", f"tags/{tag}", "--force"], 
                           cwd=repo_path, check=True)
                
            logger.info("Git repository state has been reset")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to reset Git repository: {e}")
            return False
            
        # 5. Re-create empty build directory
        build_dir.mkdir(exist_ok=True)
            
        logger.info("Deep clean completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Deep clean failed: {e}")
        return False 