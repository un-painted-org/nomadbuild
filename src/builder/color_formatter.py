#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# color_formatter.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
# Colored logging formatter for CLI output

import logging
import sys

# ANSI color codes
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    
    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright foreground colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log messages based on level."""
    
    LEVEL_COLORS = {
        logging.DEBUG: Colors.BRIGHT_BLACK,
        logging.INFO: Colors.BRIGHT_WHITE,
        logging.WARNING: Colors.BRIGHT_YELLOW,
        logging.ERROR: Colors.BRIGHT_RED,
        logging.CRITICAL: Colors.RED + Colors.BOLD
    }
    
    LEVEL_NAMES = {
        logging.DEBUG: Colors.BRIGHT_BLACK + "DEBUG" + Colors.RESET,
        logging.INFO: Colors.BRIGHT_CYAN + "INFO" + Colors.RESET,
        logging.WARNING: Colors.BRIGHT_YELLOW + "WARNING" + Colors.RESET,
        logging.ERROR: Colors.BRIGHT_RED + "ERROR" + Colors.RESET,
        logging.CRITICAL: Colors.RED + Colors.BOLD + "CRITICAL" + Colors.RESET
    }
    
    def __init__(self, fmt=None, datefmt=None, style='%', use_colors=True):
        super().__init__(fmt, datefmt, style)
        self.use_colors = use_colors and sys.stdout.isatty()  # Only use colors if stdout is a TTY
    
    def format(self, record):
        # Save the original levelname
        original_levelname = record.levelname
        
        # Replace the levelname with the colored version if colors are enabled
        if self.use_colors:
            record.levelname = self.LEVEL_NAMES.get(record.levelno, original_levelname)
            
            # Add color to the message based on level
            color = self.LEVEL_COLORS.get(record.levelno, Colors.RESET)
            
            # Special handling for specific message types
            message = record.getMessage()
            if "Build successful" in message or "completed successfully" in message:
                record.msg = f"{Colors.BRIGHT_GREEN}{record.msg}{Colors.RESET}"
            elif "Build failed" in message or "Error:" in message:
                record.msg = f"{Colors.BRIGHT_RED}{record.msg}{Colors.RESET}"
            elif "Warning:" in message:
                record.msg = f"{Colors.BRIGHT_YELLOW}{record.msg}{Colors.RESET}"
            elif "--- " in message and " ---" in message:  # Section headers
                record.msg = f"{Colors.BOLD}{Colors.BRIGHT_MAGENTA}{record.msg}{Colors.RESET}"
            else:
                # Default color based on level
                record.msg = f"{color}{record.msg}{Colors.RESET}"
        
        # Format the record
        result = super().format(record)
        
        # Restore the original levelname
        record.levelname = original_levelname
        
        return result

def setup_colored_logging(logger, level=logging.INFO):
    """Set up colored logging for the given logger."""
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Create formatter
    formatter = ColoredFormatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    return logger
