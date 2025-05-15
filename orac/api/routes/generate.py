"""
orac.api.routes.generate
-----------------------
API routes for text generation.
"""

import time
from fastapi import APIRouter, HTTPException
from orac.api.models.schemas import GenerationRequest, GenerationResponse
from orac.llama_cpp_client import LlamaCppClient
from orac.model_config import get_model_config
from orac.prompt_manager import prompt_manager
from orac.logger import get_logger
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
    """Generate text using the specified model."""
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
        
        # Get model config
        model_config = get_model_config(request.model)
        
        # Get appropriate system prompt using prompt manager
        prompt_state = prompt_manager.get_system_prompt(
            model_name=request.model,
            user_prompt=request.system_prompt,
            model_config=model_config
        )
        
        # Format the final prompt
        if model_config and model_config.type == ModelType.CHAT:
            prompt = prompt_manager.format_prompt(
                system_prompt=prompt_state.prompt,
                user_prompt=request.prompt,
                model_name=request.model
            )
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
            
            # Log prompt state for debugging
            logger.debug(f"Prompt state: {prompt_state.dict()}")
            
            # Return response with prompt metadata
            return GenerationResponse(
                generated_text=response.response,
                model=request.model,
                prompt=request.prompt,  # Return original prompt without system prompt
                parameters={
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens,
                    "top_p": request.top_p,
                    "top_k": request.top_k,
                    "system_prompt": {
                        "text": prompt_state.prompt,
                        "source": prompt_state.source,
                        "metadata": prompt_state.metadata
                    } if model_config and model_config.type == ModelType.CHAT else None
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