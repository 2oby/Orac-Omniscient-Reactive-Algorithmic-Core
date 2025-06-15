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
import asyncio

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
        # Use the environment variable or default path
        model_path = os.getenv("ORAC_MODELS_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "models/gguf"))
        client = LlamaCppClient(model_path=model_path)
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
        # Get the model to use (default or specified)
        favorites = load_favorites()
        model_to_use = request.model or favorites.get("default_model")
        
        if not model_to_use:
            raise HTTPException(
                status_code=400,
                detail="No model specified in request and no default model configured"
            )
        
        # Load model configs to get the prompt format
        model_configs = load_model_configs()
        model_config = model_configs.get("models", {}).get(model_to_use, {})
        
        # Get the prompt format template
        prompt_format = model_config.get("prompt_format", {})
        template = prompt_format.get("template", "{system_prompt}\n\n{user_prompt}")
        
        # Format the prompt using the template
        formatted_prompt = template.format(
            system_prompt=request.system_prompt or "",
            user_prompt=request.prompt
        )
        
        client = await get_client()
        response = await client.generate(
            model=model_to_use,  # Use the determined model
            prompt=formatted_prompt,
            stream=request.stream,
            temperature=request.temperature,
            top_p=request.top_p,
            top_k=request.top_k,
            max_tokens=request.max_tokens,
            timeout=30,  # Set a 30-second timeout for the API endpoint
            json_mode=request.json_mode
        )
        return GenerationResponse(
            status="success",
            response=response.text,
            elapsed_ms=response.response_time * 1000,  # Convert to milliseconds
            model=model_to_use  # Return the actual model used
        )
    except Exception as e:
        logger.error(f"Error generating text: {e}")
        if "timed out" in str(e):
            raise HTTPException(status_code=504, detail="Generation timed out")
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

@app.post("/v1/homeassistant/cache", tags=["Home Assistant"])
async def create_homeassistant_cache() -> Dict[str, Any]:
    """Create Home Assistant cache by fetching entities, services, and areas."""
    try:
        from orac.homeassistant.client import HomeAssistantClient
        from orac.homeassistant.config import HomeAssistantConfig
        import os
        
        # Load configuration
        config_path = os.path.join(os.path.dirname(__file__), "homeassistant", "config.yaml")
        config = HomeAssistantConfig.from_yaml(config_path)
        
        logger.info(f"Creating Home Assistant cache for {config.host}:{config.port}")
        
        # Create client and fetch data to trigger cache
        async with HomeAssistantClient(config) as client:
            # Fetch entities
            logger.info("Fetching entities...")
            entities = await client.get_states(use_cache=False)  # Force fresh fetch
            
            # Fetch services
            logger.info("Fetching services...")
            services = await client.get_services(use_cache=False)  # Force fresh fetch
            
            # Fetch areas
            logger.info("Fetching areas...")
            areas = await client.get_areas(use_cache=False)  # Force fresh fetch
            
            # Get cache stats
            cache_stats = client.get_cache_stats()
            
            return {
                "status": "success",
                "message": "Home Assistant cache created successfully",
                "cache_stats": cache_stats,
                "entities_fetched": len(entities),
                "service_domains_fetched": len(services),
                "areas_fetched": len(areas),
                "cache_directory": str(config.cache_dir) if config.cache_dir else None
            }
            
    except Exception as e:
        logger.error(f"Error creating Home Assistant cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/homeassistant/cache/stats", tags=["Home Assistant"])
async def get_homeassistant_cache_stats() -> Dict[str, Any]:
    """Get Home Assistant cache statistics."""
    try:
        from orac.homeassistant.client import HomeAssistantClient
        from orac.homeassistant.config import HomeAssistantConfig
        import os
        
        # Load configuration
        config_path = os.path.join(os.path.dirname(__file__), "homeassistant", "config.yaml")
        config = HomeAssistantConfig.from_yaml(config_path)
        
        # Create client and get cache stats
        async with HomeAssistantClient(config) as client:
            cache_stats = client.get_cache_stats()
            
            return {
                "status": "success",
                "cache_stats": cache_stats,
                "cache_directory": str(config.cache_dir) if config.cache_dir else None
            }
            
    except Exception as e:
        logger.error(f"Error getting Home Assistant cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """Initialize the API on startup."""
    global client
    try:
        # Create client instance with proper model path
        model_path = os.getenv("ORAC_MODELS_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "models/gguf"))
        client = LlamaCppClient(model_path=model_path)
        
        # Load default model if configured
        favorites = load_favorites()
        if favorites.get("default_model"):
            try:
                logger.info(f"Loading default model: {favorites['default_model']}")
                # Use _ensure_server_running instead of load_model
                await client._ensure_server_running(
                    model=favorites["default_model"],
                    temperature=0.7,
                    top_p=0.7,
                    top_k=40,
                    json_mode=True
                )
                logger.info("Default model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load default model: {e}")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    global client
    if client:
        try:
            await client.cleanup()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# Web interface routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main web interface."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "ORAC - Omniscient Reactive Algorithmic Core"}
    ) 