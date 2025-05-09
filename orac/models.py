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

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    """Information about an Ollama model."""
    name: str
    modified_at: Optional[str] = Field(None, description="ISO 8601 timestamp")
    size: Optional[int] = Field(None, description="Size in bytes")
    digest: Optional[str] = Field(None, description="Model digest")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional model details")


class ModelListResponse(BaseModel):
    """Response containing a list of models."""
    models: List[ModelInfo] = Field(..., description="List of available models")


class ModelLoadRequest(BaseModel):
    """Request to load a model."""
    name: str = Field(..., description="Name of the model to load")
    path: Optional[str] = Field(None, description="Path to model file (for local models)")


class ModelLoadResponse(BaseModel):
    """Response from a model load operation."""
    status: str = Field(..., description="Status of the load operation")
    message: Optional[str] = Field(None, description="Additional information")
    error: Optional[str] = Field(None, description="Error message if load failed")
    elapsed_seconds: Optional[float] = Field(None, description="Time taken to load in seconds")


class ModelUnloadResponse(BaseModel):
    """Response from a model unload operation."""
    status: str = Field(..., description="Status of the unload operation")
    message: Optional[str] = Field(None, description="Additional information")
    error: Optional[str] = Field(None, description="Error message if unload failed")


class GenerationRequest(BaseModel):
    """Request for text generation."""
    model: str = Field(..., description="Name of the model to use")
    prompt: str = Field(..., description="Text prompt to send to the model")
    stream: bool = Field(False, description="Whether to stream the response")
    temperature: float = Field(0.7, description="Sampling temperature")
    top_p: float = Field(0.7, description="Top-p sampling parameter")
    top_k: int = Field(40, description="Top-k sampling parameter")
    stop: Optional[List[str]] = Field(None, description="Stop sequences")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens to generate")


class GenerationResponse(BaseModel):
    """Response from a text generation request."""
    status: str = Field(..., description="Status of the generation")
    response: Optional[str] = Field(None, description="Generated text response")
    elapsed_ms: float = Field(..., description="Time taken to generate in milliseconds")
    error: Optional[str] = Field(None, description="Error message if generation failed")
    model: Optional[str] = Field(None, description="Model used for generation")


class ModelPullRequest(BaseModel):
    """Request to pull a model from Ollama library."""
    name: str = Field(..., description="Name of the model to pull")


class ModelPullResponse(BaseModel):
    """Response from a model pull operation."""
    status: str = Field(..., description="Status of the pull operation")
    message: Optional[str] = Field(None, description="Additional information")
    error: Optional[str] = Field(None, description="Error message if pull failed")
    elapsed_seconds: Optional[float] = Field(None, description="Time taken to pull in seconds")


class ModelShowResponse(BaseModel):
    """Response containing details about a model."""
    status: str = Field(..., description="Status of the operation")
    model: Optional[Dict[str, Any]] = Field(None, description="Model details")
    error: Optional[str] = Field(None, description="Error message if operation failed")


# System resource models for Jetson monitoring
class JetsonResources(BaseModel):
    """System resource information specific to Jetson platforms."""
    cpu_percent: float = Field(..., description="CPU usage percentage")
    memory_percent: float = Field(..., description="Memory usage percentage")
    memory_available_mb: float = Field(..., description="Available memory in MB")
    memory_used_mb: float = Field(..., description="Used memory in MB")
    memory_total_mb: float = Field(..., description="Total memory in MB")
    gpu_percent: Optional[float] = Field(None, description="GPU usage percentage")
    temperature_cpu: Optional[float] = Field(None, description="CPU temperature in Celsius")
    temperature_gpu: Optional[float] = Field(None, description="GPU temperature in Celsius")