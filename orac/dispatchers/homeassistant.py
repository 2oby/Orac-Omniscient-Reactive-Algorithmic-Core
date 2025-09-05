"""
Home Assistant Dispatcher

MVP dispatcher that controls a specific device (lounge lamp)
by parsing LLM output for keywords.
"""

import os
import json
import requests
from typing import Any, Dict, Optional
from .base import BaseDispatcher


class HomeAssistantDispatcher(BaseDispatcher):
    """
    MVP Home Assistant dispatcher.
    
    Controls the lounge lamp by parsing text for "on"/"off" keywords.
    This is a simplified MVP - future versions will use JSON parsing
    and entity mapping.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Home Assistant dispatcher.
        
        Args:
            config: Optional configuration (can override HA_HOST and HA_TOKEN)
        """
        super().__init__(config)
        
        # Get configuration from environment or config dict
        self.ha_host = config.get('ha_host') if config else None
        self.ha_token = config.get('ha_token') if config else None
        
        # Fall back to environment variables
        if not self.ha_host:
            self.ha_host = os.getenv('HA_HOST', 'http://192.168.8.191:8123')
        if not self.ha_token:
            self.ha_token = os.getenv('HA_TOKEN', '')
        
        # MVP: Hardcoded entity for lounge lamp
        self.target_entity = 'light.lounge_lamp'
    
    def execute(self, llm_output: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the LLM output by parsing for keywords and calling HA API.
        
        Args:
            llm_output: The raw output from the LLM
            context: Optional context (topic configuration, etc.)
        
        Returns:
            A dictionary with execution results
        """
        try:
            # MVP: Simple keyword parsing
            llm_lower = llm_output.lower()
            
            # Determine action from keywords
            action = None
            if 'turn on' in llm_lower or 'switch on' in llm_lower or ' on ' in llm_lower:
                action = 'turn_on'
            elif 'turn off' in llm_lower or 'switch off' in llm_lower or ' off ' in llm_lower:
                action = 'turn_off'
            
            if not action:
                return {
                    'success': False,
                    'result': None,
                    'error': 'Could not determine action from LLM output (looking for on/off keywords)'
                }
            
            # Call Home Assistant API
            result = self._call_ha_service('light', action, self.target_entity)
            
            return {
                'success': True,
                'result': {
                    'entity': self.target_entity,
                    'action': action,
                    'llm_output': llm_output,
                    'ha_response': result
                },
                'error': None
            }
            
        except Exception as e:
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
        url = f"{self.ha_host}/api/services/{domain}/{service}"
        headers = {
            'Authorization': f'Bearer {self.ha_token}',
            'Content-Type': 'application/json'
        }
        data = {
            'entity_id': entity_id
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        
        return response.json() if response.text else {'status': 'success'}
    
    @property
    def name(self) -> str:
        """Return the display name of this dispatcher."""
        return "Home Assistant (MVP)"
    
    @property
    def description(self) -> str:
        """Return a brief description of what this dispatcher does."""
        return "Controls lounge lamp via Home Assistant (on/off only)"