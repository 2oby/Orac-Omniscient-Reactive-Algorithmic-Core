#!/usr/bin/env python3
"""
Test script for grammar generation with NULL fallback.

This script demonstrates how the grammar manager handles NULL values
by using the entity_id as the friendly name in grammar constraints.
"""

import asyncio
import logging
from orac.homeassistant.client import HomeAssistantClient
from orac.homeassistant.config import HomeAssistantConfig
from orac.homeassistant.mapping_config import EntityMappingConfig
from orac.homeassistant.grammar_manager import HomeAssistantGrammarManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_grammar_generation():
    """Test the grammar generation with NULL fallback functionality."""
    
    # Initialize Home Assistant config and client
    config = HomeAssistantConfig.from_yaml("orac/homeassistant/config.yaml")
    async with HomeAssistantClient(config) as client:
        # Initialize mapping config and grammar manager
        mapping_config = EntityMappingConfig(client=client)
        grammar_manager = HomeAssistantGrammarManager(client, mapping_config)
        
        print("=== Grammar Generation with NULL Fallback Test ===\n")
        
        # Show current mappings
        print("1. Current entity mappings:")
        mappings = mapping_config.get_mapping_summary()
        for entity_id, friendly_name in mapping_config._mappings.items():
            status = "✅" if friendly_name and friendly_name.lower() != 'null' else "❌ NULL"
            print(f"   {status} {entity_id} -> {friendly_name}")
        print()
        
        # Run auto-discovery to see if any NULL values are generated
        print("2. Running auto-discovery...")
        auto_mappings = await mapping_config.auto_discover_entities()
        
        # Show auto-discovery results
        print("3. Auto-discovery results:")
        for entity_id, friendly_name in auto_mappings.items():
            status = "✅" if friendly_name and friendly_name.lower() != 'null' else "❌ NULL"
            print(f"   {status} {entity_id} -> {friendly_name}")
        print()
        
        # Generate grammar
        print("4. Generating grammar with NULL fallback...")
        grammar = await grammar_manager.generate_grammar()
        
        # Show grammar structure
        print("5. Generated grammar structure:")
        print(f"   - Device vocabulary: {len(grammar.get('properties', {}).get('device', {}).get('enum', []))} items")
        print(f"   - Action vocabulary: {len(grammar.get('properties', {}).get('action', {}).get('enum', []))} items")
        print(f"   - Location vocabulary: {len(grammar.get('properties', {}).get('location', {}).get('enum', []))} items")
        print()
        
        # Show device vocabulary (this is where NULL fallback happens)
        print("6. Device vocabulary (with NULL fallback):")
        device_vocab = grammar.get('properties', {}).get('device', {}).get('enum', [])
        for device in device_vocab:
            print(f"   - {device}")
        print()
        
        # Demonstrate NULL fallback functionality
        print("7. NULL Fallback Demonstration:")
        print("   When the grammar manager encounters a NULL friendly name,")
        print("   it automatically uses the entity_id as the friendly name.")
        print("   This ensures the LLM always has a valid vocabulary to work with.")
        print()
        
        # Show example LLM constraints
        print("8. Example LLM Grammar Constraints:")
        print("   The LLM will be constrained to use these device names:")
        for device in device_vocab[:5]:  # Show first 5
            print(f"   - '{device}'")
        if len(device_vocab) > 5:
            print(f"   - ... and {len(device_vocab) - 5} more")
        print()
        
        print("=== Test Complete ===")
        print("\nKey Benefits:")
        print("1. No UI popup required - system handles NULL values automatically")
        print("2. LLM always has valid vocabulary - no missing friendly names")
        print("3. Entity IDs serve as fallback friendly names")
        print("4. Users can still manually edit mappings later if desired")

if __name__ == "__main__":
    asyncio.run(test_grammar_generation()) 