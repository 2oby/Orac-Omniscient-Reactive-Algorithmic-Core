#!/usr/bin/env python3
"""
Debug script to test GBNF grammar format and identify parsing issues.
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

async def debug_gbnf():
    """Debug the GBNF grammar format."""
    
    print("=== GBNF Grammar Format Debug ===\n")
    
    try:
        # Initialize Home Assistant components
        config = HomeAssistantConfig.from_yaml("orac/homeassistant/config.yaml")
        
        async with HomeAssistantClient(config) as client:
            # Initialize mapping config and grammar manager
            mapping_config = EntityMappingConfig(client=client)
            grammar_manager = HomeAssistantGrammarManager(client, mapping_config)
            
            print("1. Generating Grammar Dictionary...")
            
            # Generate grammar dictionary
            grammar_dict = await grammar_manager.generate_grammar()
            
            # Extract vocabulary
            device_vocab = grammar_dict.get("properties", {}).get("device", {}).get("enum", [])
            action_vocab = grammar_dict.get("properties", {}).get("action", {}).get("enum", [])
            location_vocab = grammar_dict.get("properties", {}).get("location", {}).get("enum", [])
            
            print(f"   - Device vocabulary: {len(device_vocab)} items")
            print(f"   - Action vocabulary: {len(action_vocab)} items")
            print(f"   - Location vocabulary: {len(location_vocab)} items")
            print()
            
            print("2. Generating GBNF Grammar...")
            
            # Generate GBNF grammar string
            gbnf_grammar = grammar_manager.generate_gbnf_grammar(grammar_dict)
            
            print("   - Full GBNF Grammar:")
            print("   " + "="*60)
            print(gbnf_grammar)
            print("   " + "="*60)
            print()
            
            print("3. Analyzing GBNF Grammar Issues...")
            
            # Check for common GBNF issues
            issues = []
            
            # Check for unescaped quotes in device values
            for device in device_vocab:
                if '"' in device:
                    issues.append(f"Device '{device}' contains unescaped quotes")
            
            # Check for unescaped quotes in action values
            for action in action_vocab:
                if '"' in action:
                    issues.append(f"Action '{action}' contains unescaped quotes")
            
            # Check for unescaped quotes in location values
            for location in location_vocab:
                if '"' in location:
                    issues.append(f"Location '{location}' contains unescaped quotes")
            
            # Check for very long alternation rules
            device_rule = f'device_value ::= {" | ".join([f\'"{d}"\' for d in device_vocab])}'
            if len(device_rule) > 1000:
                issues.append(f"Device value rule is very long ({len(device_rule)} chars)")
            
            action_rule = f'action_value ::= {" | ".join([f\'"{a}"\' for a in action_vocab])}'
            if len(action_rule) > 2000:
                issues.append(f"Action value rule is very long ({len(action_rule)} chars)")
            
            # Check for special characters that might cause issues
            special_chars = ['\n', '\r', '\t']
            for char in special_chars:
                for device in device_vocab:
                    if char in device:
                        issues.append(f"Device '{device}' contains special character '{repr(char)}'")
                for action in action_vocab:
                    if char in action:
                        issues.append(f"Action '{action}' contains special character '{repr(char)}'")
                for location in location_vocab:
                    if char in location:
                        issues.append(f"Location '{location}' contains special character '{repr(char)}'")
            
            if issues:
                print("   ❌ Found potential GBNF issues:")
                for issue in issues:
                    print(f"     • {issue}")
            else:
                print("   ✅ No obvious GBNF format issues found")
            print()
            
            print("4. Testing Simplified Grammar...")
            
            # Create a simplified grammar with just a few devices
            simplified_devices = ["bedroom lights", "bathroom lights"]
            simplified_actions = ["turn on", "turn off"]
            simplified_locations = ["bedroom", "bathroom"]
            
            simplified_grammar = f"""root ::= object

object ::= "{{" ws (string ":" ws value ("," ws string ":" ws value)*)? ws "}}"

value ::= object | array | string | number | boolean | null

array ::= "[" ws (value ("," ws value)*)? ws "]"

string ::= device_string | action_string | location_string | generic_string

device_string ::= "\\"device\\"" ":" ws "\\"" device_value "\\""
action_string ::= "\\"action\\"" ":" ws "\\"" action_value "\\""
location_string ::= "\\"location\\"" ":" ws "\\"" location_value "\\""
generic_string ::= "\\"" ([^"\\\\] | "\\\\" (["\\\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F]))* "\\""

device_value ::= {" | ".join([f'"{d}"' for d in simplified_devices])}
action_value ::= {" | ".join([f'"{a}"' for a in simplified_actions])}
location_value ::= {" | ".join([f'"{l}"' for l in simplified_locations])}

number ::= "-"? ([0-9] | [1-9] [0-9]*) ("." [0-9]+)? ([eE] [-+]? [0-9]+)?

boolean ::= "true" | "false"

null ::= "null"

ws ::= [ \\t\\n\\r]*
"""
            
            print("   - Simplified GBNF Grammar:")
            print("   " + "="*60)
            print(simplified_grammar)
            print("   " + "="*60)
            print()
            
            print("5. Recommendations...")
            print("   - Try using the simplified grammar first")
            print("   - Check llama.cpp version and GBNF support")
            print("   - Verify grammar syntax with llama.cpp documentation")
            print("   - Consider reducing vocabulary size if rules are too long")
            print()
            
            print("=== GBNF Debug Complete ===")
            
    except Exception as e:
        print(f"Error during debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_gbnf()) 