#!/usr/bin/env python3
"""
Debug script to show the exact GBNF grammar being generated and identify syntax errors.
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orac.homeassistant.client import HomeAssistantClient
from orac.homeassistant.config import HomeAssistantConfig
from orac.homeassistant.mapping_config import EntityMappingConfig
from orac.homeassistant.grammar_manager import HomeAssistantGrammarManager

async def debug_grammar_syntax():
    """Debug the GBNF grammar syntax issues."""
    
    print("=== Debugging GBNF Grammar Syntax ===\n")
    
    try:
        # Initialize Home Assistant components
        config = HomeAssistantConfig.from_yaml("orac/homeassistant/config.yaml")
        
        async with HomeAssistantClient(config) as client:
            # Initialize mapping config and grammar manager
            mapping_config = EntityMappingConfig(client=client)
            grammar_manager = HomeAssistantGrammarManager(client, mapping_config)
            
            print("Generating Home Assistant grammar...")
            
            # Generate grammar dictionary
            grammar_dict = await grammar_manager.generate_grammar()
            
            # Extract vocabulary for analysis
            device_vocab = grammar_dict.get("properties", {}).get("device", {}).get("enum", [])
            action_vocab = grammar_dict.get("properties", {}).get("action", {}).get("enum", [])
            location_vocab = grammar_dict.get("properties", {}).get("location", {}).get("enum", [])
            
            print(f"Vocabulary sizes: {len(device_vocab)} devices, {len(action_vocab)} actions, {len(location_vocab)} locations")
            print(f"Sample devices: {device_vocab[:3]}")
            print(f"Sample actions: {action_vocab[:3]}")
            print(f"Sample locations: {location_vocab[:3]}")
            
            # Generate GBNF grammar string
            gbnf_grammar = grammar_manager.generate_gbnf_grammar(grammar_dict)
            
            print(f"\nGBNF Grammar Length: {len(gbnf_grammar)} characters")
            print("\n=== FULL GBNF GRAMMAR ===")
            print(gbnf_grammar)
            print("=== END GBNF GRAMMAR ===")
            
            # Check for specific issues
            print("\n=== GRAMMAR ANALYSIS ===")
            
            # Check for problematic patterns
            issues = []
            
            # Check for unescaped quotes in vocabulary
            for device in device_vocab:
                if '"' in device:
                    issues.append(f"Device '{device}' contains unescaped quotes")
            
            for action in action_vocab:
                if '"' in action:
                    issues.append(f"Action '{action}' contains unescaped quotes")
            
            for location in location_vocab:
                if '"' in location:
                    issues.append(f"Location '{location}' contains unescaped quotes")
            
            # Check for problematic characters
            for device in device_vocab:
                if '\\' in device:
                    issues.append(f"Device '{device}' contains backslashes")
            
            # Check for empty strings
            if any(not d.strip() for d in device_vocab):
                issues.append("Empty device names found")
            
            if any(not a.strip() for a in action_vocab):
                issues.append("Empty action names found")
            
            if any(not l.strip() for l in location_vocab):
                issues.append("Empty location names found")
            
            # Check for spaces in rule names (should be camelCase)
            if ' ' in gbnf_grammar.split('::=')[0]:
                issues.append("Rule names contain spaces")
            
            # Report issues
            if issues:
                print("❌ Issues found:")
                for issue in issues:
                    print(f"   - {issue}")
            else:
                print("✅ No obvious syntax issues found")
            
            # Test with a minimal grammar first
            print("\n=== TESTING MINIMAL GRAMMAR ===")
            minimal_grammar = '''root ::= object
object ::= "{" ws devicestring ws "}"
devicestring ::= "\\"device\\"" ":" ws "\\"" devicevalue "\\""
devicevalue ::= "kitchen lights" | "bedroom lights"
ws ::= [ \\t\\n\\r]*'''
            
            print("Minimal grammar:")
            print(minimal_grammar)
            
            # Test the minimal grammar
            import subprocess
            import tempfile
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.gbnf', delete=False) as f:
                f.write(minimal_grammar)
                minimal_file = f.name
            
            try:
                cmd = [
                    "/app/third_party/llama_cpp/bin/llama-cli",
                    "-m", "/app/models/gguf/Qwen3-0.6B-Q4_K_M.gguf",
                    "-p", "turn on the kitchen lights",
                    "--grammar", minimal_file,
                    "-n", "10",
                    "--temp", "0.1"
                ]
                
                print(f"\nTesting minimal grammar...")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                print(f"Return code: {result.returncode}")
                if result.returncode == 0:
                    print("✅ Minimal grammar works!")
                    print(f"Output: {result.stdout}")
                else:
                    print("❌ Minimal grammar failed!")
                    print(f"Error: {result.stderr}")
                    
            finally:
                os.unlink(minimal_file)
            
            # Now test the full grammar
            print("\n=== TESTING FULL GRAMMAR ===")
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.gbnf', delete=False) as f:
                f.write(gbnf_grammar)
                full_file = f.name
            
            try:
                cmd = [
                    "/app/third_party/llama_cpp/bin/llama-cli",
                    "-m", "/app/models/gguf/Qwen3-0.6B-Q4_K_M.gguf",
                    "-p", "turn on the kitchen lights",
                    "--grammar", full_file,
                    "-n", "10",
                    "--temp", "0.1"
                ]
                
                print(f"Testing full grammar...")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                print(f"Return code: {result.returncode}")
                if result.returncode == 0:
                    print("✅ Full grammar works!")
                    print(f"Output: {result.stdout}")
                else:
                    print("❌ Full grammar failed!")
                    print(f"Error: {result.stderr}")
                    
            finally:
                os.unlink(full_file)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_grammar_syntax()) 