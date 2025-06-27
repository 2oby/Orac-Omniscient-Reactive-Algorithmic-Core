#!/bin/bash
# Update llama-cpp-jetson submodule to specified version

set -e

# Configuration - Change this to update to a different version
TARGET_VERSION="v0.1.0-llama-cpp-b5306"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Updating llama-cpp-jetson to version: $TARGET_VERSION"

cd "$PROJECT_ROOT/third_party/llama_cpp"

# Fetch latest changes
git fetch origin

# Checkout specified version
git checkout "$TARGET_VERSION"

cd "$PROJECT_ROOT"

# Commit submodule update
git add third_party/llama_cpp
git commit -m "Update llama-cpp-jetson to version $TARGET_VERSION"

echo "Successfully updated llama-cpp-jetson to $TARGET_VERSION" 