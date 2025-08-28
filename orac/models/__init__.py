"""ORAC models package - re-exports from original models.py for backward compatibility."""

# Import everything from the original models.py in parent directory
from ..models import (
    ModelInfo, ModelListResponse, ModelLoadRequest, ModelLoadResponse,
    ModelUnloadResponse, GenerationRequest, GenerationResponse, PromptResponse
)

# Also export Topic model
from .topic import Topic, TopicSettings, GrammarConfig

__all__ = [
    'ModelInfo', 'ModelListResponse', 'ModelLoadRequest', 'ModelLoadResponse',
    'ModelUnloadResponse', 'GenerationRequest', 'GenerationResponse', 'PromptResponse',
    'Topic', 'TopicSettings', 'GrammarConfig'
]