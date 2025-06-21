"""
Domain-to-device mapping logic.

This module handles mapping Home Assistant domains to simplified device types
for LLM grammar constraints, including smart detection for edge cases.
"""

import logging
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)

class DeviceType(str, Enum):
    """Simplified device types for user-friendly commands."""
    LIGHTS = "lights"
    THERMOSTAT = "thermostat"
    FAN = "fan"
    BLINDS = "blinds"
    TV = "tv"
    MUSIC = "music"
    ALARM = "alarm"
    SWITCH = "switch"  # Generic switches not controlling lights
    SCENE = "scene"
    AUTOMATION = "automation"

class DomainMapper:
    """Maps Home Assistant domains to simplified device types."""
    
    # Core domain mappings
    DOMAIN_TO_DEVICE_TYPE = {
        'light': DeviceType.LIGHTS,
        'climate': DeviceType.THERMOSTAT,
        'fan': DeviceType.FAN,
        'cover': DeviceType.BLINDS,
        'alarm_control_panel': DeviceType.ALARM,
        'scene': DeviceType.SCENE,
        'automation': DeviceType.AUTOMATION,
    }
    
    # Actions available for each domain
    DOMAIN_ACTIONS = {
        'light': ["turn on", "turn off", "toggle", "dim", "brighten", "set to %"],
        'switch': ["turn on", "turn off", "toggle"],
        'climate': ["turn on", "turn off", "set to %", "increase", "decrease"],
        'fan': ["turn on", "turn off", "toggle", "set to %"],
        'cover': ["open", "close", "raise", "lower", "set to %"],
        'media_player': ["turn on", "turn off", "play", "pause", "stop", "set to %"],
        'alarm_control_panel': ["turn on", "turn off", "toggle"],
        'input_button': ["press", "activate", "trigger"],
        'scene': ["turn on", "activate", "trigger"],
        'automation': ["trigger", "run", "start"]
    }
    
    def __init__(self):
        """Initialize the domain mapper."""
        logger.info("DomainMapper initialized")
    
    def determine_device_type(self, entity: Dict[str, Any], domain: str) -> Optional[DeviceType]:
        """Determine simplified device type from HA entity.
        
        Args:
            entity: Home Assistant entity data
            domain: Entity domain (e.g., 'light', 'switch', 'media_player')
            
        Returns:
            DeviceType if the entity should be included, None if it should be excluded
        """
        # Handle media players (TV vs Music)
        if domain == 'media_player':
            return self._determine_media_player_type(entity)
        
        # Handle switches (lights vs generic)
        if domain == 'switch':
            return self._determine_switch_type(entity)
        
        # Handle covers (blinds vs other covers)
        if domain == 'cover':
            return self._determine_cover_type(entity)
        
        # Handle input buttons (scene triggers)
        if domain == 'input_button':
            return self._determine_input_button_type(entity)
        
        # Default domain mapping
        return self.DOMAIN_TO_DEVICE_TYPE.get(domain)
    
    def _determine_media_player_type(self, entity: Dict[str, Any]) -> DeviceType:
        """Determine if media player is TV or music device.
        
        Args:
            entity: Media player entity data
            
        Returns:
            DeviceType.TV or DeviceType.MUSIC
        """
        entity_id = entity['entity_id'].lower()
        friendly_name = entity.get('attributes', {}).get('friendly_name', '').lower()
        device_class = entity.get('attributes', {}).get('device_class', '').lower()
        
        # TV indicators
        tv_indicators = ['tv', 'television', 'display', 'monitor', 'screen']
        if any(indicator in entity_id for indicator in tv_indicators):
            return DeviceType.TV
        if any(indicator in friendly_name for indicator in tv_indicators):
            return DeviceType.TV
        if 'tv' in device_class:
            return DeviceType.TV
        
        # Music indicators
        music_indicators = ['speaker', 'audio', 'sound', 'music', 'amp', 'receiver']
        if any(indicator in entity_id for indicator in music_indicators):
            return DeviceType.MUSIC
        if any(indicator in friendly_name for indicator in music_indicators):
            return DeviceType.MUSIC
        
        # Default to music for unknown media players
        return DeviceType.MUSIC
    
    def _determine_switch_type(self, entity: Dict[str, Any]) -> Optional[DeviceType]:
        """Determine if switch controls lights or is generic.
        
        Args:
            entity: Switch entity data
            
        Returns:
            DeviceType.LIGHTS if it controls lights, None if generic switch
        """
        entity_id = entity['entity_id'].lower()
        friendly_name = entity.get('attributes', {}).get('friendly_name', '').lower()
        
        # Light control indicators
        light_indicators = ['light', 'lamp', 'bulb', 'ceiling', 'wall', 'floor']
        if any(indicator in entity_id for indicator in light_indicators):
            return DeviceType.LIGHTS
        if any(indicator in friendly_name for indicator in light_indicators):
            return DeviceType.LIGHTS
        
        # Skip generic switches (don't include in mapping)
        return None
    
    def _determine_cover_type(self, entity: Dict[str, Any]) -> DeviceType:
        """Determine cover type (default to blinds).
        
        Args:
            entity: Cover entity data
            
        Returns:
            DeviceType.BLINDS or DeviceType.SWITCH for non-blind covers
        """
        entity_id = entity['entity_id'].lower()
        friendly_name = entity.get('attributes', {}).get('friendly_name', '').lower()
        
        # Non-blind indicators
        non_blind_indicators = ['garage', 'door', 'gate', 'shutter']
        if any(indicator in entity_id for indicator in non_blind_indicators):
            return DeviceType.SWITCH  # Treat as generic switch
        
        return DeviceType.BLINDS
    
    def _determine_input_button_type(self, entity: Dict[str, Any]) -> DeviceType:
        """Determine input button type (scene triggers).
        
        Args:
            entity: Input button entity data
            
        Returns:
            DeviceType.SCENE for scene triggers
        """
        entity_id = entity['entity_id'].lower()
        friendly_name = entity.get('attributes', {}).get('friendly_name', '').lower()
        
        # Scene indicators
        scene_indicators = ['scene', 'good night', 'morning', 'evening', 'mode']
        if any(indicator in entity_id for indicator in scene_indicators):
            return DeviceType.SCENE
        if any(indicator in friendly_name for indicator in scene_indicators):
            return DeviceType.SCENE
        
        # Default to scene for input buttons
        return DeviceType.SCENE
    
    def get_actions_for_device_type(self, device_type: DeviceType) -> List[str]:
        """Get available actions for a device type.
        
        Args:
            device_type: The device type to get actions for
            
        Returns:
            List of available actions for the device type
        """
        actions = set()
        
        # Find which domains map to this device type
        for domain, mapped_type in self.DOMAIN_TO_DEVICE_TYPE.items():
            if mapped_type == device_type:
                actions.update(self.DOMAIN_ACTIONS.get(domain, []))
        
        # Handle special cases
        if device_type == DeviceType.TV:
            actions.update(self.DOMAIN_ACTIONS.get('media_player', []))
        elif device_type == DeviceType.MUSIC:
            actions.update(self.DOMAIN_ACTIONS.get('media_player', []))
        elif device_type == DeviceType.SCENE:
            # Include both scene and input_button actions
            actions.update(self.DOMAIN_ACTIONS.get('scene', []))
            actions.update(self.DOMAIN_ACTIONS.get('input_button', []))
        
        return sorted(list(actions))
    
    def get_actions_for_domain(self, domain: str) -> List[str]:
        """Get available actions for a domain.
        
        Args:
            domain: The Home Assistant domain
            
        Returns:
            List of available actions for the domain
        """
        return self.DOMAIN_ACTIONS.get(domain, [])
    
    def get_supported_domains(self) -> List[str]:
        """Get list of supported domains.
        
        Returns:
            List of domains that are supported for mapping
        """
        return list(self.DOMAIN_TO_DEVICE_TYPE.keys()) + ['media_player', 'switch', 'cover', 'input_button']
    
    def is_supported_domain(self, domain: str) -> bool:
        """Check if a domain is supported for mapping.
        
        Args:
            domain: The domain to check
            
        Returns:
            True if the domain is supported, False otherwise
        """
        return domain in self.get_supported_domains() 