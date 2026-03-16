# ORAC Core — Project Context

> **Human?** Read [README.md](README.md) instead for project overview.

## What This Is

The central processing hub of the ORAC system. Receives transcribed text from ORAC STT, runs it through topic-specific LLM pipelines with grammar constraints, and dispatches commands to backends like Home Assistant.

## Key Infrastructure

- **Target:** NVIDIA Orin Nano (`ssh orin4` / 192.168.8.192)
- **Remote path:** `/home/toby/ORAC/`
- **Container:** `orac-orac` on port 8000
- **Runtime:** NVIDIA (GPU-accelerated)
- **Web UI:** http://192.168.8.192:8000
- **GitHub:** https://github.com/2oby/Orac-Omniscient-Reactive-Algorithmic-Core

## Project Layout

```
Orac-Omniscient-Reactive-Algorithmic-Core/
├── orac/                              # Main application code
│   ├── api.py                         # FastAPI app and routes
│   ├── api_heartbeat.py               # Heartbeat endpoint from STT
│   ├── topic_manager.py               # Topic CRUD, routing, persistence
│   ├── services/generation_service.py  # LLM generation + caching
│   ├── dispatchers/homeassistant.py   # Home Assistant dispatcher
│   ├── backends/                      # Backend integrations
│   │   └── homeassistant_backend.py
│   └── cache/stt_response_cache.py    # STT response cache
├── data/topics.yaml                   # Persisted topic configuration
├── models/gguf/                       # GGUF model files
├── third_party/llama_cpp/             # llama.cpp binaries + libs (built on host)
├── deploy_and_test.sh                 # Deploy to Orin
├── docker-compose.yml                 # Service definition
└── Dockerfile                         # Container build
```

## Important Rules

- **This is the command processing and backend integration layer.** Transcription is handled by ORAC STT, not here.
- **Topics are persisted** in `data/topics.yaml`. This file is the source of truth.
- **llama.cpp binaries must be built on the Jetson host** (ARM + CUDA). Mounted read-only from `third_party/llama_cpp/`.
- **Host CUDA libs are mounted into the container** (`/usr/local/cuda/targets/aarch64-linux/lib`).
- **Current model:** Qwen3-0.6B-Q8_0.gguf — small enough for Orin Nano's GPU.
- **Environment vars:** `HA_URL` (Home Assistant URL), `HA_TOKEN` (long-lived access token).

## Active Topics

| Topic | Wake Word | Backend | Triggers | Description |
|-------|-----------|---------|----------|-------------|
| computa | computer_v2 | homeassistant_8ca84424 | 1460 | Smart home control (active) |
| general | alexa | (none) | 0 | General AI assistant |
| alexa | alexa | (none) | 0 | Auto-discovered, unused |
| homeassistant | (none) | (none) | 0 | Auto-discovered, unused |

## Deploying

```bash
./deploy_and_test.sh "commit message"
```

## Common Commands

```bash
# Check service
ssh orin4 "docker logs -f orac"
curl http://192.168.8.192:8000/health

# Test generation
curl -X POST http://192.168.8.192:8000/v1/generate/home_assistant \
  -H "Content-Type: application/json" \
  -d '{"prompt": "turn on bedroom lights"}'

# Check last command
curl http://192.168.8.192:8000/api/last-command | python3 -m json.tool

# Restart
ssh orin4 "docker restart orac"
```

## Known Bugs

See system-level `NEXT.md` Bugs section — 3 cache-related issues (global cache, no state verification, error command caching).
