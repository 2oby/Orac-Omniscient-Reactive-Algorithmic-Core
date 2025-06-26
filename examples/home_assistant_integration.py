#!/usr/bin/env python3
"""
Home Assistant Integration Example

This example demonstrates how to integrate the smart home parser with
Home Assistant to convert natural language commands into actual device
control actions.
"""

import asyncio
import json
import os
import sys
from typing import Dict, List, Optional

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orac.smart_home_parser import SmartHomeParser
from orac.homeassistant.client import HomeAssistantClient

class SmartHomeAssistant:
    """
    Smart Home Assistant Integration
    
    Combines the smart home parser with Home Assistant client to provide
    natural language control of smart home devices.
    """
    
    def __init__(self, model_path: str, ha_url: str, ha_token: str):
        """
        Initialize the Smart Home Assistant.
        
        Args:
            model_path: Path to GGUF model file
            ha_url: Home Assistant URL (e.g., "http://localhost:8123")
            ha_token: Home Assistant long-lived access token
        """
        self.parser = SmartHomeParser(model_path)
        self.ha_client = HomeAssistantClient(ha_url, ha_token)
        
        # Device mapping: generic terms -> Home Assistant entity IDs
        self.device_mapping = {
            "bedroom lights": [
                "light.bedroom_lamp",
                "light.bedroom_ceiling",
                "light.bedroom_nightstand"
            ],
            "bathroom lights": [
                "light.bathroom_main",
                "light.bathroom_mirror"
            ],
            "kitchen lights": [
                "light.kitchen_ceiling",
                "light.kitchen_under_cabinet"
            ],
            "living room lights": [
                "light.living_room_main",
                "light.living_room_lamp",
                "light.living_room_tv"
            ]
        }
        
        # Action mapping: generic actions -> Home Assistant services
        self.action_mapping = {
            "turn on": {
                "light": "light.turn_on",
                "switch": "switch.turn_on",
                "cover": "cover.open_cover"
            },
            "turn off": {
                "light": "light.turn_off", 
                "switch": "switch.turn_off",
                "cover": "cover.close_cover"
            },
            "toggle": {
                "light": "light.toggle",
                "switch": "switch.toggle",
                "cover": "cover.toggle"
            }
        }
    
    async def parse_and_execute(self, user_input: str) -> Dict:
        """
        Parse a natural language command and execute it in Home Assistant.
        
        Args:
            user_input: Natural language command
            
        Returns:
            Dictionary with parse result and execution status
        """
        try:
            # Parse the command
            parsed = await self.parser.parse_command(user_input)
            
            if parsed.get("action") == "error":
                return {
                    "success": False,
                    "error": "Failed to parse command",
                    "parsed": parsed
                }
            
            # Validate the parsed result
            if not self.parser.validate_command(parsed):
                return {
                    "success": False,
                    "error": "Invalid action or device",
                    "parsed": parsed
                }
            
            # Get device entities
            device_name = parsed["device"]
            action_name = parsed["action"]
            
            if device_name not in self.device_mapping:
                return {
                    "success": False,
                    "error": f"Unknown device: {device_name}",
                    "parsed": parsed
                }
            
            entity_ids = self.device_mapping[device_name]
            
            # Determine service to call
            service_calls = []
            for entity_id in entity_ids:
                # Determine domain from entity ID
                domain = entity_id.split('.')[0]
                
                if action_name in self.action_mapping and domain in self.action_mapping[action_name]:
                    service = self.action_mapping[action_name][domain]
                    service_calls.append({
                        "service": service,
                        "target": {"entity_id": entity_id}
                    })
            
            if not service_calls:
                return {
                    "success": False,
                    "error": f"No valid service found for action: {action_name}",
                    "parsed": parsed
                }
            
            # Execute the service calls
            results = []
            for service_call in service_calls:
                try:
                    result = await self.ha_client.call_service(
                        service_call["service"],
                        service_call["target"]
                    )
                    results.append({
                        "entity_id": service_call["target"]["entity_id"],
                        "service": service_call["service"],
                        "success": True,
                        "result": result
                    })
                except Exception as e:
                    results.append({
                        "entity_id": service_call["target"]["entity_id"],
                        "service": service_call["service"],
                        "success": False,
                        "error": str(e)
                    })
            
            # Check if any calls succeeded
            successful_calls = [r for r in results if r["success"]]
            
            return {
                "success": len(successful_calls) > 0,
                "parsed": parsed,
                "execution": {
                    "total_calls": len(service_calls),
                    "successful_calls": len(successful_calls),
                    "failed_calls": len(results) - len(successful_calls),
                    "results": results
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "parsed": None
            }
    
    async def get_device_status(self, device_name: str) -> Dict:
        """
        Get the current status of a device.
        
        Args:
            device_name: Generic device name (e.g., "bedroom lights")
            
        Returns:
            Dictionary with device status information
        """
        if device_name not in self.device_mapping:
            return {"error": f"Unknown device: {device_name}"}
        
        entity_ids = self.device_mapping[device_name]
        status = {}
        
        for entity_id in entity_ids:
            try:
                state = await self.ha_client.get_state(entity_id)
                status[entity_id] = {
                    "state": state.state,
                    "attributes": state.attributes
                }
            except Exception as e:
                status[entity_id] = {"error": str(e)}
        
        return status
    
    async def list_available_devices(self) -> List[str]:
        """List all available devices."""
        return list(self.device_mapping.keys())
    
    async def list_available_actions(self) -> List[str]:
        """List all available actions."""
        return list(self.action_mapping.keys())
    
    async def close(self):
        """Clean up resources."""
        await self.parser.close()
        await self.ha_client.close()


async def main():
    """Example usage of SmartHomeAssistant."""
    
    # Configuration
    model_path = os.getenv("SMART_HOME_MODEL_PATH")
    ha_url = os.getenv("HOME_ASSISTANT_URL", "http://localhost:8123")
    ha_token = os.getenv("HOME_ASSISTANT_TOKEN")
    
    if not model_path:
        print("❌ Error: SMART_HOME_MODEL_PATH environment variable not set")
        return
    
    if not ha_token:
        print("❌ Error: HOME_ASSISTANT_TOKEN environment variable not set")
        return
    
    # Initialize Smart Home Assistant
    smart_ha = SmartHomeAssistant(model_path, ha_url, ha_token)
    
    print("🏠 Smart Home Assistant Integration")
    print("=" * 40)
    
    # List available devices and actions
    devices = await smart_ha.list_available_devices()
    actions = await smart_ha.list_available_actions()
    
    print(f"Available devices: {', '.join(devices)}")
    print(f"Available actions: {', '.join(actions)}")
    print()
    
    # Test commands
    test_commands = [
        "Turn on the bathroom lights",
        "Turn off the kitchen lights",
        "Toggle bedroom lights"
    ]
    
    for command in test_commands:
        print(f"💬 Command: {command}")
        
        # Parse and execute
        result = await smart_ha.parse_and_execute(command)
        
        print(f"📤 Parsed: {json.dumps(result['parsed'], indent=2)}")
        
        if result['success']:
            print("✅ Execution successful")
            execution = result['execution']
            print(f"   Total calls: {execution['total_calls']}")
            print(f"   Successful: {execution['successful_calls']}")
            print(f"   Failed: {execution['failed_calls']}")
        else:
            print(f"❌ Execution failed: {result['error']}")
        
        print()
    
    # Get device status
    print("📊 Device Status:")
    for device in devices:
        status = await smart_ha.get_device_status(device)
        print(f"  {device}: {json.dumps(status, indent=4)}")
    
    # Clean up
    await smart_ha.close()


if __name__ == "__main__":
    asyncio.run(main()) 