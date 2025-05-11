from fastapi import APIRouter, HTTPException
from orac.models import ModelListResponse, ModelInfo
from orac.llama_cpp_client import LlamaCppClient
from orac.logger import get_logger

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
        return {"models": [ModelInfo(**m) for m in models]}
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 