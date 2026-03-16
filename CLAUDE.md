# ORAC Core - Project Context

## What is ORAC Core?

The central processing hub of the ORAC system. Receives transcribed text from ORAC STT, runs it through topic-specific LLM pipelines with grammar constraints, and dispatches commands to backends like Home Assistant.

## Deployment

- **Target**: NVIDIA Orin Nano (`ssh orin4` / 192.168.8.192)
- **Remote path**: `/home/toby/ORAC/`
- **Container**: `orac-orac` on port 8000
- **Runtime**: NVIDIA (GPU-accelerated)
- **Web UI**: http://192.168.8.192:8000

## Tech Stack

- Python, FastAPI/Uvicorn
- llama.cpp for LLM inference (CUDA-accelerated)
- GBNF grammars for structured output
- Current model: Qwen3-0.6B-Q8_0.gguf
- Docker with NVIDIA runtime on Jetson

## Key Paths

| Path | Purpose |
|------|---------|
| `orac/` | Main application code |
| `orac/api.py` | FastAPI app and endpoints |
| `orac/api_heartbeat.py` | Heartbeat endpoint from STT |
| `orac/topic_manager.py` | Topic CRUD and routing |
| `orac/services/generation_service.py` | LLM generation + caching |
| `orac/dispatchers/homeassistant.py` | Home Assistant dispatcher |
| `orac/backends/` | Backend integrations |
| `data/topics.yaml` | Persisted topic configuration |
| `models/gguf/` | GGUF model files |
| `third_party/llama_cpp/` | llama.cpp binaries and libs |

## Active Topics

| Topic | Wake Word | Backend | Description |
|-------|-----------|---------|-------------|
| computa | computer_v2 | homeassistant_8ca84424 | Smart home control (1460 triggers) |
| general | alexa | (none) | General AI assistant |
| alexa | alexa | (none) | Auto-discovered, unused |
| homeassistant | (none) | (none) | Auto-discovered, unused |

## Deploy

```bash
./deploy_and_test.sh "commit message"
```

## Environment Variables

- `HA_URL` - Home Assistant URL (default: http://192.168.8.100:8123)
- `HA_TOKEN` - Home Assistant long-lived access token
- `ORAC_MODELS_PATH` - Path to GGUF models
- `LOG_LEVEL` - Logging level

## Rules

- This is the command processing and backend integration layer
- Transcription is handled by ORAC STT, not here
- Topics are persisted in `data/topics.yaml`
- Host CUDA libs are mounted into the container (Jetson SBSA workaround)
