"""
Entity mapping configuration loader.

This module handles loading and managing entity-to-friendly-name mappings
from configuration files for LLM grammar constraints.
Each HA entity maps to exactly ONE friendly name.
"""

import os
import yaml
import logging
from typing import Dict, List, Optional, Set, Any
from pathlib import Path
from .client import HomeAssistantClient
from .domain_mapper import DomainMapper

logger = logging.getLogger(__name__)

class EntityMappingConfig:
    """Configuration loader for entity-to-friendly-name mappings."""
    
    def __init__(self, config_path: Optional[str] = None, client: Optional[HomeAssistantClient] = None):
        """Initialize the mapping configuration.
        
        Args:
            config_path: Path to the entity mappings YAML file.
                         Defaults to 'entity_mappings.yaml' in the same directory.
            client: HomeAssistantClient instance for auto-discovery
        """
        if config_path is None:
            # Default to entity_mappings.yaml in the same directory as this file
            current_dir = Path(__file__).parent
            config_path = current_dir / "entity_mappings.yaml"
        
        self.config_path = Path(config_path)
        self.client = client
        self.domain_mapper = DomainMapper()
        self._mappings: Dict[str, str] = {}  # entity_id -> friendly_name
        self._reverse_mappings: Dict[str, str] = {}  # friendly_name -> entity_id
        self._loaded = False
        
        self._load_mappings()
    
    def _load_mappings(self) -> None:
        """Load entity mappings from the configuration file."""
        try:
            if not self.config_path.exists():
                logger.warning(f"Entity mappings file not found: {self.config_path}")
                self._mappings = {}
            else:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._mappings = yaml.safe_load(f) or {}
                logger.info(f"Loaded {len(self._mappings)} existing entity mappings from {self.config_path}")
            
            # Build reverse mappings for quick lookup
            self._build_reverse_mappings()
            self._loaded = True
            
        except Exception as e:
            logger.error(f"Failed to load entity mappings from {self.config_path}: {e}")
            self._mappings = {}
    
    def _build_reverse_mappings(self) -> None:
        """Build reverse mappings from friendly names to entity IDs."""
        self._reverse_mappings.clear()
        
        for entity_id, friendly_name in self._mappings.items():
            if friendly_name:  # All friendly names are now valid (no NULL values)
                # Normalize friendly name for consistent lookup
                normalized = self._normalize_friendly_name(friendly_name)
                if normalized in self._reverse_mappings:
                    logger.warning(f"Duplicate friendly name '{friendly_name}' for entities "
                                 f"'{self._reverse_mappings[normalized]}' and '{entity_id}'")
                else:
                    self._reverse_mappings[normalized] = entity_id
    
    def _normalize_friendly_name(self, friendly_name: str) -> str:
        """Normalize a friendly name for consistent lookup.
        
        Args:
            friendly_name: The friendly name to normalize
            
        Returns:
            Normalized friendly name (lowercase, trimmed)
        """
        return friendly_name.lower().strip()
    
    async def auto_discover_entities(self) -> Dict[str, str]:
        """Auto-discover entities from Home Assistant and generate initial mappings.
        
        This method:
        1. Fetches all entities from Home Assistant
        2. Filters for relevant entities using DomainMapper
        3. Generates initial friendly names (or NULL if not obvious)
        4. Preserves existing mappings from YAML file
        5. Returns the complete mapping dictionary
        
        Returns:
            Dictionary mapping entity_id -> friendly_name (with NULL for missing names)
        """
        if not self.client:
            logger.error("HomeAssistantClient not provided for auto-discovery")
            return self._mappings.copy()
        
        logger.info("Starting auto-discovery of Home Assistant entities...")
        
        try:
            # Get all entities from Home Assistant
            entities = await self.client.get_states()
            logger.info(f"Found {len(entities)} total entities in Home Assistant")
            
            # Filter for relevant entities
            relevant_entities = []
            for entity in entities:
                entity_id = entity['entity_id']
                domain = entity_id.split('.')[0]
                
                # Check if domain is supported
                if not self.domain_mapper.is_supported_domain(domain):
                    continue
                
                # Determine device type
                device_type = self.domain_mapper.determine_device_type(entity, domain)
                if device_type:  # Entity is relevant
                    relevant_entities.append(entity)
            
            logger.info(f"Found {len(relevant_entities)} relevant entities for mapping")
            
            # Generate initial mappings
            auto_mappings = {}
            for entity in relevant_entities:
                entity_id = entity['entity_id']
                
                # Skip if we already have a mapping (preserve existing)
                if entity_id in self._mappings:
                    auto_mappings[entity_id] = self._mappings[entity_id]
                    continue
                
                # Generate initial friendly name
                friendly_name = self._generate_initial_friendly_name(entity)
                auto_mappings[entity_id] = friendly_name
            
            # Update internal mappings
            self._mappings = auto_mappings
            self._build_reverse_mappings()
            
            logger.info(f"Auto-discovery complete. Generated {len(auto_mappings)} mappings")
            return auto_mappings.copy()
            
        except Exception as e:
            logger.error(f"Error during auto-discovery: {e}")
            return self._mappings.copy()
    
    def _generate_initial_friendly_name(self, entity: Dict[str, Any]) -> str:
        """Generate initial friendly name for an entity.
        
        Args:
            entity: Home Assistant entity data
            
        Returns:
            Generated friendly name or entity_id if no obvious name available
        """
        entity_id = entity['entity_id']
        domain = entity_id.split('.')[0]
        
        # Strategy 1: Use Home Assistant's friendly_name if available
        ha_friendly_name = entity.get('attributes', {}).get('friendly_name')
        if ha_friendly_name:
            return ha_friendly_name.lower()
        
        # Strategy 2: Parse from entity_id
        parts = entity_id.split('.')
        if len(parts) >= 2:
            device_name = parts[1]
            
            # Replace underscores with spaces
            device_name = device_name.replace('_', ' ')
            
            # Add domain-specific suffixes
            if domain == 'light':
                if not device_name.endswith('lights') and not device_name.endswith('light'):
                    device_name += ' lights'
            elif domain == 'input_button':
                if 'scene' in device_name:
                    device_name = device_name.replace('scene_', '').replace('_scene', '')
                    device_name += ' scene'
            
            return device_name
        
        # Strategy 3: Use entity_id as friendly name for unclear cases
        return entity_id
    
    def get_friendly_name(self, entity_id: str) -> Optional[str]:
        """Get the friendly name for a given entity ID.
        
        Args:
            entity_id: The Home Assistant entity ID
            
        Returns:
            Friendly name if found, None otherwise
        """
        return self._mappings.get(entity_id)
    
    def get_entity_id(self, friendly_name: str) -> Optional[str]:
        """Get the entity ID for a given friendly name.
        
        Args:
            friendly_name: The friendly name to look up
            
        Returns:
            Entity ID if found, None otherwise
        """
        normalized = self._normalize_friendly_name(friendly_name)
        return self._reverse_mappings.get(normalized)
    
    def get_all_entity_ids(self) -> Set[str]:
        """Get all entity IDs that have mappings.
        
        Returns:
            Set of all entity IDs with friendly name mappings
        """
        return set(self._mappings.keys())
    
    def get_all_friendly_names(self) -> Set[str]:
        """Get all friendly names defined in the configuration.
        
        Returns:
            Set of all friendly names
        """
        return set(self._mappings.values())
    
    def get_entities_needing_friendly_names(self) -> List[str]:
        """Get list of entity IDs that need friendly names (have NULL values).
        
        Returns:
            List of entity IDs with NULL friendly names
        """
        return [entity_id for entity_id, name in self._mappings.items() 
                if not name or name.lower() == 'null']
    
    def has_mapping(self, entity_id: str) -> bool:
        """Check if an entity ID has a friendly name mapping.
        
        Args:
            entity_id: The entity ID to check
            
        Returns:
            True if the entity has a mapping, False otherwise
        """
        return entity_id in self._mappings
    
    def has_valid_mapping(self, entity_id: str) -> bool:
        """Check if an entity ID has a valid (non-NULL) friendly name mapping.
        
        Args:
            entity_id: The entity ID to check
            
        Returns:
            True if the entity has a valid mapping, False otherwise
        """
        friendly_name = self._mappings.get(entity_id)
        return friendly_name and friendly_name.lower() != 'null'
    
    def add_mapping(self, entity_id: str, friendly_name: str) -> None:
        """Add a new entity mapping.
        
        Args:
            entity_id: The Home Assistant entity ID
            friendly_name: The friendly name for the entity
        """
        self._mappings[entity_id] = friendly_name
        self._build_reverse_mappings()
        logger.info(f"Added mapping for {entity_id}: {friendly_name}")
    
    def remove_mapping(self, entity_id: str) -> None:
        """Remove an entity mapping.
        
        Args:
            entity_id: The entity ID to remove
        """
        if entity_id in self._mappings:
            del self._mappings[entity_id]
            self._build_reverse_mappings()
            logger.info(f"Removed mapping for {entity_id}")
    
    def save_mappings(self) -> None:
        """Save current mappings to the YAML file."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._mappings, f, default_flow_style=False, sort_keys=True)
            logger.info(f"Saved {len(self._mappings)} mappings to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save mappings to {self.config_path}: {e}")
    
    def reload(self) -> None:
        """Reload the configuration from the file."""
        self._load_mappings()
    
    def get_mapping_summary(self) -> Dict[str, Any]:
        """Get a summary of the current mappings.
        
        Returns:
            Dictionary containing mapping statistics
        """
        total_entities = len(self._mappings)
        entities_with_names = len([name for name in self._mappings.values() if name and name.lower() != 'null'])
        entities_needing_names = total_entities - entities_with_names
        
        return {
            "total_entities": total_entities,
            "entities_with_friendly_names": entities_with_names,
            "entities_needing_friendly_names": entities_needing_names,
            "config_file": str(self.config_path),
            "config_file_exists": self.config_path.exists()
        }

    def get_version(self) -> str:
        """Get a version string for the current mapping configuration.
        
        Returns:
            Version string based on file modification time and content hash
        """
        try:
            if not self.config_path.exists():
                return "no-file"
            
            # Get file modification time
            mtime = self.config_path.stat().st_mtime
            
            # Simple hash of mappings content
            content_hash = hash(str(sorted(self._mappings.items())))
            
            return f"{mtime}-{content_hash}"
            
        except Exception as e:
            logger.warning(f"Error generating version: {e}")
            return "error" 