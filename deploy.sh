#!/bin/bash
# deploy.sh

# Exit on any error
set -e

# Function to handle errors
handle_error() {
    echo "Error occurred on line $1"
    echo "Command that failed: $2"
    exit 1
}

# Set up error handling
trap 'handle_error $LINENO "$BASH_COMMAND"' ERR

# Get commit message from argument or use default
COMMIT_MSG=${1:-"Update voice service"}

# Check if SSH key is available
if ! ssh -q -o BatchMode=yes -o ConnectTimeout=5 orin exit; then
    echo "Error: Cannot connect to orin server. Please check your SSH configuration."
    exit 1
fi

# Pull latest changes from remote repository
echo "Pulling latest changes..."
if ! git pull; then
    echo "Error: Failed to pull changes from remote repository"
    exit 1
fi

# Add, commit, and push changes
echo "Committing changes..."
git add .
if ! git commit -m "$COMMIT_MSG"; then
    echo "Error: Failed to commit changes"
    exit 1
fi

echo "Pushing changes..."
if ! git push; then
    echo "Error: Failed to push changes"
    exit 1
fi

# SSH into Orin, pull changes, and restart the service
echo "Deploying to orin server..."
if ! ssh orin "cd ~/voice_service && git pull && docker-compose up --build -d"; then
    echo "Error: Failed to deploy on orin server"
    exit 1
fi

# Stream logs from the container with a timeout
echo "Streaming logs (press Ctrl+C to exit)..."
timeout 300 ssh orin "docker logs -f voice-service" || true

echo "Deployment completed successfully!"