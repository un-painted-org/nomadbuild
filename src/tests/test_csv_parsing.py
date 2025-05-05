# test_csv_parsing.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
# Tests for CSV parsing functionality
import pytest
import tempfile
import os
from pathlib import Path
from src.builder.device import parse_csv_file

def test_parse_csv_file_valid():
    """Test parsing a valid CSV file with IP addresses."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("192.168.1.100\n")
        f.write("192.168.1.101\n")
        f.write("10.0.0.1\n")
        temp_file = f.name
    
    try:
        # Parse the CSV file
        ip_addresses = parse_csv_file(temp_file)
        
        # Verify the parsed IP addresses
        assert len(ip_addresses) == 3
        assert "192.168.1.100" in ip_addresses
        assert "192.168.1.101" in ip_addresses
        assert "10.0.0.1" in ip_addresses
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)

def test_parse_csv_file_with_comments():
    """Test parsing a CSV file with comments and empty lines."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("# This is a comment\n")
        f.write("\n")  # Empty line
        f.write("192.168.1.100\n")
        f.write("  # Another comment\n")
        f.write("192.168.1.101\n")
        temp_file = f.name
    
    try:
        # Parse the CSV file
        ip_addresses = parse_csv_file(temp_file)
        
        # Verify the parsed IP addresses
        assert len(ip_addresses) == 2
        assert "192.168.1.100" in ip_addresses
        assert "192.168.1.101" in ip_addresses
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)

def test_parse_csv_file_with_invalid_ips():
    """Test parsing a CSV file with some invalid IP addresses."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("192.168.1.100\n")
        f.write("invalid_ip\n")
        f.write("192.168.1.256\n")  # Invalid IP (256 is out of range)
        f.write("192.168.1.101\n")
        temp_file = f.name
    
    try:
        # Parse the CSV file
        ip_addresses = parse_csv_file(temp_file)
        
        # Verify that only valid IP addresses are returned
        assert len(ip_addresses) == 2
        assert "192.168.1.100" in ip_addresses
        assert "192.168.1.101" in ip_addresses
        assert "invalid_ip" not in ip_addresses
        assert "192.168.1.256" not in ip_addresses
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)

def test_parse_csv_file_nonexistent():
    """Test parsing a non-existent CSV file."""
    # Use a path that definitely doesn't exist
    nonexistent_file = "/tmp/nonexistent_file_12345.csv"
    
    # Parse the non-existent CSV file
    ip_addresses = parse_csv_file(nonexistent_file)
    
    # Verify that an empty list is returned
    assert ip_addresses == []

def test_parse_csv_file_empty():
    """Test parsing an empty CSV file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        # Create an empty file
        temp_file = f.name
    
    try:
        # Parse the empty CSV file
        ip_addresses = parse_csv_file(temp_file)
        
        # Verify that an empty list is returned
        assert ip_addresses == []
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)

def test_parse_csv_file_with_multiple_columns():
    """Test parsing a CSV file with multiple columns."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("192.168.1.100,Device1,Active\n")
        f.write("192.168.1.101,Device2,Inactive\n")
        f.write("10.0.0.1,Device3,Active\n")
        temp_file = f.name
    
    try:
        # Parse the CSV file
        ip_addresses = parse_csv_file(temp_file)
        
        # Verify that only the IP addresses are returned
        assert len(ip_addresses) == 3
        assert "192.168.1.100" in ip_addresses
        assert "192.168.1.101" in ip_addresses
        assert "10.0.0.1" in ip_addresses
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)
