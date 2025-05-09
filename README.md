ORAC, the Omniscient Reactive Algorithmic Core, is an open-source GitHub project designed to power smart home control through a sophisticated voice service. Built with Python and leveraging FastAPI, ORAC processes natural language commands using lightweight language models like TinyLlama to generate structured JSON outputs for controlling devices such as lights, thermostats, and TVs. Its modular architecture supports multiple models, efficient memory management, and GPU acceleration when available, ensuring responsive and adaptable performance. ORAC’s logging and error-handling mechanisms make it reliable for developers seeking to integrate voice-driven automation into smart home ecosystems.

# ORAC - Omniscient Reactive Algorithmic Core

ORAC is a lightweight, Jetson-optimized wrapper around Ollama that provides efficient model loading, text generation, and comprehensive logging specifically designed for NVIDIA Jetson platforms, with optimizations for the Orin Nano's memory constraints and ARM64 architecture.

## Features

- **Jetson-Optimized**: Specifically designed for NVIDIA Jetson Orin Nano with memory and performance optimizations
- **Efficient Model Loading**: Streamlined loading of GGUF models with proper error handling
- **Memory Management**: Careful memory usage monitoring and optimizations for constrained environments
- **Comprehensive Logging**: Detailed logs to help with troubleshooting and performance tuning
- **CLI Tool**: Easy-to-use command-line interface for testing and management
- **Docker Integration**: Reliable containerized deployment with proper GPU access

## Installation

### Prerequisites

- NVIDIA Jetson device (Orin Nano recommended)
- JetPack 6.0 or later
- Docker and Docker Compose
- Git

### Quick Setup on Jetson

Run the following commands to set up ORAC on your Jetson device:

```bash
# Clone the repository
git clone https://github.com/2oby/Orac-Omniscient-Reactive-Algorithmic-Core.git
cd Orac-Omniscient-Reactive-Algorithmic-Core

# Run the setup script
bash scripts/setup_jetson.sh

# Start the containers
docker compose up -d
```

## Usage

### CLI Commands

ORAC provides a command-line interface for interacting with models:

```bash
# Check Ollama status
docker compose exec orac python -m orac.cli status

# List available models
docker compose exec orac python -m orac.cli list

# Pull a model from Ollama library
docker compose exec orac python -m orac.cli pull tinyllama

# Load a model
docker compose exec orac python -m orac.cli load tinyllama

# Generate text from a model
docker compose exec orac python -m orac.cli generate tinyllama "Write a haiku about AI on a Jetson Nano"

# Test a model with a simple prompt
docker compose exec orac python -m orac.cli test tinyllama

# Show model details
docker compose exec orac python -m orac.cli show tinyllama

# Unload a model
docker compose exec orac python -m orac.cli unload tinyllama
```

### Recommended Models for Jetson Orin Nano

The Jetson Orin Nano has limited memory compared to desktop GPUs. Here are some recommended models that work well on this platform:

- **TinyLlama** - Small and efficient model that runs well on Jetson Orin Nano
- **Phi-2** - Microsoft's compact and capable model
- **Mistral-7B-Instruct** (Q4_K_M quantization) - Good balance of performance and quality
- **RedPajama-INCITE** (Q4 quantization) - Lightweight alternative

## Project Structure

```
ORAC/
├── logs/                    # Log directory
├── models/
│   └── gguf/               # Place your GGUF models here
├── orac/                    # Core Python package
│   ├── __init__.py
│   ├── cli.py              # Command-line interface
│   ├── logger.py           # Centralized logging
│   ├── model_loader.py     # Model loading logic
│   ├── models.py           # Pydantic models
│   └── ollama_client.py    # Client wrapper
├── scripts/
│   ├── deploy_and_test.sh  # Deployment script
│   └── setup_jetson.sh     # Jetson setup script
├── tests/                   # Unit tests
├── docker-compose.yml       # Docker configuration
├── Dockerfile               # Container definition
└── README.md                # This file
```

## Memory Optimization Tips

Running LLMs on Jetson devices requires careful memory management:

1. **Use Quantized Models**: Always use GGUF files with Q4_K_M or smaller quantization
2. **Set Context Window Size**: Use smaller context windows (2048 or lower)
3. **GPU Layers**: Configure appropriate GPU_LAYERS in .env (start with 24 and adjust)
4. **Swap Space**: Ensure adequate swap is configured (the setup script handles this)
5. **Monitor Memory**: Use `free -h` and `docker stats` to monitor memory usage

## Development and Testing

### Running Tests

```bash
# Run tests inside the container
docker compose exec orac pytest

# Run a specific test file
docker compose exec orac pytest tests/test_model_loader.py
```

### Deployment

A deployment script is provided to push your changes to a remote Jetson device:

```bash
# Deploy to remote Jetson (requires SSH configuration)
./scripts/deploy_and_test.sh "Your commit message" "branch-name" "service-name"
```

## Troubleshooting

- **Logs**: Check the logs in `logs/orac.log` for detailed information
- **Docker Logs**: View container logs with `docker compose logs -f`
- **Memory Issues**: If models fail to load, check memory with `free -h` and consider using smaller models
- **Container Access**: Debug inside the container with `docker compose exec orac bash`

## License

MIT License

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.