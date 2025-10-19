import os
import json
import uuid
from pathlib import Path
from typing import Dict, Optional, Any, List
from datetime import datetime
import logging
import aiohttp
import asyncio
from enum import Enum

from orac.config import NetworkConfig
from orac.homeassistant.client import HomeAssistantClient
from orac.homeassistant.config import HomeAssistantConfig

from orac.backends.backend_factory import BackendFactory
from orac.backends.abstract_backend import AbstractBackend

logger = logging.getLogger(__name__)


class BackendType(Enum):
    HOMEASSISTANT = "homeassistant"
    # Future: Add more backend types


class BackendStatus(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    TESTING = "testing"


class BackendManager:
    """Manages backend configurations and operations"""

    def __init__(self, data_dir: str = None):
        """Initialize the backend manager

        Args:
            data_dir: Directory to store backend configurations
        """
        if data_dir is None:
            # Check if DATA_DIR environment variable is set (from docker-compose)
            data_dir = os.getenv('DATA_DIR')
            if not data_dir:
                # Fall back to default relative to this file
                base_dir = Path(__file__).parent.parent
                data_dir = base_dir / "data"

        self.data_dir = Path(data_dir)
        self.backends_dir = self.data_dir / "backends"
        self.backends: Dict[str, Dict] = {}

        # Ensure backends directory exists
        self.backends_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"BackendManager using data directory: {self.data_dir}")
        logger.info(f"Backends directory: {self.backends_dir}")

        # Load existing backends
        self.load_backends()

    def load_backends(self) -> None:
        """Load all backends from JSON files"""
        logger.info(f"Loading backends from {self.backends_dir}")

        if not self.backends_dir.exists():
            logger.info("Backends directory does not exist, creating it")
            self.backends_dir.mkdir(parents=True, exist_ok=True)
            return

        for backend_file in self.backends_dir.glob("*.json"):
            try:
                with open(backend_file, 'r') as f:
                    backend_data = json.load(f)
                    backend_id = backend_data.get('id')
                    if backend_id:
                        self.backends[backend_id] = backend_data
                        logger.info(f"Loaded backend: {backend_id} from {backend_file}")
            except Exception as e:
                logger.error(f"Failed to load backend from {backend_file}: {e}")

    def save_backend(self, backend_id: str) -> bool:
        """Save a specific backend to JSON file

        Args:
            backend_id: The ID of the backend to save

        Returns:
            True if successful, False otherwise
        """
        if backend_id not in self.backends:
            logger.error(f"Backend {backend_id} not found")
            return False

        backend_file = self.backends_dir / f"{backend_id}.json"

        try:
            # Update timestamp
            self.backends[backend_id]['updated_at'] = datetime.now().isoformat()

            with open(backend_file, 'w') as f:
                json.dump(self.backends[backend_id], f, indent=2, default=str)

            logger.info(f"Saved backend {backend_id} to {backend_file}")

            # Auto-regenerate grammar when backend device mappings change
            try:
                from orac.backend_grammar_generator import BackendGrammarGenerator
                grammar_generator = BackendGrammarGenerator(str(self.data_dir))

                # Check if any devices are configured
                backend = self.backends[backend_id]
                has_mapped_devices = any(
                    d.get("enabled") and d.get("device_type") and d.get("location")
                    for d in backend.get("devices", [])
                )

                if has_mapped_devices:
                    logger.info(f"Auto-regenerating grammar for backend {backend_id} after device changes")
                    result = grammar_generator.generate_and_save_grammar(backend_id)
                    if result["success"]:
                        logger.info(f"Grammar regenerated successfully for backend {backend_id}")
                    else:
                        logger.warning(f"Failed to regenerate grammar: {result.get('error')}")
                else:
                    logger.info(f"No mapped devices for backend {backend_id}, skipping grammar generation")
            except Exception as e:
                logger.warning(f"Failed to auto-regenerate grammar for backend {backend_id}: {e}")
                # Don't fail the save operation if grammar generation fails

            return True
        except Exception as e:
            logger.error(f"Failed to save backend {backend_id}: {e}")
            return False

    def create_backend(self, name: str, backend_type: str, connection: Dict) -> Dict:
        """Create a new backend configuration

        Args:
            name: User-friendly name for the backend
            backend_type: Type of backend (e.g., 'homeassistant')
            connection: Connection details (url, port, token, etc.)

        Returns:
            The created backend configuration
        """
        backend_id = f"{backend_type}_{uuid.uuid4().hex[:8]}"

        backend = {
            "id": backend_id,
            "name": name,
            "type": backend_type,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "connection": connection,
            "status": {
                "connected": False,
                "last_check": None,
                "version": None,
                "error": None
            },
            "device_mappings": {},
            "device_types": ["lights", "heating", "media_player", "blinds", "switches"],
            "locations": [],
            "statistics": {
                "total_devices": 0,
                "enabled_devices": 0,
                "mapped_devices": 0,
                "last_sync": None
            }
        }

        self.backends[backend_id] = backend
        self.save_backend(backend_id)

        logger.info(f"Created backend: {backend_id} ({name})")
        return backend

    def get_backend(self, backend_id: str) -> Optional[Dict]:
        """Get a backend by ID

        Args:
            backend_id: The backend ID

        Returns:
            The backend configuration or None
        """
        return self.backends.get(backend_id)

    def create_backend_instance(self, backend_id: str) -> Optional[AbstractBackend]:
        """Create a backend instance using the backend factory.

        Creates an instance of the appropriate backend class (e.g., HomeAssistantBackend)
        which encapsulates the dispatcher internally.

        Args:
            backend_id: The backend ID

        Returns:
            Backend instance or None if not found or creation failed
        """
        backend_config = self.get_backend(backend_id)
        if not backend_config:
            logger.error(f"Backend configuration not found for {backend_id}")
            return None

        try:
            # Transform the stored config format to the format expected by backends
            # The stored format has 'connection' details that need to be mapped
            transformed_config = {
                'id': backend_config.get('id'),
                'name': backend_config.get('name'),
                'type': backend_config.get('type'),
                'enabled': backend_config.get('enabled', True),
                'device_mappings': backend_config.get('device_mappings', {}),
                'devices': backend_config.get('devices', [])
            }

            # Map connection details based on backend type
            if backend_config.get('type') == 'homeassistant':
                connection = backend_config.get('connection', {})
                transformed_config['homeassistant'] = {
                    'url': f"{connection.get('url', 'http://localhost')}:{connection.get('port', NetworkConfig.DEFAULT_HA_PORT)}",
                    'token': connection.get('token', ''),
                    'verify_ssl': connection.get('verify_ssl', False)
                }

            # If dispatcher_type was stored (from legacy migration), include it
            if 'dispatcher_type' in backend_config:
                transformed_config['dispatcher_type'] = backend_config['dispatcher_type']

            # Create backend instance using factory
            backend_instance = BackendFactory.create(backend_id, transformed_config)

            if backend_instance:
                logger.info(f"Created backend instance for {backend_id}: {backend_instance}")
            else:
                logger.error(f"Failed to create backend instance for {backend_id}")

            return backend_instance

        except Exception as e:
            logger.error(f"Error creating backend instance for {backend_id}: {e}")
            return None

    def list_backends(self) -> List[Dict]:
        """List all backends

        Returns:
            List of all backend configurations
        """
        return list(self.backends.values())

    def update_backend(self, backend_id: str, updates: Dict) -> Optional[Dict]:
        """Update a backend configuration

        Args:
            backend_id: The backend ID
            updates: Dictionary of updates to apply

        Returns:
            The updated backend or None if not found
        """
        if backend_id not in self.backends:
            logger.error(f"Backend {backend_id} not found")
            return None

        backend = self.backends[backend_id]

        # Update allowed fields
        if 'name' in updates:
            backend['name'] = updates['name']

        if 'connection' in updates:
            backend['connection'].update(updates['connection'])

        # Save and return
        if self.save_backend(backend_id):
            return backend
        return None

    def delete_backend(self, backend_id: str) -> bool:
        """Delete a backend

        Args:
            backend_id: The backend ID

        Returns:
            True if successful, False otherwise
        """
        if backend_id not in self.backends:
            logger.error(f"Backend {backend_id} not found")
            return False

        backend_file = self.backends_dir / f"{backend_id}.json"

        try:
            if backend_file.exists():
                backend_file.unlink()
            del self.backends[backend_id]
            logger.info(f"Deleted backend: {backend_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete backend {backend_id}: {e}")
            return False

    async def test_connection(self, backend_id: str) -> Dict:
        """Test backend connection

        Args:
            backend_id: The backend ID

        Returns:
            Dictionary with test results
        """
        backend = self.get_backend(backend_id)
        if not backend:
            return {
                "success": False,
                "error": f"Backend {backend_id} not found"
            }

        backend_type = backend.get('type')
        connection = backend.get('connection', {})

        if backend_type == BackendType.HOMEASSISTANT.value:
            return await self._test_homeassistant_connection(backend_id, connection)
        else:
            return {
                "success": False,
                "error": f"Unsupported backend type: {backend_type}"
            }

    async def _test_homeassistant_connection(self, backend_id: str, connection: Dict) -> Dict:
        """Test Home Assistant connection

        Args:
            backend_id: The backend ID
            connection: Connection configuration

        Returns:
            Test result dictionary
        """
        try:
            # Extract connection details
            url = connection.get('url', '')
            port = connection.get('port', NetworkConfig.DEFAULT_HA_PORT)
            token = connection.get('token', '')

            if not url or not token:
                return {
                    "success": False,
                    "error": "Missing URL or API token"
                }

            # Parse URL to extract host
            if url.startswith('http://'):
                host = url[7:]
            elif url.startswith('https://'):
                host = url[8:]
            else:
                host = url

            # Create HA config
            ha_config = HomeAssistantConfig(
                host=host,
                port=port,
                token=token,
                ssl=url.startswith('https'),
                verify_ssl=connection.get('verify_ssl', True),
                timeout=connection.get('timeout', NetworkConfig.HA_TIMEOUT)
            )

            # Create HA client and test connection
            async with HomeAssistantClient(ha_config) as ha_client:
                is_connected = await ha_client.validate_connection()

                if is_connected:
                    # Get some basic info
                    states = await ha_client.get_states(use_cache=False)

                    # Update backend status
                    backend = self.backends[backend_id]
                    backend['status'] = {
                        'connected': True,
                        'last_check': datetime.now().isoformat(),
                        'version': "Connected",  # HA doesn't easily expose version
                        'error': None
                    }
                    self.save_backend(backend_id)

                    return {
                        "success": True,
                        "entity_count": len(states) if states else 0,
                        "message": "Connection successful"
                    }
                else:
                    # Update backend status with error
                    backend = self.backends[backend_id]
                    backend['status'] = {
                        'connected': False,
                        'last_check': datetime.now().isoformat(),
                        'version': None,
                        'error': 'Connection failed'
                    }
                    self.save_backend(backend_id)

                    return {
                        "success": False,
                        "error": 'Connection failed - check URL and token'
                    }

        except Exception as e:
            logger.error(f"Error testing HA connection: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def validate_device_mappings(self, backend_id: str) -> List[str]:
        """Check for duplicate Type + Location combinations

        Args:
            backend_id: The backend ID

        Returns:
            List of conflict messages
        """
        backend = self.get_backend(backend_id)
        if not backend:
            return [f"Backend {backend_id} not found"]

        conflicts = []
        seen_combinations = {}

        for device_id, mapping in backend.get('device_mappings', {}).items():
            if not mapping.get('enabled'):
                continue

            device_type = mapping.get('device_type')
            location = mapping.get('location')

            if device_type and location:
                combo = f"{device_type}:{location}"
                if combo in seen_combinations:
                    conflicts.append(
                        f"Duplicate mapping: {device_id} and {seen_combinations[combo]} "
                        f"both have Type='{device_type}' and Location='{location}'"
                    )
                else:
                    seen_combinations[combo] = device_id

        return conflicts

    def get_device_by_mapping(self, backend_id: str, device_type: str, location: str) -> Optional[str]:
        """Find device with specific Type + Location combination

        Args:
            backend_id: The backend ID
            device_type: The device type
            location: The location

        Returns:
            Device entity_id or None
        """
        backend = self.get_backend(backend_id)
        if not backend:
            return None

        for device_id, mapping in backend.get('device_mappings', {}).items():
            if (mapping.get('enabled') and
                mapping.get('device_type') == device_type and
                mapping.get('location') == location):
                return device_id

        return None

    def add_device_type(self, backend_id: str, device_type: str) -> bool:
        """Add a custom device type

        Args:
            backend_id: The backend ID
            device_type: The device type to add

        Returns:
            True if successful
        """
        backend = self.get_backend(backend_id)
        if not backend:
            return False

        if 'device_types' not in backend:
            backend['device_types'] = []

        if device_type not in backend['device_types']:
            backend['device_types'].append(device_type)
            self.save_backend(backend_id)
            return True
        return False

    def add_location(self, backend_id: str, location: str) -> bool:
        """Add a custom location

        Args:
            backend_id: The backend ID
            location: The location to add

        Returns:
            True if successful
        """
        backend = self.get_backend(backend_id)
        if not backend:
            return False

        if 'locations' not in backend:
            backend['locations'] = []

        if location not in backend['locations']:
            backend['locations'].append(location)
            self.save_backend(backend_id)
            return True
        return False

    async def fetch_entities(self, backend_id: str) -> Dict:
        """Fetch entities from a backend

        Args:
            backend_id: The backend ID

        Returns:
            Dictionary with fetch results
        """
        backend = self.get_backend(backend_id)
        if not backend:
            return {
                "success": False,
                "error": f"Backend {backend_id} not found",
                "entities": []
            }

        backend_type = backend.get('type')
        connection = backend.get('connection', {})

        if backend_type == BackendType.HOMEASSISTANT.value:
            return await self._fetch_homeassistant_entities(backend_id, connection)
        else:
            return {
                "success": False,
                "error": f"Unsupported backend type: {backend_type}",
                "entities": []
            }

    async def _fetch_homeassistant_entities(self, backend_id: str, connection: Dict) -> Dict:
        """Fetch entities from Home Assistant

        Args:
            backend_id: The backend ID
            connection: Connection configuration

        Returns:
            Dictionary with entities
        """
        try:
            # Extract connection details
            url = connection.get('url', '')
            port = connection.get('port', NetworkConfig.DEFAULT_HA_PORT)
            token = connection.get('token', '')

            # Parse URL to extract host
            if url.startswith('http://'):
                host = url[7:]
            elif url.startswith('https://'):
                host = url[8:]
            else:
                host = url

            # Create HA config
            ha_config = HomeAssistantConfig(
                host=host,
                port=port,
                token=token,
                ssl=url.startswith('https'),
                verify_ssl=connection.get('verify_ssl', True),
                timeout=connection.get('timeout', NetworkConfig.HA_TIMEOUT)
            )

            # Fetch entities
            async with HomeAssistantClient(ha_config) as ha_client:
                entities = await ha_client.get_states(use_cache=False)

            if entities is not None:
                # Process entities
                backend = self.backends[backend_id]

                # Ensure device_mappings exists
                if 'device_mappings' not in backend:
                    backend['device_mappings'] = {}

                # Ensure locations exists and extract areas
                if 'locations' not in backend:
                    backend['locations'] = []

                # Extract areas as locations
                areas_found = set()
                for entity in entities:
                    area = entity.get('attributes', {}).get('area')
                    if area and area != 'Unknown':
                        areas_found.add(area)

                # Add areas as locations if not already present
                for area in areas_found:
                    if area not in backend['locations']:
                        backend['locations'].append(area)

                # Update or add device mappings
                for entity in entities:
                    entity_id = entity.get('entity_id')
                    if entity_id:
                        # Preserve existing mapping if it exists
                        if entity_id in backend['device_mappings']:
                            # Update original area if changed
                            backend['device_mappings'][entity_id]['original_area'] = entity.get('attributes', {}).get('area', 'Unknown')
                            backend['device_mappings'][entity_id]['original_name'] = entity.get('attributes', {}).get('friendly_name', entity_id)
                            backend['device_mappings'][entity_id]['state'] = entity.get('state')
                            backend['device_mappings'][entity_id]['attributes'] = entity.get('attributes', {})
                        else:
                            # Create new device mapping
                            domain = entity_id.split('.')[0] if '.' in entity_id else 'unknown'

                            # Suggest initial device type based on domain
                            suggested_type = None
                            if domain == 'light':
                                suggested_type = 'lights'
                            elif domain == 'climate':
                                suggested_type = 'heating'
                            elif domain == 'media_player':
                                suggested_type = 'media_player'
                            elif domain == 'cover':
                                suggested_type = 'blinds'
                            elif domain == 'switch':
                                # Could be lights or switches
                                suggested_type = 'switches'

                            backend['device_mappings'][entity_id] = {
                                'enabled': False,
                                'device_type': suggested_type,
                                'location': None,
                                'original_area': entity.get('attributes', {}).get('area', 'Unknown'),
                                'original_name': entity.get('attributes', {}).get('friendly_name', entity_id),
                                'domain': domain,
                                'configured_at': None,
                                'state': entity.get('state'),
                                'attributes': entity.get('attributes', {})
                            }

                # Update statistics
                backend['statistics'] = {
                    'total_devices': len(backend['device_mappings']),
                    'enabled_devices': sum(1 for d in backend['device_mappings'].values() if d['enabled']),
                    'mapped_devices': sum(1 for d in backend['device_mappings'].values()
                                        if d['enabled'] and d.get('device_type') and d.get('location')),
                    'last_sync': datetime.now().isoformat()
                }

                self.save_backend(backend_id)

                return {
                    "success": True,
                    "devices": list(backend['device_mappings'].values()),
                    "count": len(backend['device_mappings']),
                    "locations_found": list(backend['locations']),
                    "device_types": backend.get('device_types', [])
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to fetch entities",
                    "entities": []
                }

        except Exception as e:
            logger.error(f"Error fetching HA entities: {e}")
            return {
                "success": False,
                "error": str(e),
                "entities": []
            }

    def update_device_mapping(self, backend_id: str, device_id: str, updates: Dict) -> Optional[Dict]:
        """Update device mapping configuration

        Args:
            backend_id: The backend ID
            device_id: The device ID
            updates: Dictionary of updates

        Returns:
            Updated device mapping or None
        """
        backend = self.get_backend(backend_id)
        if not backend:
            logger.error(f"Backend {backend_id} not found")
            return None

        if 'device_mappings' not in backend:
            backend['device_mappings'] = {}

        if device_id not in backend['device_mappings']:
            logger.error(f"Device {device_id} not found in backend {backend_id}")
            return None

        mapping = backend['device_mappings'][device_id]

        # Update allowed fields
        if 'enabled' in updates:
            mapping['enabled'] = updates['enabled']
            if updates['enabled'] and not mapping.get('configured_at'):
                mapping['configured_at'] = datetime.now().isoformat()

        if 'device_type' in updates:
            mapping['device_type'] = updates['device_type']

        if 'location' in updates:
            mapping['location'] = updates['location']

        # Update statistics
        backend['statistics'] = {
            'total_devices': len(backend['device_mappings']),
            'enabled_devices': sum(1 for d in backend['device_mappings'].values() if d['enabled']),
            'mapped_devices': sum(1 for d in backend['device_mappings'].values()
                                if d['enabled'] and d.get('device_type') and d.get('location')),
            'last_sync': backend['statistics'].get('last_sync')
        }

        self.save_backend(backend_id)
        return mapping

    def update_entity(self, backend_id: str, entity_id: str, updates: Dict) -> Optional[Dict]:
        """Legacy method - redirects to update_device_mapping for compatibility"""
        return self.update_device_mapping(backend_id, entity_id, updates)

    def bulk_update_device_mappings(self, backend_id: str, device_ids: List[str], updates: Dict) -> Dict:
        """Bulk update multiple device mappings

        Args:
            backend_id: The backend ID
            device_ids: List of device IDs to update
            updates: Dictionary of updates

        Returns:
            Dictionary with results
        """
        backend = self.get_backend(backend_id)
        if not backend:
            return {
                "success": False,
                "error": f"Backend {backend_id} not found",
                "updated": 0
            }

        updated = 0
        for device_id in device_ids:
            if self.update_device_mapping(backend_id, device_id, updates):
                updated += 1

        return {
            "success": True,
            "updated": updated,
            "total": len(device_ids)
        }

    def bulk_update_entities(self, backend_id: str, entity_ids: List[str], updates: Dict) -> Dict:
        """Legacy method - redirects to bulk_update_device_mappings"""
        return self.bulk_update_device_mappings(backend_id, entity_ids, updates)

    def get_device_mappings(self, backend_id: str, filter_enabled: Optional[bool] = None) -> List[Dict]:
        """Get device mappings for a backend

        Args:
            backend_id: The backend ID
            filter_enabled: If provided, filter by enabled status

        Returns:
            List of device mappings
        """
        backend = self.get_backend(backend_id)
        if not backend:
            return []

        devices = []
        for device_id, device_data in backend.get('device_mappings', {}).items():
            if filter_enabled is None or device_data['enabled'] == filter_enabled:
                device = device_data.copy()
                device['device_id'] = device_id
                devices.append(device)

        return devices

    def get_entities(self, backend_id: str, filter_enabled: Optional[bool] = None) -> List[Dict]:
        """Legacy method - redirects to get_device_mappings for compatibility"""
        return self.get_device_mappings(backend_id, filter_enabled)