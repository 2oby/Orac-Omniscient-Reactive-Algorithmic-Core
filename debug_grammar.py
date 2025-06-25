#!/usr/bin/env python3
"""
Debug script to investigate grammar constraints issue.
This script will generate and inspect the GBNF grammar to identify the problem.
"""

import asyncio
import json
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orac.homeassistant.client import HomeAssistantClient
from orac.homeassistant.config import HomeAssistantConfig
from orac.homeassistant.mapping_config import EntityMappingConfig
from orac.homeassistant.grammar_manager import HomeAssistantGrammarManager

async def debug_grammar():
    """Debug the grammar generation process."""
    
    print("=== Grammar Constraints Debug ===\n")
    
    try:
        # Initialize Home Assistant components
        config = HomeAssistantConfig.from_yaml("orac/homeassistant/config.yaml")
        
        async with HomeAssistantClient(config) as client:
            # Initialize mapping config and grammar manager
            mapping_config = EntityMappingConfig(client=client)
            grammar_manager = HomeAssistantGrammarManager(client, mapping_config)
            
            print("1. Testing Auto-Discovery...")
            
            # Run auto-discovery to get latest mappings
            auto_mappings = await mapping_config.auto_discover_entities()
            
            print(f"   - Discovered {len(auto_mappings)} entities")
            
            # Show mappings
            print("   - Entity mappings:")
            for entity_id, friendly_name in auto_mappings.items():
                status = "✅" if friendly_name and friendly_name.lower() != 'null' else "❌ NULL"
                print(f"     {status} {entity_id} -> {friendly_name}")
            print()
            
            print("2. Generating Grammar Dictionary...")
            
            # Generate grammar dictionary
            grammar_dict = await grammar_manager.generate_grammar()
            
            # Extract vocabulary
            device_vocab = grammar_dict.get("properties", {}).get("device", {}).get("enum", [])
            action_vocab = grammar_dict.get("properties", {}).get("action", {}).get("enum", [])
            location_vocab = grammar_dict.get("properties", {}).get("location", {}).get("enum", [])
            
            print(f"   - Device vocabulary ({len(device_vocab)} items):")
            for device in device_vocab:
                print(f"     • {device}")
            print()
            
            print(f"   - Action vocabulary ({len(action_vocab)} items):")
            for action in action_vocab:
                print(f"     • {action}")
            print()
            
            print(f"   - Location vocabulary ({len(location_vocab)} items):")
            for location in location_vocab:
                print(f"     • {location}")
            print()
            
            print("3. Generating GBNF Grammar...")
            
            # Generate GBNF grammar string
            gbnf_grammar = grammar_manager.generate_gbnf_grammar(grammar_dict)
            
            print("   - GBNF Grammar:")
            print("   " + "="*50)
            print(gbnf_grammar)
            print("   " + "="*50)
            print()
            
            print("4. Testing Grammar Validation...")
            
            # Test if "attic" and "toilet" are in the device vocabulary
            test_devices = ["attic", "toilet", "bedroom lights", "bathroom lights"]
            
            for device in test_devices:
                if device in device_vocab:
                    print(f"   ✅ '{device}' is in vocabulary")
                else:
                    print(f"   ❌ '{device}' is NOT in vocabulary")
            print()
            
            print("5. Grammar Analysis...")
            
            # Check if the grammar has proper device constraints
            if "device_value ::=" in gbnf_grammar:
                print("   ✅ GBNF grammar contains device_value rule")
                
                # Extract the device_value rule
                lines = gbnf_grammar.split('\n')
                for line in lines:
                    if line.strip().startswith('device_value ::='):
                        print(f"   - Device value rule: {line.strip()}")
                        break
            else:
                print("   ❌ GBNF grammar missing device_value rule")
            
            if "device_string ::=" in gbnf_grammar:
                print("   ✅ GBNF grammar contains device_string rule")
            else:
                print("   ❌ GBNF grammar missing device_string rule")
            
            print()
            
            print("6. Expected vs Actual Behavior...")
            print("   Expected: 'turn on the attic lights' should fail")
            print("   Expected: 'turn on the toilet lights' should fail")
            print("   Actual: LLM is generating responses with invalid devices")
            print()
            
            print("=== Debug Complete ===")
            
    except Exception as e:
        print(f"Error during debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_grammar()) 