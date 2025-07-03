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

# Create a non-root user that can be overridden at runtime
RUN groupadd -r orac && useradd -r -g orac -u 1000 orac

# Install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install --no-cache-dir -r requirements.txt

# Create necessary directories with proper permissions
# These will be overridden by volume mounts, but ensures proper initial state
RUN mkdir -p /app/data /app/logs /app/cache /app/test_logs && \
    chown -R orac:orac /app/data /app/logs /app/cache /app/test_logs && \
    chmod 755 /app/data /app/logs /app/cache /app/test_logs

# Copy application code and configuration files
COPY . /app/
COPY data/grammars.yaml /app/data/grammars.yaml

# Make llama.cpp binaries executable
RUN chmod +x /app/third_party/llama_cpp/bin/*

# Install the package in development mode
# TODO: For production deployment, replace with: RUN pip3 install .
# The -e flag creates an editable install which is only needed during development
RUN pip3 install -e .

# Create startup script
RUN echo '#!/bin/sh\nuvicorn orac.api:app --host 0.0.0.0 --port 8000' > /app/start.sh && \
    chmod +x /app/start.sh

# Change ownership of the entire app directory to the orac user
RUN chown -R orac:orac /app

# Switch to non-root user
USER orac

# Set the entrypoint
ENTRYPOINT ["/app/start.sh"]
    