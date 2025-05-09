#!/usr/bin/env bash
set -euo pipefail

# Improved deploy_and_test.sh script with Jetson-specific optimizations
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

# 2) Remote: pull, build & test in container
echo -e "${YELLOW}👉 Running remote update & tests on $REMOTE_ALIAS...${NC}"
ssh "$REMOTE_ALIAS" "\
    set -euo pipefail; \
    echo '${BLUE}📂 Updating code from repository...${NC}'; \
    cd \$HOME/ORAC; \
    git remote set-url origin $SSH_ORIGIN || true; \
    git fetch origin; \
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
    
    echo '${BLUE}🐳 Detecting Docker command...${NC}'; \
    if command -v docker compose &> /dev/null; then \
        DOCKER_CMD='docker compose'; \
        echo 'Using: docker compose'; \
    else \
        DOCKER_CMD='docker-compose'; \
        echo 'Using: docker-compose'; \
    fi; \
    
    echo '${BLUE}🐳 Building & starting containers...${NC}'; \
    \$DOCKER_CMD build --no-cache -t orac:latest .; \
    \$DOCKER_CMD up --build -d; \
    
    echo '${BLUE}🔍 Checking container logs...${NC}'; \
    sleep 5; \
    \$DOCKER_CMD logs $SERVICE_NAME | tail -n 20; \
    
    echo '${BLUE}🧪 Running pytest inside container \"$SERVICE_NAME\"...${NC}'; \
    echo '${YELLOW}Running core tests...${NC}'; \
    \$DOCKER_CMD exec -T $SERVICE_NAME pytest -q tests/ --ignore=tests/test_real_models.py; \
    
    echo '${BLUE}🧪 Testing CLI functionality...${NC}'; \
    \$DOCKER_CMD exec -T $SERVICE_NAME python -m orac.cli status; \
    
    echo '${BLUE}📊 Checking resource usage after tests...${NC}'; \
    echo 'Container stats:'; \
    \$DOCKER_CMD stats --no-stream; \
"

echo -e "${GREEN}🎉 Deployment + remote tests inside '$SERVICE_NAME' succeeded!${NC}"

# Ask if we want to run a model test
read -p "Do you want to test loading and generating with a model? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}👉 Running model test on $REMOTE_ALIAS...${NC}"
    
    # Ask for the model name
    read -p "Enter model name to test (default: tinyllama): " MODEL_NAME
    MODEL_NAME=${MODEL_NAME:-"tinyllama"}
    
    ssh "$REMOTE_ALIAS" "\
        set -euo pipefail; \
        cd \$HOME/ORAC; \
        if command -v docker compose &> /dev/null; then \
            DOCKER_CMD='docker compose'; \
        else \
            DOCKER_CMD='docker-compose'; \
        fi; \
        
        echo '${BLUE}🧪 Testing model loading for $MODEL_NAME...${NC}'; \
        \$DOCKER_CMD exec -T $SERVICE_NAME python -m orac.cli load $MODEL_NAME; \
        
        echo '${BLUE}🧪 Testing generation with $MODEL_NAME...${NC}'; \
        \$DOCKER_CMD exec -T $SERVICE_NAME python -m orac.cli generate $MODEL_NAME 'Write a haiku about AI running on a Jetson Nano'; \
        
        echo '${BLUE}📊 Checking resource usage after model test...${NC}'; \
        echo 'Container stats:'; \
        \$DOCKER_CMD stats --no-stream; \
    "
fi

echo -e "${GREEN}🎉 All deployment and test operations completed successfully!${NC}"