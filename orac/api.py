"""
orac.api
--------
API interface for ORAC.

This is a placeholder module for future API development. Currently provides
a minimal API with a single endpoint for listing models.
"""

from typing import List, Dict, Any

import httpx
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

from orac.logger import get_logger
from orac.ollama_client import OllamaClient
from orac.models import ModelListResponse, ModelInfo, ModelLoadResponse, GenerationResponse

# Get a logger for this module
logger = get_logger(__name__)

# Create FastAPI application
app = FastAPI(
    title="ORAC API",
    description="Ollama client API optimized for NVIDIA Jetson platforms",
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
    """Dependency for getting the Ollama client."""
    client = OllamaClient()
    try:
        yield client
    finally:
        await client.close()


@app.get("/", tags=["General"])
async def root():
    """API root endpoint."""
    return {
        "name": "ORAC API",
        "description": "Ollama client API optimized for NVIDIA Jetson platforms",
        "version": "0.2.0-mvp"
    }


@app.get("/v1/models", response_model=ModelListResponse, tags=["Models"])
async def list_models(client: OllamaClient = Depends(get_client)):
    """List all available models."""
    try:
        logger.info("API request: List models")
        models_list = await client.list_models()
        
        # Convert to ModelInfo objects
        model_infos = []
        for model in models_list:
            model_infos.append(
                ModelInfo(
                    name=model.get("name", ""),
                    modified_at=model.get("modified_at", None),
                    size=model.get("size", None),
                    digest=model.get("digest", None),
                    details=model
                )
            )
        
        logger.info(f"Returning {len(model_infos)} models")
        return ModelListResponse(models=model_infos)
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        raise HTTPException(status_code=502, detail=f"Error communicating with Ollama: {str(e)}")


@app.get("/healthz", tags=["Health"])
async def healthcheck(client: OllamaClient = Depends(get_client)):
    """Health check endpoint."""
    try:
        version = await client.get_version()
        return {
            "status": "healthy" if version != "unknown" else "degraded",
            "ollama_version": version
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }