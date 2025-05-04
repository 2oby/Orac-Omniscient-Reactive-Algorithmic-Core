# syntax=docker/dockerfile:1

# --- Stage 1: Base image with Ollama and CUDA 12.6 ---
FROM dustynv/ollama:r36.4.3 AS base

# Cache APT packages to speed up rebuilds
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Ensure pip-installed binaries (pytest, uvicorn, etc.) are on PATH
ENV PATH="/usr/local/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy only the files needed for dependency installation first
COPY requirements.txt pyproject.toml /app/

# Install dependencies in a separate layer for better caching
RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install --no-cache-dir -r requirements.txt && \
    pip3 install --no-cache-dir -e .

# Now copy the rest of the application
COPY . /app/

# Point Ollama at the mounted host models folder
ENV OLLAMA_MODELS=/models/gguf

# Expose FastAPI port
EXPOSE 8000

# Start the FastAPI app
ENTRYPOINT ["uvicorn", "orac.api:app", "--host", "0.0.0.0", "--port", "8000"]
    