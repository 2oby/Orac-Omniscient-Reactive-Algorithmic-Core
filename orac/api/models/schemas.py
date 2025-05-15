from pydantic import BaseModel, Field
from typing import Optional, List

class GenerationRequest(BaseModel):
    """Request model for text generation."""
    prompt: str = Field(..., description="The input prompt for generation")
    model: str = Field("Qwen3-0.6B-Q4_K_M.gguf", description="Model to use for generation")
    system_prompt: Optional[str] = Field(None, description="System prompt to use for chat models")
    temperature: float = Field(0.7, ge=0.0, le=1.0, description="Sampling temperature")
    max_tokens: int = Field(512, ge=1, le=2048, description="Maximum number of tokens to generate")
    top_p: float = Field(0.7, ge=0.0, le=1.0, description="Top-p sampling parameter")
    top_k: int = Field(40, ge=1, description="Top-k sampling parameter")

class GenerationResponse(BaseModel):
    """Response model for text generation."""
    generated_text: str = Field(..., description="The generated text")
    model: str = Field(..., description="Model used for generation")
    prompt: str = Field(..., description="The input prompt")
    parameters: dict = Field(..., description="Generation parameters used")
    elapsed_ms: float = Field(..., description="Time taken for generation in milliseconds") 