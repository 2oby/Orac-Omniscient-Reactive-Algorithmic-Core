#!/usr/bin/env python3
"""
Simple script to run the ORAC API server for testing.

This script starts the FastAPI server with Home Assistant integration
enabled, allowing you to test the grammar constraints and command processing.
"""

import uvicorn
import os
import sys

# Add the orac package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'orac'))

from orac.api import app

if __name__ == "__main__":
    print("Starting ORAC API server with Home Assistant integration...")
    print("Server will be available at: http://localhost:8000")
    print("Home Assistant command endpoint: http://localhost:8000/v1/homeassistant/command")
    print("API documentation: http://localhost:8000/docs")
    print()
    print("Press Ctrl+C to stop the server")
    print()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 