"""Factory for creating backend instances.

Backends encapsulate dispatchers internally. The factory creates the
appropriate backend type based on configuration.
"""

import logging
from typing import Dict, Optional
from .abstract_backend import AbstractBackend
from .homeassistant_backend import HomeAssistantBackend

logger = logging.getLogger(__name__)


class BackendFactory:
    """Factory for creating backend instances based on type."""

    # Registry of available backend types
    _backend_types = {
        'homeassistant': HomeAssistantBackend,
        # Future backend types can be added here:
        # 'zigbee': ZigbeeBackend,
        # 'knx': KNXBackend,
        # 'mqtt': MQTTBackend,
    }

    @classmethod
    def create(cls, backend_id: str, config: Dict) -> Optional[AbstractBackend]:
        """Create a backend instance based on configuration.

        Args:
            backend_id: Unique identifier for the backend
            config: Backend configuration dictionary

        Returns:
            Backend instance or None if type not supported
        """
        backend_type = config.get('type')

        if not backend_type:
            logger.error(f"No type specified for backend {backend_id}")
            return None

        if backend_type not in cls._backend_types:
            logger.error(f"Unknown backend type: {backend_type}")
            return None

        try:
            # Get the backend class
            backend_class = cls._backend_types[backend_type]

            # Create and return instance
            backend = backend_class(backend_id, config)
            logger.info(f"Created {backend_type} backend: {backend_id}")

            return backend

        except Exception as e:
            logger.error(f"Failed to create backend {backend_id}: {e}")
            return None

    @classmethod
    def register_backend_type(cls, type_name: str, backend_class):
        """Register a new backend type.

        Args:
            type_name: Name of the backend type
            backend_class: Backend class (must inherit from AbstractBackend)
        """
        if not issubclass(backend_class, AbstractBackend):
            raise ValueError(f"{backend_class} must inherit from AbstractBackend")

        cls._backend_types[type_name] = backend_class
        logger.info(f"Registered backend type: {type_name}")

    @classmethod
    def get_available_types(cls) -> list:
        """Get list of available backend types.

        Returns:
            List of backend type names
        """
        return list(cls._backend_types.keys())

    @classmethod
    def is_type_supported(cls, backend_type: str) -> bool:
        """Check if a backend type is supported.

        Args:
            backend_type: Backend type name

        Returns:
            True if type is supported
        """
        return backend_type in cls._backend_types