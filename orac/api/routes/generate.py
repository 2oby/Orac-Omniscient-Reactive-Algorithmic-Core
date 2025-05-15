import time
from fastapi import APIRouter, HTTPException
from orac.api.models.schemas import GenerationRequest, GenerationResponse
from orac.llama_cpp_client import LlamaCppClient
from orac.logger import get_logger
from orac.model_config import get_model_config
from orac.models.model_type import ModelType

router = APIRouter(tags=["generation"])
logger = get_logger(__name__)

# Initialize the llama.cpp client
client = LlamaCppClient()

@router.post(
    "/generate",
    response_model=GenerationResponse,
    operation_id="generate_text",
    summary="Generate text using the specified model",
    description="Generate text using the specified model and parameters. Returns the generated text along with generation metadata."
)
async def generate_text(request: GenerationRequest) -> GenerationResponse:
    """Generate text using the specified model and parameters."""
    try:
        start_time = time.time()
        
        # Validate model exists by checking available models
        models = await client.list_models()
        model_names = [m["name"] for m in models]
        if request.model not in model_names:
            raise HTTPException(
                status_code=404,
                detail=f"Model {request.model} not found. Available models: {model_names}"
            )
        
        # Get model config to check if it's a chat model and get system prompt
        model_config = get_model_config(request.model)
        if model_config and model_config.type == ModelType.CHAT:
            # Use provided system prompt or fall back to model config
            system_prompt = request.system_prompt or model_config.system_prompt
            if system_prompt:
                # Format prompt with system prompt for chat models
                prompt = f"System: {system_prompt}\n\nUser: {request.prompt}\n\nAssistant:"
            else:
                prompt = request.prompt
        else:
            prompt = request.prompt
        
        # Generate text
        try:
            response = await client.generate(
                model=request.model,
                prompt=prompt,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                top_p=request.top_p,
                top_k=request.top_k
            )
            
            # The generate method returns a PromptResponse object
            return GenerationResponse(
                generated_text=response.response,
                model=request.model,
                prompt=request.prompt,  # Return original prompt without system prompt
                parameters={
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens,
                    "top_p": request.top_p,
                    "top_k": request.top_k,
                    "system_prompt": system_prompt if model_config and model_config.type == ModelType.CHAT else None
                },
                elapsed_ms=response.elapsed_ms
            )
                
        except Exception as e:
            logger.error(f"Model generation failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Model generation failed: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during text generation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error during text generation: {str(e)}"
        ) 