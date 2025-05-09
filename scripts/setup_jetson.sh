#!/usr/bin/env bash
set -euo pipefail

# Setup script for ORAC on NVIDIA Jetson Orin Nano
# Usage: ./scripts/setup_jetson.sh

# Terminal colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 ORAC Setup Script for Jetson Orin Nano${NC}"
echo -e "${BLUE}=======================================${NC}"

# Check if we're running on a Jetson device
if [[ ! -f /etc/nv_tegra_release ]]; then
    echo -e "${RED}❌ This script is designed to run on a Jetson device.${NC}"
    echo -e "${RED}   It appears you are not running on a Jetson platform.${NC}"
    exit 1
fi

# Create directory structure
echo -e "${YELLOW}👉 Creating directory structure...${NC}"
mkdir -p ~/ORAC/models/gguf
mkdir -p ~/ORAC/logs

# Clone repository if not exists
if [[ ! -d ~/ORAC/.git ]]; then
    echo -e "${YELLOW}👉 Cloning ORAC repository...${NC}"
    git clone https://github.com/2oby/Orac-Omniscient-Reactive-Algorithmic-Core.git ~/ORAC_tmp
    # Move all content from tmp to actual directory
    mv ~/ORAC_tmp/* ~/ORAC/
    mv ~/ORAC_tmp/.git* ~/ORAC/
    rm -rf ~/ORAC_tmp
else
    echo -e "${YELLOW}👉 Updating existing ORAC repository...${NC}"
    cd ~/ORAC
    git pull
fi

# Add docker group and user if needed
if ! groups | grep -q docker; then
    echo -e "${YELLOW}👉 Setting up Docker permissions...${NC}"
    sudo groupadd -f docker
    sudo usermod -aG docker $USER
    echo -e "${YELLOW}   You may need to log out and back in for Docker permissions to take effect.${NC}"
fi

# Check Docker installation
echo -e "${YELLOW}👉 Checking Docker installation...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}   Docker not found, installing...${NC}"
    
    # Install Docker prerequisites
    sudo apt-get update
    sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
    
    # Download and install Docker
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    
    # Start Docker service
    sudo systemctl enable docker
    sudo systemctl start docker
    
    echo -e "${GREEN}✓ Docker installed successfully${NC}"
else
    echo -e "${GREEN}✓ Docker already installed${NC}"
fi

# Check Docker Compose installation
echo -e "${YELLOW}👉 Checking Docker Compose installation...${NC}"
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${YELLOW}   Docker Compose not found, installing...${NC}"
    
    # Install Docker Compose
    COMPOSE_VERSION="v2.20.3"
    sudo curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-aarch64" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    
    echo -e "${GREEN}✓ Docker Compose installed successfully${NC}"
else
    echo -e "${GREEN}✓ Docker Compose already installed${NC}"
fi

# Optimize system for running LLMs
echo -e "${YELLOW}👉 Optimizing system for LLMs...${NC}"

# Set up swap if needed
TOTAL_MEM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
TOTAL_MEM_GB=$((TOTAL_MEM_KB / 1024 / 1024))
SWAP_SIZE_GB=8

if [[ $TOTAL_MEM_GB -lt 16 ]]; then
    echo -e "${YELLOW}   System has less than 16GB RAM (${TOTAL_MEM_GB}GB detected)${NC}"
    echo -e "${YELLOW}   Setting up ${SWAP_SIZE_GB}GB swap file${NC}"
    
    # Check if swap already exists
    SWAP_EXISTS=$(sudo swapon --show | wc -l)
    
    if [[ $SWAP_EXISTS -eq 0 ]]; then
        # Create swap file
        sudo fallocate -l ${SWAP_SIZE_GB}G /var/swapfile
        sudo chmod 600 /var/swapfile
        sudo mkswap /var/swapfile
        sudo swapon /var/swapfile
        
        # Add to fstab
        if ! grep -q '/var/swapfile' /etc/fstab; then
            echo '/var/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab
        fi
        
        echo -e "${GREEN}✓ ${SWAP_SIZE_GB}GB swap file created and activated${NC}"
    else
        echo -e "${GREEN}✓ Swap already configured${NC}"
    fi
    
    # Set swappiness lower for better performance
    echo -e "${YELLOW}   Setting swappiness to 10 for better performance${NC}"
    sudo sysctl vm.swappiness=10
    if ! grep -q 'vm.swappiness' /etc/sysctl.conf; then
        echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
    fi
fi

# Set maximum clock speed for better performance
# Jetson Orin Nano-specific
if [[ -f /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]]; then
    echo -e "${YELLOW}   Setting CPU governor to performance${NC}"
    echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
    
    # Make the change permanent
    if ! grep -q 'CPU governor' /etc/rc.local; then
        sudo sh -c 'if ! [ -f /etc/rc.local ]; then echo "#!/bin/sh -e\nexit 0" > /etc/rc.local; chmod +x /etc/rc.local; fi'
        sudo sed -i -e '$i \# Set CPU governor to performance\necho performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor\n' /etc/rc.local
    fi
fi

# Set up Python environment
echo -e "${YELLOW}👉 Setting up Python environment...${NC}"
cd ~/ORAC

# Create a minimal Modelfile if it doesn't exist
if [[ ! -f ~/ORAC/models/gguf/Modelfile ]]; then
    echo -e "${YELLOW}   Creating dummy Modelfile in models/gguf directory${NC}"
    echo -e "FROM dummy.gguf\n\nPARAMETER temperature 0.7\nPARAMETER num_ctx 2048" > ~/ORAC/models/gguf/Modelfile
fi

# Check if Python environment needs updating
if [[ -f ~/ORAC/requirements.txt ]]; then
    echo -e "${YELLOW}   Installing/updating Python dependencies${NC}"
    pip3 install -r requirements.txt
    pip3 install -e .
fi

echo -e "${GREEN}✓ Python environment set up successfully${NC}"

# Configure environment variables
echo -e "${YELLOW}👉 Setting up environment variables...${NC}"

# Create .env file if it doesn't exist
if [[ ! -f ~/ORAC/.env ]]; then
    echo -e "${YELLOW}   Creating .env file${NC}"
    cat > ~/ORAC/.env << EOF
# ORAC environment configuration
OLLAMA_HOST=orac-ollama
OLLAMA_PORT=11434
OLLAMA_MODEL_PATH=/models/gguf
LOG_LEVEL=INFO
LOG_DIR=/logs

# Jetson optimizations
GPU_LAYERS=24
CPU_THREADS=6
EOF
fi

# Build the Docker images
echo -e "${YELLOW}👉 Building Docker images...${NC}"
cd ~/ORAC

if command -v docker compose &> /dev/null; then
    docker compose build
else
    docker-compose build
fi

echo -e "${GREEN}🎉 ORAC setup complete!${NC}"
echo -e "${YELLOW}To start ORAC, run the following command:${NC}"
echo -e "${BLUE}cd ~/ORAC && docker compose up -d${NC}"
echo
echo -e "${YELLOW}To check the status, run:${NC}"
echo -e "${BLUE}docker compose logs -f${NC}"
echo
echo -e "${YELLOW}To test a model, run:${NC}"
echo -e "${BLUE}docker compose exec orac python -m orac.cli status${NC}"
echo -e "${BLUE}docker compose exec orac python -m orac.cli list${NC}"
echo -e "${BLUE}docker compose exec orac python -m orac.cli pull tinyllama${NC}"
echo -e "${BLUE}docker compose exec orac python -m orac.cli load tinyllama${NC}"
echo -e "${BLUE}docker compose exec orac python -m orac.cli test tinyllama${NC}"