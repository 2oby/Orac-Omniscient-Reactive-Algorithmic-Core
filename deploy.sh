#!/bin/bash
# deploy.sh

# Get commit message from argument or use default
COMMIT_MSG=${1:-"Update voice service"}

# Add, commit, and push changes
git add .
git commit -m "$COMMIT_MSG"
git push

# SSH into Orin, pull changes, and restart the service
ssh orin "cd ~/voice_service && git pull && docker-compose up --build -d"

# Stream logs from the container
ssh orin "docker logs -f voice-service"