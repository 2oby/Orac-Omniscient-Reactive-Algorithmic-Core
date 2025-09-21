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

from orac.homeassistant.client import HomeAssistantClient
from orac.homeassistant.config import HomeAssistantConfig

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
            "entities": {},
            "statistics": {
                "total_entities": 0,
                "enabled_entities": 0,
                "configured_entities": 0,
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
            port = connection.get('port', 8123)
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
                timeout=connection.get('timeout', 10)
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
            port = connection.get('port', 8123)
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
                timeout=connection.get('timeout', 10)
            )

            # Fetch entities
            async with HomeAssistantClient(ha_config) as ha_client:
                entities = await ha_client.get_states(use_cache=False)

            if entities is not None:
                # Process entities
                backend = self.backends[backend_id]

                # Update or add entities
                for entity in entities:
                    entity_id = entity.get('entity_id')
                    if entity_id:
                        # Preserve existing configuration if it exists
                        if entity_id in backend['entities']:
                            # Update original_name and area if changed
                            backend['entities'][entity_id]['original_name'] = entity.get('attributes', {}).get('friendly_name', entity_id)
                            backend['entities'][entity_id]['area'] = entity.get('attributes', {}).get('area', 'Unknown')
                        else:
                            # Create new entity configuration
                            backend['entities'][entity_id] = {
                                'enabled': False,
                                'friendly_name': None,
                                'aliases': [],
                                'original_name': entity.get('attributes', {}).get('friendly_name', entity_id),
                                'domain': entity_id.split('.')[0] if '.' in entity_id else 'unknown',
                                'area': entity.get('attributes', {}).get('area', 'Unknown'),
                                'priority': 5,
                                'configured_at': None,
                                'state': entity.get('state'),
                                'attributes': entity.get('attributes', {})
                            }

                # Update statistics
                backend['statistics'] = {
                    'total_entities': len(backend['entities']),
                    'enabled_entities': sum(1 for e in backend['entities'].values() if e['enabled']),
                    'configured_entities': sum(1 for e in backend['entities'].values() if e['configured_at']),
                    'last_sync': datetime.now().isoformat()
                }

                self.save_backend(backend_id)

                return {
                    "success": True,
                    "entities": list(backend['entities'].values()),
                    "count": len(backend['entities'])
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

    def update_entity(self, backend_id: str, entity_id: str, updates: Dict) -> Optional[Dict]:
        """Update entity configuration

        Args:
            backend_id: The backend ID
            entity_id: The entity ID
            updates: Dictionary of updates

        Returns:
            Updated entity or None
        """
        backend = self.get_backend(backend_id)
        if not backend:
            logger.error(f"Backend {backend_id} not found")
            return None

        if entity_id not in backend['entities']:
            logger.error(f"Entity {entity_id} not found in backend {backend_id}")
            return None

        entity = backend['entities'][entity_id]

        # Update allowed fields
        if 'enabled' in updates:
            entity['enabled'] = updates['enabled']
            if updates['enabled'] and not entity['configured_at']:
                entity['configured_at'] = datetime.now().isoformat()

        if 'friendly_name' in updates:
            entity['friendly_name'] = updates['friendly_name']

        if 'aliases' in updates:
            entity['aliases'] = updates['aliases']

        if 'priority' in updates:
            entity['priority'] = updates['priority']

        # Update statistics
        backend['statistics'] = {
            'total_entities': len(backend['entities']),
            'enabled_entities': sum(1 for e in backend['entities'].values() if e['enabled']),
            'configured_entities': sum(1 for e in backend['entities'].values() if e['configured_at']),
            'last_sync': backend['statistics'].get('last_sync')
        }

        self.save_backend(backend_id)
        return entity

    def bulk_update_entities(self, backend_id: str, entity_ids: List[str], updates: Dict) -> Dict:
        """Bulk update multiple entities

        Args:
            backend_id: The backend ID
            entity_ids: List of entity IDs to update
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
        for entity_id in entity_ids:
            if self.update_entity(backend_id, entity_id, updates):
                updated += 1

        return {
            "success": True,
            "updated": updated,
            "total": len(entity_ids)
        }

    def get_entities(self, backend_id: str, filter_enabled: Optional[bool] = None) -> List[Dict]:
        """Get entities for a backend

        Args:
            backend_id: The backend ID
            filter_enabled: If provided, filter by enabled status

        Returns:
            List of entities
        """
        backend = self.get_backend(backend_id)
        if not backend:
            return []

        entities = []
        for entity_id, entity_data in backend['entities'].items():
            if filter_enabled is None or entity_data['enabled'] == filter_enabled:
                entity = entity_data.copy()
                entity['entity_id'] = entity_id
                entities.append(entity)

        return entities