#!/usr/bin/env bash
set -euo pipefail

# Improved deploy_and_test.sh script with llama.cpp integration
# Usage: ./scripts/deploy_and_test.sh [commit_message] [branch] [service_name]

# Default parameters
COMMIT_MSG=${1:-"Update ORAC MVP"}
DEPLOY_BRANCH=${2:-"mvp"}
SERVICE_NAME=${3:-"orac"}   # Docker Compose service to exec into
REMOTE_ALIAS="orin"
SSH_ORIGIN="git@github.com:2oby/Orac-Omniscient-Reactive-Algorithmic-Core.git"

# Terminal colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 ORAC Deployment Script for Jetson${NC}"
echo -e "${BLUE}===============================${NC}"

# Check if we're connected to the Jetson
echo -e "${YELLOW}👉 Checking connection to $REMOTE_ALIAS...${NC}"
if ! ssh -q -o BatchMode=yes -o ConnectTimeout=5 "$REMOTE_ALIAS" exit; then
    echo -e "${RED}❌ Cannot connect to $REMOTE_ALIAS. Please check your SSH configuration.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Connected to $REMOTE_ALIAS${NC}"

# 1) Local: switch, pull, commit, push
echo -e "${YELLOW}👉 Pushing local commits to '$DEPLOY_BRANCH'...${NC}"

current_branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$current_branch" != "$DEPLOY_BRANCH" ]; then
    echo -e "${YELLOW}Switching from $current_branch to $DEPLOY_BRANCH${NC}"
    git checkout "$DEPLOY_BRANCH"
fi

echo -e "${YELLOW}Pulling latest changes from origin/$DEPLOY_BRANCH${NC}"
git pull origin "$DEPLOY_BRANCH"

# Add all changes
echo -e "${YELLOW}Adding all changes${NC}"
git add -A

# Commit if there are any changes
if git diff --cached --quiet; then
    echo -e "${YELLOW}No changes to commit${NC}"
else
    echo -e "${YELLOW}Committing with message: $COMMIT_MSG${NC}"
    git commit -m "$COMMIT_MSG"
    
    echo -e "${YELLOW}Pushing to origin/$DEPLOY_BRANCH${NC}"
    git push origin "$DEPLOY_BRANCH"
fi

# 2) Remote: commit local changes, pull, build & test in container
echo -e "${YELLOW}👉 Running remote update & tests on $REMOTE_ALIAS...${NC}"
ssh "$REMOTE_ALIAS" "\
    set -euo pipefail; \
    echo '${BLUE}📂 Updating code from repository...${NC}'; \
    cd \$HOME/ORAC; \
    git remote set-url origin $SSH_ORIGIN || true; \
    git fetch origin; \
    
    # Check for local changes to favorites.json
    if git diff --quiet data/favorites.json 2>/dev/null; then
        echo '${BLUE}No local changes to favorites.json${NC}'
    else
        echo '${BLUE}Found local changes to favorites.json, committing...${NC}'
        git add data/favorites.json
        git commit -m 'chore: update model favorites from production' || true
    fi; \
    
    if git show-ref --verify --quiet refs/heads/$DEPLOY_BRANCH; then \
        git checkout $DEPLOY_BRANCH; \
    else \
        git checkout -b $DEPLOY_BRANCH origin/$DEPLOY_BRANCH; \
    fi; \
    git pull origin $DEPLOY_BRANCH; \
    
    echo '${BLUE}🔍 Checking system resources...${NC}'; \
    echo 'Memory:'; \
    free -h; \
    echo 'Disk:'; \
    df -h | grep -E '/$|/home'; \
    echo 'GPU:'; \
    if command -v nvidia-smi &> /dev/null; then \
        nvidia-smi; \
    else \
        echo 'nvidia-smi not available'; \
        jetson_release 2>/dev/null || echo 'jetson_release not available'; \
    fi; \
    
    echo '${BLUE}🔍 Checking llama.cpp binaries...${NC}'; \
    if [ -d 'third_party/llama_cpp/bin' ]; then \
        echo 'Checking llama.cpp binaries:'; \
        ls -l third_party/llama_cpp/bin/; \
        echo 'Checking library path:'; \
        ls -l third_party/llama_cpp/lib/; \
    else \
        echo '${RED}❌ llama.cpp binaries not found${NC}'; \
        exit 1; \
    fi; \
    
    echo '${BLUE}🔍 Checking model directory...${NC}'; \
    if [ -d 'models/gguf' ]; then \
        echo 'Available models:'; \
        ls -lh models/gguf/*.gguf 2>/dev/null || echo 'No GGUF models found'; \
    else \
        echo '${RED}❌ models/gguf directory not found${NC}'; \
        exit 1; \
    fi; \
    
    echo '${BLUE}🐳 Detecting Docker command...${NC}'; \
    if command -v docker compose &> /dev/null; then \
        DOCKER_CMD='docker compose'; \
        echo 'Using: docker compose'; \
    else \
        DOCKER_CMD='docker-compose'; \
        echo 'Using: docker-compose'; \
    fi; \
    
    echo '${BLUE}🐳 Building & starting containers...${NC}'; \
    \$DOCKER_CMD up --build -d; \
    
    echo '${BLUE}🔍 Checking container logs...${NC}'; \
    sleep 5; \
    \$DOCKER_CMD logs $SERVICE_NAME | tail -n 20; \
    
    echo '${BLUE}🧪 Running pytest inside container \"$SERVICE_NAME\"...${NC}'; \
    echo '${YELLOW}Running core tests...${NC}'; \
    \$DOCKER_CMD exec -T $SERVICE_NAME pytest -v tests/test_cli_generation.py --log-cli-level=INFO --capture=no; \
    
    echo '${BLUE}📊 Checking resource usage after tests...${NC}'; \
    if command -v nvidia-smi &> /dev/null; then \
        nvidia-smi; \
    else \
        echo 'GPU memory info not available'; \
    fi; \
    
    echo '${BLUE}📊 Checking container stats...${NC}'; \
    \$DOCKER_CMD stats --no-stream; \
"

echo -e "${GREEN}🎉 All deployment and test operations completed successfully!${NC}"

# Run model test directly
echo -e "${YELLOW}👉 Running model test on $REMOTE_ALIAS...${NC}"
MODEL_NAME="Qwen3-0.6B-Q4_K_M.gguf"

ssh "$REMOTE_ALIAS" "\
    set -euo pipefail; \
    cd \$HOME/ORAC; \
    if command -v docker compose &> /dev/null; then \
        DOCKER_CMD='docker compose'; \
    else \
        DOCKER_CMD='docker-compose'; \
    fi; \
    
    echo '${BLUE}🔍 Checking model file...${NC}'; \
    \$DOCKER_CMD exec -T $SERVICE_NAME ls -l /app/models/gguf/$MODEL_NAME; \
    
    echo '${BLUE}🧪 Testing generation with $MODEL_NAME...${NC}'; \
    \$DOCKER_CMD exec -T $SERVICE_NAME python3 -m orac.cli generate --model $MODEL_NAME --prompt 'Write a haiku about AI running on a Jetson Orin'; \
    
    echo '${BLUE}📊 Checking GPU memory after generation...${NC}'; \
    if command -v nvidia-smi &> /dev/null; then \
        nvidia-smi; \
    else \
        echo 'GPU memory info not available'; \
    fi; \
    
    echo '${BLUE}📊 Checking container stats...${NC}'; \
    \$DOCKER_CMD stats --no-stream; \
"

echo -e "${GREEN}🎉 All deployment and test operations completed successfully!${NC}"