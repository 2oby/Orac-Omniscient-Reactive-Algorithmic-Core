FROM nvcr.io/nvidia/l4t-ml:r36.2.0-py3

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential cmake git libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Install Python dependencies with pinned numpy
RUN pip install --no-cache-dir numpy==1.26.4 fastapi==0.110.3 uvicorn transformers==4.51.0 \
    pydantic==2.4.2 accelerate bitsandbytes einops sentencepiece \
    httpx rich psutil regex sacremoses protobuf pyyaml safetensors

# Install llama-cpp-python 0.3.8
RUN pip install --no-cache-dir --force-reinstall llama-cpp-python==0.3.8

# Create necessary directories with permissions
RUN mkdir -p /models /models/cache /models/gguf /app/logs && \
    chmod -R 777 /models && \
    chmod -R 777 /app/logs

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