"""Abstract base class for all backend implementations.

Sprint 5: Backends now encapsulate dispatchers internally.
Each backend type manages its own dispatcher for command execution.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class AbstractBackend(ABC):
    """Base class for all backend implementations.

    Backends handle both:
    1. Grammar generation from configured devices
    2. Command execution through internal dispatchers
    """

    def __init__(self, backend_id: str, config: Dict):
        """Initialize the backend.

        Args:
            backend_id: Unique identifier for this backend instance
            config: Backend configuration dictionary
        """
        self.backend_id = backend_id
        self.config = config
        self.name = config.get('name', backend_id)
        self.type = config.get('type')
        self.enabled = config.get('enabled', True)
        self.dispatcher_type = config.get('dispatcher_type', self.type)  # Internal use

        logger.info(f"Initialized {self.__class__.__name__} backend '{self.name}' (ID: {backend_id})")

    @abstractmethod
    async def fetch_entities(self) -> List[Dict]:
        """Fetch available entities from the backend system.

        Returns:
            List of entity dictionaries with structure:
                - entity_id: Unique identifier
                - domain: Entity domain (e.g., light, switch)
                - friendly_name: Human-readable name
                - attributes: Additional entity attributes
        """
        pass

    @abstractmethod
    def generate_grammar(self) -> Dict:
        """Generate GBNF grammar from configured devices.

        Returns:
            Dictionary containing:
                - grammar: The GBNF grammar string
                - schema: JSON schema for validation
                - metadata: Additional grammar metadata
        """
        pass

    @abstractmethod
    async def dispatch_command(self, command: Dict, context: Optional[Dict] = None) -> Dict:
        """Execute the LLM-generated command on the backend system.

        This method encapsulates the dispatcher functionality internally.

        Args:
            command: The parsed command dictionary from LLM
            context: Optional context with topic information

        Returns:
            Dictionary containing:
                - success: Boolean indicating success
                - message: Human-readable result message
                - data: Additional result data
                - error: Error message if failed
        """
        pass

    @abstractmethod
    async def test_connection(self) -> Dict:
        """Verify backend connectivity and configuration.

        Returns:
            Dictionary containing:
                - connected: Boolean indicating connection status
                - message: Status message
                - version: Backend system version (if available)
                - details: Additional connection details
        """
        pass

    @abstractmethod
    def get_statistics(self) -> Dict:
        """Get backend statistics and status.

        Returns:
            Dictionary containing:
                - status: Current backend status
                - device_count: Number of configured devices
                - last_command: Information about last executed command
                - metrics: Performance metrics
        """
        pass

    def get_device_mappings(self) -> Dict[str, Dict]:
        """Get device mappings configuration.

        Returns:
            Dictionary of device mappings from config
        """
        return self.config.get('device_mappings', {})

    def is_enabled(self) -> bool:
        """Check if backend is enabled.

        Returns:
            True if backend is enabled
        """
        return self.enabled

    def get_info(self) -> Dict:
        """Get backend information summary.

        Returns:
            Dictionary with backend information
        """
        return {
            'id': self.backend_id,
            'name': self.name,
            'type': self.type,
            'enabled': self.enabled,
            'dispatcher_type': self.dispatcher_type,  # Internal
            'device_count': len(self.get_device_mappings())
        }

    async def validate_command(self, command: Dict) -> bool:
        """Validate a command before execution.

        Args:
            command: Command dictionary to validate

        Returns:
            True if command is valid for this backend
        """
        # Base validation - can be overridden by subclasses
        required_fields = ['device', 'action']
        return all(field in command for field in required_fields)

    def __str__(self):
        """String representation of the backend."""
        return f"{self.__class__.__name__}(id={self.backend_id}, name={self.name})"

    def __repr__(self):
        """Detailed representation of the backend."""
        return f"{self.__class__.__name__}(id={self.backend_id}, name={self.name}, type={self.type}, enabled={self.enabled})"