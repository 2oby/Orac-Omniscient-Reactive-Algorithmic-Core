from fastapi import APIRouter, HTTPException
from orac.models import ModelListResponse, ModelInfo
from orac.llama_cpp_client import LlamaCppClient
from orac.logger import get_logger
from orac.favorites import add_favorite, remove_favorite, is_favorite

router = APIRouter(tags=["models"])
logger = get_logger(__name__)

# Initialize the llama.cpp client
client = LlamaCppClient()

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