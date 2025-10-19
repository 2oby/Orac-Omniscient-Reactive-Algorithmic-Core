"""Backend implementations for ORAC Core.

Backends encapsulate dispatchers internally - each backend type manages
its own dispatcher for command execution.
"""

from .abstract_backend import AbstractBackend
from .homeassistant_backend import HomeAssistantBackend
from .backend_factory import BackendFactory

__all__ = ['AbstractBackend', 'HomeAssistantBackend', 'BackendFactory']