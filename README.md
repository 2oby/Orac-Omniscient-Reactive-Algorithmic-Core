# ORAC (Omniscient Reactive Algorithmic Core)

ORAC is a lightweight, Jetson-optimized wrapper around llama.cpp that provides efficient model loading, text generation, and comprehensive logging specifically designed for NVIDIA Jetson platforms, with optimizations for the Orin Nano's memory constraints and GPU capabilities.

## Features

- Direct integration with llama.cpp for efficient model inference
- Support for GGUF models (Qwen3, TinyLlama, etc.)
- Optimized for NVIDIA Jetson platforms
- Comprehensive logging and monitoring
- REST API for model management and text generation
- Command-line interface for easy interaction

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/2oby/Orac-Omniscient-Reactive-Algorithmic-Core.git
cd Orac-Omniscient-Reactive-Algorithmic-Core
```

2. Install dependencies:
```bash
pip install -e .
```

3. Place your GGUF models in the `models/gguf` directory.

4. Use the CLI to interact with models:
```bash
# Check system status
python -m orac.cli status

# List available models
python -m orac.cli list

# Generate text
python -m orac.cli generate --model qwen3-7b-instruct.gguf --prompt "Write a haiku about AI"
```

5. Or use the REST API:
```bash
# Start the API server
uvicorn orac.api:app --host 0.0.0.0 --port 8000

# List models
curl http://localhost:8000/v1/models

# Generate text
curl -X POST http://localhost:8000/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen3-7b-instruct.gguf", "prompt": "Write a haiku about AI"}'
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

## Development

1. Install development dependencies:
```bash
pip install -e ".[dev]"
```

2. Run tests:
```bash
pytest
```

3. Run linting:
```bash
flake8 orac tests
```

## Environment Setup

ORAC uses environment variables for configuration. Each machine (development, Jetson, etc.) should have its own `.env` file:

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Adjust the values in `.env` for your environment:
   - For local development:
     - `LOG_DIR=./logs`
     - `ORAC_MODELS_PATH=./models/gguf`
   - For Docker container:
     - `LOG_DIR=/app/logs`
     - `ORAC_MODELS_PATH=/models/gguf`
   - For Jetson Orin:
     - Adjust `GPU_LAYERS` and `CPU_THREADS` based on your hardware
     - Use Docker container paths

3. The `.env` file is git-ignored and should remain local to each machine.

## License

MIT License