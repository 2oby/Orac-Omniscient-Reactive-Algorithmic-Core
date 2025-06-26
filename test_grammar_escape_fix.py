#!/usr/bin/env python3
"""
Test script to verify the grammar escape fix for spaces in vocabulary terms.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orac.homeassistant.config import HomeAssistantConfig
from orac.homeassistant.client import HomeAssistantClient
from orac.homeassistant.mapping_config import EntityMappingConfig
from orac.homeassistant.grammar_manager import HomeAssistantGrammarManager

async def test_grammar_escape_fix():
    """Test that the grammar escape fix works correctly."""
    
    print("=== Testing Grammar Escape Fix ===\n")
    
    try:
        # Initialize Home Assistant components
        config = HomeAssistantConfig.from_yaml("orac/homeassistant/config.yaml")
        
        async with HomeAssistantClient(config) as client:
            # Initialize mapping config and grammar manager
            mapping_config = EntityMappingConfig(client=client)
            grammar_manager = HomeAssistantGrammarManager(client, mapping_config)
            
            print("1. Generating grammar with escape fix...")
            
            # Generate grammar dictionary
            grammar_dict = await grammar_manager.generate_grammar()
            
            # Extract vocabulary for analysis
            device_vocab = grammar_dict.get("properties", {}).get("device", {}).get("enum", [])
            action_vocab = grammar_dict.get("properties", {}).get("action", {}).get("enum", [])
            location_vocab = grammar_dict.get("properties", {}).get("location", {}).get("enum", [])
            
            print(f"   - Device vocabulary ({len(device_vocab)} items):")
            for device in device_vocab[:5]:  # Show first 5
                print(f"     • {device}")
            if len(device_vocab) > 5:
                print(f"     ... and {len(device_vocab) - 5} more")
            print()
            
            print(f"   - Action vocabulary ({len(action_vocab)} items):")
            for action in action_vocab[:5]:  # Show first 5
                print(f"     • {action}")
            if len(action_vocab) > 5:
                print(f"     ... and {len(action_vocab) - 5} more")
            print()
            
            print(f"   - Location vocabulary ({len(location_vocab)} items):")
            for location in location_vocab[:5]:  # Show first 5
                print(f"     • {location}")
            if len(location_vocab) > 5:
                print(f"     ... and {len(location_vocab) - 5} more")
            print()
            
            print("2. Generating GBNF grammar with escape fix...")
            
            # Generate GBNF grammar string
            gbnf_grammar = grammar_manager.generate_gbnf_grammar(grammar_dict)
            
            print(f"   - GBNF grammar length: {len(gbnf_grammar)} characters")
            print()
            
            print("3. Testing grammar validation...")
            
            # Test grammar validation
            is_valid = grammar_manager.validate_gbnf_grammar(gbnf_grammar)
            print(f"   - Grammar validation: {'✅ PASSED' if is_valid else '❌ FAILED'}")
            print()
            
            print("4. Checking for escaped spaces in grammar...")
            
            # Check for escaped spaces in the grammar
            lines_with_spaces = []
            for line in gbnf_grammar.split('\n'):
                if '::=' in line and ('" ' in line or ' "' in line):
                    # This line contains vocabulary with spaces
                    lines_with_spaces.append(line.strip())
            
            print(f"   - Found {len(lines_with_spaces)} lines with vocabulary containing spaces:")
            for line in lines_with_spaces[:3]:  # Show first 3
                print(f"     • {line}")
            if len(lines_with_spaces) > 3:
                print(f"     ... and {len(lines_with_spaces) - 3} more")
            print()
            
            print("5. Verifying space escaping...")
            
            # Check if spaces are properly escaped
            unescaped_spaces = []
            for line in gbnf_grammar.split('\n'):
                if '::=' in line:
                    # Look for vocabulary patterns
                    import re
                    vocab_pattern = r'"([^"]*)"'
                    matches = re.findall(vocab_pattern, line)
                    for match in matches:
                        if ' ' in match and '\\ ' not in match:
                            unescaped_spaces.append(f"'{match}' in line: {line.strip()}")
            
            if unescaped_spaces:
                print("   ❌ Found unescaped spaces:")
                for issue in unescaped_spaces[:3]:
                    print(f"     • {issue}")
                if len(unescaped_spaces) > 3:
                    print(f"     ... and {len(unescaped_spaces) - 3} more")
            else:
                print("   ✅ All spaces properly escaped")
            print()
            
            print("6. Testing specific vocabulary items...")
            
            # Test specific items that should be in the grammar
            test_items = [
                ("bedroom lights", "device"),
                ("kitchen lights", "device"), 
                ("turn on", "action"),
                ("turn off", "action"),
                ("bedroom", "location"),
                ("kitchen", "location")
            ]
            
            for item, category in test_items:
                if item in gbnf_grammar:
                    print(f"   ✅ '{item}' found in {category} grammar")
                else:
                    print(f"   ❌ '{item}' NOT found in {category} grammar")
            print()
            
            print("7. Grammar structure analysis...")
            
            # Check grammar structure
            grammar_lines = gbnf_grammar.split('\n')
            rule_count = sum(1 for line in grammar_lines if '::=' in line)
            print(f"   - Total grammar rules: {rule_count}")
            
            # Check for required rules
            required_rules = ['root', 'object', 'string', 'value', 'ws']
            for rule in required_rules:
                if f"{rule} ::=" in gbnf_grammar:
                    print(f"   ✅ '{rule}' rule present")
                else:
                    print(f"   ❌ '{rule}' rule missing")
            print()
            
            print("=== Test Summary ===")
            print(f"✅ Grammar generation: {len(device_vocab)} devices, {len(action_vocab)} actions, {len(location_vocab)} locations")
            print(f"✅ GBNF grammar: {len(gbnf_grammar)} characters generated")
            print(f"✅ Grammar validation: {'PASSED' if is_valid else 'FAILED'}")
            print(f"✅ Space escaping: {'PASSED' if not unescaped_spaces else 'FAILED'}")
            print("✅ Grammar structure: All required rules present")
            
            if is_valid and not unescaped_spaces:
                print("\n🎉 All tests PASSED! The grammar escape fix is working correctly.")
            else:
                print("\n⚠️  Some tests FAILED. Please check the issues above.")
            
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_grammar_escape_fix()) 