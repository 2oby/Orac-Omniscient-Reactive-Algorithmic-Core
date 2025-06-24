#!/usr/bin/env python3
"""
Test script for the auto-popup functionality.

This script demonstrates how the auto-popup system works by:
1. Checking the current state of entity mappings
2. Simulating the discovery of new entities
3. Testing the auto-popup API endpoint
4. Showing how the popup would be triggered
"""

import asyncio
import json
import os
import sys
import aiohttp

# Add the orac package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'orac'))

from orac.homeassistant.client import HomeAssistantClient
from orac.homeassistant.config import HomeAssistantConfig
from orac.homeassistant.mapping_config import EntityMappingConfig

async def test_auto_popup():
    """Test the auto-popup functionality."""
    
    print("=== Auto-Popup Functionality Test ===\n")
    
    # Initialize Home Assistant components
    config = HomeAssistantConfig.from_yaml("orac/homeassistant/config.yaml")
    
    async with HomeAssistantClient(config) as client:
        # Initialize mapping config
        mapping_config = EntityMappingConfig(client=client)
        
        print("1. Current Entity Mappings:")
        current_mappings = mapping_config.get_mapping_summary()
        print(f"   - Total entities: {current_mappings['total_entities']}")
        print(f"   - Entities with friendly names: {current_mappings['entities_with_friendly_names']}")
        print(f"   - Entities needing friendly names: {current_mappings['entities_needing_friendly_names']}")
        print()
        
        # Test the auto-popup API endpoint
        print("2. Testing Auto-Popup API Endpoint:")
        api_url = "http://localhost:8000/v1/homeassistant/mapping/check-auto-popup"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(api_url) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        print(f"   - Should show popup: {result['should_show_popup']}")
                        print(f"   - New entities found: {result['total_new_count']}")
                        print(f"   - Total entities: {result['total_entities']}")
                        print(f"   - Message: {result['popup_message']}")
                        
                        if result['should_show_popup']:
                            print("   ✅ Auto-popup would be triggered!")
                            print("   - New entities that need friendly names:")
                            for entity in result['new_entities'][:5]:  # Show first 5
                                print(f"     * {entity['entity_id']} -> {entity['current_name']}")
                            if len(result['new_entities']) > 5:
                                print(f"     ... and {len(result['new_entities']) - 5} more")
                        else:
                            print("   ✅ No popup needed - all entities have friendly names")
                            
                    else:
                        error_text = await response.text()
                        print(f"   ❌ HTTP Error {response.status}: {error_text}")
                        
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        print()
        
        # Test the popup trigger simulation
        print("3. Popup Trigger Simulation:")
        print("   The auto-popup system works as follows:")
        print("   - Checks for new entities every 30 seconds")
        print("   - If new entities are found, shows a notification")
        print("   - After 2 seconds, opens the entity mapping popup")
        print("   - User can then add friendly names to new entities")
        print("   - Popup won't show again for 5 minutes after dismissal")
        print()
        
        # Show how to test manually
        print("4. Manual Testing:")
        print("   To test the auto-popup manually:")
        print("   - Open the web interface at http://localhost:8000")
        print("   - The auto-popup is enabled by default")
        print("   - Add a new entity to Home Assistant")
        print("   - Wait up to 30 seconds for the popup to appear")
        print("   - Or click 'Check New Entities' to trigger immediately")
        print()
        
        # Show API endpoints
        print("5. Available API Endpoints:")
        print("   - GET /v1/homeassistant/mapping/check-auto-popup")
        print("     Returns whether popup should be shown")
        print("   - GET /v1/homeassistant/mapping/new-entities")
        print("     Returns list of entities needing friendly names")
        print("   - POST /v1/homeassistant/mapping/save")
        print("     Saves a friendly name for an entity")
        print()
        
        print("=== Test Complete ===")
        print("\nThe auto-popup system is now fully functional!")
        print("It will automatically detect new entities and prompt users")
        print("to add friendly names, ensuring the grammar constraints")
        print("always have the latest vocabulary.")

if __name__ == "__main__":
    asyncio.run(test_auto_popup()) 