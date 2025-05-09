# syntax=docker/dockerfile:1

# --- Stage 1: Base image with Ollama and CUDA 12.6 ---
FROM dustynv/ollama:r36.4.3 AS base

# Set environment variables for GPU optimization
ENV CUDA_VISIBLE_DEVICES=0
ENV OLLAMA_HOST=0.0.0.0
ENV OLLAMA_MODELS=/models/gguf

# Install Python and dependencies
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 python3-pip python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/

# Create log directory
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Set the entrypoint
ENTRYPOINT ["python3", "-m", "orac.cli"]
    