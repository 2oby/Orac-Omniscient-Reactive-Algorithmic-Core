# ORAC Development Instructions

## Overview

ORAC (Omniscient Reactive Algorithmic Core) is a lightweight, Jetson-optimized wrapper around llama.cpp that provides:
- Direct model loading and inference
- Support for GGUF models
- Optimized for NVIDIA Jetson platforms
- Comprehensive logging and monitoring
- REST API for model management
- Command-line interface

## Quick Start: Using orin3 and deploy_and_test

### SSH Access to Jetson Orin (orin3)

The `orin3` hostname is configured as an SSH shortcut for the remote Jetson Orin machine.

**Remote Environment:**
- **Host**: Jetson Orin running Ubuntu 22.04 ARM64
- **Project Path**: `/home/toby/ORAC`
- **Container**: The ORAC application runs in a Docker container named `orac` (image: `orac-orac`)
- **Container Status**: Check with `docker ps` on the remote machine

```bash
# Connect to the remote Jetson Orin machine
ssh orin3

# You'll be connected to the Jetson Orin running Ubuntu 22.04 ARM64
# Navigate to the project directory
cd /home/toby/ORAC

# Check the current status
git status
ls -la

# Check if the Docker container is running
docker ps
```

**Execute Commands Directly (Non-Interactive):**
```bash
# Run a single command and return to local machine
ssh orin3 "ls -al"

# Check git status on remote
ssh orin3 "cd /home/toby/ORAC && git status"

# Check if Docker container is running
ssh orin3 "docker ps"

# Check container logs
ssh orin3 "docker logs orac"

# Pull latest changes
ssh orin3 "cd /home/toby/ORAC && git pull origin main"

# Restart the Docker container
ssh orin3 "cd /home/toby/ORAC && docker restart orac"

# Check logs
ssh orin3 "tail -f /home/toby/ORAC/logs/orac.log"
```

**Next Steps:**
For high priority upcoming tasks and current development focus, see the [Critical Path Implementation Plan](CRITICAL_PATH_IMPLEMENTATION.md).

### Using the deploy_and_test Script

The `deploy_and_test.sh` script automates the deployment process from your local machine to the remote Jetson Orin.

**Basic Usage:**
```bash
./scripts/deploy_and_test.sh "commit_message" "branch" "service_name"
```

**Deployment Script:**
```bash
# Deploy changes to remote machine with commit message
./scripts/deploy_and_test.sh "Your commit message here"

# Optional parameters (all have sensible defaults):
# ./scripts/deploy_and_test.sh [commit_message] [branch] [service_name] [cleanup_level]
# 
# Defaults:
# - commit_message: "Update ORAC MVP"
# - branch: "Grammar" 
# - service_name: "orac"
# - cleanup_level: "normal"

# Example usage:
./scripts/deploy_and_test.sh "Fix GBNF parsing issue in grammar manager"

# Deploy to specific branch
./scripts/deploy_and_test.sh "Add new domain mapping logic" "dev"

# Deploy with aggressive cleanup
./scripts/deploy_and_test.sh "Update llama.cpp to version 5306 for GBNF support" "main" "orac" "aggressive"
```

**What the Script Does:**
1. **Local Changes**: Commits your current changes with the provided message
2. **Git Push**: Pushes to the specified branch on the remote repository
3. **Remote Update**: SSH into orin3 and pulls the latest changes
4. **Container Restart**: Restarts the Docker container (e.g., "orac")
5. **Verification**: Runs tests to ensure deployment was successful

**Troubleshooting:**
```bash
# If the script fails, check the logs
tail -f logs/deploy.log

# Manual deployment if script fails
git add .
git commit -m "Your commit message"
git push origin main
ssh orin3
cd /home/toby/ORAC
git pull origin main
docker restart orac
```

## Development Tasks

### 1. Environment Setup

1. Install Python dependencies:
```bash
pip install -e ".[dev]"
```

2. Set up environment variables:
```bash
# Create .env file
cat > .env << EOF
LOG_LEVEL=INFO
LOG_DIR=/logs
EOF
```

3. Create necessary directories:
```bash
mkdir -p models/gguf logs
```

4. **Remote Development Setup (Jetson Orin)**
   
   **SSH Access:**
   ```bash
   # SSH into the remote Jetson Orin machine
   ssh orin3
   
   # Or with specific user if needed
   ssh username@orin3
   
   # Navigate to project directory
   cd /home/toby/ORAC
   ```

   **Deployment Script:**
   ```bash
   # Deploy changes to remote machine with commit message
   ./scripts/deploy_and_test.sh "Your commit message here"
   
   # Optional parameters (all have sensible defaults):
   # ./scripts/deploy_and_test.sh [commit_message] [branch] [service_name] [cleanup_level]
   # 
   # Defaults:
   # - commit_message: "Update ORAC MVP"
   # - branch: "Grammar" 
   # - service_name: "orac"
   # - cleanup_level: "normal"
   
   # Example usage:
   ./scripts/deploy_and_test.sh "Fix GBNF parsing issue in grammar manager"
   
   # Deploy to specific branch
   ./scripts/deploy_and_test.sh "Add new domain mapping logic" "dev"
   
   # Deploy with aggressive cleanup
   ./scripts/deploy_and_test.sh "Update llama.cpp to version 5306 for GBNF support" "main" "orac" "aggressive"
   
   # The script will:
   # 1. Commit your changes with the provided message
   # 2. Push to the specified branch
   # 3. SSH into orin3 and pull the latest changes
   # 4. Restart the Docker container
   # 5. Run tests to verify deployment
   ```

   **Manual Deployment (if script fails):**
   ```bash
   # Commit and push changes
   git add .
   git commit -m "Your commit message"
   git push origin main
   
   # SSH into remote and update
   ssh orin3
   cd /home/toby/ORAC
   git pull origin main
   
   # Restart Docker container
   docker restart orac
   
   # Check container status
   docker ps
   docker logs orac
   ```

### 2. Model Management

1. Place GGUF models in `models/gguf/`
2. Use `llama_cpp_client.py` for model operations:
   - List models
   - Generate text
   - Quantize models
   - Start server mode

### 3. Testing

1. Run unit tests:
```bash
pytest
```

2. Run integration tests:
```bash
pytest tests/test_real_models.py
```

3. Test CLI:
```bash
python -m orac.cli status
python -m orac.cli list
python -m orac.cli generate --model qwen3-7b-instruct.gguf --prompt "Write a haiku"
```

4. Test API:
```bash
uvicorn orac.api:app --reload
curl http://localhost:8000/v1/models
```

5. **Test Grammar Functionality (Docker Container):**
```bash
# SSH into remote machine
ssh orin3

# Navigate to project directory
cd /home/toby/ORAC

# Execute grammar tests inside the Docker container
docker exec orac python test_grammar_basic.py

# Test specific grammar files
docker exec orac python -c "
import subprocess
import os
cmd = ['/app/third_party/llama_cpp/bin/llama-cli', 
       '-m', '/models/gguf/distilgpt2.Q3_K_L.gguf',
       '-p', 'say hello',
       '--grammar-file', '/app/data/grammars/hello_world.gbnf',
       '-n', '10', '--temp', '0.0']
result = subprocess.run(cmd, capture_output=True, text=True)
print('Output:', result.stdout)
print('Error:', result.stderr)
"

# Check grammar files in container
docker exec orac ls -la /app/data/grammars/
docker exec orac cat /app/data/grammars/hello_world.gbnf
```

**Grammar Testing Strategy:**
Based on the [Critical Path Implementation Plan](CRITICAL_PATH_IMPLEMENTATION.md), there's a known GBNF parsing bug in llama.cpp v5306. The testing approach is:

1. **Start Simple**: Test basic grammars like `hello_world.gbnf` that work
2. **Incremental Complexity**: Gradually add complexity to find the breaking point
3. **Document Failures**: Record which grammars fail and at what point
4. **Workarounds**: Use unconstrained generation with post-processing validation if needed

**Current Grammar Status:**
- ✅ `hello_world.gbnf` - Simple grammar with single root rule (works)
- ❌ `static_actions.gbnf` - Complex grammar with multiple non-terminals (fails)
- 🔄 **Next**: Create intermediate complexity grammars to find the breaking point

### 4. Deployment

1. Build Docker image:
```bash
docker build -t orac .
```

2. Run container:
```bash
docker run -d --gpus all -v $(pwd)/models:/models -v $(pwd)/logs:/logs orac
```

3. Deploy to Jetson:
```bash
./scripts/deploy_and_test.sh "Update message" "branch" "service"
```

## Project Structure

```
orac/
├── api.py           # FastAPI REST API
├── cli.py           # Command-line interface
├── llama_cpp_client.py  # llama.cpp client wrapper
├── logger.py        # Logging configuration
└── models.py        # Data models
```

## Development Guidelines

1. **Code Style**
   - Use type hints
   - Follow PEP 8
   - Add docstrings
   - Write tests

2. **Error Handling**
   - Use specific exceptions
   - Add error context
   - Log errors properly

3. **Performance**
   - Monitor memory usage
   - Use async/await
   - Optimize for Jetson

4. **Testing**
   - Unit test all functions
   - Integration test with real models
   - Test error cases

## License

MIT License