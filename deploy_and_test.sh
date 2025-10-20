#!/bin/bash

# Deploy and Test Script for ORAC
# This script ensures:
# - All changes are committed to GitHub (single source of truth)
# - Orin pulls from GitHub
# - Files are properly copied into Docker container
# - Container is restarted
# - Basic tests verify deployment

echo "========================================="
echo "ORAC Deploy and Test"
echo "========================================="

# Parse arguments
REBUILD=false
COMMIT_MSG=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --rebuild)
            REBUILD=true
            shift
            ;;
        *)
            COMMIT_MSG="$1"
            shift
            ;;
    esac
done

# Use default commit message if not provided
COMMIT_MSG="${COMMIT_MSG:-Code updates $(date +%Y%m%d_%H%M%S)}"

# Create timestamp for this deployment
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Backup existing files in Docker
echo "Creating backups of existing files..."
ssh orin4 << EOF
cd /home/toby/ORAC
BACKUP_DIR="backups/${TIMESTAMP}"
mkdir -p "\$BACKUP_DIR"
echo "Creating backup in \$BACKUP_DIR"

# Backup key files from Docker container
docker cp orac:/app/orac/static/js/backend_entities.js "\$BACKUP_DIR/" 2>/dev/null
docker cp orac:/app/orac/templates/backend_entities.html "\$BACKUP_DIR/" 2>/dev/null
docker cp orac:/app/orac/api.py "\$BACKUP_DIR/" 2>/dev/null
docker cp orac:/app/orac/backend_manager.py "\$BACKUP_DIR/" 2>/dev/null
echo "Backups created in \$BACKUP_DIR"
EOF

# Check for uncommitted changes and commit them
echo ""
echo "Checking for changes to commit..."
if git diff-index --quiet HEAD --; then
    echo "No changes to commit, proceeding with deployment..."
else
    echo "Committing changes..."
    git add -A
    git commit -m "${COMMIT_MSG}"
fi

# Always push to ensure GitHub is up to date
echo "Pushing to GitHub..."
CURRENT_BRANCH=$(git branch --show-current)
git push origin "$CURRENT_BRANCH"

# Deploy to Orin
echo ""
echo "Deploying to Orin..."
CURRENT_BRANCH=$(git branch --show-current)
ssh orin4 << EOF
cd /home/toby/ORAC

# Stash any local changes to avoid merge conflicts
if ! git diff-index --quiet HEAD --; then
    echo "Stashing local changes on Orin..."
    git stash
fi

# Fetch all branches
echo "Fetching from GitHub..."
git fetch origin

# Checkout and pull the current branch
echo "Switching to branch: $CURRENT_BRANCH"
git checkout "$CURRENT_BRANCH" 2>/dev/null || git checkout -b "$CURRENT_BRANCH" origin/"$CURRENT_BRANCH"

# Reset to match origin (GitHub is source of truth)
echo "Resetting to match origin/$CURRENT_BRANCH (GitHub is source of truth)"
git reset --hard origin/"$CURRENT_BRANCH"

# Copy ALL relevant files into Docker container
echo "Copying files into Docker container..."

# Copy Python backend files
for file in orac/*.py orac/**/*.py; do
    if [ -f "\$file" ]; then
        docker cp "\$file" "orac:/app/\$file" 2>/dev/null
    fi
done

# Copy Python package directories (with __init__.py)
for dir in orac/*/; do
    if [ -d "\$dir" ] && [ -f "\${dir}__init__.py" ]; then
        echo "Copying package directory: \$dir"
        docker exec orac mkdir -p "/app/\$dir" 2>/dev/null
        docker cp "\${dir}." "orac:/app/\$dir"
    fi
done

# Copy entire static directory
docker cp orac/static/. orac:/app/orac/static/

# Copy entire templates directory
docker cp orac/templates/. orac:/app/orac/templates/

echo "Files copied to Docker container"
EOF

# Rebuild and restart the container
echo ""
if [ "$REBUILD" = true ]; then
    echo "Rebuilding Docker image..."
    ssh orin4 << EOF
cd /home/toby/ORAC
docker compose down
docker compose build
docker compose up -d
EOF
    echo "Container rebuilt and started"
else
    echo "Restarting ORAC container..."
    ssh orin4 "docker restart orac"
fi

echo "Waiting for container to restart..."
sleep 5

# Run comprehensive tests
echo ""
echo "========================================="
echo "Running Tests"
echo "========================================="

# Test 1: Container status
echo "1. Container status:"
if ssh orin4 "docker ps | grep orac | grep -q Up"; then
    echo "   ✓ Container is running"
else
    echo "   ✗ Container is NOT running"
    echo "   Check logs with: ssh orin4 'docker logs orac --tail 50'"
    exit 1
fi

# Test 2: API health check
echo ""
echo "2. API health check:"
if curl -s -f http://192.168.8.192:8000/ > /dev/null 2>&1; then
    echo "   ✓ API is responding"
else
    echo "   ✗ API is NOT responding"
    exit 1
fi

# Test 3: Backend endpoints
echo ""
echo "3. Backend endpoints:"
BACKEND_ID="homeassistant_8ca84424"

# Test mappings endpoint
DEVICE_COUNT=$(curl -s http://192.168.8.192:8000/api/backends/${BACKEND_ID}/mappings 2>/dev/null | grep -o '"device_id"' | wc -l)
if [ "$DEVICE_COUNT" -gt 0 ]; then
    echo "   ✓ Mappings endpoint: Found $DEVICE_COUNT devices"
else
    echo "   ✗ Mappings endpoint: No devices found or error"
fi

# Test fetch endpoint
if curl -s -X POST http://192.168.8.192:8000/api/backends/${BACKEND_ID}/entities/fetch 2>/dev/null | grep -q '"status":"success"'; then
    echo "   ✓ Fetch endpoint: Working"
else
    echo "   ✗ Fetch endpoint: Not working"
fi

# Test 4: Static files
echo ""
echo "4. Static file deployment:"
JS_FILE="http://192.168.8.192:8000/static/js/backend_entities.js"
if curl -s "$JS_FILE" | grep -q "loadDeviceData"; then
    echo "   ✓ JavaScript files accessible"
    if curl -s "$JS_FILE" | grep -q "console.log"; then
        echo "   ✓ Debug logging present"
    else
        echo "   ⚠ Debug logging not found"
    fi
else
    echo "   ✗ JavaScript files NOT accessible"
fi

# Test 5: Docker logs check
echo ""
echo "5. Recent Docker logs:"
ssh orin4 "docker logs orac --tail 5 2>&1 | grep -E '(ERROR|WARNING|Started)' | tail -3" || echo "   No significant log entries"

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Deployment ID: ${TIMESTAMP}"
echo "Commit Message: ${COMMIT_MSG}"
echo ""
echo "UI Access Points:"
echo "  Main:     http://192.168.8.192:8000/"
echo "  Backends: http://192.168.8.192:8000/backends"
echo "  Entities: http://192.168.8.192:8000/backends/${BACKEND_ID}/entities"
echo ""
echo "Debug Commands:"
echo "  View logs:    ssh orin4 'docker logs orac --tail 50'"
echo "  Enter shell:  ssh orin4 'docker exec -it orac bash'"
echo "  Restart:      ssh orin4 'docker restart orac'"
echo ""
echo "To revert this deployment:"
echo "  ssh orin4"
echo "  cd /home/toby/ORAC"
echo "  # Restore from backup"
echo "  for f in backups/${TIMESTAMP}/*; do"
echo "    docker cp \"\$f\" orac:/app/orac/"
echo "  done"
echo "  docker restart orac"