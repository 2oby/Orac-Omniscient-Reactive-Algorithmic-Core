#!/usr/bin/env bash
set -euo pipefail

# Check if Docker rebuild is needed
# Usage: ./scripts/check_rebuild_needed.sh [image_name] [max_age_hours]

IMAGE_NAME="${1:-orac-orac:latest}"
MAX_AGE_HOURS="${2:-24}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if image exists
if ! docker images -q "$IMAGE_NAME" >/dev/null 2>&1; then
    echo -e "${YELLOW}Image $IMAGE_NAME not found - rebuild needed${NC}"
    exit 1
fi

# Get image creation time
IMAGE_CREATED=$(docker inspect "$IMAGE_NAME" --format='{{.Created}}' 2>/dev/null || echo "")
if [ -z "$IMAGE_CREATED" ]; then
    echo -e "${YELLOW}Could not get image creation time - rebuild needed${NC}"
    exit 1
fi

# Convert to timestamp
IMAGE_TIMESTAMP=$(date -d "$IMAGE_CREATED" +%s 2>/dev/null || echo "0")
CURRENT_TIMESTAMP=$(date +%s)
AGE_SECONDS=$((CURRENT_TIMESTAMP - IMAGE_TIMESTAMP))
AGE_HOURS=$((AGE_SECONDS / 3600))

echo -e "${BLUE}Image $IMAGE_NAME created $AGE_HOURS hours ago${NC}"

# Check if image is too old
if [ "$AGE_HOURS" -gt "$MAX_AGE_HOURS" ]; then
    echo -e "${YELLOW}Image is older than ${MAX_AGE_HOURS} hours - rebuild recommended${NC}"
    exit 1
fi

# Check for newer source files
NEWEST_SOURCE=$(find . -name '*.py' -o -name '*.yaml' -o -name '*.yml' -o -name '*.json' -o -name '*.txt' -o -name '*.md' -o -name 'Dockerfile' -o -name 'requirements.txt' | xargs stat -c %Y 2>/dev/null | sort -n | tail -1 || echo "0")

if [ "$NEWEST_SOURCE" -gt "$IMAGE_TIMESTAMP" ]; then
    echo -e "${YELLOW}Source files are newer than image - rebuild needed${NC}"
    exit 1
fi

echo -e "${GREEN}No rebuild needed - image is recent and up to date${NC}"
exit 0 