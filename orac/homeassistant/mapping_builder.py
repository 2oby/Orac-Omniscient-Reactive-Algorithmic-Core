"""
Home Assistant Mapping Builder.

This module provides the HAMappingBuilder class that converts discovered
Home Assistant data into mapping structures for LLM grammar constraints.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from .domain_mapper import DomainMapper, DeviceType
from .location_detector import LocationDetector

logger = logging.getLogger(__name__)

class HAMappingBuilder:
    """Builder for creating mapping structures from Home Assistant discovery data."""
    
    def __init__(self):
        """Initialize the mapping builder."""
        self.domain_mapper = DomainMapper()
        self.location_detector = LocationDetector()
        logger.info("HAMappingBuilder initialized")
    
    def build_mapping(self, discovery_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build the complete mapping structure from discovery data.
        
        Args:
            discovery_data: Result from HADiscoveryService.discover_all()
            
        Returns:
            Complete mapping structure for LLM grammar constraints
        """
        logger.info("Building mapping structure from discovery data...")
        
        entities = discovery_data.get('entities', [])
        areas = discovery_data.get('areas', [])
        devices = discovery_data.get('devices', [])
        entity_registry = discovery_data.get('entity_registry', [])
        
        # Initialize mapping structure
        mapping = {
            "version": "1.0",
            "last_updated": datetime.now().isoformat() + "Z",
            "auto_discovered": True,
            "vocabulary": self._build_vocabulary(entities, areas),
            "device_actions": {},
            "device_locations": {"all": [], "everywhere": []},
            "entity_mappings": {},
            "service_mappings": self._get_service_mappings()
        }
        
        # Build entity registry lookup
        entity_area_map = {}
        for entry in entity_registry:
            if entry.get('area_id'):
                entity_area_map[entry['entity_id']] = entry['area_id']
        
        # Build device area lookup
        device_area_map = {}
        for device in devices:
            if device.get('area_id'):
                device_area_map[device['id']] = device['area_id']
        
        # Build area name lookup
        area_name_map = {}
        for area in areas:
            area_name_map[area.get('area_id')] = area.get('name', '').lower().replace('_', ' ')
        
        # Process entities and build mappings
        discovered_locations = set()
        entity_by_location_and_type = {}
        
        for entity in entities:
            entity_id = entity['entity_id']
            domain = entity_id.split('.')[0]
            
            # Skip domains we don't handle
            if not self.domain_mapper.is_supported_domain(domain):
                continue
            
            # Determine device type
            device_type = self.domain_mapper.determine_device_type(entity, domain)
            if not device_type:
                continue
            
            # Determine location using location detector
            location = self.location_detector.detect_location(
                entity,
                entity_area_map=entity_area_map,
                device_area_map=device_area_map,
                area_name_map=area_name_map,
                entity_registry=entity_registry
            )
            
            if location and location not in ['unknown', 'all', 'everywhere']:
                discovered_locations.add(location)
                
                # Store entity by location and type
                if location not in entity_by_location_and_type:
                    entity_by_location_and_type[location] = {}
                if device_type not in entity_by_location_and_type[location]:
                    entity_by_location_and_type[location][device_type] = []
                
                entity_by_location_and_type[location][device_type].append(entity_id)
        
        # Update vocabulary with discovered locations
        mapping['vocabulary']['locations'].extend(sorted(discovered_locations))
        
        # Build device_actions (which actions each device type supports)
        mapping['device_actions'] = self._build_device_actions()
        
        # Build device_locations (which devices exist in which locations)
        mapping['device_locations'] = self._build_device_locations(
            entity_by_location_and_type, discovered_locations
        )
        
        # Build entity_mappings (actual entity IDs for each location/device combo)
        mapping['entity_mappings'] = entity_by_location_and_type
        
        logger.info(f"Mapping structure built with {len(discovered_locations)} locations and {len(entity_by_location_and_type)} entity mappings")
        return mapping
    
    def _build_vocabulary(self, entities: List[Dict[str, Any]], areas: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Build vocabulary from discovered entities and areas.
        
        Args:
            entities: List of Home Assistant entities
            areas: List of Home Assistant areas
            
        Returns:
            Vocabulary structure with devices, actions, and locations
        """
        # Get all device types from domain mapper
        device_types = list(DeviceType)
        
        # Get all actions from domain mapper
        actions = set()
        for domain in self.domain_mapper.get_supported_domains():
            actions.update(self.domain_mapper.get_actions_for_domain(domain))
        
        # Get area names
        area_names = [area.get('name', '').lower().replace('_', ' ') for area in areas if area.get('name')]
        
        vocabulary = {
            "devices": [device_type.value for device_type in device_types],
            "actions": sorted(list(actions)),
            "locations": ["all", "everywhere"] + area_names
        }
        
        return vocabulary
    
    def _build_device_actions(self) -> Dict[str, List[str]]:
        """Build device actions mapping.
        
        Returns:
            Dictionary mapping device types to available actions
        """
        device_actions = {}
        
        for device_type in DeviceType:
            actions = self.domain_mapper.get_actions_for_device_type(device_type)
            device_actions[device_type.value] = actions
        
        return device_actions
    
    def _build_device_locations(self, entity_by_location_and_type: Dict[str, Dict[str, List[str]]], 
                               discovered_locations: Set[str]) -> Dict[str, List[str]]:
        """Build device locations mapping.
        
        Args:
            entity_by_location_and_type: Entities organized by location and device type
            discovered_locations: Set of discovered location names
            
        Returns:
            Dictionary mapping locations to available device types
        """
        device_locations = {"all": [], "everywhere": []}
        
        # Build location-specific device lists
        for location in discovered_locations:
            if location in entity_by_location_and_type:
                device_types = list(entity_by_location_and_type[location].keys())
                device_locations[location] = [device_type.value for device_type in device_types]
                
                # Add to 'all' and 'everywhere'
                for device_type in device_types:
                    if device_type.value not in device_locations['all']:
                        device_locations['all'].append(device_type.value)
                    if device_type.value not in device_locations['everywhere']:
                        device_locations['everywhere'].append(device_type.value)
        
        return device_locations
    
    def _get_service_mappings(self) -> Dict[str, List[str]]:
        """Get service mappings for actions.
        
        Returns:
            Dictionary mapping actions to Home Assistant service calls
        """
        return {
            "turn on": ["light.turn_on", "switch.turn_on", "climate.set_hvac_mode", "fan.turn_on", "cover.open_cover", "media_player.turn_on"],
            "turn off": ["light.turn_off", "switch.turn_off", "climate.set_hvac_mode", "fan.turn_off", "cover.close_cover", "media_player.turn_off"],
            "toggle": ["light.toggle", "switch.toggle", "fan.toggle"],
            "dim": ["light.turn_on"],
            "brighten": ["light.turn_on"],
            "set to %": ["light.turn_on", "climate.set_temperature", "fan.set_percentage", "cover.set_cover_position"],
            "increase": ["climate.set_temperature"],
            "decrease": ["climate.set_temperature"],
            "open": ["cover.open_cover"],
            "close": ["cover.close_cover"],
            "raise": ["cover.open_cover"],
            "lower": ["cover.close_cover"],
            "play": ["media_player.media_play"],
            "pause": ["media_player.media_pause"],
            "stop": ["media_player.media_stop"],
            "trigger": ["automation.trigger", "scene.turn_on"],
            "activate": ["scene.turn_on", "automation.trigger"]
        }
    
    def get_mapping_summary(self, mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of the mapping structure.
        
        Args:
            mapping: Complete mapping structure
            
        Returns:
            Dictionary with mapping summary statistics
        """
        vocabulary = mapping.get('vocabulary', {})
        device_actions = mapping.get('device_actions', {})
        device_locations = mapping.get('device_locations', {})
        entity_mappings = mapping.get('entity_mappings', {})
        
        # Count entities by location and device type
        entity_counts = {}
        total_entities = 0
        for location, device_types in entity_mappings.items():
            entity_counts[location] = {}
            for device_type, entities in device_types.items():
                entity_counts[location][device_type.value] = len(entities)
                total_entities += len(entities)
        
        summary = {
            'total_devices': len(vocabulary.get('devices', [])),
            'total_actions': len(vocabulary.get('actions', [])),
            'total_locations': len(vocabulary.get('locations', [])),
            'total_entities_mapped': total_entities,
            'locations_with_devices': len([loc for loc, devices in device_locations.items() if devices]),
            'entity_counts_by_location': entity_counts,
            'device_types_supported': list(device_actions.keys()),
            'location_names': [loc for loc in vocabulary.get('locations', []) if loc not in ['all', 'everywhere']]
        }
        
        return summary 