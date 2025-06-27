#!/bin/bash
# Rollback llama-cpp-jetson submodule to previous version

set -e

# Configuration - Change this to rollback to a different version
TARGET_VERSION="v0.1.0-llama-cpp-b5306"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Rolling back llama-cpp-jetson to: $TARGET_VERSION"

# Create backup of current state
BACKUP_DIR="$PROJECT_ROOT/third_party/llama_cpp_backup_$(date +%Y%m%d_%H%M%S)"
echo "Creating backup at: $BACKUP_DIR"
cp -r "$PROJECT_ROOT/third_party/llama_cpp" "$BACKUP_DIR"

cd "$PROJECT_ROOT/third_party/llama_cpp"

# Fetch latest changes
git fetch origin

# Checkout target version
git checkout "$TARGET_VERSION"

cd "$PROJECT_ROOT"

# Commit rollback
git add third_party/llama_cpp
git commit -m "Rollback llama-cpp-jetson to $TARGET_VERSION"

echo "Successfully rolled back to $TARGET_VERSION"
echo "Backup created at: $BACKUP_DIR" 