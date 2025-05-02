FROM nvcr.io/nvidia/l4t-ml:r36.2.0-py3

WORKDIR /app

RUN apt-get update && apt-get install -y \
        build-essential cmake git libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

# Python libs (unchanged)
RUN pip install --upgrade pip
RUN pip install fastapi==0.110.3 uvicorn transformers==4.51.0 \
        pydantic==2.4.2 accelerate bitsandbytes einops sentencepiece \
        httpx rich psutil regex sacremoses protobuf pyyaml safetensors numpy

# Build llama‑cpp‑python 0.3.8 for Orin GPU
ENV CMAKE_ARGS="-DGGML_CUDA=ON -DGGML_CUDA_ARCH=87"
ENV FORCE_CMAKE=1           # prevent pip from ever grabbing an x86 wheel
RUN pip install --no-binary :all: --no-cache-dir llama-cpp-python==0.3.8

# Create necessary directories
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
