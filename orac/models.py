"""
orac.models
-----------
Data models for ORAC.

Defines Pydantic models for request/response validation and type safety.
These models are used for llama.cpp-based model management and inference.
"""

from typing import List, Optional, Dict, Any, Set
from pydantic import BaseModel, Field, validator
from enum import Enum

class ModelType(str, Enum):
    """Type of model (chat or completion)."""
    CHAT = "chat"
    COMPLETION = "completion"

class ModelCapability(str, Enum):
    """Capabilities a model may have."""
    SYSTEM_PROMPT = "system_prompt"
    CHAT_HISTORY = "chat_history"
    INSTRUCTION_FOLLOWING = "instruction_following"
    CREATIVE_WRITING = "creative_writing"
    COMPLEX_REASONING = "complex_reasoning"
    TEXT_COMPLETION = "text_completion"

class ModelSettings(BaseModel):
    """Model-specific settings."""
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(2048, gt=0, description="Maximum tokens to generate")
    top_p: float = Field(0.95, ge=0.0, le=1.0, description="Top-p sampling parameter")
    repeat_penalty: float = Field(1.1, ge=0.0, description="Repeat penalty")
    top_k: int = Field(40, gt=0, description="Top-k sampling parameter")

class ModelConfig(BaseModel):
    """Configuration for a specific model."""
    type: ModelType = Field(..., description="Type of model (chat or completion)")
    system_prompt: Optional[str] = Field(None, description="Default system prompt for chat models")
    capabilities: Set[ModelCapability] = Field(..., description="Model capabilities")
    settings: ModelSettings = Field(default_factory=ModelSettings, description="Model-specific settings")
    notes: Optional[str] = Field(None, description="Additional notes about the model")

    @validator('system_prompt')
    def validate_system_prompt(cls, v, values):
        """Validate system prompt based on model type."""
        if 'type' in values and values['type'] == ModelType.CHAT and v is None:
            return "You are a helpful AI assistant. Provide accurate and concise responses."
        return v

class ModelConfigs(BaseModel):
    """Container for all model configurations."""
    defaults: ModelSettings = Field(default_factory=ModelSettings, description="Default settings for all models")
    models: Dict[str, ModelConfig] = Field(..., description="Model-specific configurations")

class ModelInfo(BaseModel):
    """Information about a model."""
    name: str = Field(..., description="Model name")
    size: int = Field(..., description="Model size in bytes")
    modified: float = Field(..., description="Last modification timestamp")
    backend: str = Field("llama_cpp", description="Backend used for inference")
    is_favorite: bool = Field(False, description="Whether the model is favorited")
    config: Optional[ModelConfig] = Field(None, description="Model configuration if available")

class ModelListResponse(BaseModel):
    """Response for model listing endpoint."""
    models: List[ModelInfo] = Field(..., description="List of available models")

class PromptRequest(BaseModel):
    """Request for text generation."""
    model: str = Field(..., description="Model name to use")
    prompt: str = Field(..., description="Text prompt")
    stream: bool = Field(False, description="Whether to stream the response")
    temperature: float = Field(0.7, description="Sampling temperature")
    top_p: float = Field(0.7, description="Top-p sampling parameter")
    top_k: int = Field(40, description="Top-k sampling parameter")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens to generate")

class PromptResponse(BaseModel):
    """Response from text generation."""
    response: str = Field(..., description="Generated text")
    elapsed_ms: float = Field(..., description="Generation time in milliseconds")
    model: str = Field(..., description="Model used for generation")
    prompt: str = Field(..., description="Original prompt")
    finish_reason: Optional[str] = Field(None, description="Reason for generation completion")
    usage: Optional[Dict[str, int]] = Field(None, description="Token usage statistics")

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