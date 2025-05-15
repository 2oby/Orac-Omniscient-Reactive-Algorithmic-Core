"""
orac.prompt_manager
------------------
Centralized system prompt management for ORAC.

Provides a clear hierarchy of system prompts and validation.
"""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from orac.logger import get_logger
from orac.models import ModelConfig, ModelType

logger = get_logger(__name__)

class SystemPromptSource(str, Enum):
    """Source of the system prompt."""
    USER_INPUT = "user_input"
    MODEL_CONFIG = "model_config"
    DEFAULT = "default"

class SystemPromptState(BaseModel):
    """Current state of the system prompt."""
    prompt: str = Field(..., description="The actual system prompt text")
    source: SystemPromptSource = Field(..., description="Where this prompt came from")
    model_name: Optional[str] = Field(None, description="Associated model name if any")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @validator('prompt')
    def validate_prompt(cls, v: str) -> str:
        """Validate system prompt format."""
        if not v.strip():
            raise ValueError("System prompt cannot be empty")
        if len(v) > 4096:  # Reasonable limit for system prompts
            raise ValueError("System prompt too long (max 4096 chars)")
        return v.strip()

class PromptManager:
    """Manages system prompts with clear hierarchy and validation."""
    
    DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant running on a Jetson Orin Nano.
You aim to be concise, accurate, and helpful in your responses."""

    def __init__(self):
        self._current_state: Optional[SystemPromptState] = None
        self._history: list[SystemPromptState] = []
        logger.info("Initialized PromptManager")

    def get_system_prompt(
        self,
        model_name: str,
        user_prompt: Optional[str] = None,
        model_config: Optional[ModelConfig] = None
    ) -> SystemPromptState:
        """
        Get the appropriate system prompt following the hierarchy:
        1. User provided prompt (if valid)
        2. Model config prompt (if available)
        3. Default prompt
        """
        # Log the request
        logger.info(f"Getting system prompt for model {model_name}")
        logger.debug(f"User prompt: {user_prompt}")
        logger.debug(f"Model config: {model_config}")

        # Try user prompt first
        if user_prompt:
            try:
                state = SystemPromptState(
                    prompt=user_prompt,
                    source=SystemPromptSource.USER_INPUT,
                    model_name=model_name,
                    metadata={"user_provided": True}
                )
                logger.info("Using user-provided system prompt")
                self._update_state(state)
                return state
            except ValueError as e:
                logger.warning(f"Invalid user system prompt: {e}")
                # Fall through to next source

        # Try model config
        if model_config and model_config.type == ModelType.CHAT and model_config.system_prompt:
            try:
                state = SystemPromptState(
                    prompt=model_config.system_prompt,
                    source=SystemPromptSource.MODEL_CONFIG,
                    model_name=model_name,
                    metadata={"model_type": model_config.type}
                )
                logger.info("Using model config system prompt")
                self._update_state(state)
                return state
            except ValueError as e:
                logger.warning(f"Invalid model config system prompt: {e}")
                # Fall through to default

        # Use default
        state = SystemPromptState(
            prompt=self.DEFAULT_SYSTEM_PROMPT,
            source=SystemPromptSource.DEFAULT,
            model_name=model_name,
            metadata={"model_type": model_config.type if model_config else None}
        )
        logger.info("Using default system prompt")
        self._update_state(state)
        return state

    def _update_state(self, new_state: SystemPromptState) -> None:
        """Update current state and history."""
        self._current_state = new_state
        self._history.append(new_state)
        # Keep only last 10 states in history
        if len(self._history) > 10:
            self._history.pop(0)

    def get_current_state(self) -> Optional[SystemPromptState]:
        """Get the current system prompt state."""
        return self._current_state

    def get_history(self) -> list[SystemPromptState]:
        """Get the system prompt history."""
        return self._history.copy()

    def format_prompt(self, system_prompt: str, user_prompt: str, model_name: str) -> str:
        """Format the final prompt based on model type."""
        if "qwen" in model_name.lower():
            return f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n"
        else:
            return f"System: {system_prompt}\n\nUser: {user_prompt}\n\nAssistant:"

# Global prompt manager instance
prompt_manager = PromptManager() 