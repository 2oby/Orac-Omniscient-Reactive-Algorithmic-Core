"""
Home Assistant Discovery Service.

This module provides the HADiscoveryService class that orchestrates the complete
discovery process for Home Assistant entities, areas, devices, and their relationships.
"""

import logging
from typing import Dict, List, Optional, Any
from .client import HomeAssistantClient
from .config import HomeAssistantConfig

logger = logging.getLogger(__name__)

class HADiscoveryService:
    """Service for discovering Home Assistant configuration and building mappings."""
    
    def __init__(self, client: HomeAssistantClient):
        """Initialize the discovery service.
        
        Args:
            client: HomeAssistantClient instance for API communication
        """
        self.client = client
        logger.info("HADiscoveryService initialized")
    
    async def discover_all(self) -> Dict[str, Any]:
        """Complete discovery process.
        
        This method orchestrates the entire discovery process:
        1. Fetch all entities from /api/states
        2. Fetch areas from /api/areas
        3. Fetch devices from /api/config/device_registry/list
        4. Fetch entity registry from /api/config/entity_registry/list
        5. Return structured data for mapping builder
        
        Returns:
            Dictionary containing all discovered data
        """
        logger.info("Starting complete Home Assistant discovery...")
        
        try:
            # 1. Get all entities
            logger.info("Fetching entities...")
            entities = await self.client.get_states()
            logger.info(f"Found {len(entities)} entities")
            
            # 2. Get areas (rooms)
            logger.info("Fetching areas...")
            areas = await self.client.get_areas()
            logger.info(f"Found {len(areas)} areas")
            
            # 3. Get devices and their area assignments
            logger.info("Fetching device registry...")
            devices = await self.client.get_device_registry()
            logger.info(f"Found {len(devices)} devices")
            
            # 4. Get entity registry for area assignments
            logger.info("Fetching entity registry...")
            entity_registry = await self.client.get_entity_registry()
            logger.info(f"Found {len(entity_registry)} entity registry entries")
            
            # 5. Build the discovery result
            discovery_result = {
                'entities': entities,
                'areas': areas,
                'devices': devices,
                'entity_registry': entity_registry,
                'discovery_metadata': {
                    'total_entities': len(entities),
                    'total_areas': len(areas),
                    'total_devices': len(devices),
                    'total_entity_registry_entries': len(entity_registry)
                }
            }
            
            logger.info("Discovery complete")
            return discovery_result
            
        except Exception as e:
            logger.error(f"Error during discovery: {e}")
            raise
    
    async def discover_entities(self) -> List[Dict[str, Any]]:
        """Discover all entities from Home Assistant.
        
        Returns:
            List of entity data from /api/states
        """
        logger.info("Discovering entities...")
        entities = await self.client.get_states()
        logger.info(f"Found {len(entities)} entities")
        return entities
    
    async def discover_areas(self) -> List[Dict[str, Any]]:
        """Discover all areas from Home Assistant.
        
        Returns:
            List of area data from /api/areas
        """
        logger.info("Discovering areas...")
        areas = await self.client.get_areas()
        logger.info(f"Found {len(areas)} areas")
        return areas
    
    async def discover_devices(self) -> List[Dict[str, Any]]:
        """Discover all devices from Home Assistant.
        
        Returns:
            List of device data from /api/config/device_registry/list
        """
        logger.info("Discovering devices...")
        devices = await self.client.get_device_registry()
        logger.info(f"Found {len(devices)} devices")
        return devices
    
    async def discover_entity_registry(self) -> List[Dict[str, Any]]:
        """Discover entity registry from Home Assistant.
        
        Returns:
            List of entity registry data from /api/config/entity_registry/list
        """
        logger.info("Discovering entity registry...")
        entity_registry = await self.client.get_entity_registry()
        logger.info(f"Found {len(entity_registry)} entity registry entries")
        return entity_registry
    
    async def validate_connection(self) -> bool:
        """Validate connection to Home Assistant.
        
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            logger.info("Validating Home Assistant connection...")
            # Try to fetch a small amount of data
            entities = await self.client.get_states()
            logger.info("Connection validation successful")
            return True
        except Exception as e:
            logger.error(f"Connection validation failed: {e}")
            return False
    
    def get_discovery_summary(self, discovery_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of discovery results.
        
        Args:
            discovery_data: Result from discover_all()
            
        Returns:
            Dictionary with discovery summary statistics
        """
        entities = discovery_data.get('entities', [])
        areas = discovery_data.get('areas', [])
        devices = discovery_data.get('devices', [])
        entity_registry = discovery_data.get('entity_registry', [])
        
        # Count entities by domain
        domain_counts = {}
        for entity in entities:
            domain = entity['entity_id'].split('.')[0]
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
        # Count entities with area assignments
        entities_with_areas = 0
        for entry in entity_registry:
            if entry.get('area_id'):
                entities_with_areas += 1
        
        # Count devices with area assignments
        devices_with_areas = 0
        for device in devices:
            if device.get('area_id'):
                devices_with_areas += 1
        
        summary = {
            'total_entities': len(entities),
            'total_areas': len(areas),
            'total_devices': len(devices),
            'total_entity_registry_entries': len(entity_registry),
            'entities_by_domain': domain_counts,
            'entities_with_area_assignments': entities_with_areas,
            'devices_with_area_assignments': devices_with_areas,
            'area_names': [area.get('name', 'Unknown') for area in areas]
        }
        
        return summary 