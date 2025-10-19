"""
orac.api.routes.backends
------------------------
Backend management endpoints.

Handles CRUD operations for backends, entities, device types, locations,
mappings validation, and grammar generation.
"""

from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any

from orac.logger import get_logger
from orac.api.dependencies import get_backend_manager, get_backend_grammar_generator

logger = get_logger(__name__)

router = APIRouter(tags=["Backends"])


# Backend CRUD Operations

@router.post("/api/backends")
async def create_backend(request: Request) -> Dict[str, Any]:
    """Create a new backend configuration."""
    try:
        data = await request.json()
        backend_manager = get_backend_manager()
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


@router.get("/api/backends")
async def list_backends() -> Dict[str, Any]:
    """List all configured backends."""
    try:
        backend_manager = get_backend_manager()
        backends = backend_manager.list_backends()
        return {
            "status": "success",
            "backends": backends
        }
    except Exception as e:
        logger.error(f"Error listing backends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/backends/{backend_id}")
async def get_backend(backend_id: str) -> Dict[str, Any]:
    """Get a specific backend configuration."""
    try:
        backend_manager = get_backend_manager()
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


@router.put("/api/backends/{backend_id}")
async def update_backend(backend_id: str, request: Request) -> Dict[str, Any]:
    """Update a backend configuration."""
    try:
        data = await request.json()
        backend_manager = get_backend_manager()
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


@router.delete("/api/backends/{backend_id}")
async def delete_backend(backend_id: str) -> Dict[str, Any]:
    """Delete a backend configuration."""
    try:
        backend_manager = get_backend_manager()
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


@router.post("/api/backends/{backend_id}/test")
async def test_backend_connection(backend_id: str) -> Dict[str, Any]:
    """Test a backend connection."""
    try:
        backend_manager = get_backend_manager()
        result = await backend_manager.test_connection(backend_id)
        return {
            "status": "success" if result.get("success") else "error",
            "result": result
        }
    except Exception as e:
        logger.error(f"Error testing backend connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Entity Management

@router.post("/api/backends/{backend_id}/entities/fetch")
async def fetch_backend_entities(backend_id: str) -> Dict[str, Any]:
    """Fetch entities from a backend."""
    try:
        backend_manager = get_backend_manager()
        result = await backend_manager.fetch_entities(backend_id)
        return {
            "status": "success" if result.get("success") else "error",
            "result": result
        }
    except Exception as e:
        logger.error(f"Error fetching entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/backends/{backend_id}/entities")
async def get_backend_entities(backend_id: str, enabled: bool = None) -> Dict[str, Any]:
    """Get configured entities for a backend."""
    try:
        backend_manager = get_backend_manager()
        entities = backend_manager.get_entities(backend_id, filter_enabled=enabled)
        return {
            "status": "success",
            "entities": entities
        }
    except Exception as e:
        logger.error(f"Error getting entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/backends/{backend_id}/entities/{entity_id}")
async def update_backend_entity(backend_id: str, entity_id: str, request: Request) -> Dict[str, Any]:
    """Update an entity configuration."""
    try:
        data = await request.json()
        backend_manager = get_backend_manager()
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


@router.post("/api/backends/{backend_id}/entities/bulk")
async def bulk_update_entities(backend_id: str, request: Request) -> Dict[str, Any]:
    """Bulk update entity configurations."""
    try:
        data = await request.json()
        entity_ids = data.get("entity_ids", [])
        updates = data.get("updates", {})
        backend_manager = get_backend_manager()
        result = backend_manager.bulk_update_entities(backend_id, entity_ids, updates)
        return {
            "status": "success" if result.get("success") else "error",
            "result": result
        }
    except Exception as e:
        logger.error(f"Error in bulk update: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Configuration Management

@router.post("/api/backends/{backend_id}/save")
async def save_backend_configuration(backend_id: str) -> Dict[str, Any]:
    """Save the current backend configuration to disk."""
    try:
        backend_manager = get_backend_manager()
        if backend_manager.save_backend(backend_id):
            return {
                "status": "success",
                "message": "Configuration saved successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save configuration")
    except Exception as e:
        logger.error(f"Error saving backend configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/backends/{backend_id}/device-types")
async def add_device_type(backend_id: str, request: Request) -> Dict[str, Any]:
    """Add a custom device type to a backend."""
    try:
        data = await request.json()
        device_type = data.get("device_type")
        if not device_type:
            raise HTTPException(status_code=400, detail="device_type is required")

        backend_manager = get_backend_manager()
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


@router.post("/api/backends/{backend_id}/locations")
async def add_location(backend_id: str, request: Request) -> Dict[str, Any]:
    """Add a custom location to a backend."""
    try:
        data = await request.json()
        location = data.get("location")
        if not location:
            raise HTTPException(status_code=400, detail="location is required")

        backend_manager = get_backend_manager()
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


# Mapping Validation

@router.post("/api/backends/{backend_id}/validate-mappings")
async def validate_mappings(backend_id: str) -> Dict[str, Any]:
    """Validate device mappings for conflicts."""
    try:
        backend_manager = get_backend_manager()
        conflicts = backend_manager.validate_device_mappings(backend_id)
        return {
            "status": "success" if not conflicts else "error",
            "valid": len(conflicts) == 0,
            "conflicts": conflicts
        }
    except Exception as e:
        logger.error(f"Error validating mappings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/backends/{backend_id}/mappings")
async def get_backend_mappings(backend_id: str, enabled: bool = None) -> Dict[str, Any]:
    """Get device mappings with validation status."""
    try:
        backend_manager = get_backend_manager()
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


# Grammar Generation

@router.post("/api/backends/{backend_id}/grammar/generate")
async def generate_backend_grammar(backend_id: str) -> Dict[str, Any]:
    """Generate GBNF grammar from backend device mappings."""
    try:
        backend_grammar_generator = get_backend_grammar_generator()
        result = backend_grammar_generator.generate_and_save_grammar(backend_id)
        return {
            "status": "success" if result.get("success") else "error",
            "result": result
        }
    except Exception as e:
        logger.error(f"Error generating grammar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/backends/{backend_id}/grammar")
async def get_backend_grammar(backend_id: str) -> Dict[str, Any]:
    """Get generated grammar file content."""
    try:
        backend_grammar_generator = get_backend_grammar_generator()
        grammar_file = backend_grammar_generator.get_grammar_file_path(backend_id)
        if not grammar_file.exists():
            raise HTTPException(status_code=404, detail="Grammar file not found. Generate grammar first.")

        with open(grammar_file, 'r') as f:
            grammar_content = f.read()

        return {
            "status": "success",
            "grammar_file": str(grammar_file),
            "grammar_content": grammar_content
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting grammar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/backends/{backend_id}/grammar/test")
async def test_grammar_command(backend_id: str, request: Request) -> Dict[str, Any]:
    """Test a command against backend's generated grammar."""
    try:
        data = await request.json()
        command = data.get("command")
        if not command:
            raise HTTPException(status_code=400, detail="command is required")

        backend_grammar_generator = get_backend_grammar_generator()
        result = backend_grammar_generator.test_command_against_grammar(backend_id, command)
        return {
            "status": "success" if result.get("valid") else "error",
            "result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing grammar command: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/backends/{backend_id}/grammar/status")
async def get_backend_grammar_status(backend_id: str) -> Dict[str, Any]:
    """Get grammar generation status for a backend."""
    try:
        backend_grammar_generator = get_backend_grammar_generator()
        status = backend_grammar_generator.get_grammar_status(backend_id)
        return {
            "status": "success",
            "grammar_status": status
        }
    except Exception as e:
        logger.error(f"Error getting grammar status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
