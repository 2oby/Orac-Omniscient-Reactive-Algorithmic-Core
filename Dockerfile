# --- Stage 1: base image with Ollama and CUDA 12.6 ---
    FROM dustynv/ollama:r36.4.3 AS base

    # Install Python 3.10 and pip (if not already there)
    RUN apt-get update && \
        apt-get install -y --no-install-recommends python3 python3-pip && \
        apt-get clean && rm -rf /var/lib/apt/lists/*
    
    # Copy application code
    WORKDIR /app
    COPY . /app
    
    # Install Python dependencies
    RUN pip3 install --no-cache-dir -r requirements.txt
    
    # Point Ollama at the mounted host folder
    ENV OLLAMA_MODELS=/models/gguf
    
    EXPOSE 8000
    ENTRYPOINT ["uvicorn", "orac.api:app", "--host", "0.0.0.0", "--port", "8000"]
    