"""
orac.logger
-----------
Centralized logging configuration for ORAC.

This module provides a consistent logging setup across all ORAC components,
with features like:
- Log rotation to prevent large log files
- Configurable log levels via environment variables
- Both file and console logging
- Structured log format for easier parsing
"""

import os
import logging
from logging.handlers import RotatingFileHandler
import sys
import time
from datetime import datetime
import platform
import json

# Create logs directory if it doesn't exist
LOG_DIR = os.environ.get("LOG_DIR", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Get log level from environment or use INFO as default
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.path.join(LOG_DIR, "orac.log")

# Configure log format for different handlers
CONSOLE_FORMAT = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
FILE_FORMAT = '%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s'

# Log startup information to help with debugging
STARTUP_TIME = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
HOSTNAME = platform.node()
SYSTEM_INFO = {
    "platform": platform.platform(),
    "python_version": platform.python_version(),
    "processor": platform.processor(),
    "startup_time": STARTUP_TIME,
    "hostname": HOSTNAME
}

# Initialize root logger
root_logger = logging.getLogger()

# Set the log level from environment or default
try:
    numeric_level = getattr(logging, LOG_LEVEL)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {LOG_LEVEL}")
    root_logger.setLevel(numeric_level)
except (AttributeError, ValueError):
    print(f"WARNING: Invalid log level '{LOG_LEVEL}'. Using INFO.")
    root_logger.setLevel(logging.INFO)

# Clear any existing handlers (to avoid duplicates during reloads)
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# Create formatters
console_formatter = logging.Formatter(CONSOLE_FORMAT)
file_formatter = logging.Formatter(FILE_FORMAT)

# Setup console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(console_formatter)
root_logger.addHandler(console_handler)

# Setup file handler with rotation (10MB files, keep 5 backup files)
try:
    file_handler = RotatingFileHandler(
        LOG_FILE, 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
except Exception as e:
    # If file logging fails, log to console only
    root_logger.error(f"Failed to setup file logging: {str(e)}")

# Module-level logger for use in this file
logger = logging.getLogger(__name__)

# Log startup information
logger.info(f"ORAC logger initialized at {STARTUP_TIME}")
logger.info(f"Log level set to {LOG_LEVEL}")
logger.info(f"System info: {json.dumps(SYSTEM_INFO)}")


def get_logger(name):
    """
    Get a logger instance for a module.
    
    Args:
        name: The name of the module (typically __name__)
        
    Returns:
        A configured logger instance
    """
    logger = logging.getLogger(name)
    return logger


class LoggerAdapter(logging.LoggerAdapter):
    """
    Adapter for adding contextual information to logs.
    
    Usage:
        logger = LoggerAdapter(get_logger(__name__), {"context": "my_context"})
        logger.info("Message with context")
    """
    
    def process(self, msg, kwargs):
        extra = kwargs.get("extra", {})
        
        # Add context from the adapter
        if hasattr(self, "extra") and isinstance(self.extra, dict):
            for key, value in self.extra.items():
                if key not in extra:
                    extra[key] = value
        
        # Add timestamp if not present
        if "timestamp" not in extra:
            extra["timestamp"] = time.time()
        
        # Update kwargs with enhanced extra
        kwargs["extra"] = extra
        
        return msg, kwargs


def get_context_logger(name, context=None):
    """
    Get a logger with context.
    
    Args:
        name: The name of the module
        context: A dictionary with context information
        
    Returns:
        A logger adapter with context
    """
    logger = get_logger(name)
    if context is None:
        context = {}
    return LoggerAdapter(logger, context)