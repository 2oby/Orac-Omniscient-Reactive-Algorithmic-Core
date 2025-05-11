#!/bin/sh

# Check system status
python3 -m orac.cli status

# Start the FastAPI application
exec "$@" 