# ORAC Core User Guide

Complete guide for deploying, configuring, and operating ORAC Core.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Installation & Deployment](#installation--deployment)
3. [Configuration](#configuration)
4. [Setting Up Backends](#setting-up-backends)
5. [Creating Topics](#creating-topics)
6. [Working with Grammars](#working-with-grammars)
7. [Monitoring & Operations](#monitoring--operations)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### 5-Minute Setup

```bash
# 1. Clone repository
git clone https://github.com/2oby/Orac-Omniscient-Reactive-Algorithmic-Core.git
cd Orac-Omniscient-Reactive-Algorithmic-Core

# 2. Place models
cp your-model.gguf models/gguf/

# 3. Configure (optional)
cat > .env << EOF
HA_URL=http://192.168.8.99:8123
HA_TOKEN=your_token_here
EOF

# 4. Deploy
docker compose up -d

# 5. Test
curl http://localhost:8000/health
```

---

## Installation & Deployment

### Prerequisites

**Hardware:**
- Jetson Orin Nano (4GB+ RAM) or CUDA-capable device
- 15-32GB storage
- Network connectivity

**Software:**
- Docker & Docker Compose
- NVIDIA Container Toolkit (for GPU)

### Installation

**1. Install Docker:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

**2. Install NVIDIA Container Toolkit (Jetson):**
```bash
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

**3. Clone ORAC:**
```bash
git clone https://github.com/2oby/Orac-Omniscient-Reactive-Algorithmic-Core.git
cd Orac-Omniscient-Reactive-Algorithmic-Core
```

### Deployment

**Standard Deployment:**
```bash
docker compose up -d
docker logs -f orac
```

**Remote Deployment (to Jetson):**
```bash
./deploy_and_test.sh "Initial deployment"
```

The script will:
- Commit and push changes to GitHub
- Pull on remote device
- Restart Docker container
- Run health checks

**Rebuild (after major changes):**
```bash
./deploy_and_test.sh --rebuild "Major update"
```

### Verify Deployment

```bash
# Check container
docker ps | grep orac

# Check health
curl http://localhost:8000/health

# Check logs
docker logs --tail 50 orac

# Check GPU
docker exec orac nvidia-smi
```

---

## Configuration

### Environment Variables

Create `.env` file in project root:

```bash
# Home Assistant (if using HA backend)
HA_URL=http://192.168.8.99:8123
HA_TOKEN=your_long_lived_token

# Paths
ORAC_MODELS_PATH=/models/gguf
LOG_LEVEL=INFO

# Container settings
UID=1000
GID=1000
TZ=Europe/Amsterdam
```

### Model Configuration

Edit `data/model_configs.yaml`:

```yaml
models:
  Qwen3-0.6B-Q4_K_M.gguf:
    context_size: 2048
    gpu_layers: 24      # Adjust for your hardware
    n_threads: 6
    temperature: 0.7
    top_p: 0.95
    max_tokens: 512
```

**GPU Layers Guide:**
- Jetson Orin Nano 4GB: 16-24 layers
- Jetson Orin Nano 8GB: 24-33 layers
- More layers = faster, but uses more memory

### Adding Models

```bash
# Copy model to models directory
cp your-model.gguf models/gguf/

# Restart ORAC
docker restart orac

# Verify model is available
curl http://localhost:8000/v1/models
```

**Recommended Models:**
- **TinyLlama 1.1B** (700MB) - Fast, testing
- **Qwen 0.6B-3B** (2-4GB) - Home automation
- **Qwen 7B** (4.5GB) - Advanced queries

---

## Setting Up Backends

### What are Backends?

Backends are external services that ORAC controls (e.g., Home Assistant). They receive structured commands from the LLM and execute actions.

### Home Assistant Backend

**1. Generate HA Token:**
- Open Home Assistant
- Profile → "Long-Lived Access Tokens"
- Create token named "ORAC Core"
- Copy the token

**2. Configure Environment:**
```bash
# Add to .env
HA_URL=http://192.168.8.99:8123
HA_TOKEN=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...

# Restart
docker restart orac
```

**3. Create Backend:**
```bash
curl -X POST http://localhost:8000/api/backends \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Home Assistant",
    "type": "homeassistant",
    "connection": {
      "url": "'"$HA_URL"'",
      "token": "'"$HA_TOKEN"'"
    }
  }'
```

Save the `backend_id` from the response.

**4. Test Connection:**
```bash
curl -X POST http://localhost:8000/api/backends/{backend_id}/test
```

**5. Fetch Entities:**
```bash
curl http://localhost:8000/api/backends/{backend_id}/entities
```

**6. Generate Grammar:**
```bash
curl -X POST http://localhost:8000/api/backends/{backend_id}/grammar
```

This creates a grammar file with all your Home Assistant devices.

---

## Creating Topics

### What are Topics?

Topics are processing pipelines that define:
- Which model to use
- Grammar constraints
- Backend for execution
- LLM settings

### Create Home Automation Topic

```bash
curl -X POST http://localhost:8000/api/topics \
  -H "Content-Type: application/json" \
  -d '{
    "name": "home_assistant",
    "model": "Qwen3-0.6B-Q4_K_M.gguf",
    "backend_id": "backend_abc123",
    "grammar_file": "backend_abc123.gbnf",
    "settings": {
      "temperature": 0.1,
      "top_p": 0.9,
      "max_tokens": 100
    },
    "wake_word": "hey oracle"
  }'
```

### Using Topics

```bash
curl -X POST http://localhost:8000/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "turn on bedroom lights",
    "topic": "home_assistant"
  }'
```

### Topic Settings Guide

| Use Case | Temperature | Top P | Model Size |
|----------|-------------|-------|------------|
| Home Control | 0.0-0.1 | 0.8-0.9 | Small (0.6B-3B) |
| General Chat | 0.7-0.8 | 0.9-0.95 | Medium (3B-7B) |
| Code Help | 0.2-0.4 | 0.9-0.95 | Large (7B+) |

**Temperature:**
- 0.0-0.2: Deterministic, focused
- 0.7-1.0: Creative, diverse

---

## Working with Grammars

### What are Grammars?

GBNF grammars constrain LLM output to valid JSON, ensuring parseable responses.

**Without Grammar:**
```
"Sure! I'll turn on the bedroom lights for you."
```

**With Grammar:**
```json
{"action":"turn on","device":"lights","location":"bedroom"}
```

### Auto-Generated Grammars

The easiest way is to generate from your backend:

```bash
curl -X POST http://localhost:8000/api/backends/{backend_id}/grammar
```

This creates `data/grammars/{backend_id}.gbnf` with all your devices.

### Custom Grammar Example

Create `data/grammars/simple.gbnf`:

```gbnf
root ::= "{" ws
  "\"action\"" ws ":" ws action ws "," ws
  "\"device\"" ws ":" ws device ws "," ws
  "\"location\"" ws ":" ws location ws
"}"

action ::= "\"turn on\"" | "\"turn off\"" | "\"toggle\""
device ::= "\"lights\"" | "\"switch\"" | "\"thermostat\""
location ::= "\"bedroom\"" | "\"kitchen\"" | "\"living room\""

ws ::= [ \t\n]*
```

### Testing Grammars

```bash
curl -X POST http://localhost:8000/v1/generate \
  -d '{
    "model": "Qwen3-0.6B-Q4_K_M.gguf",
    "prompt": "turn on bedroom lights",
    "grammar_file": "simple.gbnf",
    "temperature": 0.0
  }'
```

---

## Monitoring & Operations

### Health Checks

```bash
# Basic health
curl http://localhost:8000/health

# Detailed status
curl http://localhost:8000/heartbeat
```

### Viewing Logs

```bash
# Real-time logs
docker logs -f orac

# Last 100 lines
docker logs --tail 100 orac

# Since timestamp
docker logs --since "2025-10-20T14:00:00" orac
```

### Resource Monitoring

```bash
# Container stats
docker stats orac

# GPU usage
nvidia-smi

# Memory
free -h

# Disk space
df -h
```

### Performance Metrics

**Typical Response Times (Jetson Orin Nano 8GB):**

| Model Size | Generation Time | Total End-to-End |
|------------|----------------|------------------|
| 0.6B | 500-1000ms | 1-2s |
| 3B | 1000-2000ms | 2-3s |
| 7B | 2000-4000ms | 3-5s |

### Monitoring Script

```bash
#!/bin/bash
# monitor_orac.sh

while true; do
    # Check health
    if ! curl -sf http://localhost:8000/health > /dev/null; then
        echo "ALERT: ORAC is down"
        docker restart orac
    fi

    # Check GPU temperature
    TEMP=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits)
    if [ $TEMP -gt 85 ]; then
        echo "WARNING: High GPU temperature: ${TEMP}°C"
    fi

    sleep 300  # Check every 5 minutes
done
```

---

## Troubleshooting

### Container Won't Start

**Check logs:**
```bash
docker logs orac
```

**Common fixes:**
```bash
# Port in use - change port in docker-compose.yml
ports: "8080:8000"

# GPU not available
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# Permission denied
sudo usermod -aG docker $USER
# Log out and back in
```

### Model Not Found

```bash
# Check models in container
docker exec orac ls -la /models/gguf/

# Copy model
cp your-model.gguf models/gguf/
docker restart orac
```

### Backend Connection Fails

```bash
# Test from container
docker exec orac curl -H "Authorization: Bearer $HA_TOKEN" \
  http://192.168.8.99:8123/api/

# Common issues:
# - Wrong URL (no trailing slash)
# - Invalid token (regenerate in HA)
# - Network not reachable (check firewall)
# - HA not running
```

### LLM Not Following Grammar

**Solutions:**
1. Lower temperature to 0.0
2. Strengthen system prompt
3. Test with simpler grammar
4. Verify grammar file exists

### Out of Memory

```bash
# Check memory usage
docker stats orac
nvidia-smi

# Solutions:
# 1. Reduce GPU layers in model_configs.yaml
gpu_layers: 16  # Reduce from 24

# 2. Reduce context size
context_size: 2048  # Reduce from 4096

# 3. Use smaller model
```

### Slow Performance

**Optimize GPU:**
```yaml
# In model_configs.yaml
gpu_layers: 33  # Increase (if memory allows)
```

**Check GPU usage:**
```bash
# Should show GPU utilization
watch -n 1 nvidia-smi
```

**Use faster model:**
- Q4_K_M instead of Q8_0 (smaller, faster)

### Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| "Connection refused" | Backend not reachable | Check HA_URL, verify HA is running |
| "Model not found" | Model not in models/ | Copy model to models/gguf/ |
| "CUDA out of memory" | Too many GPU layers | Reduce gpu_layers setting |
| "Grammar parse error" | Invalid GBNF syntax | Check grammar file syntax |
| "401 Unauthorized" | Invalid HA token | Regenerate token in Home Assistant |

### Getting Help

1. Check logs: `docker logs orac`
2. Search [GitHub Issues](https://github.com/2oby/Orac-Omniscient-Reactive-Algorithmic-Core/issues)
3. Create new issue with:
   - Environment details
   - Steps to reproduce
   - Log output
   - Configuration (sanitize tokens!)

---

## Best Practices

### Security
- Never commit tokens to git
- Use `.env` for sensitive data
- Regenerate tokens periodically

### Performance
- Use appropriate model size for your use case
- Monitor GPU temperature
- Keep models quantized (Q4_K_M recommended)

### Maintenance
- Review logs regularly
- Update models periodically
- Keep Docker images updated
- Monitor disk space

### Configuration
- Document your configuration changes
- Test after configuration changes
- Use version control for config files

---

## Quick Reference

### Essential Commands

```bash
# Start ORAC
docker compose up -d

# Stop ORAC
docker compose down

# Restart ORAC
docker restart orac

# View logs
docker logs -f orac

# Deploy updates
./deploy_and_test.sh "Update description"

# Check health
curl http://localhost:8000/health

# List models
curl http://localhost:8000/v1/models

# List backends
curl http://localhost:8000/api/backends

# List topics
curl http://localhost:8000/api/topics
```

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Check health |
| `/v1/models` | GET | List models |
| `/v1/generate` | POST | Generate text |
| `/api/backends` | GET/POST | Manage backends |
| `/api/topics` | GET/POST | Manage topics |

### Configuration Files

| File | Purpose |
|------|---------|
| `.env` | Environment variables |
| `docker-compose.yml` | Docker configuration |
| `data/model_configs.yaml` | Model settings |
| `data/topics.yaml` | Topic definitions |
| `data/grammars/*.gbnf` | Grammar files |

---

For advanced topics and development, see [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md).

*Last Updated: October 2025*
