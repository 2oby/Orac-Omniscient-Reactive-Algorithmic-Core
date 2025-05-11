import time
from fastapi import APIRouter, HTTPException
from orac.api.models.schemas import GenerationRequest, GenerationResponse
from orac.llama_cpp_client import LlamaCppClient
from orac.logger import get_logger

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
        
        # Validate model exists
        if not client.model_exists(request.model):
            raise HTTPException(
                status_code=404,
                detail=f"Model {request.model} not found. Available models: {client.list_models()}"
            )
        
        # Generate text
        try:
            response = client.generate(
                model=request.model,
                prompt=request.prompt,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                top_p=request.top_p,
                top_k=request.top_k
            )
            
            if not isinstance(response, str):
                raise ValueError("Model returned invalid response format")
                
        except Exception as e:
            logger.error(f"Model generation failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Model generation failed: {str(e)}"
            )
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return GenerationResponse(
            generated_text=response,
            model=request.model,
            prompt=request.prompt,
            parameters={
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "top_p": request.top_p,
                "top_k": request.top_k
            },
            elapsed_ms=elapsed_ms
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during text generation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error during text generation: {str(e)}"
        ) 