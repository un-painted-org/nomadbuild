#!/usr/bin/env python3
# get_version_info.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
"""
Get version information from git for NomadBuild
Uses git to determine the current version based on tags or commits
"""

import subprocess
import json
import os
import datetime
import sys

def run_git_command(command):
    """Run a git command and return its output"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None
    except Exception as e:
        print(f"Error running git command: {e}", file=sys.stderr)
        return None

def get_version_info():
    """Get version information from git"""
    # Check if we're in a git repository
    if not os.path.exists(".git") and not run_git_command("git rev-parse --is-inside-work-tree"):
        return {
            "version": "unknown",
            "date": datetime.datetime.now().strftime("%B %d, %Y"),
            "commit": "unknown",
            "is_tag": False
        }
        
    # Try to get the most recent tag
    tag = run_git_command("git describe --tags --abbrev=0 2>/dev/null")
    
    if tag:
        # We have a tag, get its date
        tag_date = run_git_command(f"git log -1 --format=%ai {tag}")
        commit = run_git_command(f"git rev-parse --short {tag}")
        
        # Convert tag date to more readable format if available
        if tag_date:
            try:
                date_obj = datetime.datetime.strptime(tag_date.split()[0], "%Y-%m-%d")
                formatted_date = date_obj.strftime("%B %d, %Y")
            except:
                formatted_date = tag_date
        else:
            formatted_date = datetime.datetime.now().strftime("%B %d, %Y")
            
        return {
            "version": tag,
            "date": formatted_date,
            "commit": commit,
            "is_tag": True
        }
    else:
        # No tag found, use master branch and latest commit
        branch = run_git_command("git rev-parse --abbrev-ref HEAD")
        if not branch:
            branch = "master"
            
        commit = run_git_command("git rev-parse --short HEAD")
        if not commit:
            commit = "unknown"
            
        commit_date = run_git_command("git log -1 --format=%ai")
        if commit_date:
            try:
                date_obj = datetime.datetime.strptime(commit_date.split()[0], "%Y-%m-%d")
                formatted_date = date_obj.strftime("%B %d, %Y")
            except:
                formatted_date = commit_date
        else:
            formatted_date = datetime.datetime.now().strftime("%B %d, %Y")
            
        return {
            "version": f"{branch}@{commit}",
            "date": formatted_date,
            "commit": commit,
            "is_tag": False
        }

def write_version_file():
    """Write version information to a JSON file"""
    version_info = get_version_info()
    
    # Ensure directory exists
    os.makedirs("src/web_static/version", exist_ok=True)
    
    # Write to file
    with open("src/web_static/version/version.json", "w") as f:
        json.dump(version_info, f, indent=2)
        
    print(f"Version info written to src/web_static/version/version.json:")
    print(f"  Version: {version_info['version']}")
    print(f"  Date: {version_info['date']}")
    print(f"  Commit: {version_info['commit']}")
    print(f"  Is Tag: {version_info['is_tag']}")
    
    return version_info

if __name__ == "__main__":
    write_version_file() 