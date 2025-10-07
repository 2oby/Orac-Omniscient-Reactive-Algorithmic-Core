"""Home Assistant backend implementation with integrated dispatcher.

Sprint 5: The dispatcher is now encapsulated within the backend.
Users only need to configure the backend, not the dispatcher.
"""

import logging
from typing import Dict, List, Optional, Any
from .abstract_backend import AbstractBackend
from orac.homeassistant.client import HomeAssistantClient
from orac.dispatchers.homeassistant import HomeAssistantDispatcher
from orac.backend_grammar_generator import BackendGrammarGenerator

logger = logging.getLogger(__name__)


class HomeAssistantBackend(AbstractBackend):
    """Home Assistant backend with integrated dispatcher.

    This backend handles both:
    1. Grammar generation from Home Assistant entities
    2. Command execution through internal Home Assistant dispatcher
    """

    def __init__(self, backend_id: str, config: Dict):
        """Initialize Home Assistant backend with internal dispatcher.

        Args:
            backend_id: Unique identifier for this backend instance
            config: Backend configuration dictionary
        """
        super().__init__(backend_id, config)

        # Initialize Home Assistant client
        self.client = self._create_client()

        # Sprint 5: Dispatcher is now internal!
        # Users no longer need to configure this separately
        self.dispatcher = HomeAssistantDispatcher()
        logger.info(f"Initialized internal HomeAssistant dispatcher for backend '{self.name}'")

        # Grammar generator for creating GBNF from device mappings
        self.grammar_generator = BackendGrammarGenerator()

        # Cache for entities
        self._entities_cache = []
        self._cache_valid = False

    def _create_client(self) -> HomeAssistantClient:
        """Create and configure Home Assistant client.

        Returns:
            Configured HomeAssistantClient instance
        """
        from orac.homeassistant.config import HomeAssistantConfig
        from urllib.parse import urlparse

        ha_config = self.config.get('homeassistant', {})

        # Parse URL to get host and port
        url = ha_config.get('url', 'http://localhost:8123')
        parsed = urlparse(url)
        host = parsed.hostname or 'localhost'
        port = parsed.port or (443 if parsed.scheme == 'https' else 8123)
        ssl = parsed.scheme == 'https'

        # Create HomeAssistantConfig object with correct fields
        config_obj = HomeAssistantConfig(
            host=host,
            port=port,
            token=ha_config.get('token', ''),
            ssl=ssl,
            verify_ssl=ha_config.get('verify_ssl', False),
            timeout=ha_config.get('timeout', 10)
        )

        return HomeAssistantClient(config_obj)

    async def fetch_entities(self) -> List[Dict]:
        """Fetch available entities from Home Assistant.

        Returns:
            List of entity dictionaries
        """
        try:
            if not self._cache_valid:
                self._entities_cache = await self.client.fetch_entities()
                self._cache_valid = True
                logger.info(f"Fetched {len(self._entities_cache)} entities from Home Assistant")

            return self._entities_cache

        except Exception as e:
            logger.error(f"Failed to fetch entities from Home Assistant: {e}")
            return []

    def generate_grammar(self) -> Dict:
        """Generate GBNF grammar from configured devices.

        Returns:
            Dictionary containing grammar and metadata
        """
        try:
            # Get device mappings from config
            device_mappings = self.get_device_mappings()

            if not device_mappings:
                logger.warning(f"No device mappings configured for backend '{self.name}'")
                return {
                    'grammar': '',
                    'schema': {},
                    'metadata': {'error': 'No device mappings configured'}
                }

            # Generate grammar using BackendGrammarGenerator
            grammar_result = self.grammar_generator.generate_from_backend(
                self.backend_id,
                device_mappings
            )

            logger.info(f"Generated grammar for backend '{self.name}' with {len(device_mappings)} device mappings")

            return {
                'grammar': grammar_result.get('grammar', ''),
                'schema': grammar_result.get('schema', {}),
                'metadata': {
                    'backend_id': self.backend_id,
                    'backend_name': self.name,
                    'device_count': len(device_mappings),
                    'grammar_file': grammar_result.get('file_path')
                }
            }

        except Exception as e:
            logger.error(f"Failed to generate grammar for backend '{self.name}': {e}")
            return {
                'grammar': '',
                'schema': {},
                'metadata': {'error': str(e)}
            }

    async def dispatch_command(self, command: Dict, context: Optional[Dict] = None) -> Dict:
        """Execute command through internal Home Assistant dispatcher.

        Sprint 5: This replaces the need for separate dispatcher configuration.
        The dispatcher is now an internal implementation detail.

        Args:
            command: The parsed command dictionary from LLM
            context: Optional context with topic information

        Returns:
            Dictionary with execution result
        """
        try:
            # Validate command
            if not await self.validate_command(command):
                return {
                    'success': False,
                    'message': 'Invalid command format',
                    'error': 'Command missing required fields'
                }

            # Add backend context
            if context is None:
                context = {}
            context['backend_id'] = self.backend_id
            context['backend_name'] = self.name
            context['backend_type'] = 'homeassistant'

            # Execute through internal dispatcher
            logger.info(f"Executing command through internal dispatcher: {command}")
            result = await self.dispatcher.execute(command, context)

            # Add backend info to result
            result['backend'] = {
                'id': self.backend_id,
                'name': self.name,
                'type': 'homeassistant'
            }

            return result

        except Exception as e:
            logger.error(f"Failed to dispatch command through backend '{self.name}': {e}")
            return {
                'success': False,
                'message': 'Command execution failed',
                'error': str(e),
                'backend': {
                    'id': self.backend_id,
                    'name': self.name,
                    'type': 'homeassistant'
                }
            }

    async def test_connection(self) -> Dict:
        """Test connection to Home Assistant.

        Returns:
            Connection test result
        """
        try:
            # Test by fetching config
            config = await self.client.get_config()

            return {
                'connected': True,
                'message': 'Successfully connected to Home Assistant',
                'version': config.get('version', 'Unknown'),
                'details': {
                    'location_name': config.get('location_name'),
                    'time_zone': config.get('time_zone'),
                    'components': len(config.get('components', [])),
                    'url': self.client.url
                }
            }

        except Exception as e:
            logger.error(f"Connection test failed for backend '{self.name}': {e}")
            return {
                'connected': False,
                'message': 'Failed to connect to Home Assistant',
                'error': str(e),
                'details': {
                    'url': self.client.url
                }
            }

    def get_statistics(self) -> Dict:
        """Get backend statistics and status.

        Returns:
            Backend statistics
        """
        device_mappings = self.get_device_mappings()

        stats = {
            'status': 'active' if self.enabled else 'disabled',
            'device_count': len(device_mappings),
            'dispatcher_type': 'homeassistant (internal)',  # Sprint 5: Show it's internal
            'backend_type': 'homeassistant',
            'metrics': {
                'entities_cached': len(self._entities_cache),
                'cache_valid': self._cache_valid
            }
        }

        # Add device breakdown
        if device_mappings:
            device_types = {}
            for device_data in device_mappings.values():
                device_type = device_data.get('type', 'unknown')
                device_types[device_type] = device_types.get(device_type, 0) + 1
            stats['device_types'] = device_types

        return stats

    async def validate_command(self, command: Dict) -> bool:
        """Validate a Home Assistant command.

        Args:
            command: Command dictionary to validate

        Returns:
            True if command is valid
        """
        # Check required fields for Home Assistant commands
        required_fields = ['device', 'action']
        if not all(field in command for field in required_fields):
            logger.warning(f"Command missing required fields: {command}")
            return False

        # Check if device exists in mappings
        device_mappings = self.get_device_mappings()
        device_key = f"{command['device']}/{command.get('location', 'default')}"

        if device_key not in device_mappings:
            # Try without location
            device_key = f"{command['device']}/default"
            if device_key not in device_mappings:
                logger.warning(f"Device not found in mappings: {device_key}")
                return False

        return True

    def invalidate_cache(self):
        """Invalidate the entities cache."""
        self._cache_valid = False
        self._entities_cache = []
        logger.info(f"Invalidated entities cache for backend '{self.name}'")

    def __str__(self):
        """String representation."""
        return f"HomeAssistantBackend(id={self.backend_id}, name={self.name}, dispatcher=internal)"