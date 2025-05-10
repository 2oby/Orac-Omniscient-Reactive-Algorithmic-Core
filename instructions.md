# ORAC Development Instructions

## Overview

ORAC (Omniscient Reactive Algorithmic Core) is a lightweight, Jetson-optimized wrapper around llama.cpp that provides:
- Direct model loading and inference
- Support for GGUF models
- Optimized for NVIDIA Jetson platforms
- Comprehensive logging and monitoring
- REST API for model management
- Command-line interface

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