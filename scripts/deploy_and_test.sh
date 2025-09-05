#!/usr/bin/env bash
set -euo pipefail

# Improved deploy_and_test.sh script with llama.cpp integration
# Usage: ./scripts/deploy_and_test.sh [commit_message] [branch] [service_name] [cleanup_level]
# cleanup_level: normal (default) or aggressive

# Default parameters
COMMIT_MSG=${1:-"Update ORAC MVP"}
DEPLOY_BRANCH=${2:-"master"}   # Default to 'master' branch if not specified
SERVICE_NAME=${3:-"orac"}   # Docker Compose service to exec into
CLEANUP_LEVEL=${4:-"light"}   # light, normal, or aggressive
REMOTE_ALIAS="orin4"
SSH_ORIGIN="https://github.com/2oby/Orac-Omniscient-Reactive-Algorithmic-Core.git"

# Terminal colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 ORAC Deployment Script for Jetson${NC}"
echo -e "${BLUE}===============================${NC}"
echo -e "${YELLOW}Deploying branch: $DEPLOY_BRANCH${NC}"
echo -e "${YELLOW}Usage: ./scripts/deploy_and_test.sh [commit_message] [branch] [service_name] [cleanup_level]${NC}"
echo -e "${YELLOW}Example: ./scripts/deploy_and_test.sh \"Update API\" MVP_API${NC}"
echo -e "${YELLOW}Example: ./scripts/deploy_and_test.sh \"Update API\" MVP_API orac light${NC}"
echo -e "${YELLOW}Cleanup levels: light (default), normal, aggressive${NC}"
echo -e "${BLUE}===============================${NC}"

# Check if we're on the correct branch
current_branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$current_branch" != "$DEPLOY_BRANCH" ]; then
    echo -e "${YELLOW}⚠️  Warning: You are on branch '$current_branch' but deploying to '$DEPLOY_BRANCH'${NC}"
    echo -e "${YELLOW}   This is normal if you're deploying from a different branch${NC}"
fi

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

# Check if this is first run on remote
echo -e "${YELLOW}👉 Checking remote configuration...${NC}"
if ! ssh "$REMOTE_ALIAS" "[ -f \$HOME/ORAC/data/favorites.json ] && [ -f \$HOME/ORAC/data/model_configs.yaml ]"; then
    echo -e "${YELLOW}First run detected - copying configuration files...${NC}"
    # Create remote data directory
    ssh "$REMOTE_ALIAS" "mkdir -p \$HOME/ORAC/data"
    # Copy files to remote (using path relative to project root)
    scp "$(git rev-parse --show-toplevel)/data/favorites.json" "$(git rev-parse --show-toplevel)/data/model_configs.yaml" "$REMOTE_ALIAS:\$HOME/ORAC/data/" || {
        echo -e "${RED}❌ No local config files found - you will need to create these manually on the test machine${NC}"
        exit 1
    }
    echo -e "${GREEN}✓ Configuration files copied successfully${NC}"
fi

# 2) Remote: pull, build & test in container
echo -e "${YELLOW}👉 Running remote update & tests on $REMOTE_ALIAS...${NC}"
ssh "$REMOTE_ALIAS" "\
    set -euo pipefail; \
    echo '${BLUE}📂 Updating code from repository...${NC}'; \
    cd \$HOME/ORAC; \
    git remote set-url origin $SSH_ORIGIN || true; \
    git fetch origin; \
    
    # Force reset to remote branch, discarding any local changes
    echo '${BLUE}📝 Resetting to remote state...${NC}'; \
    git reset --hard origin/$DEPLOY_BRANCH; \
    # Clean untracked files but exclude logs, cache, and data directories
    git clean -fd --exclude=logs/ --exclude=cache/ --exclude=data/; \
    
    # Download Git LFS files (llama.cpp binaries) - only if needed
    echo '${BLUE}📥 Checking Git LFS files...${NC}'; \
    if command -v git-lfs &> /dev/null; then \
        # Check if binaries already exist and are up to date
        if [ -s third_party/llama_cpp/bin/llama-server ] && [ -s third_party/llama_cpp/bin/llama-cli ]; then \
            echo '${GREEN}✓ llama.cpp binaries already exist, skipping download${NC}'; \
        else \
            echo '${YELLOW}📥 Downloading Git LFS files...${NC}'; \
            git lfs pull; \
            echo '${GREEN}✓ Git LFS files downloaded successfully${NC}'; \
        fi; \
    else \
        echo '${YELLOW}⚠️  git-lfs not available, checking if binaries exist...${NC}'; \
        if [ -s third_party/llama_cpp/bin/llama-server ]; then \
            echo '${GREEN}✓ llama.cpp binaries found${NC}'; \
        else \
            echo '${RED}❌ llama.cpp binaries not found and git-lfs not available${NC}'; \
            echo '${YELLOW}You may need to install git-lfs or manually copy binaries${NC}'; \
        fi; \
    fi; \
    
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
    \
    echo '${BLUE}🔍 Checking disk space thresholds...${NC}'; \
    if [ -f 'scripts/monitor_disk_space.sh' ]; then \
        echo 'Running disk space check...'; \
        bash scripts/monitor_disk_space.sh check; \
    else \
        echo 'Disk space monitoring script not found'; \
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
    
    echo '${BLUE}🧹 Cleaning up old Docker resources...${NC}'; \
    echo '${YELLOW}Cleanup level: $CLEANUP_LEVEL${NC}'; \
    \
    echo '${YELLOW}Disk space before cleanup:${NC}'; \
    df -h | grep -E '/$|/home'; \
    \
    echo '${YELLOW}Docker disk usage before cleanup:${NC}'; \
    docker system df 2>/dev/null || echo 'Docker system df not available'; \
    \
    echo '${YELLOW}Stopping and removing old containers...${NC}'; \
    \$DOCKER_CMD down --remove-orphans 2>/dev/null || true; \
    docker container prune -f 2>/dev/null || true; \
    \
    if [ "$CLEANUP_LEVEL" = "aggressive" ]; then \
        echo '${YELLOW}🔄 Aggressive cleanup mode - removing ALL unused Docker resources...${NC}'; \
        echo '${YELLOW}Removing all unused images (including dangling)...${NC}'; \
        docker image prune -a -f 2>/dev/null || true; \
        \
        echo '${YELLOW}Removing all unused volumes...${NC}'; \
        docker volume prune -f 2>/dev/null || true; \
        \
        echo '${YELLOW}Removing all unused networks...${NC}'; \
        docker network prune -f 2>/dev/null || true; \
        \
        echo '${YELLOW}Removing build cache...${NC}'; \
        docker builder prune -a -f 2>/dev/null || true; \
        \
        echo '${YELLOW}Full system prune...${NC}'; \
        docker system prune -a -f --volumes 2>/dev/null || true; \
    elif [ "$CLEANUP_LEVEL" = "normal" ]; then \
        echo '${YELLOW}Normal cleanup mode - removing unused resources...${NC}'; \
        echo '${YELLOW}Removing unused images...${NC}'; \
        docker image prune -a -f 2>/dev/null || true; \
        \
        echo '${YELLOW}Removing unused volumes...${NC}'; \
        docker volume prune -f 2>/dev/null || true; \
        \
        echo '${YELLOW}Removing unused networks...${NC}'; \
        docker network prune -f 2>/dev/null || true; \
    else \
        echo '${YELLOW}Light cleanup mode - preserving images, cleaning minimal resources...${NC}'; \
        echo '${YELLOW}Removing stopped containers...${NC}'; \
        docker container prune -f 2>/dev/null || true; \
        \
        echo '${YELLOW}Removing unused networks...${NC}'; \
        docker network prune -f 2>/dev/null || true; \
        \
        echo '${YELLOW}Cleaning build cache if needed...${NC}'; \
        # Only clean build cache if it's getting large
        BUILD_CACHE_SIZE=\$(docker system df 2>/dev/null | grep "Build Cache" | awk '{print \$4}' | sed 's/GB//' || echo "0"); \
        if [ "\$BUILD_CACHE_SIZE" != "0" ] && [ "\$BUILD_CACHE_SIZE" -gt 20 ]; then \
            echo '${YELLOW}Build cache is \${BUILD_CACHE_SIZE}GB, cleaning...${NC}'; \
            docker builder prune -a -f 2>/dev/null || true; \
        else \
            echo '${GREEN}Build cache size is acceptable (\${BUILD_CACHE_SIZE}GB)${NC}'; \
        fi; \
    fi; \
    \
    echo '${YELLOW}Disk space after cleanup:${NC}'; \
    df -h | grep -E '/$|/home'; \
    \
    echo '${YELLOW}Docker disk usage after cleanup:${NC}'; \
    docker system df 2>/dev/null || echo 'Docker system df not available'; \
    \
    echo '${GREEN}✓ Docker cleanup completed${NC}'; \
    
    echo '${BLUE}🐳 Building & starting containers...${NC}'; \
    # Always force a rebuild for reliability
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

    echo '${BLUE}🧪 Testing Home Assistant integration...${NC}'; \
    \$DOCKER_CMD exec -T $SERVICE_NAME python3 -m pytest tests/test_homeassistant.py -v; \
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
    \$DOCKER_CMD exec -T $SERVICE_NAME ls -l /models/gguf/$MODEL_NAME; \
    
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