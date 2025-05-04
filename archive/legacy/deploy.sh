#!/bin/bash
# deploy.sh - Simple deployment script for voice service

# Get commit message from argument or use default
COMMIT_MSG=${1:-"Update voice service"}

# Pull latest changes first to avoid rejection
echo "Pulling latest changes..."
git pull

# Add, commit, and push changes
echo "Committing and pushing changes..."
git add .
git commit -m "$COMMIT_MSG" || echo "No changes to commit"
git push

# SSH into Orin, pull changes, and restart the service
echo "Deploying to Orin..."
ssh orin "cd ~/voice_service && git pull && 
    if command -v docker-compose &> /dev/null; then
        docker-compose up --build -d
    else
        docker compose up --build -d
    fi"

# Stream logs from the container (press Ctrl+C to exit)
echo "Streaming logs..."
ssh orin "docker logs -f voice-service"
