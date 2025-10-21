# ORAC Core

**Omniscient Reactive Algorithmic Core**

ORAC is a lightweight, NVIDIA Jetson-optimized LLM inference server built on llama.cpp, designed for voice-controlled smart home automation and natural language command processing.

## What is ORAC?

ORAC Core provides:
- **LLM Inference**: Direct integration with llama.cpp for efficient model inference on edge devices
- **Grammar-Constrained Generation**: GBNF grammar support for deterministic, structured outputs
- **Backend Integration**: Pluggable backend system (Home Assistant, and more)
- **Topic-Based Routing**: Route commands to specialized processing pipelines
- **RESTful API**: Complete API for generation, configuration, and backend management
- **Jetson-Optimized**: Tuned for NVIDIA Jetson Orin and other edge compute platforms

## Quick Start

### Prerequisites

- NVIDIA Jetson device (Orin Nano/NX recommended) or x86_64 with NVIDIA GPU
- Docker & Docker Compose
- GGUF format LLM models

### 5-Minute Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/2oby/Orac-Omniscient-Reactive-Algorithmic-Core.git
   cd Orac-Omniscient-Reactive-Algorithmic-Core
   ```

2. **Place your models**
   ```bash
   # Put GGUF models in models/gguf/
   cp your-model.gguf models/gguf/
   ```

3. **Configure environment** (optional)
   ```bash
   # Create .env file for Home Assistant integration
   cat > .env << EOF
   HA_URL=http://your-ha-ip:8123
   HA_TOKEN=your_long_lived_token
   EOF
   ```

4. **Deploy with Docker**
   ```bash
   # Standard deployment
   docker-compose up -d

   # View logs
   docker logs -f orac
   ```

5. **Test the API**
   ```bash
   # Check status
   curl http://localhost:8000/health

   # List available models
   curl http://localhost:8000/v1/models

   # Generate text
   curl -X POST http://localhost:8000/v1/generate \
     -H "Content-Type: application/json" \
     -d '{"model": "your-model.gguf", "prompt": "Hello, ORAC!"}'
   ```

## Key Features

### Grammar-Constrained Generation
Use GBNF grammars to constrain LLM output to valid JSON structures:

```bash
curl -X POST http://localhost:8000/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "turn on the bedroom lights",
    "topic": "home_assistant",
    "grammar_file": "ha_commands.gbnf"
  }'
```

Returns structured JSON like:
```json
{"action":"turn on","device":"lights","location":"bedroom"}
```

### Backend System
Create and manage backends for command execution:

```bash
# Create a Home Assistant backend
curl -X POST http://localhost:8000/api/backends \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Home Assistant",
    "type": "homeassistant",
    "connection": {
      "url": "http://192.168.1.100:8123",
      "token": "your_token"
    }
  }'

# Fetch entities from backend
curl http://localhost:8000/api/backends/{backend_id}/entities
```

### Topic-Based Routing
Topics define complete processing pipelines with their own:
- LLM model and settings
- GBNF grammar for output constraints
- Backend for command execution

```bash
# Create a topic for home automation
curl -X POST http://localhost:8000/api/topics \
  -H "Content-Type: application/json" \
  -d '{
    "name": "home_assistant",
    "model": "qwen-7b.gguf",
    "backend_id": "ha_backend_123",
    "grammar_file": "ha_commands.gbnf"
  }'
```

## Documentation

**Complete documentation available in the [docs/](docs/) directory:**

- **[User Guide](docs/USER_GUIDE.md)** - Installation, deployment, configuration, backends, topics, grammars, monitoring, and troubleshooting
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)** - Architecture, development setup, API reference, testing, coding standards, and contributing guidelines

## Project Status

ORAC Core is in active development. Current version: **0.2.0**

Recent improvements:
- ✅ Backend abstraction and factory pattern
- ✅ Topic-based command routing
- ✅ Grammar-constrained generation
- ✅ Home Assistant backend integration
- ✅ RESTful API for backends and topics
- ✅ Docker deployment with GPU support

See [cleanup.MD](cleanup.MD) for detailed development progress.

## Architecture Highlights

```
Voice Command → STT → ORAC Core → Backend Service
                        ↓
                   LLM (Grammar)
                        ↓
                   Topic Manager
                        ↓
                  Backend Executor
```

- **LLM Layer**: llama.cpp integration with GGUF model support
- **Topic Manager**: Routes commands to appropriate processing pipelines
- **Backend System**: Abstract backend interface with pluggable implementations
- **Grammar System**: GBNF parser and constrained generation
- **API Layer**: FastAPI-based REST API

See [Developer Guide](docs/DEVELOPER_GUIDE.md#architecture-overview) for detailed architecture documentation.

## Network Configuration

Default network configuration for typical deployment:

| Component | IP Address | Purpose |
|-----------|-----------|---------|
| ORAC Core (Jetson) | 192.168.8.192 | Main LLM inference server |
| Home Assistant | 192.168.8.99:8123 | Smart home backend |

Customize via environment variables (see [User Guide](docs/USER_GUIDE.md#configuration)).

## Technology Stack

- **LLM Runtime**: [llama.cpp](https://github.com/ggerganov/llama.cpp) (CUDA-enabled)
- **API Framework**: FastAPI + Uvicorn
- **Containerization**: Docker with NVIDIA runtime
- **Language**: Python 3.8+
- **Platforms**: NVIDIA Jetson (ARM64), x86_64 with CUDA

## Use Cases

- **Voice-Controlled Smart Home**: Natural language commands for Home Assistant
- **Edge AI Inference**: Run LLMs locally on Jetson devices
- **Constrained Generation**: Structured outputs for deterministic command processing
- **Multi-Backend Orchestration**: Control multiple services from a single interface

## Hardware Requirements

### Minimum (Jetson Orin Nano 4GB)
- 4GB RAM
- 15GB storage
- CUDA-capable GPU

### Recommended (Jetson Orin Nano 8GB+)
- 8GB+ RAM
- 32GB+ storage
- CUDA-capable GPU

See [User Guide](docs/USER_GUIDE.md#installation--deployment) for detailed requirements.

## Contributing

We welcome contributions! See [Developer Guide](docs/DEVELOPER_GUIDE.md#contributing) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/2oby/Orac-Omniscient-Reactive-Algorithmic-Core/issues)
- **Discussions**: [GitHub Discussions](https://github.com/2oby/Orac-Omniscient-Reactive-Algorithmic-Core/discussions)

---

**Quick Links**: [User Guide](docs/USER_GUIDE.md) | [Developer Guide](docs/DEVELOPER_GUIDE.md)
