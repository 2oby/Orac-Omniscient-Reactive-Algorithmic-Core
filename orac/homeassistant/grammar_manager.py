# This file will contain the HomeAssistantGrammarManager class that handles the generation
# and management of grammars for Home Assistant commands. It will discover entities and
# services, generate appropriate grammar rules, and maintain the grammar files used
# by the LLM for understanding and validating Home Assistant commands.

"""
Grammar management for Home Assistant integration.

This module handles the generation and management of JSON grammars for LLM inference,
including:
- Dynamic grammar generation from Home Assistant entities and services
- Constraint management for devices, actions, and locations
- Mapping between generic terms and specific entity IDs
- Integration with grammars.yaml for configuration
- Support for manual additions and auto-discovery

The grammar manager ensures that LLM outputs are constrained to valid
Home Assistant commands while maintaining user-friendly terminology.
"""

import logging
from typing import Dict, List, Any, Optional
from .client import HomeAssistantClient
from .models import HomeAssistantEntity, HomeAssistantService
from .mapping_config import EntityMappingConfig
from .domain_mapper import DomainMapper

logger = logging.getLogger(__name__)

class HomeAssistantGrammarManager:
    """Grammar manager for Home Assistant integration.
    
    This class generates and manages grammar rules for LLM command validation,
    integrating with entity mappings and auto-discovery.
    """
    
    def __init__(self, client: HomeAssistantClient, mapping_config: Optional[EntityMappingConfig] = None):
        """Initialize the grammar manager.
        
        Args:
            client: HomeAssistantClient instance for API access
            mapping_config: EntityMappingConfig instance for entity mappings
        """
        self.client = client
        self.mapping_config = mapping_config or EntityMappingConfig(client=client)
        self.domain_mapper = DomainMapper()
        logger.info("HomeAssistantGrammarManager initialized")

    def _get_friendly_name_with_fallback(self, entity_id: str) -> str:
        """Get friendly name for an entity, using entity_id as fallback if NULL.
        
        Args:
            entity_id: The Home Assistant entity ID
            
        Returns:
            Friendly name or entity_id if mapping is NULL
        """
        if not self.mapping_config:
            return entity_id
        
        friendly_name = self.mapping_config.get_friendly_name(entity_id)
        if not friendly_name or friendly_name.lower() == 'null':
            # Use entity_id as friendly name when NULL is encountered
            return entity_id
        return friendly_name

    async def generate_grammar(self) -> Dict[str, Any]:
        """Generate grammar rules from Home Assistant entities and services.
        
        Returns:
            Dictionary containing grammar rules for LLM constraint
        """
        logger.info("Generating grammar rules from Home Assistant data...")
        
        try:
            # Get entities and services
            entities = await self.client.get_states()
            services = await self.client.get_services()
            
            # Generate grammar structure
            grammar = {
                "type": "object",
                "properties": {
                    "device": {
                        "type": "string",
                        "enum": self._generate_device_vocabulary(entities)
                    },
                    "action": {
                        "type": "string", 
                        "enum": self._generate_action_vocabulary(services)
                    },
                    "location": {
                        "type": "string",
                        "enum": self._generate_location_vocabulary(entities)
                    }
                },
                "required": ["device", "action"]
            }
            
            logger.info(f"Generated grammar with {len(grammar['properties']['device']['enum'])} devices, "
                       f"{len(grammar['properties']['action']['enum'])} actions")
            
            return grammar
            
        except Exception as e:
            logger.error(f"Error generating grammar: {e}")
            return {}

    def _generate_device_vocabulary(self, entities: List[Dict[str, Any]]) -> List[str]:
        """Generate device vocabulary from entities.
        
        Args:
            entities: List of Home Assistant entities
            
        Returns:
            List of device friendly names for grammar
        """
        device_names = []
        
        for entity in entities:
            entity_id = entity['entity_id']
            domain = entity_id.split('.')[0]
            
            # Only include relevant domains
            if not self.domain_mapper.is_supported_domain(domain):
                continue
            
            # Get friendly name with fallback to entity_id
            friendly_name = self._get_friendly_name_with_fallback(entity_id)
            device_names.append(friendly_name)
        
        # Remove duplicates and sort
        return sorted(list(set(device_names)))

    def _generate_action_vocabulary(self, services: Dict[str, Any]) -> List[str]:
        """Generate action vocabulary from services.
        
        Args:
            services: Dictionary of Home Assistant services
            
        Returns:
            List of action verbs for grammar
        """
        actions = set()
        
        # Common action mappings
        action_mappings = {
            'turn_on': 'turn on',
            'turn_off': 'turn off', 
            'toggle': 'toggle',
            'open': 'open',
            'close': 'close',
            'play': 'play',
            'pause': 'pause',
            'stop': 'stop',
            'set_temperature': 'set temperature',
            'set_hvac_mode': 'set mode',
            'press': 'press',
            'trigger': 'trigger'
        }
        
        for domain, domain_services in services.items():
            for service_name in domain_services:
                # Map service names to user-friendly actions
                if service_name in action_mappings:
                    actions.add(action_mappings[service_name])
                else:
                    # Use service name as-is for unknown services
                    actions.add(service_name.replace('_', ' '))
        
        return sorted(list(actions))

    def _generate_location_vocabulary(self, entities: List[Dict[str, Any]]) -> List[str]:
        """Generate location vocabulary from entities.
        
        Args:
            entities: List of Home Assistant entities
            
        Returns:
            List of location names for grammar
        """
        locations = set()
        
        # Extract locations from entity attributes
        for entity in entities:
            attributes = entity.get('attributes', {})
            
            # Check for area information
            if 'area_id' in attributes:
                locations.add(attributes['area_id'])
            
            # Check for room information in friendly_name
            friendly_name = attributes.get('friendly_name', '')
            if friendly_name:
                # Simple room extraction (could be enhanced)
                words = friendly_name.lower().split()
                for word in words:
                    if word in ['bedroom', 'bathroom', 'kitchen', 'living', 'lounge', 'hall', 'office']:
                        locations.add(word)
        
        # Add common locations if none found
        if not locations:
            locations.update(['bedroom', 'bathroom', 'kitchen', 'living room', 'office'])
        
        return sorted(list(locations))

    async def update_grammar(self) -> None:
        """Update grammar rules with latest Home Assistant data."""
        logger.info("Updating grammar rules...")
        
        # Run auto-discovery to get latest mappings
        if self.mapping_config:
            await self.mapping_config.auto_discover_entities()
        
        # Generate new grammar
        grammar = await self.generate_grammar()
        
        # TODO: Save grammar to file or database
        logger.info("Grammar update complete")

    async def get_grammar(self) -> Dict[str, Any]:
        """Get current grammar rules.
        
        Returns:
            Dictionary containing current grammar rules
        """
        return await self.generate_grammar()

    async def discover_and_log_data(self) -> None:
        """Discover and log all Home Assistant data (for debugging).
        
        This method fetches entities, services, and areas from Home Assistant
        and logs them to the console for inspection.
        """
        logger.info("Discovering Home Assistant data...")
        
        try:
            # Get all entities
            entities = await self.client.get_states()
            logger.info("\n=== Home Assistant Entities ===")
            for entity in entities:
                entity_id = entity.get('entity_id')
                friendly_name = self._get_friendly_name_with_fallback(entity_id)
                logger.info(f"Entity: {entity_id} -> {friendly_name} = {entity.get('state')}")
            
            # Get all services
            services = await self.client.get_services()
            logger.info("\n=== Home Assistant Services ===")
            for domain, domain_services in services.items():
                logger.info(f"\nDomain: {domain}")
                for service in domain_services:
                    logger.info(f"  Service: {service}")
            
            # Get all areas
            areas = await self.client.get_areas()
            logger.info("\n=== Home Assistant Areas ===")
            for area in areas:
                logger.info(f"Area: {area.get('name')} (ID: {area.get('area_id')})")
            
            logger.info("\nHome Assistant data discovery complete")
            
        except Exception as e:
            logger.error(f"Error discovering Home Assistant data: {e}")
            raise
