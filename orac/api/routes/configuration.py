"""
orac.api.routes.configuration
-----------------------------
Configuration management endpoints for favorites and model configs.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from orac.logger import get_logger
from orac.config import load_favorites, save_favorites, load_model_configs, save_model_configs

logger = get_logger(__name__)

router = APIRouter(tags=["Configuration"])


@router.get("/v1/config/favorites")
async def get_favorites() -> Dict[str, Any]:
    """Get favorites configuration."""
    try:
        return load_favorites()
    except Exception as e:
        logger.error(f"Error getting favorites: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/config/favorites")
async def update_favorites(config: Dict[str, Any]) -> Dict[str, Any]:
    """Update favorites configuration."""
    try:
        save_favorites(config)
        return {"status": "success", "message": "Favorites updated successfully"}
    except Exception as e:
        logger.error(f"Error updating favorites: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/config/models")
async def get_model_configs() -> Dict[str, Any]:
    """Get model configurations."""
    try:
        return load_model_configs()
    except Exception as e:
        logger.error(f"Error getting model configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/config/models")
async def update_model_configs(config: Dict[str, Any]) -> Dict[str, Any]:
    """Update model configurations."""
    try:
        save_model_configs(config)
        return {"status": "success", "message": "Model configurations updated successfully"}
    except Exception as e:
        logger.error(f"Error updating model configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
