"""
orac.api.routes.system
----------------------
System status and health endpoints.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime

from orac.logger import get_logger
from orac.config import APIConfig
from orac.api.dependencies import get_client, get_last_command_storage

logger = get_logger(__name__)

router = APIRouter(tags=["System"])


@router.get("/v1/status")
async def get_status() -> Dict[str, Any]:
    """Get system status."""
    try:
        client = await get_client()
        models = await client.list_models()
        return {
            "status": "ok",
            "models_available": len(models),
            "version": APIConfig.VERSION
        }
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/last-command")
async def get_last_command() -> Dict[str, Any]:
    """Get the last command that was processed."""
    storage = get_last_command_storage()
    return {
        "command": storage.get("command", ""),
        "topic": storage.get("topic", ""),
        "timestamp": storage.get("timestamp").isoformat() if storage.get("timestamp") else None,
        "generated_json": storage.get("generated_json"),
        "ha_request": storage.get("ha_request"),
        "ha_response": storage.get("ha_response"),
        "error": storage.get("error"),
        "success": storage.get("success", False)
    }
