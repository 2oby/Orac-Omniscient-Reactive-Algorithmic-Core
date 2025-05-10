"""
orac.api
--------
API interface for ORAC.

Provides a FastAPI-based REST API for interacting with llama.cpp models.
"""

from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

from orac.logger import get_logger
from orac.llama_cpp_client import LlamaCppClient
from orac.models import ModelListResponse, ModelInfo, PromptRequest, PromptResponse

# Get a logger for this module
logger = get_logger(__name__)

# Create FastAPI application
app = FastAPI(
    title="ORAC API",
    description="llama.cpp API optimized for NVIDIA Jetson platforms",
    version="0.2.0-mvp"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only, restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Client dependency
async def get_client():
    """Dependency for getting the llama.cpp client."""
    client = LlamaCppClient()
    try:
        yield client
    finally:
        pass  # No cleanup needed for llama.cpp client

@app.get("/v1/models", response_model=ModelListResponse)
async def list_models(client: LlamaCppClient = Depends(get_client)):
    """List available models."""
    try:
        models = await client.list_models()
        return {"models": [ModelInfo(**m) for m in models]}
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/generate", response_model=PromptResponse)
async def generate(request: PromptRequest, client: LlamaCppClient = Depends(get_client)):
    """Generate text from a model."""
    try:
        response = await client.generate(request.model, request.prompt, request.stream)
        return response
    except Exception as e:
        logger.error(f"Error generating text: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/healthz", tags=["Health"])
async def healthcheck(client: LlamaCppClient = Depends(get_client)):
    """Health check endpoint."""
    try:
        # Try to list models as a basic health check
        models = await client.list_models()
        return {
            "status": "healthy",
            "models_count": len(models)
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }