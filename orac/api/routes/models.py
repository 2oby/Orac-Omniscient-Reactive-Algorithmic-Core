from fastapi import APIRouter, HTTPException
from orac.models import (
    ModelListResponse, ModelInfo, ModelConfig, ModelConfigs,
    ModelSettings, ModelType, ModelCapability
)
from orac.llama_cpp_client import LlamaCppClient
from orac.logger import get_logger
from orac.favorites import add_favorite, remove_favorite, is_favorite
from orac.model_config import (
    get_model_config, update_model_config, delete_model_config,
    get_default_settings, update_default_settings, load_configs, create_or_update_model_config
)
from typing import Set

router = APIRouter(tags=["models"])
logger = get_logger(__name__)

# Initialize the llama.cpp client
client = LlamaCppClient()

def normalize_model_name(model_name: str) -> str:
    """Remove .gguf extension from model name if present."""
    return model_name.replace('.gguf', '')

@router.get(
    "/models",
    response_model=ModelListResponse,
    operation_id="list_models",
    summary="List available models",
    description="Returns a list of all available GGUF models in the models directory."
)
async def list_models() -> ModelListResponse:
    """List available models."""
    try:
        models = await client.list_models()
        # Add favorite status to each model
        models_with_favorites = [
            {**m, "is_favorite": is_favorite(m["name"])} 
            for m in models
        ]
        # Sort models: favorites first, then by name
        sorted_models = sorted(
            models_with_favorites,
            key=lambda x: (not x["is_favorite"], x["name"])
        )
        return {"models": [ModelInfo(**m) for m in sorted_models]}
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/models/{model_name}/favorite",
    operation_id="add_favorite",
    summary="Add model to favorites",
    description="Adds a model to the favorites list."
)
async def favorite_model(model_name: str):
    """Add a model to favorites."""
    try:
        if add_favorite(model_name):
            return {"status": "success", "message": f"Added {model_name} to favorites"}
        return {"status": "info", "message": f"{model_name} was already in favorites"}
    except Exception as e:
        logger.error(f"Error adding favorite: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete(
    "/models/{model_name}/favorite",
    operation_id="remove_favorite",
    summary="Remove model from favorites",
    description="Removes a model from the favorites list."
)
async def unfavorite_model(model_name: str):
    """Remove a model from favorites."""
    try:
        if remove_favorite(model_name):
            return {"status": "success", "message": f"Removed {model_name} from favorites"}
        return {"status": "info", "message": f"{model_name} was not in favorites"}
    except Exception as e:
        logger.error(f"Error removing favorite: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/models/configs",
    response_model=ModelConfigs,
    operation_id="get_model_configs",
    summary="Get all model configurations",
    description="Returns the complete model configuration including defaults and model-specific settings."
)
async def get_configs() -> ModelConfigs:
    """Get all model configurations."""
    try:
        return load_configs()
    except Exception as e:
        logger.error(f"Error getting model configs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/models/{model_name}/config",
    response_model=ModelConfig,
    operation_id="get_model_config",
    summary="Get model configuration",
    description="Returns the configuration for a specific model."
)
async def get_model_config(model_name: str):
    """Get configuration for a specific model."""
    normalized_name = normalize_model_name(model_name)
    config = get_model_config(normalized_name)
    if config is None:
        raise HTTPException(
            status_code=404,
            detail=f"No configuration found for model {model_name}. Use PUT to create one."
        )
    return config

@router.put(
    "/models/{model_name}/config",
    response_model=ModelConfig,
    operation_id="update_model_config",
    summary="Update model configuration",
    description="Updates the configuration for a specific model."
)
async def update_model_config(model_name: str, config: ModelConfig):
    """Create or update configuration for a specific model."""
    try:
        logger.info(f"Received update request for model: {model_name}")
        normalized_name = normalize_model_name(model_name)
        logger.info(f"Normalized model name: {normalized_name}")
        logger.info(f"Config data: {config.model_dump()}")
        
        result = create_or_update_model_config(normalized_name, config)
        logger.info(f"Successfully updated config for model: {normalized_name}")
        return result
    except Exception as e:
        logger.error(f"Error updating model config: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update configuration for model {model_name}: {str(e)}"
        )

@router.delete(
    "/models/{model_name}/config",
    operation_id="delete_model_config",
    summary="Delete model configuration",
    description="Deletes the configuration for a specific model."
)
async def delete_config(model_name: str):
    """Delete configuration for a specific model."""
    try:
        model_name = normalize_model_name(model_name)
        if delete_model_config(model_name):
            return {"status": "success", "message": f"Deleted configuration for {model_name}"}
        return {"status": "info", "message": f"No configuration found for {model_name}"}
    except Exception as e:
        logger.error(f"Error deleting model config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/models/configs/defaults",
    response_model=ModelSettings,
    operation_id="get_default_settings",
    summary="Get default settings",
    description="Returns the default settings for all models."
)
async def get_defaults() -> ModelSettings:
    """Get default model settings."""
    try:
        return get_default_settings()
    except Exception as e:
        logger.error(f"Error getting default settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put(
    "/models/configs/defaults",
    response_model=ModelSettings,
    operation_id="update_default_settings",
    summary="Update default settings",
    description="Updates the default settings for all models."
)
async def update_defaults(settings: ModelSettings) -> ModelSettings:
    """Update default model settings."""
    try:
        if update_default_settings(settings):
            return settings
        raise HTTPException(status_code=500, detail="Failed to update default settings")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating default settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 