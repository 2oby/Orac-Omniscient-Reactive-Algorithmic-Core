#!/bin/bash

# ORAC Docker Permissions Setup Script
# This script automatically detects the current user's UID/GID and sets up Docker permissions

echo "🔧 ORAC Docker Permissions Setup"
echo "================================"

# Detect current user's UID and GID
CURRENT_UID=$(id -u)
CURRENT_GID=$(id -g)
CURRENT_USER=$(whoami)

echo "Current user: $CURRENT_USER (UID: $CURRENT_UID, GID: $CURRENT_GID)"

# Create cache directory if it doesn't exist
if [ ! -d "cache" ]; then
    echo "📁 Creating cache directory..."
    mkdir -p cache
fi

# Set correct permissions on cache directory
echo "🔐 Setting cache directory permissions..."
sudo chown -R $CURRENT_UID:$CURRENT_GID cache
chmod -R 755 cache

# Create homeassistant subdirectory
mkdir -p cache/homeassistant
chown -R $CURRENT_UID:$CURRENT_GID cache/homeassistant
chmod -R 755 cache/homeassistant

echo "✅ Cache permissions set correctly"
echo ""
echo "🚀 You can now run Docker with:"
echo "   UID=$CURRENT_UID GID=$CURRENT_GID docker compose up"
echo ""
echo "Or set environment variables permanently:"
echo "   export UID=$CURRENT_UID"
echo "   export GID=$CURRENT_GID"
echo ""
echo "Then run: docker compose up" 