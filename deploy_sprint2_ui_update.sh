#!/bin/bash

# Deploy Sprint 2 UI Updates to Orin
# This script updates the UI to match the new design with:
# - Device cards instead of checkboxes
# - Click-to-enable/disable (green/orange)
# - Device Types and Locations on the right
# - Improved drop zones with labels

echo "========================================="
echo "Sprint 2 UI Update Deployment"
echo "========================================="

# Backup existing files
echo "Creating backups of existing files..."
ssh orin4 << 'EOF'
cd /home/toby/ORAC
mkdir -p backups/sprint2_ui_$(date +%Y%m%d_%H%M%S)
cp orac/templates/backend_entities.html backups/sprint2_ui_$(date +%Y%m%d_%H%M%S)/ 2>/dev/null
cp orac/static/js/backend_entities.js backups/sprint2_ui_$(date +%Y%m%d_%H%M%S)/ 2>/dev/null
echo "Backups created"
EOF

# Copy the updated files
echo "Copying updated UI files..."

# First, we need to rename the updated files to replace the originals
cp orac/templates/backend_entities_updated.html orac/templates/backend_entities.html
cp orac/static/js/backend_entities_updated.js orac/static/js/backend_entities.js

# Commit and push changes
echo "Committing changes..."
git add .
git commit -m "Sprint 2 UI Update: Card-based device interface with improved drag-and-drop"
git push origin master

# Pull on the Orin
echo "Deploying to Orin..."
ssh orin4 << 'EOF'
cd /home/toby/ORAC
git pull origin master
echo "Files updated on Orin"
EOF

# Restart the container
echo "Restarting ORAC container..."
ssh orin4 "docker restart orac"

echo "Waiting for container to restart..."
sleep 5

# Check if container is running
echo "Checking container status..."
ssh orin4 "docker ps | grep orac"

echo "========================================="
echo "Sprint 2 UI Update Complete!"
echo "========================================="
echo ""
echo "The updated UI features:"
echo "✓ Device cards with click-to-enable (green/orange)"
echo "✓ No more checkboxes - click entire card"
echo "✓ Device Types and Locations panels on the right"
echo "✓ Improved drop zones with 'DEVICE TYPE' and 'LOCATION' labels"
echo "✓ Better visual feedback during drag operations"
echo ""
echo "Test the new UI at: http://192.168.8.192:8000/backends"
echo ""
echo "To revert if needed:"
echo "ssh orin4"
echo "cd /home/toby/ORAC"
echo "cp backups/sprint2_ui_*/backend_entities.html orac/templates/"
echo "cp backups/sprint2_ui_*/backend_entities.js orac/static/js/"
echo "docker restart orac"