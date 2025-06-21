"""
Location detection for Home Assistant entities.

This module handles detecting the location/room of Home Assistant entities
using multiple strategies, enabling room-based commands and location-aware
grammar constraints.
"""

import logging
from typing import Dict, List, Optional, Any, Set

logger = logging.getLogger(__name__)

class LocationDetector:
    """Detects entity locations using multiple strategies.
    
    This class implements a hierarchical approach to location detection:
    1. Direct entity area assignment (most accurate)
    2. Device area assignment (very accurate)
    3. Parse from entity ID (fallback)
    4. Parse from friendly name (fallback)
    5. Parse from device info (last resort)
    
    Enables commands like:
    - "Turn off everything in the bedroom"
    - "Turn on all lights in the kitchen"
    - "Turn off everything, everywhere"
    """
    
    def __init__(self):
        """Initialize the location detector with common location patterns."""
        # Common location patterns for parsing entity names and IDs
        self.common_locations = {
            'bedroom': ['bedroom', 'master', 'guest', 'kids', 'child', 'sleep'],
            'kitchen': ['kitchen', 'cooking', 'pantry', 'dining'],
            'living room': ['living', 'lounge', 'family', 'sitting', 'tv room'],
            'bathroom': ['bathroom', 'toilet', 'shower', 'washroom', 'restroom'],
            'office': ['office', 'study', 'workspace', 'desk', 'work'],
            'garage': ['garage', 'carport', 'parking'],
            'basement': ['basement', 'cellar', 'lower'],
            'attic': ['attic', 'loft', 'upper'],
            'hallway': ['hall', 'corridor', 'passage', 'entry'],
            'dining room': ['dining', 'dinner', 'eat'],
            'laundry': ['laundry', 'utility', 'washer', 'mudroom'],
            'outdoor': ['outdoor', 'outside', 'exterior', 'garden', 'patio', 'yard']
        }
        
        logger.info("LocationDetector initialized")
    
    def detect_location(self, 
                       entity: Dict[str, Any],
                       entity_area_map: Dict[str, str],
                       device_area_map: Dict[str, str],
                       areas: Dict[str, str],
                       entity_registry: List[Dict[str, Any]]) -> Optional[str]:
        """Detect entity location using multiple strategies.
        
        Args:
            entity: Home Assistant entity data
            entity_area_map: Mapping of entity_id -> area_id from entity registry
            device_area_map: Mapping of device_id -> area_id from device registry
            areas: Mapping of area_id -> area_name from area registry
            entity_registry: List of entity registry entries
            
        Returns:
            Normalized location name (e.g., "bedroom", "kitchen") or None if not found
        """
        entity_id = entity['entity_id']
        
        # Strategy 1: Direct entity area assignment (most accurate)
        location = self._check_entity_area_assignment(entity_id, entity_area_map, areas)
        if location:
            logger.debug(f"Location detected via entity area assignment: {entity_id} -> {location}")
            return location
        
        # Strategy 2: Device area assignment (very accurate)
        location = self._check_device_area_assignment(entity_id, device_area_map, areas, entity_registry)
        if location:
            logger.debug(f"Location detected via device area assignment: {entity_id} -> {location}")
            return location
        
        # Strategy 3: Parse from entity ID (fallback)
        location = self._parse_from_entity_id(entity_id)
        if location:
            logger.debug(f"Location detected via entity ID parsing: {entity_id} -> {location}")
            return location
        
        # Strategy 4: Parse from friendly name (fallback)
        location = self._parse_from_friendly_name(entity)
        if location:
            logger.debug(f"Location detected via friendly name parsing: {entity_id} -> {location}")
            return location
        
        # Strategy 5: Parse from device info (last resort)
        location = self._parse_from_device_info(entity, entity_registry)
        if location:
            logger.debug(f"Location detected via device info parsing: {entity_id} -> {location}")
            return location
        
        logger.debug(f"No location detected for entity: {entity_id}")
        return None
    
    def _check_entity_area_assignment(self, entity_id: str, entity_area_map: Dict[str, str], areas: Dict[str, str]) -> Optional[str]:
        """Check if entity has direct area assignment.
        
        Args:
            entity_id: The entity ID to check
            entity_area_map: Mapping of entity_id -> area_id
            areas: Mapping of area_id -> area_name
            
        Returns:
            Normalized location name or None
        """
        if entity_id in entity_area_map:
            area_id = entity_area_map[entity_id]
            if area_id in areas:
                return self._normalize_location_name(areas[area_id])
        return None
    
    def _check_device_area_assignment(self, entity_id: str, device_area_map: Dict[str, str], areas: Dict[str, str], entity_registry: List[Dict[str, Any]]) -> Optional[str]:
        """Check if entity's device has area assignment.
        
        Args:
            entity_id: The entity ID to check
            device_area_map: Mapping of device_id -> area_id
            areas: Mapping of area_id -> area_name
            entity_registry: List of entity registry entries
            
        Returns:
            Normalized location name or None
        """
        # Find device ID for this entity
        device_id = None
        for reg_entity in entity_registry:
            if reg_entity['entity_id'] == entity_id and reg_entity.get('device_id'):
                device_id = reg_entity['device_id']
                break
        
        if device_id and device_id in device_area_map:
            area_id = device_area_map[device_id]
            if area_id in areas:
                return self._normalize_location_name(areas[area_id])
        
        return None
    
    def _parse_from_entity_id(self, entity_id: str) -> Optional[str]:
        """Parse location from entity ID.
        
        Args:
            entity_id: The entity ID to parse
            
        Returns:
            Location name or None
        """
        entity_id_lower = entity_id.lower()
        
        for location, patterns in self.common_locations.items():
            for pattern in patterns:
                if pattern in entity_id_lower:
                    return location
        
        return None
    
    def _parse_from_friendly_name(self, entity: Dict[str, Any]) -> Optional[str]:
        """Parse location from friendly name.
        
        Args:
            entity: Home Assistant entity data
            
        Returns:
            Location name or None
        """
        friendly_name = entity.get('attributes', {}).get('friendly_name', '').lower()
        if not friendly_name:
            return None
        
        for location, patterns in self.common_locations.items():
            for pattern in patterns:
                if pattern in friendly_name:
                    return location
        
        return None
    
    def _parse_from_device_info(self, entity: Dict[str, Any], entity_registry: List[Dict[str, Any]]) -> Optional[str]:
        """Parse location from device information.
        
        Args:
            entity: Home Assistant entity data
            entity_registry: List of entity registry entries
            
        Returns:
            Location name or None
        """
        entity_id = entity['entity_id']
        
        # Find device info for this entity
        for reg_entity in entity_registry:
            if reg_entity['entity_id'] == entity_id:
                device_name = reg_entity.get('name', '').lower()
                if device_name:
                    for location, patterns in self.common_locations.items():
                        for pattern in patterns:
                            if pattern in device_name:
                                return location
                break
        
        return None
    
    def _normalize_location_name(self, area_name: str) -> str:
        """Normalize area name to standard location format.
        
        Args:
            area_name: Raw area name from Home Assistant
            
        Returns:
            Normalized location name
        """
        # Convert to lowercase and replace underscores/hyphens with spaces
        normalized = area_name.lower().replace('_', ' ').replace('-', ' ')
        
        # Map common variations to standard names
        location_mapping = {
            'living': 'living room',
            'lounge': 'living room',
            'family room': 'living room',
            'sitting room': 'living room',
            'tv room': 'living room',
            'dining': 'dining room',
            'dinner room': 'dining room',
            'master bedroom': 'bedroom',
            'guest bedroom': 'bedroom',
            'kids bedroom': 'bedroom',
            'child bedroom': 'bedroom',
            'utility room': 'laundry',
            'washer room': 'laundry',
            'mudroom': 'laundry',
            'garden': 'outdoor',
            'patio': 'outdoor',
            'backyard': 'outdoor',
            'front yard': 'outdoor',
            'entry': 'hallway',
            'entryway': 'hallway'
        }
        
        return location_mapping.get(normalized, normalized)
    
    def get_discovered_locations(self, entities: List[Dict[str, Any]], **kwargs) -> Set[str]:
        """Get all discovered locations from entities.
        
        Args:
            entities: List of Home Assistant entities
            **kwargs: Additional arguments for detect_location
            
        Returns:
            Set of discovered location names
        """
        locations = set()
        
        for entity in entities:
            location = self.detect_location(entity, **kwargs)
            if location and location not in ['unknown', 'all', 'everywhere']:
                locations.add(location)
        
        return locations
    
    def validate_location_detection(self, entities: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Validate location detection results.
        
        Args:
            entities: List of Home Assistant entities
            **kwargs: Additional arguments for detect_location
            
        Returns:
            Dictionary with validation results and statistics
        """
        results = {
            'total_entities': len(entities),
            'entities_with_locations': 0,
            'entities_without_locations': 0,
            'detection_methods': {
                'entity_area': 0,
                'device_area': 0,
                'entity_id_parse': 0,
                'friendly_name_parse': 0,
                'device_info_parse': 0
            },
            'locations_found': set(),
            'entities_without_location': []
        }
        
        for entity in entities:
            # Track which method was used (simplified tracking)
            location = self.detect_location(entity, **kwargs)
            if location:
                results['entities_with_locations'] += 1
                results['locations_found'].add(location)
            else:
                results['entities_without_locations'] += 1
                results['entities_without_location'].append(entity['entity_id'])
        
        return results
    
    def build_location_mapping(self, entities: List[Dict[str, Any]], **kwargs) -> Dict[str, Dict[str, List[str]]]:
        """Build a mapping of locations to device types to entity IDs.
        
        This creates the structure needed for room-based commands:
        {
            "bedroom": {
                "lights": ["light.bedroom_lights", "light.bedroom_lamp"],
                "fan": ["fan.bedroom_ceiling_fan"]
            },
            "kitchen": {
                "lights": ["light.kitchen_lights"],
                "thermostat": ["climate.kitchen_thermostat"]
            }
        }
        
        Args:
            entities: List of Home Assistant entities
            **kwargs: Additional arguments for detect_location
            
        Returns:
            Hierarchical mapping of location -> device_type -> entity_ids
        """
        from .domain_mapper import DomainMapper
        
        domain_mapper = DomainMapper()
        location_mapping = {}
        
        for entity in entities:
            entity_id = entity['entity_id']
            domain = entity_id.split('.')[0]
            
            # Skip unsupported domains
            if not domain_mapper.is_supported_domain(domain):
                continue
            
            # Determine device type
            device_type = domain_mapper.determine_device_type(entity, domain)
            if not device_type:
                continue
            
            # Detect location
            location = self.detect_location(entity, **kwargs)
            if not location or location in ['unknown', 'all', 'everywhere']:
                continue
            
            # Build mapping structure
            if location not in location_mapping:
                location_mapping[location] = {}
            
            if device_type.value not in location_mapping[location]:
                location_mapping[location][device_type.value] = []
            
            location_mapping[location][device_type.value].append(entity_id)
        
        return location_mapping 