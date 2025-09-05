"""
Base Dispatcher Interface

Abstract base class for all ORAC dispatchers.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseDispatcher(ABC):
    """
    Abstract base class for ORAC dispatchers.
    
    Dispatchers take LLM output and execute it through
    various systems (Home Assistant, shell commands, etc.)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the dispatcher with optional configuration.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
    
    @abstractmethod
    def execute(self, llm_output: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the LLM output through this dispatcher.
        
        Args:
            llm_output: The raw output from the LLM
            context: Optional context (topic configuration, etc.)
        
        Returns:
            A dictionary with:
                - success: bool
                - result: Any (dispatcher-specific result)
                - error: Optional[str] (error message if failed)
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Return the display name of this dispatcher.
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """
        Return a brief description of what this dispatcher does.
        """
        pass