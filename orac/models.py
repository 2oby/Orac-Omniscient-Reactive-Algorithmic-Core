"""
orac.models
-----------
Pydantic models for the Ollama client API that define the data structures for:
- Model information and metadata
- API request/response payloads
- Model loading and unloading operations
- Prompt requests and responses

These models ensure type safety and validation for all interactions with the Ollama API,
providing clear interfaces for model management and inference operations.
"""

# orac/models.py
from typing import List, Optional

from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    name: str
    modified: str | None = None   # ISO 8601 timestamp from Ollama
    size: int | None = None       # bytes; Ollama omits this sometimes


class ModelListResponse(BaseModel):
    models: List[ModelInfo]


class ModelLoadRequest(BaseModel):
    name: str = Field(..., description="Name of the model to load")


class ModelLoadResponse(BaseModel):
    status: str = Field(..., description="Status of the load operation")
    error: Optional[str] = Field(None, description="Error message if load failed")


class ModelUnloadResponse(BaseModel):
    status: str = Field(..., description="Status of the unload operation")
    error: Optional[str] = Field(None, description="Error message if unload failed")


class PromptRequest(BaseModel):
    model: str = Field(..., description="Name of the model to use")
    prompt: str = Field(..., description="Text prompt to send to the model")
    stream: bool = Field(False, description="Whether to stream the response")


class PromptResponse(BaseModel):
    response: str = Field(..., description="Model's response text")
    elapsed_ms: float = Field(..., description="Time taken to generate response in milliseconds")
    error: Optional[str] = Field(None, description="Error message if generation failed")
