"""
Home Assistant Dispatcher

Dispatcher that controls Home Assistant devices by parsing
JSON output from the LLM and executing the appropriate actions.
"""

import os
import json
import requests
import logging
from typing import Any, Dict, Optional
from .base import BaseDispatcher

logger = logging.getLogger(__name__)


class HomeAssistantDispatcher(BaseDispatcher):
    """
    Home Assistant dispatcher that parses JSON commands.
    
    Parses JSON output from LLM with device/action/location fields
    and controls the appropriate Home Assistant entities.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Home Assistant dispatcher.
        
        Args:
            config: Optional configuration (can override HA_URL and HA_TOKEN)
        """
        super().__init__(config)
        
        # Get configuration from environment or config dict
        self.ha_url = config.get('ha_url') if config else None
        self.ha_token = config.get('ha_token') if config else None
        
        # Fall back to environment variables (using correct HA_URL)
        if not self.ha_url:
            self.ha_url = os.getenv('HA_URL', 'http://192.168.8.99:8123')
        if not self.ha_token:
            self.ha_token = os.getenv('HA_TOKEN', '')
        
        # Entity mappings for different locations
        # TODO: Load from entity_mappings.yaml
        self.entity_mappings = {
            'living room': {
                'lights': 'switch.lounge_lamp_plug'  # Using the lounge lamp for living room
            },
            'lounge': {
                'lights': 'switch.lounge_lamp_plug'
            }
        }
    
    def execute(self, llm_output: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the LLM output by parsing JSON and calling HA API.
        
        Args:
            llm_output: The raw output from the LLM (expected to be JSON)
            context: Optional context (topic configuration, etc.)
        
        Returns:
            A dictionary with execution results
        """
        try:
            logger.info(f"HomeAssistantDispatcher executing with output: {llm_output}")
            
            # Parse JSON output from LLM
            try:
                command = json.loads(llm_output.strip())
                logger.debug(f"Parsed command: {command}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
                return {
                    'success': False,
                    'result': None,
                    'error': f'Invalid JSON output from LLM: {str(e)}'
                }
            
            # Extract fields from JSON
            device = command.get('device', '').lower()
            action = command.get('action', '').lower()
            location = command.get('location', '').lower()
            
            logger.info(f"Command details - Device: {device}, Action: {action}, Location: {location}")
            
            # Map action to HA service
            service = None
            if action in ['on', 'turn on']:
                service = 'turn_on'
            elif action in ['off', 'turn off']:
                service = 'turn_off'
            elif action in ['toggle']:
                service = 'toggle'
            else:
                logger.warning(f"Unknown action: {action}")
                return {
                    'success': False,
                    'result': None,
                    'error': f'Unknown action: {action}'
                }
            
            # Get entity from mappings
            entity_id = None
            if location in self.entity_mappings:
                if device in self.entity_mappings[location]:
                    entity_id = self.entity_mappings[location][device]
                    logger.info(f"Found entity mapping: {entity_id}")
            
            if not entity_id:
                logger.warning(f"No entity mapping for {device} in {location}")
                # Fallback to lounge lamp for any light command
                if device == 'lights':
                    entity_id = 'switch.lounge_lamp_plug'
                    logger.info(f"Using fallback entity: {entity_id}")
                else:
                    return {
                        'success': False,
                        'result': None,
                        'error': f'No entity mapping found for {device} in {location}'
                    }
            
            # Determine domain from entity_id
            domain = entity_id.split('.')[0]
            
            # Call Home Assistant API
            logger.info(f"Calling HA service: {domain}/{service} for entity {entity_id}")
            result = self._call_ha_service(domain, service, entity_id)
            
            return {
                'success': True,
                'result': {
                    'entity': entity_id,
                    'action': service,
                    'command': command,
                    'ha_response': result
                },
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Error in HomeAssistantDispatcher: {e}")
            return {
                'success': False,
                'result': None,
                'error': str(e)
            }
    
    def _call_ha_service(self, domain: str, service: str, entity_id: str) -> Dict[str, Any]:
        """
        Call a Home Assistant service.
        
        Args:
            domain: Service domain (e.g., 'light')
            service: Service name (e.g., 'turn_on')
            entity_id: Entity to control
        
        Returns:
            Response from Home Assistant
        """
        url = f"{self.ha_url}/api/services/{domain}/{service}"
        headers = {
            'Authorization': f'Bearer {self.ha_token}',
            'Content-Type': 'application/json'
        }
        data = {
            'entity_id': entity_id
        }
        
        logger.info(f"Calling HA API: {url} with entity: {entity_id}")
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        
        return response.json() if response.text else {'status': 'success'}
    
    @property
    def name(self) -> str:
        """Return the display name of this dispatcher."""
        return "Home Assistant"
    
    @property
    def description(self) -> str:
        """Return a brief description of what this dispatcher does."""
        return "Controls Home Assistant devices via JSON commands"