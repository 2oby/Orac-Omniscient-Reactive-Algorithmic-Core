#!/usr/bin/env python3
"""
Run the ORAC web interface.

This script starts the web interface on port 80.
Note: Running on port 80 typically requires root/sudo privileges.
"""

import uvicorn
from orac.web import app

if __name__ == "__main__":
    print("Starting ORAC web interface on http://localhost:80")
    print("Note: You may need to run this script with sudo to use port 80")
    uvicorn.run(app, host="0.0.0.0", port=80) 