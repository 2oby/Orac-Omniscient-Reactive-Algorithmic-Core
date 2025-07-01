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

# Add Home Assistant imports
from orac.homeassistant.client import HomeAssistantClient
from orac.homeassistant.config import HomeAssistantConfig
from orac.homeassistant.mapping_config import EntityMappingConfig
from orac.homeassistant.grammar_manager import HomeAssistantGrammarManager

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

# Global Home Assistant components
ha_client = None
ha_mapping_config = None
ha_grammar_manager = None

async def get_client() -> LlamaCppClient:
    """Get or create the llama.cpp client instance."""
    global client
    if client is None:
        logger.info("Initializing llama.cpp client")
        # Use the environment variable or default path
        model_path = os.getenv("ORAC_MODELS_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "models/gguf"))
        client = LlamaCppClient(model_path=model_path)
    return client

async def get_ha_client() -> HomeAssistantClient:
    """Get or create the Home Assistant client instance."""
    global ha_client
    if ha_client is None:
        logger.info("Initializing Home Assistant client")
        config_path = os.path.join(os.path.dirname(__file__), "homeassistant", "config.yaml")
        config = HomeAssistantConfig.from_yaml(config_path)
        ha_client = HomeAssistantClient(config)
        # Initialize the async context manager
        await ha_client.__aenter__()
    return ha_client

async def get_ha_mapping_config() -> EntityMappingConfig:
    """Get or create the Home Assistant mapping config instance."""
    global ha_mapping_config
    if ha_mapping_config is None:
        logger.info("Initializing Home Assistant mapping config")
        client = await get_ha_client()
        ha_mapping_config = EntityMappingConfig(client=client)
    return ha_mapping_config

async def get_ha_grammar_manager() -> HomeAssistantGrammarManager:
    """Get or create the Home Assistant grammar manager instance."""
    global ha_grammar_manager
    if ha_grammar_manager is None:
        logger.info("Initializing Home Assistant grammar manager")
        client = await get_ha_client()
        mapping_config = await get_ha_mapping_config()
        ha_grammar_manager = HomeAssistantGrammarManager(client=client, mapping_config=mapping_config)
    return ha_grammar_manager

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

@app.post("/v1/homeassistant/grammar/gbnf", tags=["Home Assistant"])
async def generate_gbnf_grammar() -> Dict[str, Any]:
    """Generate GBNF grammar file for Home Assistant commands."""
    try:
        grammar_manager = await get_ha_grammar_manager()
        gbnf_content = await grammar_manager.generate_gbnf_grammar()
        grammar_file_path = await grammar_manager.save_gbnf_grammar()
        
        return {
            "status": "success",
            "message": "GBNF grammar generated successfully",
            "grammar_file": grammar_file_path,
            "grammar_content": gbnf_content
        }
    except Exception as e:
        logger.error(f"Error generating GBNF grammar: {e}")
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
        
        # Check if this is a Home Assistant command (simple heuristic)
        ha_keywords = ["turn on", "turn off", "light", "switch", "thermostat", "bedroom", "kitchen"]
        is_ha_command = any(keyword in request.prompt.lower() for keyword in ha_keywords)
        
        # Use GBNF grammar for Home Assistant commands
        grammar_file = request.grammar_file  # Use grammar_file from request
        if grammar_file and not os.path.exists(grammar_file):
            logger.warning(f"Grammar file not found: {grammar_file}, falling back to JSON grammar")
            grammar_file = None
        elif not grammar_file and is_ha_command and request.json_mode:
            # Use set_temp.gbnf as default for Home Assistant commands
            grammar_file = os.path.join(os.path.dirname(__file__), "..", "data", "test_grammars", "set_temp.gbnf")
            if os.path.exists(grammar_file):
                logger.info(f"Using set_temp.gbnf grammar for HA command: {grammar_file}")
            else:
                logger.warning(f"set_temp.gbnf not found at {grammar_file}, falling back to unknown_set.gbnf")
                fallback_grammar = os.path.join(os.path.dirname(__file__), "..", "data", "test_grammars", "unknown_set.gbnf")
                if os.path.exists(fallback_grammar):
                    grammar_file = fallback_grammar
                    logger.info(f"Using fallback grammar: {fallback_grammar}")
                else:
                    logger.warning(f"Fallback grammar not found, using JSON grammar")
                    grammar_file = None
        
        # Format the prompt based on whether we're using a grammar file
        if grammar_file and os.path.exists(grammar_file):
            # Use the same prompt format as the CLI test for grammar files
            # But respect user-provided system prompt if available
            if request.system_prompt:
                system_prompt = request.system_prompt
            else:
                system_prompt = "You are a JSON-only formatter. Respond with a JSON object containing 'device', 'action', and 'location' keys."
            # Start the JSON structure to give the model a clear starting point
            formatted_prompt = f"{system_prompt}\n\nUser: {request.prompt}\nAssistant: {{\"device\":\""
        else:
            # Use the standard prompt format for non-grammar requests
            prompt_format = model_config.get("prompt_format", {})
            template = prompt_format.get("template", "{system_prompt}\n\n{user_prompt}")
            
            # Use JSON-specific system prompt when in JSON mode
            if request.json_mode:
                system_prompt = "You must respond with valid JSON only. Do not include any explanations, thinking, or commentary outside the JSON structure. Your response should be clean, properly formatted JSON that directly answers the request."
            else:
                # Use provided system prompt or fall back to model's default
                system_prompt = request.system_prompt or model_config.get("system_prompt", "")
            
            # Format the prompt using the template
            formatted_prompt = template.format(
                system_prompt=system_prompt,
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
            json_mode=request.json_mode,
            grammar_file=grammar_file
        )
        
        # For grammar files, we need to complete the JSON structure
        response_text = response.text
        if grammar_file and os.path.exists(grammar_file):
            # The model response should complete the JSON, but we need to ensure it's properly closed
            if not response_text.strip().endswith('}'):
                # Try to find the end of the JSON structure
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group()
                else:
                    # If no complete JSON found, try to close it properly
                    response_text = response_text.strip()
                    if not response_text.endswith('"'):
                        response_text += '"'
                    if not response_text.endswith('}'):
                        response_text += '}'
        
        return GenerationResponse(
            status="success",
            response=response_text,
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
        client = await get_ha_client()
        cache = client.cache
        
        # Get cache statistics
        stats = cache.get_stats()
        
        return {
            "status": "success",
            "cache_stats": stats,
            "cache_enabled": cache.is_enabled(),
            "cache_directory": cache.cache_dir if hasattr(cache, 'cache_dir') else None
        }
    except Exception as e:
        logger.error(f"Error getting Home Assistant cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# New Home Assistant Mapping API Endpoints

@app.get("/v1/homeassistant/mapping/list", tags=["Home Assistant"])
async def list_entity_mappings() -> Dict[str, Any]:
    """List all entity mappings."""
    try:
        mapping_config = await get_ha_mapping_config()
        summary = mapping_config.get_mapping_summary()
        
        # Get the actual mappings from the internal attribute
        mappings = mapping_config._mappings
        
        return {
            "status": "success",
            "mappings": mappings,
            "summary": summary
        }
    except Exception as e:
        logger.error(f"Error listing entity mappings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/homeassistant/mapping/check-null", tags=["Home Assistant"])
async def check_null_mappings() -> Dict[str, Any]:
    """Check for entities that need friendly names (NULL mappings)."""
    try:
        mapping_config = await get_ha_mapping_config()
        mappings = mapping_config._mappings
        
        null_entities = []
        for entity_id, friendly_name in mappings.items():
            if not friendly_name or friendly_name.lower() == 'null':
                null_entities.append({
                    "entity_id": entity_id,
                    "current_name": friendly_name,
                    "suggested_name": entity_id.replace('_', ' ').replace('.', ' ')
                })
        
        return {
            "status": "success",
            "null_entities": null_entities,
            "total_null_count": len(null_entities),
            "total_entities": len(mappings)
        }
    except Exception as e:
        logger.error(f"Error checking null mappings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/homeassistant/mapping/save", tags=["Home Assistant"])
async def save_entity_mapping(entity_id: str, friendly_name: str) -> Dict[str, Any]:
    """Save a single entity mapping."""
    try:
        mapping_config = await get_ha_mapping_config()
        mapping_config.add_mapping(entity_id, friendly_name)
        await mapping_config.save_mappings()
        
        return {
            "status": "success",
            "message": f"Mapping saved: {entity_id} -> {friendly_name}",
            "entity_id": entity_id,
            "friendly_name": friendly_name
        }
    except Exception as e:
        logger.error(f"Error saving entity mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/v1/homeassistant/mapping/update", tags=["Home Assistant"])
async def update_entity_mappings(mappings: Dict[str, str]) -> Dict[str, Any]:
    """Update multiple entity mappings."""
    try:
        mapping_config = await get_ha_mapping_config()
        
        updated_count = 0
        for entity_id, friendly_name in mappings.items():
            mapping_config.add_mapping(entity_id, friendly_name)
            updated_count += 1
        
        await mapping_config.save_mappings()
        
        return {
            "status": "success",
            "message": f"Updated {updated_count} mappings",
            "updated_count": updated_count,
            "mappings": mappings
        }
    except Exception as e:
        logger.error(f"Error updating entity mappings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/homeassistant/mapping/auto-discover", tags=["Home Assistant"])
async def run_auto_discovery() -> Dict[str, Any]:
    """Run auto-discovery to find and map new entities."""
    try:
        mapping_config = await get_ha_mapping_config()
        
        # Run auto-discovery
        await mapping_config.auto_discover_entities()
        
        # Get updated mappings
        mappings = mapping_config.get_all_mappings()
        
        return {
            "status": "success",
            "message": "Auto-discovery completed",
            "total_mappings": len(mappings),
            "entities_with_friendly_names": len([m for m in mappings.values() if m and m.lower() != 'null']),
            "entities_needing_names": len([m for m in mappings.values() if not m or m.lower() == 'null'])
        }
    except Exception as e:
        logger.error(f"Error running auto-discovery: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/homeassistant/grammar", tags=["Home Assistant"])
async def get_grammar() -> Dict[str, Any]:
    """Get current grammar rules."""
    try:
        grammar_manager = await get_ha_grammar_manager()
        grammar = await grammar_manager.generate_grammar()
        
        return {
            "status": "success",
            "grammar": grammar,
            "device_count": len(grammar.get("properties", {}).get("device", {}).get("enum", [])),
            "action_count": len(grammar.get("properties", {}).get("action", {}).get("enum", [])),
            "location_count": len(grammar.get("properties", {}).get("location", {}).get("enum", []))
        }
    except Exception as e:
        logger.error(f"Error getting grammar: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/homeassistant/grammar/update", tags=["Home Assistant"])
async def update_grammar() -> Dict[str, Any]:
    """Update grammar rules with latest Home Assistant data."""
    try:
        grammar_manager = await get_ha_grammar_manager()
        await grammar_manager.update_grammar()
        
        # Get updated grammar
        grammar = await grammar_manager.generate_grammar()
        
        return {
            "status": "success",
            "message": "Grammar updated successfully",
            "grammar": grammar,
            "device_count": len(grammar.get("properties", {}).get("device", {}).get("enum", [])),
            "action_count": len(grammar.get("properties", {}).get("action", {}).get("enum", [])),
            "location_count": len(grammar.get("properties", {}).get("location", {}).get("enum", []))
        }
    except Exception as e:
        logger.error(f"Error updating grammar: {e}")
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
                
                # Start with set_temp.gbnf grammar for Home Assistant commands with temperature/percentage support
                grammar_file = os.path.join(os.path.dirname(__file__), "..", "data", "test_grammars", "set_temp.gbnf")
                if os.path.exists(grammar_file):
                    logger.info(f"Starting default model with set_temp.gbnf grammar: {grammar_file}")
                    await client._ensure_server_running(
                        model=favorites["default_model"],
                        temperature=0.1,  # Use 0.1 for temperature/percentage grammar (optimized settings)
                        top_p=0.9,
                        top_k=10,
                        json_mode=True,
                        grammar_file=grammar_file
                    )
                else:
                    logger.warning(f"set_temp.gbnf not found at {grammar_file}, falling back to unknown_set.gbnf")
                    fallback_grammar = os.path.join(os.path.dirname(__file__), "..", "data", "test_grammars", "unknown_set.gbnf")
                    if os.path.exists(fallback_grammar):
                        logger.info(f"Using fallback grammar: {fallback_grammar}")
                        await client._ensure_server_running(
                            model=favorites["default_model"],
                            temperature=0.0,
                            top_p=0.8,
                            top_k=30,
                            json_mode=True,
                            grammar_file=fallback_grammar
                        )
                    else:
                        logger.warning(f"Fallback grammar not found, starting with default JSON grammar")
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
    global client, ha_client
    if client:
        try:
            await client.cleanup()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    # Clean up Home Assistant client
    if ha_client:
        try:
            await ha_client.__aexit__(None, None, None)
        except Exception as e:
            logger.error(f"Error during HA client shutdown: {e}")

# Web interface routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main web interface."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "ORAC - Omniscient Reactive Algorithmic Core"}
    ) 