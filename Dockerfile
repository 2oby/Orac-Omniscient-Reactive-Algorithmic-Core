# syntax=docker/dockerfile:1

# --- Stage 1: Base image with CUDA 12.6 ---
FROM nvidia/cuda:12.6.0-runtime-ubuntu22.04 AS base

# Set environment variables for GPU optimization
ENV CUDA_VISIBLE_DEVICES=0
ENV LD_LIBRARY_PATH="/app/third_party/llama_cpp/lib:${LD_LIBRARY_PATH}"

# Install Python and dependencies
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 python3-pip python3-dev \
    libgomp1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/

# Make llama.cpp binaries executable
RUN chmod +x /app/third_party/llama_cpp/bin/*

# Install the package in development mode
# TODO: For production deployment, replace with: RUN pip3 install .
# The -e flag creates an editable install which is only needed during development
RUN pip3 install -e .

# Create log directory
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Create data directory for configurations
RUN mkdir -p /app/data && chmod 777 /app/data

# Create startup script
RUN echo '#!/bin/sh\nuvicorn orac.api:app --host 0.0.0.0 --port 8000' > /app/start.sh && \
    chmod +x /app/start.sh

# Set the entrypoint
ENTRYPOINT ["/app/start.sh"]
    