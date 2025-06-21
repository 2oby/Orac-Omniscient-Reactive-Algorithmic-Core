#!/usr/bin/env python3
"""
Test script for auto-discovery of Home Assistant entities.

This script demonstrates how the mapping config auto-discovers entities
and generates initial mappings with NULL values for missing friendly names.
"""

import asyncio
import logging
from orac.homeassistant.client import HomeAssistantClient
from orac.homeassistant.config import HomeAssistantConfig
from orac.homeassistant.mapping_config import EntityMappingConfig

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_auto_discovery():
    """Test the auto-discovery functionality."""
    
    # Initialize Home Assistant config and client
    config = HomeAssistantConfig.from_yaml("orac/homeassistant/config.yaml")
    client = HomeAssistantClient(config)
    
    # Initialize mapping config with client for auto-discovery
    mapping_config = EntityMappingConfig(client=client)
    
    print("=== Home Assistant Entity Auto-Discovery Test ===\n")
    
    # Show existing mappings (if any)
    print("1. Existing mappings from YAML file:")
    existing_mappings = mapping_config.get_mapping_summary()
    print(f"   - Total entities: {existing_mappings['total_entities']}")
    print(f"   - Entities with friendly names: {existing_mappings['entities_with_friendly_names']}")
    print(f"   - Entities needing friendly names: {existing_mappings['entities_needing_friendly_names']}")
    
    if existing_mappings['entities_with_mappings']:
        print("   - Existing mappings:")
        for entity_id in existing_mappings['entities_with_mappings']:
            friendly_name = mapping_config.get_friendly_name(entity_id)
            print(f"     {entity_id} -> {friendly_name}")
    print()
    
    # Run auto-discovery
    print("2. Running auto-discovery...")
    auto_mappings = await mapping_config.auto_discover_entities()
    
    # Show auto-discovery results
    print("3. Auto-discovery results:")
    summary = mapping_config.get_mapping_summary()
    print(f"   - Total entities discovered: {summary['total_entities']}")
    print(f"   - Entities with friendly names: {summary['entities_with_friendly_names']}")
    print(f"   - Entities needing friendly names: {summary['entities_needing_friendly_names']}")
    print()
    
    # Show all mappings
    print("4. Complete mapping list:")
    for entity_id, friendly_name in auto_mappings.items():
        status = "✅" if friendly_name and friendly_name.lower() != 'null' else "❌ NULL"
        print(f"   {status} {entity_id} -> {friendly_name}")
    print()
    
    # Show entities that need friendly names
    entities_needing_names = mapping_config.get_entities_needing_friendly_names()
    if entities_needing_names:
        print("5. Entities needing friendly names (will trigger UI prompts):")
        for entity_id in entities_needing_names:
            print(f"   - {entity_id}")
        print()
        print("   These entities will trigger user dialogs in the ORAC application")
        print("   to complete the friendly name mappings.")
    else:
        print("5. All entities have friendly names! ✅")
    print()
    
    # Demonstrate lookup functionality
    print("6. Testing lookup functionality:")
    
    # Test entity_id -> friendly_name lookup
    for entity_id in list(auto_mappings.keys())[:3]:  # Test first 3
        friendly_name = mapping_config.get_friendly_name(entity_id)
        print(f"   {entity_id} -> {friendly_name}")
    
    # Test friendly_name -> entity_id lookup (for non-NULL names)
    valid_names = [name for name in auto_mappings.values() if name and name.lower() != 'null']
    if valid_names:
        test_name = valid_names[0]
        entity_id = mapping_config.get_entity_id(test_name)
        print(f"   '{test_name}' -> {entity_id}")
    print()
    
    # Show what would be saved to YAML
    print("7. What would be saved to entity_mappings.yaml:")
    print("   (This preserves existing mappings and adds new ones with NULL values)")
    for entity_id, friendly_name in sorted(auto_mappings.items()):
        print(f"   {entity_id}: {friendly_name}")
    
    print("\n=== Test Complete ===")
    print("\nNext steps:")
    print("1. The ORAC application will detect NULL values")
    print("2. User dialogs will prompt for friendly names")
    print("3. Mappings will be saved back to the YAML file")
    print("4. Grammar constraints will be generated for the LLM")

if __name__ == "__main__":
    asyncio.run(test_auto_discovery()) 