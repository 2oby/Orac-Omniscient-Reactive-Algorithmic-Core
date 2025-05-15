"""
orac.api.routes.generate
-----------------------
API routes for text generation.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from orac.models import get_available_models, get_model_config
from orac.client import client
from orac.prompt_manager import prompt_manager
from orac.logger import get_logger
import time

logger = get_logger(__name__)
router = APIRouter()

class GenerateRequest(BaseModel):
    """Request model for text generation."""
    prompt: str = Field(..., min_length=1, max_length=4096)
    model: str
    system_prompt: Optional[str] = Field(None, max_length=4096)
    max_tokens: Optional[int] = Field(512, ge=1, le=4096)
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(0.9, ge=0.0, le=1.0)
    stop: Optional[List[str]] = Field(None, max_items=10)

    @validator('prompt')
    def validate_prompt(cls, v: str) -> str:
        """Validate prompt format."""
        if not v.strip():
            raise ValueError("Prompt cannot be empty")
        return v.strip()

    @validator('system_prompt')
    def validate_system_prompt(cls, v: Optional[str]) -> Optional[str]:
        """Validate system prompt format."""
        if v is not None and not v.strip():
            raise ValueError("System prompt cannot be empty")
        return v.strip() if v is not None else None

class GenerateResponse(BaseModel):
    """Response model for text generation."""
    text: str
    model: str
    prompt_state: Dict[str, Any]
    generation_params: Dict[str, Any]
    timing: Dict[str, float]

@router.post("/generate", response_model=GenerateResponse)
async def generate_text(request: GenerateRequest) -> GenerateResponse:
    """Generate text using the specified model."""
    start_time = time.time()
    
    try:
        # Validate model
        available_models = get_available_models()
        if not available_models:
            raise HTTPException(
                status_code=503,
                detail="No models available. Please check model directory configuration."
            )
        
        if request.model not in available_models:
            raise HTTPException(
                status_code=400,
                detail=f"Model {request.model} not available. Available models: {', '.join(available_models)}"
            )
        
        # Get model config
        try:
            model_config = get_model_config(request.model)
        except Exception as e:
            logger.error(f"Failed to get model config for {request.model}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to load model configuration: {str(e)}"
            )
        
        # Get system prompt using prompt manager
        try:
            prompt_state = await prompt_manager.get_system_prompt(
                model_name=request.model,
                user_prompt=request.system_prompt,
                model_config=model_config
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Failed to get system prompt: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to process system prompt"
            )
        
        # Format final prompt
        try:
            final_prompt = prompt_manager.format_prompt(
                system_prompt=prompt_state.prompt,
                user_prompt=request.prompt,
                model_name=request.model
            )
        except Exception as e:
            logger.error(f"Failed to format prompt: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to format prompt"
            )
        
        # Log prompt state
        logger.info(f"Using system prompt from source: {prompt_state.source}")
        logger.debug(f"Final prompt: {final_prompt}")
        
        # Generate text
        try:
            generation_start = time.time()
            response = await client.generate(
                prompt=final_prompt,
                model=request.model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                stop=request.stop
            )
            generation_time = time.time() - generation_start
            
            # Log generation
            logger.info(f"Generated {len(response)} tokens in {generation_time:.2f}s")
            
            return GenerateResponse(
                text=response,
                model=request.model,
                prompt_state={
                    "source": prompt_state.source,
                    "model_name": prompt_state.model_name,
                    "metadata": prompt_state.metadata
                },
                generation_params={
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "top_p": request.top_p,
                    "stop": request.stop
                },
                timing={
                    "generation_time": generation_time,
                    "total_time": time.time() - start_time
                }
            )
            
        except Exception as e:
            logger.error(f"Generation failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Text generation failed: {str(e)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred"
        ) 