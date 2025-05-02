FROM nvcr.io/nvidia/l4t-ml:r36.2.0-py3

WORKDIR /app

# Install system dependencies for llama.cpp
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
RUN pip install --upgrade pip
RUN pip install "fastapi>=0.104.1" \
                "uvicorn>=0.24.0" \
                "transformers>=4.51.0" \
                "pydantic==2.4.2" \
                "accelerate>=0.22.0" \
                "bitsandbytes>=0.41.0" \
                "einops>=0.6.0" \
                "sentencepiece>=0.1.99" \
                "httpx>=0.26.0" \
                "rich>=13.7.0" \
                "psutil>=5.9.0" \
                "regex>=2022.10.31" \
                "sacremoses" \
                "protobuf" \
                "pyyaml>=6.0" \
                "safetensors" \
                "llama-cpp-python>=0.2.0" \
                "numpy>=1.24.0"  # Required for llama-cpp-python

# Create necessary directories
RUN mkdir -p /models /models/cache /models/gguf /app/logs

# Copy application code and config
COPY config/ /app/config/
COPY voice_service.py /app/
COPY response_to_JSON_integration.py /app/
COPY test_client.py /app/

# Make the test script executable
RUN chmod +x /app/test_client.py

# Expose API port
EXPOSE 8000

# Set environment variables
ENV MODELS_DIR=/models
ENV TRANSFORMERS_CACHE=/models/cache
ENV CONFIG_DIR=/app/config

# Specify the exact Python interpreter path
CMD ["/usr/bin/python3", "/app/voice_service.py"]
