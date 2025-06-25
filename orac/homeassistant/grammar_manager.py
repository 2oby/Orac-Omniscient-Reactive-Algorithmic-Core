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
import json
import os
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
    
    def __init__(self, client: HomeAssistantClient, mapping_config: Optional[EntityMappingConfig] = None, 
                 grammar_file: Optional[str] = None):
        """Initialize the grammar manager.
        
        Args:
            client: HomeAssistantClient instance for API access
            mapping_config: EntityMappingConfig instance for entity mappings
            grammar_file: Path to grammar file for persistence (optional)
        """
        self.client = client
        self.mapping_config = mapping_config or EntityMappingConfig(client=client)
        self.domain_mapper = DomainMapper()
        
        # Grammar persistence
        if grammar_file:
            self.grammar_file = grammar_file
        else:
            # Default to data directory
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
            os.makedirs(data_dir, exist_ok=True)
            self.grammar_file = os.path.join(data_dir, "grammar.json")
        
        # Cache for generated grammar
        self._cached_grammar = None
        self._grammar_version = None
        
        logger.info(f"HomeAssistantGrammarManager initialized with grammar file: {self.grammar_file}")

    def _get_grammar_version(self) -> str:
        """Generate a version string for the current grammar state.
        
        Returns:
            Version string based on mapping config and client state
        """
        # Get mapping config version
        mapping_version = self.mapping_config.get_version() if self.mapping_config else "unknown"
        
        # Get client cache version
        client_version = self.client.cache.get_version() if hasattr(self.client, 'cache') else "unknown"
        
        return f"{mapping_version}-{client_version}"

    def _load_grammar_from_file(self) -> Optional[Dict[str, Any]]:
        """Load grammar from file if it exists and is valid.
        
        Returns:
            Grammar dictionary or None if file doesn't exist or is invalid
        """
        try:
            if not os.path.exists(self.grammar_file):
                return None
            
            with open(self.grammar_file, 'r') as f:
                data = json.load(f)
            
            # Check if version matches
            if data.get('version') == self._grammar_version:
                logger.info("Loaded grammar from cache file")
                return data.get('grammar')
            else:
                logger.info("Grammar cache version mismatch, regenerating")
                return None
                
        except Exception as e:
            logger.warning(f"Error loading grammar from file: {e}")
            return None

    def _save_grammar_to_file(self, grammar: Dict[str, Any]) -> None:
        """Save grammar to file with version information.
        
        Args:
            grammar: Grammar dictionary to save
        """
        try:
            data = {
                'version': self._grammar_version,
                'grammar': grammar,
                'metadata': {
                    'device_count': len(grammar.get("properties", {}).get("device", {}).get("enum", [])),
                    'action_count': len(grammar.get("properties", {}).get("action", {}).get("enum", [])),
                    'location_count': len(grammar.get("properties", {}).get("location", {}).get("enum", []))
                }
            }
            
            with open(self.grammar_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved grammar to file: {self.grammar_file}")
            
        except Exception as e:
            logger.error(f"Error saving grammar to file: {e}")

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

    async def generate_grammar(self, force_regenerate: bool = False) -> Dict[str, Any]:
        """Generate grammar rules from Home Assistant entities and services.
        
        Args:
            force_regenerate: Force regeneration even if cached version exists
            
        Returns:
            Dictionary containing grammar rules for LLM constraint
        """
        # Check if we have a cached version
        current_version = self._get_grammar_version()
        
        if not force_regenerate and self._cached_grammar and self._grammar_version == current_version:
            logger.info("Using cached grammar")
            return self._cached_grammar
        
        # Try to load from file first
        if not force_regenerate:
            cached_grammar = self._load_grammar_from_file()
            if cached_grammar:
                self._cached_grammar = cached_grammar
                self._grammar_version = current_version
                return cached_grammar
        
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
            
            # Cache the grammar
            self._cached_grammar = grammar
            self._grammar_version = current_version
            
            # Save to file
            self._save_grammar_to_file(grammar)
            
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
        
        # Extract locations from entity attributes and friendly names
        for entity in entities:
            attributes = entity.get('attributes', {})
            
            # Check for area information
            if 'area_id' in attributes:
                locations.add(attributes['area_id'])
            
            # Check for room information in friendly_name
            friendly_name = attributes.get('friendly_name', '')
            if friendly_name:
                # Simple room extraction (enhanced with more locations)
                words = friendly_name.lower().split()
                for word in words:
                    if word in ['bedroom', 'bathroom', 'kitchen', 'living', 'lounge', 'hall', 'office', 'toilet', 'garage', 'basement', 'attic']:
                        locations.add(word)
            
            # Also check entity_id for location hints
            entity_id = entity.get('entity_id', '')
            if entity_id:
                parts = entity_id.split('.')
                if len(parts) >= 2:
                    device_name = parts[1].lower()
                    for location in ['bedroom', 'bathroom', 'kitchen', 'living', 'lounge', 'hall', 'office', 'toilet', 'garage', 'basement', 'attic']:
                        if location in device_name:
                            locations.add(location)
        
        # Add common locations if none found
        if not locations:
            locations.update(['bedroom', 'bathroom', 'kitchen', 'living room', 'office'])
        
        return sorted(list(locations))

    async def update_grammar(self, run_auto_discovery: bool = True) -> None:
        """Update grammar rules with latest Home Assistant data.
        
        Args:
            run_auto_discovery: Whether to run auto-discovery before updating
        """
        logger.info("Updating grammar rules...")
        
        # Run auto-discovery to get latest mappings
        if run_auto_discovery and self.mapping_config:
            await self.mapping_config.auto_discover_entities()
        
        # Generate new grammar (force regeneration)
        grammar = await self.generate_grammar(force_regenerate=True)
        
        logger.info("Grammar update complete")

    async def get_grammar(self, force_regenerate: bool = False) -> Dict[str, Any]:
        """Get current grammar rules.
        
        Args:
            force_regenerate: Force regeneration even if cached version exists
            
        Returns:
            Dictionary containing current grammar rules
        """
        return await self.generate_grammar(force_regenerate=force_regenerate)

    def get_grammar_stats(self) -> Dict[str, Any]:
        """Get statistics about the current grammar.
        
        Returns:
            Dictionary containing grammar statistics
        """
        if not self._cached_grammar:
            return {
                "cached": False,
                "grammar_file": self.grammar_file,
                "grammar_file_exists": os.path.exists(self.grammar_file)
            }
        
        grammar = self._cached_grammar
        return {
            "cached": True,
            "grammar_file": self.grammar_file,
            "grammar_file_exists": os.path.exists(self.grammar_file),
            "device_count": len(grammar.get("properties", {}).get("device", {}).get("enum", [])),
            "action_count": len(grammar.get("properties", {}).get("action", {}).get("enum", [])),
            "location_count": len(grammar.get("properties", {}).get("location", {}).get("enum", [])),
            "version": self._grammar_version
        }

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

    def generate_gbnf_grammar(self, grammar_dict: Optional[Dict[str, Any]] = None) -> str:
        """Generate a GBNF grammar string from the grammar dictionary.
        
        Args:
            grammar_dict: Grammar dictionary (if None, uses cached grammar)
            
        Returns:
            GBNF grammar string for llama.cpp
        """
        if grammar_dict is None:
            grammar_dict = self._cached_grammar
        
        if not grammar_dict:
            # Fallback to basic JSON grammar if no grammar available
            return self._get_basic_json_grammar()
        
        # Extract vocabulary from grammar
        device_vocab = grammar_dict.get("properties", {}).get("device", {}).get("enum", [])
        action_vocab = grammar_dict.get("properties", {}).get("action", {}).get("enum", [])
        location_vocab = grammar_dict.get("properties", {}).get("location", {}).get("enum", [])
        
        # Generate GBNF grammar with proper newlines
        gbnf_grammar = f"""root ::= object

object ::= "{{" ws (string ":" ws value ("," ws string ":" ws value)*)? ws "}}"

value ::= object | array | string | number | boolean | null

array ::= "[" ws (value ("," ws value)*)? ws "]"

string ::= device_string | action_string | location_string | generic_string

device_string ::= "\\"device\\"" ":" ws "\\"" device_value "\\""
action_string ::= "\\"action\\"" ":" ws "\\"" action_value "\\""
location_string ::= "\\"location\\"" ":" ws "\\"" location_value "\\""
generic_string ::= "\\"" ([^"\\\\] | "\\\\" (["\\\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F]))* "\\""

device_value ::= {self._generate_alternation(device_vocab)}

action_value ::= {self._generate_alternation(action_vocab)}

location_value ::= {self._generate_alternation(location_vocab)}

number ::= "-"? ([0-9] | [1-9] [0-9]*) ("." [0-9]+)? ([eE] [-+]? [0-9]+)?

boolean ::= "true" | "false"

null ::= "null"

ws ::= [ \\t\\n\\r]*
"""
        
        return gbnf_grammar

    def _generate_alternation(self, values: List[str]) -> str:
        """Generate an alternation rule for GBNF grammar.
        
        Args:
            values: List of string values to alternate between
            
        Returns:
            GBNF alternation string
        """
        if not values:
            return '"empty"'  # Valid GBNF rule instead of empty string
        
        # Escape quotes and create alternation
        escaped_values = []
        for value in values:
            # Escape quotes and backslashes
            escaped = value.replace('\\', '\\\\').replace('"', '\\"')
            escaped_values.append(f'"{escaped}"')
        
        return " | ".join(escaped_values)

    def _get_basic_json_grammar(self) -> str:
        """Get a basic JSON grammar as fallback.
        
        Returns:
            Basic GBNF JSON grammar string
        """
        return """root ::= object

object ::= "{" ws (string ":" ws value ("," ws string ":" ws value)*)? ws "}"

value ::= object | array | string | number | boolean | null

array ::= "[" ws (value ("," ws value)*)? ws "]"

string ::= "\"" ([^"\\] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F]))* "\""

number ::= "-"? ([0-9] | [1-9] [0-9]*) ("." [0-9]+)? ([eE] [-+]? [0-9]+)?

boolean ::= "true" | "false"

null ::= "null"

ws ::= [ \t\n\r]*
"""
