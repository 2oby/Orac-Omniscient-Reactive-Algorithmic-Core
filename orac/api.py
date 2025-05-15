"""
orac.api
--------
FastAPI REST API for ORAC.

Provides endpoints for:
- Model management (list, load, unload)
- Text generation
- System status
- Configuration management (favorites, model settings)
- Web interface
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from typing import List, Dict, Any
import os

from orac.logger import get_logger
from orac.llama_cpp_client import LlamaCppClient
from orac.config import load_favorites, save_favorites, load_model_configs, save_model_configs
from orac.models import (
    ModelInfo, ModelListResponse, ModelLoadRequest, ModelLoadResponse,
    ModelUnloadResponse, GenerationRequest, GenerationResponse
)

# Configure logger
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="ORAC",
    description="Omniscient Reactive Algorithmic Core - Web Interface and API",
    version="0.2.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Set up static files and templates for web interface
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

# Create directories if they don't exist
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Set up templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Global client instance
client = None

async def get_client() -> LlamaCppClient:
    """Get or create the llama.cpp client instance."""
    global client
    if client is None:
        logger.info("Initializing llama.cpp client")
        client = LlamaCppClient()
    return client

@app.get("/v1/status", tags=["System"])
async def get_status() -> Dict[str, Any]:
    """Get system status."""
    try:
        client = await get_client()
        models = await client.list_models()
        return {
            "status": "ok",
            "models_available": len(models),
            "version": "0.2.0"
        }
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/models", response_model=ModelListResponse, tags=["Models"])
async def list_models() -> ModelListResponse:
    """List available models."""
    try:
        client = await get_client()
        models = await client.list_models()
        return ModelListResponse(models=[ModelInfo(**model) for model in models])
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/models/load", response_model=ModelLoadResponse, tags=["Models"])
async def load_model(request: ModelLoadRequest) -> ModelLoadResponse:
    """Load a model."""
    try:
        client = await get_client()
        result = await client.load_model(request.name)
        return ModelLoadResponse(**result)
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/models/unload", response_model=ModelUnloadResponse, tags=["Models"])
async def unload_model(model_name: str) -> ModelUnloadResponse:
    """Unload a model."""
    try:
        client = await get_client()
        result = await client.unload_model(model_name)
        return ModelUnloadResponse(**result)
    except Exception as e:
        logger.error(f"Error unloading model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/generate", response_model=GenerationResponse, tags=["Generation"])
async def generate_text(request: GenerationRequest) -> GenerationResponse:
    """Generate text from a model."""
    try:
        client = await get_client()
        response = await client.generate(
            model=request.model,
            prompt=request.prompt,
            stream=request.stream,
            temperature=request.temperature,
            top_p=request.top_p,
            top_k=request.top_k,
            max_tokens=request.max_tokens
        )
        return GenerationResponse(
            status="success",
            response=response.response,
            elapsed_ms=response.elapsed_ms,
            model=request.model
        )
    except Exception as e:
        logger.error(f"Error generating text: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/config/favorites", tags=["Configuration"])
async def get_favorites() -> Dict[str, Any]:
    """Get favorites configuration."""
    try:
        return load_favorites()
    except Exception as e:
        logger.error(f"Error getting favorites: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/config/favorites", tags=["Configuration"])
async def update_favorites(config: Dict[str, Any]) -> Dict[str, Any]:
    """Update favorites configuration."""
    try:
        save_favorites(config)
        return {"status": "success", "message": "Favorites updated successfully"}
    except Exception as e:
        logger.error(f"Error updating favorites: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/config/models", tags=["Configuration"])
async def get_model_configs() -> Dict[str, Any]:
    """Get model configurations."""
    try:
        return load_model_configs()
    except Exception as e:
        logger.error(f"Error getting model configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/config/models", tags=["Configuration"])
async def update_model_configs(config: Dict[str, Any]) -> Dict[str, Any]:
    """Update model configurations."""
    try:
        save_model_configs(config)
        return {"status": "success", "message": "Model configurations updated successfully"}
    except Exception as e:
        logger.error(f"Error updating model configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """Initialize the client on startup."""
    try:
        await get_client()
        logger.info("API server started successfully")
    except Exception as e:
        logger.error(f"Error during API startup: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    global client
    if client is not None:
        # Add any cleanup needed
        client = None
        logger.info("API server shutdown complete")

# Web interface routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main web interface."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "ORAC - Omniscient Reactive Algorithmic Core"}
    ) 