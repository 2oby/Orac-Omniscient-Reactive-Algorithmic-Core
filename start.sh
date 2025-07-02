#!/bin/bash

# Fix cache directory permissions for container user
echo "🔧 Fixing cache directory permissions..."
mkdir -p /app/cache/homeassistant
chown -R 1000:1000 /app/cache
chmod -R 755 /app/cache

echo "✅ Cache permissions fixed"
echo "🚀 Starting ORAC API server..."

# Start the application
exec uvicorn orac.api:app --host 0.0.0.0 --port 8000 