"""
Dispatcher Registry

Manages available dispatchers and provides a way to register
and retrieve them by name.
"""

from typing import Dict, Type, Optional, List
from .base import BaseDispatcher


class DispatcherRegistry:
    """
    Registry for ORAC dispatchers.
    
    Manages the registration and retrieval of dispatcher classes.
    """
    
    def __init__(self):
        """Initialize the registry."""
        self._dispatchers: Dict[str, Type[BaseDispatcher]] = {}
    
    def register(self, dispatcher_id: str, dispatcher_class: Type[BaseDispatcher]) -> None:
        """
        Register a dispatcher class.
        
        Args:
            dispatcher_id: Unique identifier for the dispatcher
            dispatcher_class: The dispatcher class to register
        """
        if not issubclass(dispatcher_class, BaseDispatcher):
            raise ValueError(f"{dispatcher_class} must be a subclass of BaseDispatcher")
        
        self._dispatchers[dispatcher_id] = dispatcher_class
    
    def get(self, dispatcher_id: str) -> Optional[Type[BaseDispatcher]]:
        """
        Get a dispatcher class by ID.
        
        Args:
            dispatcher_id: The dispatcher identifier
        
        Returns:
            The dispatcher class, or None if not found
        """
        return self._dispatchers.get(dispatcher_id)
    
    def create(self, dispatcher_id: str, config: Optional[Dict] = None) -> Optional[BaseDispatcher]:
        """
        Create an instance of a dispatcher.
        
        Args:
            dispatcher_id: The dispatcher identifier
            config: Optional configuration for the dispatcher
        
        Returns:
            An instance of the dispatcher, or None if not found
        """
        dispatcher_class = self.get(dispatcher_id)
        if dispatcher_class:
            return dispatcher_class(config)
        return None
    
    def list_available(self) -> List[Dict[str, str]]:
        """
        List all available dispatchers.
        
        Returns:
            A list of dictionaries with dispatcher info
        """
        dispatchers = []
        for dispatcher_id, dispatcher_class in self._dispatchers.items():
            # Create a temporary instance to get name and description
            instance = dispatcher_class()
            dispatchers.append({
                'id': dispatcher_id,
                'name': instance.name,
                'description': instance.description
            })
        return dispatchers
    
    def is_registered(self, dispatcher_id: str) -> bool:
        """
        Check if a dispatcher is registered.
        
        Args:
            dispatcher_id: The dispatcher identifier
        
        Returns:
            True if registered, False otherwise
        """
        return dispatcher_id in self._dispatchers


# Global registry instance
dispatcher_registry = DispatcherRegistry()

# Register built-in dispatchers
from .homeassistant import HomeAssistantDispatcher
dispatcher_registry.register('homeassistant', HomeAssistantDispatcher)