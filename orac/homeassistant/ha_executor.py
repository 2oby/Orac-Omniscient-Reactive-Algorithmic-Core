"""
Home Assistant Executor for ORAC.

This module executes JSON commands from the grammar generation system
and translates them into Home Assistant API calls.
"""

import os
import json
import logging
import aiohttp
from typing import Dict, Any, Optional
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)

class HAExecutor:
    """Execute Home Assistant commands from JSON grammar output."""
    
    def __init__(self):
        """Initialize the HA executor with environment configuration."""
        self.ha_url = os.getenv('HA_URL', 'http://192.168.8.100:8123')
        self.ha_token = os.getenv('HA_TOKEN', '')
        self.headers = {
            "Authorization": f"Bearer {self.ha_token}",
            "Content-Type": "application/json"
        }
        
        # Load entity mappings
        self.entity_mappings = self._load_entity_mappings()
        
        # Service mappings for each device type
        self.service_mappings = {
            "lights": {
                "on": ("light", "turn_on"),
                "off": ("light", "turn_off"),
                "toggle": ("light", "toggle"),
                "set": ("light", "turn_on")  # with brightness
            },
            "heating": {
                "on": ("climate", "turn_on"),
                "off": ("climate", "turn_off"),
                "set": ("climate", "set_temperature")
            },
            "blinds": {
                "open": ("cover", "open_cover"),
                "close": ("cover", "close_cover"),
                "toggle": ("cover", "toggle")
            },
            "music": {
                "on": ("media_player", "turn_on"),
                "off": ("media_player", "turn_off"),
                "loud": ("media_player", "volume_up"),
                "quiet": ("media_player", "volume_down")
            }
        }
    
    def _load_entity_mappings(self) -> Dict[str, Dict[str, str]]:
        """Load entity mappings from YAML file."""
        try:
            mapping_file = Path(__file__).parent / "entity_mappings.yaml"
            if mapping_file.exists():
                with open(mapping_file, 'r') as f:
                    data = yaml.safe_load(f)
                    return data.get('mappings', {})
            else:
                logger.warning("Entity mappings file not found, using defaults")
                return {
                    "lights": {
                        "bedroom": "light.bedroom_lights",
                        "bathroom": "light.bathroom_lights",
                        "kitchen": "light.kitchen_lights",
                        "hall": "light.hall_lights",
                        "living room": "light.lounge_lights"
                    },
                    "heating": {
                        "bedroom": "climate.bedroom",
                        "bathroom": "climate.bathroom",
                        "kitchen": "climate.kitchen",
                        "hall": "climate.hall",
                        "living room": "climate.living_room"
                    },
                    "blinds": {
                        "bedroom": "cover.bedroom_blinds",
                        "bathroom": "cover.bathroom_blinds",
                        "kitchen": "cover.kitchen_blinds",
                        "hall": "cover.hall_blinds",
                        "living room": "cover.living_room_blinds"
                    },
                    "music": {
                        "bedroom": "media_player.bedroom",
                        "bathroom": "media_player.bathroom",
                        "kitchen": "media_player.kitchen",
                        "hall": "media_player.hall",
                        "living room": "media_player.living_room"
                    }
                }
        except Exception as e:
            logger.error(f"Failed to load entity mappings: {e}")
            return {}
    
    async def execute_json_command(self, command: Dict[str, str]) -> Dict[str, Any]:
        """
        Execute a JSON command from grammar generation.
        
        Args:
            command: Dictionary with device, action, and location keys
            
        Returns:
            Dictionary with success status and details
        """
        result = {
            "success": False,
            "command": command,
            "ha_request": None,
            "ha_response": None,
            "error": None
        }
        
        try:
            # Validate command structure
            if not all(k in command for k in ["device", "action", "location"]):
                result["error"] = "Invalid command structure - missing required fields"
                return result
            
            device = command["device"]
            action_raw = command["action"]
            location = command["location"]
            
            # Handle UNKNOWN values
            if device == "UNKNOWN" or action_raw == "UNKNOWN" or location == "UNKNOWN":
                result["error"] = "Cannot execute command with UNKNOWN values"
                return result
            
            # Parse action (handle "set X%" or "set XC" formats)
            action = action_raw
            brightness = None
            temperature = None
            
            if action_raw.startswith("set "):
                if action_raw.endswith("%"):
                    action = "set"
                    brightness = int(action_raw[4:-1])  # Extract percentage
                elif action_raw.endswith("C"):
                    action = "set"
                    temperature = int(action_raw[4:-1])  # Extract temperature
            
            # Get service mapping
            if device not in self.service_mappings:
                result["error"] = f"Unknown device type: {device}"
                return result
            
            if action not in self.service_mappings[device]:
                result["error"] = f"Unknown action '{action}' for device '{device}'"
                return result
            
            domain, service = self.service_mappings[device][action]
            
            # Get entity ID
            if device not in self.entity_mappings:
                result["error"] = f"No entity mappings for device type: {device}"
                return result
            
            if location not in self.entity_mappings[device]:
                # Handle "all" location
                if location == "all":
                    entity_ids = list(self.entity_mappings[device].values())
                else:
                    result["error"] = f"Unknown location '{location}' for device '{device}'"
                    return result
            else:
                entity_ids = [self.entity_mappings[device][location]]
            
            # Prepare service data
            service_data = {"entity_id": entity_ids}
            
            # Add brightness for lights
            if brightness is not None and device == "lights":
                # Convert percentage to 0-255 scale
                service_data["brightness"] = int(brightness * 255 / 100)
            
            # Add temperature for heating
            if temperature is not None and device == "heating":
                service_data["temperature"] = temperature
            
            # Prepare HA request
            ha_endpoint = f"{self.ha_url}/api/services/{domain}/{service}"
            result["ha_request"] = {
                "url": ha_endpoint,
                "method": "POST",
                "data": service_data
            }
            
            # Make the API call
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    ha_endpoint,
                    headers=self.headers,
                    json=service_data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_text = await response.text()
                    result["ha_response"] = {
                        "status": response.status,
                        "body": response_text
                    }
                    
                    if response.status == 200:
                        result["success"] = True
                        logger.info(f"Successfully executed command: {command}")
                    else:
                        result["error"] = f"HA API returned status {response.status}: {response_text}"
                        logger.error(f"HA API error: {result['error']}")
        
        except aiohttp.ClientError as e:
            result["error"] = f"Connection error: {str(e)}"
            logger.error(f"Failed to connect to Home Assistant: {e}")
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"
            logger.error(f"Failed to execute command: {e}")
        
        return result
    
    async def test_connection(self) -> bool:
        """Test connection to Home Assistant."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.ha_url}/api/",
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


# Test function
async def test_executor():
    """Test the HA executor with sample commands."""
    executor = HAExecutor()
    
    # Test connection
    print("Testing Home Assistant connection...")
    connected = await executor.test_connection()
    print(f"Connection: {'✓ Connected' if connected else '✗ Not connected'}")
    
    if not connected:
        print("Note: Home Assistant is not available for testing")
        print("Testing command parsing only...")
    
    # Test commands
    test_commands = [
        {"device": "lights", "action": "on", "location": "bedroom"},
        {"device": "lights", "action": "off", "location": "kitchen"},
        {"device": "lights", "action": "set 50%", "location": "living room"},
        {"device": "heating", "action": "set 22C", "location": "bedroom"},
        {"device": "blinds", "action": "open", "location": "bathroom"}
    ]
    
    for cmd in test_commands:
        print(f"\nTesting: {cmd}")
        result = await executor.execute_json_command(cmd)
        if result["success"]:
            print(f"  ✓ Success")
        else:
            print(f"  ✗ Failed: {result['error']}")
        if result["ha_request"]:
            print(f"  Request: {result['ha_request']['url']}")
            print(f"  Data: {result['ha_request']['data']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_executor())