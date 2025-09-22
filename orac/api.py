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
from datetime import datetime

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

# Add Topic management imports
from orac.topic_manager import TopicManager
from orac.api_topics import router as topics_router
from orac.homeassistant.ha_executor import HAExecutor
from orac.api_heartbeat import router as heartbeat_router

# Add Dispatcher imports
from orac.dispatchers import dispatcher_registry

# Add Backend Manager import
from orac.backend_manager import BackendManager

# Configure logger
logger = get_logger(__name__)

# Initialize topic manager
topic_manager = TopicManager()

# Initialize HA executor
ha_executor = HAExecutor()

# Initialize backend manager
backend_manager = BackendManager()

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

# Include routers
app.include_router(topics_router)
app.include_router(heartbeat_router)

# Dispatcher endpoints
@app.get("/v1/dispatchers", tags=["Dispatchers"])
async def list_dispatchers() -> Dict[str, Any]:
    """List all available dispatchers."""
    try:
        dispatchers = dispatcher_registry.list_available()
        return {
            "status": "success",
            "dispatchers": dispatchers
        }
    except Exception as e:
        logger.error(f"Error listing dispatchers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Backend Management endpoints
@app.post("/api/backends", tags=["Backends"])
async def create_backend(request: Request) -> Dict[str, Any]:
    """Create a new backend configuration."""
    try:
        data = await request.json()
        backend = backend_manager.create_backend(
            name=data.get("name"),
            backend_type=data.get("type", "homeassistant"),
            connection=data.get("connection", {})
        )
        return {
            "status": "success",
            "backend": backend
        }
    except Exception as e:
        logger.error(f"Error creating backend: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/backends", tags=["Backends"])
async def list_backends() -> Dict[str, Any]:
    """List all configured backends."""
    try:
        backends = backend_manager.list_backends()
        return {
            "status": "success",
            "backends": backends
        }
    except Exception as e:
        logger.error(f"Error listing backends: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/backends/{backend_id}", tags=["Backends"])
async def get_backend(backend_id: str) -> Dict[str, Any]:
    """Get a specific backend configuration."""
    try:
        backend = backend_manager.get_backend(backend_id)
        if not backend:
            raise HTTPException(status_code=404, detail=f"Backend {backend_id} not found")
        return {
            "status": "success",
            "backend": backend
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting backend: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/backends/{backend_id}", tags=["Backends"])
async def update_backend(backend_id: str, request: Request) -> Dict[str, Any]:
    """Update a backend configuration."""
    try:
        data = await request.json()
        backend = backend_manager.update_backend(backend_id, data)
        if not backend:
            raise HTTPException(status_code=404, detail=f"Backend {backend_id} not found")
        return {
            "status": "success",
            "backend": backend
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating backend: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/backends/{backend_id}", tags=["Backends"])
async def delete_backend(backend_id: str) -> Dict[str, Any]:
    """Delete a backend configuration."""
    try:
        success = backend_manager.delete_backend(backend_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Backend {backend_id} not found")
        return {
            "status": "success",
            "message": f"Backend {backend_id} deleted"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting backend: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/backends/{backend_id}/test", tags=["Backends"])
async def test_backend_connection(backend_id: str) -> Dict[str, Any]:
    """Test a backend connection."""
    try:
        result = await backend_manager.test_connection(backend_id)
        return {
            "status": "success" if result.get("success") else "error",
            "result": result
        }
    except Exception as e:
        logger.error(f"Error testing backend connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/backends/{backend_id}/entities/fetch", tags=["Backends"])
async def fetch_backend_entities(backend_id: str) -> Dict[str, Any]:
    """Fetch entities from a backend."""
    try:
        result = await backend_manager.fetch_entities(backend_id)
        return {
            "status": "success" if result.get("success") else "error",
            "result": result
        }
    except Exception as e:
        logger.error(f"Error fetching entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/backends/{backend_id}/entities", tags=["Backends"])
async def get_backend_entities(backend_id: str, enabled: bool = None) -> Dict[str, Any]:
    """Get configured entities for a backend."""
    try:
        entities = backend_manager.get_entities(backend_id, filter_enabled=enabled)
        return {
            "status": "success",
            "entities": entities
        }
    except Exception as e:
        logger.error(f"Error getting entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/backends/{backend_id}/entities/{entity_id}", tags=["Backends"])
async def update_backend_entity(backend_id: str, entity_id: str, request: Request) -> Dict[str, Any]:
    """Update an entity configuration."""
    try:
        data = await request.json()
        entity = backend_manager.update_entity(backend_id, entity_id, data)
        if not entity:
            raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")
        return {
            "status": "success",
            "entity": entity
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating entity: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/backends/{backend_id}/entities/bulk", tags=["Backends"])
async def bulk_update_entities(backend_id: str, request: Request) -> Dict[str, Any]:
    """Bulk update entity configurations."""
    try:
        data = await request.json()
        entity_ids = data.get("entity_ids", [])
        updates = data.get("updates", {})
        result = backend_manager.bulk_update_entities(backend_id, entity_ids, updates)
        return {
            "status": "success" if result.get("success") else "error",
            "result": result
        }
    except Exception as e:
        logger.error(f"Error in bulk update: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/backends/{backend_id}/device-types", tags=["Backends"])
async def add_device_type(backend_id: str, request: Request) -> Dict[str, Any]:
    """Add a custom device type to a backend."""
    try:
        data = await request.json()
        device_type = data.get("device_type")
        if not device_type:
            raise HTTPException(status_code=400, detail="device_type is required")

        success = backend_manager.add_device_type(backend_id, device_type)
        if success:
            return {
                "status": "success",
                "message": f"Device type '{device_type}' added successfully"
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to add device type or already exists"
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding device type: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/backends/{backend_id}/locations", tags=["Backends"])
async def add_location(backend_id: str, request: Request) -> Dict[str, Any]:
    """Add a custom location to a backend."""
    try:
        data = await request.json()
        location = data.get("location")
        if not location:
            raise HTTPException(status_code=400, detail="location is required")

        success = backend_manager.add_location(backend_id, location)
        if success:
            return {
                "status": "success",
                "message": f"Location '{location}' added successfully"
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to add location or already exists"
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding location: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/backends/{backend_id}/validate-mappings", tags=["Backends"])
async def validate_mappings(backend_id: str) -> Dict[str, Any]:
    """Validate device mappings for conflicts."""
    try:
        conflicts = backend_manager.validate_device_mappings(backend_id)
        return {
            "status": "success" if not conflicts else "error",
            "valid": len(conflicts) == 0,
            "conflicts": conflicts
        }
    except Exception as e:
        logger.error(f"Error validating mappings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/backends/{backend_id}/mappings", tags=["Backends"])
async def get_backend_mappings(backend_id: str, enabled: bool = None) -> Dict[str, Any]:
    """Get device mappings with validation status."""
    try:
        devices = backend_manager.get_device_mappings(backend_id, filter_enabled=enabled)
        conflicts = backend_manager.validate_device_mappings(backend_id)
        backend = backend_manager.get_backend(backend_id)

        return {
            "status": "success",
            "devices": devices,
            "device_types": backend.get("device_types", []) if backend else [],
            "locations": backend.get("locations", []) if backend else [],
            "validation": {
                "valid": len(conflicts) == 0,
                "conflicts": conflicts
            }
        }
    except Exception as e:
        logger.error(f"Error getting mappings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Set up templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Global client instance
client = None

# Global Home Assistant components
ha_client = None
ha_mapping_config = None
ha_grammar_manager = None
ha_grammar_scheduler = None

# Store for last command
last_command_storage = {
    "command": "",
    "topic": "",
    "timestamp": None,
    "generated_json": None,
    "ha_request": None,
    "ha_response": None,
    "error": None,
    "success": False
}

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

async def get_ha_grammar_scheduler() -> 'GrammarScheduler':
    """Get or create the Home Assistant grammar scheduler instance."""
    global ha_grammar_scheduler
    if ha_grammar_scheduler is None:
        logger.info("Initializing Home Assistant grammar scheduler")
        client = await get_ha_client()
        mapping_config = await get_ha_mapping_config()
        ha_grammar_manager = await get_ha_grammar_manager()
        from .homeassistant.grammar_scheduler import GrammarScheduler
        ha_grammar_scheduler = GrammarScheduler(ha_grammar_manager, mapping_config, client)
    return ha_grammar_scheduler

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

@app.get("/api/last-command", tags=["System"])
async def get_last_command() -> Dict[str, Any]:
    """Get the last command that was processed."""
    global last_command_storage
    return {
        "command": last_command_storage.get("command", ""),
        "topic": last_command_storage.get("topic", ""),
        "timestamp": last_command_storage.get("timestamp").isoformat() if last_command_storage.get("timestamp") else None,
        "generated_json": last_command_storage.get("generated_json"),
        "ha_request": last_command_storage.get("ha_request"),
        "ha_response": last_command_storage.get("ha_response"),
        "error": last_command_storage.get("error"),
        "success": last_command_storage.get("success", False)
    }

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

@app.post("/v1/generate/{topic}", response_model=GenerationResponse, tags=["Generation"])
async def generate_text_with_topic(topic: str, request: GenerationRequest) -> GenerationResponse:
    """Generate text using a specific topic configuration."""
    return await _generate_text_impl(request, topic)

@app.post("/v1/generate", response_model=GenerationResponse, tags=["Generation"])
async def generate_text(request: GenerationRequest) -> GenerationResponse:
    """Generate text from a model (defaults to 'general' topic for backward compatibility)."""
    return await _generate_text_impl(request, "general")

async def _generate_text_impl(request: GenerationRequest, topic_id: str = "general") -> GenerationResponse:
    """Internal implementation of text generation with topic support."""
    try:
        # Store the last command
        global last_command_storage
        last_command_storage["command"] = request.prompt
        last_command_storage["topic"] = topic_id
        last_command_storage["timestamp"] = datetime.now()
        
        # Get or auto-discover topic
        topic = topic_manager.get_topic(topic_id)
        if not topic:
            # Auto-discover new topic
            logger.info(f"Auto-discovering new topic: {topic_id}")
            topic = topic_manager.auto_discover_topic(topic_id)
        
        # Check if topic is enabled
        if not topic.enabled:
            raise HTTPException(
                status_code=403,
                detail=f"Topic '{topic_id}' is disabled"
            )
        
        # Mark topic as used
        topic_manager.mark_topic_used(topic_id)
        
        # Get the model from topic or request
        model_to_use = request.model or topic.model
        
        if not model_to_use:
            raise HTTPException(
                status_code=400,
                detail="No model configured for topic and none specified in request"
            )
        
        # Load model configs to get default settings for the model
        model_configs = load_model_configs()
        model_config = model_configs.get("models", {}).get(model_to_use, {})
        
        # Use request settings, then topic settings, then model defaults
        temperature = request.temperature if request.temperature is not None else topic.settings.temperature
        top_p = request.top_p if request.top_p is not None else topic.settings.top_p
        top_k = request.top_k if request.top_k is not None else topic.settings.top_k
        max_tokens = request.max_tokens if request.max_tokens is not None else topic.settings.max_tokens
        json_mode = request.json_mode if request.json_mode is not None else topic.settings.force_json
        
        # Load model configs to get the prompt format
        model_configs = load_model_configs()
        model_config = model_configs.get("models", {}).get(model_to_use, {})
        
        # Check if this is a Home Assistant command (simple heuristic)
        ha_keywords = ["turn on", "turn off", "light", "switch", "thermostat", "bedroom", "kitchen"]
        is_ha_command = any(keyword in request.prompt.lower() for keyword in ha_keywords)
        
        # Use grammar from topic or request
        grammar_file = request.grammar_file  # Use grammar_file from request first
        
        # If no grammar in request, check topic configuration
        if not grammar_file and topic.grammar.enabled and topic.grammar.file:
            grammar_path = os.path.join(os.path.dirname(__file__), "..", "data", "grammars", topic.grammar.file)
            if os.path.exists(grammar_path):
                grammar_file = grammar_path
                logger.info(f"Using grammar from topic configuration: {topic.grammar.file}")
        if grammar_file and not os.path.exists(grammar_file):
            logger.warning(f"Grammar file not found: {grammar_file}, falling back to JSON grammar")
            grammar_file = None
        elif not grammar_file and is_ha_command and request.json_mode:
            # Use default.gbnf as default for Home Assistant commands (static grammar, not HA-generated)
            grammar_file = os.path.join(os.path.dirname(__file__), "..", "data", "grammars", "default.gbnf")
            if os.path.exists(grammar_file):
                logger.info(f"Using default.gbnf grammar for HA command (static, not HA-generated): {grammar_file}")
            else:
                logger.warning(f"default.gbnf not found at {grammar_file}, falling back to set_temp.gbnf")
                fallback_grammar = os.path.join(os.path.dirname(__file__), "..", "data", "grammars", "set_temp.gbnf")
                if os.path.exists(fallback_grammar):
                    grammar_file = fallback_grammar
                    logger.info(f"Using fallback grammar: {fallback_grammar}")
                else:
                    logger.warning(f"Fallback grammar not found, using JSON grammar")
                    grammar_file = None
        
        # Format the prompt based on whether we're using a grammar file
        if grammar_file and os.path.exists(grammar_file):
            # Use the same prompt format as the CLI test for grammar files
            # But respect user-provided system prompt if available, otherwise use model's default
            if request.system_prompt:
                system_prompt = request.system_prompt
            else:
                # Use the model's configured system prompt for grammar-based requests
                system_prompt = model_config.get("system_prompt", "You are a JSON-only formatter. For each user input, accurately interpret the intended command and respond with a single-line JSON object containing the keys: \"device\", \"action\", and \"location\". Match the \"device\" to the user-specified device (e.g., \"heating\" for heating, \"blinds\" for blinds) and select the \"action\" most appropriate for that device (e.g., \"on\", \"off\" for heating; \"open\", \"close\" for blinds) based on the provided grammar. Use \"UNKNOWN\" for unrecognized inputs. Output only the JSON object without explanations or additional text.")
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
                # Use provided system prompt, then topic's, then model's default
                system_prompt = request.system_prompt or topic.settings.system_prompt or model_config.get("system_prompt", "")
            
            # Add /no_think prefix if configured in topic
            if topic.settings.no_think and not system_prompt.startswith("/no_think"):
                system_prompt = "/no_think\n\n" + system_prompt
            
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
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_tokens=max_tokens,
            timeout=30,  # Set a 30-second timeout for the API endpoint
            json_mode=json_mode,
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
        
        # Check if topic has a configured dispatcher
        dispatcher_result = None
        if topic.dispatcher:
            try:
                # Get the dispatcher from the registry
                dispatcher = dispatcher_registry.create(topic.dispatcher)
                if dispatcher:
                    logger.info(f"Using dispatcher '{topic.dispatcher}' for topic '{topic_id}'")
                    
                    # Execute through dispatcher
                    dispatcher_result = dispatcher.execute(response_text, {'topic': topic.dict()})
                    
                    # Store dispatcher execution details
                    last_command_storage["dispatcher"] = topic.dispatcher
                    last_command_storage["dispatcher_result"] = dispatcher_result
                    last_command_storage["success"] = dispatcher_result.get("success", False)
                    
                    if dispatcher_result.get("error"):
                        logger.error(f"Dispatcher execution failed: {dispatcher_result['error']}")
                    else:
                        logger.info(f"Dispatcher execution successful")
                else:
                    logger.warning(f"Dispatcher '{topic.dispatcher}' not found in registry")
            except Exception as e:
                logger.error(f"Failed to execute through dispatcher: {e}")
                last_command_storage["error"] = str(e)
                last_command_storage["success"] = False
        
        # Legacy: If this is a home_assistant topic and no dispatcher, use old HA executor
        ha_result = None
        if topic_id == "home_assistant" and response_text and not topic.dispatcher:
            try:
                import json
                parsed_json = json.loads(response_text)
                last_command_storage["generated_json"] = parsed_json
                
                # Execute the command via HA executor
                logger.info(f"Executing HA command (legacy): {parsed_json}")
                ha_result = await ha_executor.execute_json_command(parsed_json)
                
                # Store HA execution details
                last_command_storage["ha_request"] = ha_result.get("ha_request")
                last_command_storage["ha_response"] = ha_result.get("ha_response")
                last_command_storage["error"] = ha_result.get("error")
                last_command_storage["success"] = ha_result.get("success", False)
                
                if ha_result.get("error"):
                    logger.error(f"HA execution failed: {ha_result['error']}")
                else:
                    logger.info(f"HA execution successful")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse generated JSON: {e}")
                last_command_storage["error"] = f"Invalid JSON: {str(e)}"
                last_command_storage["success"] = False
            except Exception as e:
                logger.error(f"Failed to execute HA command: {e}")
                last_command_storage["error"] = str(e)
                last_command_storage["success"] = False
        
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
        summary = mapping_config.get_entity_mapping_summary()
        
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
    """Get current grammar rules.
    
    Note: This returns the HA-generated grammar for reference. For production use,
    the system uses the static default.gbnf grammar file, not this dynamic one.
    """
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
async def update_grammar(force: bool = False) -> Dict[str, Any]:
    """Update grammar rules with latest Home Assistant data and validation."""
    try:
        # Get the grammar scheduler
        scheduler = await get_ha_grammar_scheduler()
        
        # Run update with validation
        result = await scheduler.update_grammar_with_validation(force_update=force)
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        return result
    except Exception as e:
        logger.error(f"Error updating grammar: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/homeassistant/grammar/scheduler/status", tags=["Home Assistant"])
async def get_grammar_scheduler_status() -> Dict[str, Any]:
    """Get grammar scheduler status."""
    try:
        scheduler = await get_ha_grammar_scheduler()
        return {
            "status": "success",
            "scheduler_status": scheduler.get_status()
        }
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/homeassistant/grammar/scheduler/start", tags=["Home Assistant"])
async def start_grammar_scheduler() -> Dict[str, Any]:
    """Start the grammar scheduler."""
    try:
        scheduler = await get_ha_grammar_scheduler()
        await scheduler.start_scheduler()
        
        return {
            "status": "success",
            "message": "Grammar scheduler started",
            "scheduler_status": scheduler.get_status()
        }
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/homeassistant/grammar/scheduler/stop", tags=["Home Assistant"])
async def stop_grammar_scheduler() -> Dict[str, Any]:
    """Stop the grammar scheduler."""
    try:
        scheduler = await get_ha_grammar_scheduler()
        await scheduler.stop_scheduler()
        
        return {
            "status": "success",
            "message": "Grammar scheduler stopped",
            "scheduler_status": scheduler.get_status()
        }
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
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
                
                # Start with default.gbnf grammar for Home Assistant commands (using static default, not HA-generated)
                grammar_file = os.path.join(os.path.dirname(__file__), "..", "data", "grammars", "default.gbnf")
                if os.path.exists(grammar_file):
                    logger.info(f"Starting default model with default.gbnf grammar (static, not HA-generated): {grammar_file}")
                    await client._ensure_server_running(
                        model=favorites["default_model"],
                        temperature=0.1,  # Use 0.1 for grammar-constrained generation
                        top_p=0.9,
                        top_k=10,
                        json_mode=True,
                        grammar_file=grammar_file
                    )
                else:
                    logger.warning(f"default.gbnf not found at {grammar_file}, falling back to set_temp.gbnf")
                    fallback_grammar = os.path.join(os.path.dirname(__file__), "..", "data", "grammars", "set_temp.gbnf")
                    if os.path.exists(fallback_grammar):
                        logger.info(f"Using fallback grammar: {fallback_grammar}")
                        await client._ensure_server_running(
                            model=favorites["default_model"],
                            temperature=0.1,
                            top_p=0.9,
                            top_k=10,
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
        
        # Start the grammar scheduler for daily updates
        try:
            scheduler = await get_ha_grammar_scheduler()
            await scheduler.start_scheduler()
            logger.info("Grammar scheduler started successfully")
        except Exception as e:
            logger.error(f"Failed to start grammar scheduler: {e}")
            # Don't fail startup if scheduler fails
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    global client, ha_client, ha_grammar_scheduler
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
    
    # Stop grammar scheduler
    if ha_grammar_scheduler:
        try:
            await ha_grammar_scheduler.stop_scheduler()
            logger.info("Grammar scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping grammar scheduler: {e}")

# Web interface routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main web interface."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "ORAC - Omniscient Reactive Algorithmic Core"}
    )

@app.get("/topics", response_class=HTMLResponse)
async def topics_page(request: Request):
    """Serve the topics management interface."""
    return templates.TemplateResponse(
        "topics.html",
        {"request": request, "title": "ORAC - Topics Management"}
    )

@app.get("/topics/{topic_id}", response_class=HTMLResponse)
async def topic_config_page(request: Request, topic_id: str):
    """Serve the topic configuration interface."""
    return templates.TemplateResponse(
        "topic_config.html",
        {"request": request, "topic_id": topic_id, "title": f"Topic Config - {topic_id}"}
    )

@app.get("/backends", response_class=HTMLResponse)
async def backends_page(request: Request):
    """Serve the backends management interface."""
    return templates.TemplateResponse(
        "backends.html",
        {"request": request, "title": "ORAC - Backends Management"}
    )

@app.get("/backends/{backend_id}/entities", response_class=HTMLResponse)
async def backend_entities_page(request: Request, backend_id: str):
    """Serve the backend entities configuration interface."""
    backend = backend_manager.get_backend(backend_id)
    if not backend:
        raise HTTPException(status_code=404, detail=f"Backend {backend_id} not found")
    return templates.TemplateResponse(
        "backend_entities.html",
        {"request": request, "backend_id": backend_id, "backend_name": backend.get("name", backend_id), "title": f"Configure Entities - {backend.get('name', backend_id)}"}
    )

@app.get("/model-config", response_class=HTMLResponse)
async def model_config(request: Request):
    """Serve the model configuration interface."""
    return templates.TemplateResponse(
        "model_config.html",
        {"request": request, "title": "ORAC - Model Configuration"}
    ) 