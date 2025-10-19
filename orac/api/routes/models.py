"""
orac.api.routes.models
----------------------
Model management endpoints.
"""

from fastapi import APIRouter, HTTPException

from orac.logger import get_logger
from orac.models import (
    ModelInfo, ModelListResponse, ModelLoadRequest, ModelLoadResponse,
    ModelUnloadResponse
)
from orac.api.dependencies import get_client

logger = get_logger(__name__)

router = APIRouter(tags=["Models"])


@router.get("/v1/models", response_model=ModelListResponse)
async def list_models() -> ModelListResponse:
    """List available models."""
    try:
        client = await get_client()
        models = await client.list_models()
        return ModelListResponse(models=[ModelInfo(**model) for model in models])
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/models/load", response_model=ModelLoadResponse)
async def load_model(request: ModelLoadRequest) -> ModelLoadResponse:
    """Load a model."""
    try:
        client = await get_client()
        result = await client.load_model(request.name)
        return ModelLoadResponse(**result)
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/models/unload", response_model=ModelUnloadResponse)
async def unload_model(model_name: str) -> ModelUnloadResponse:
    """Unload a model."""
    try:
        client = await get_client()
        result = await client.unload_model(model_name)
        return ModelUnloadResponse(**result)
    except Exception as e:
        logger.error(f"Error unloading model: {e}")
        raise HTTPException(status_code=500, detail=str(e))
