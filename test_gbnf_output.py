#!/usr/bin/env python3
"""
Test script to check GBNF grammar generation and test it directly.
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

async def test_gbnf_generation():
    """Test GBNF grammar generation and output."""
    
    print("=== Testing GBNF Grammar Generation ===\n")
    
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
            print("\nFirst 500 characters of GBNF grammar:")
            print("-" * 50)
            print(gbnf_grammar[:500])
            print("-" * 50)
            
            # Check if the grammar contains the expected values
            print("\nChecking for expected values in grammar:")
            print(f"Contains 'kitchen lights': {'kitchen lights' in gbnf_grammar}")
            print(f"Contains 'turn on': {'turn on' in gbnf_grammar}")
            print(f"Contains 'turn_on': {'turn_on' in gbnf_grammar}")
            
            # Test the grammar with llama-cli directly
            print("\n=== Testing with llama-cli ===")
            
            import subprocess
            import tempfile
            
            # Create a temporary file for the grammar
            with tempfile.NamedTemporaryFile(mode='w', suffix='.gbnf', delete=False) as f:
                f.write(gbnf_grammar)
                grammar_file = f.name
            
            try:
                # Test command
                cmd = [
                    "/app/third_party/llama_cpp/bin/llama-cli",
                    "-m", "/app/models/gguf/Qwen3-0.6B-Q4_K_M.gguf",
                    "-p", "turn on the kitchen lights",
                    "--grammar", grammar_file,
                    "-n", "50",
                    "--temp", "0.1",
                    "--repeat-penalty", "1.1"
                ]
                
                print(f"Running: {' '.join(cmd[:6])} [GRAMMAR_FILE] {' '.join(cmd[7:])}")
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                print(f"Return code: {result.returncode}")
                print(f"STDOUT:\n{result.stdout}")
                print(f"STDERR:\n{result.stderr}")
                
                if result.returncode == 0:
                    print("✅ Grammar test with llama-cli successful!")
                else:
                    print("❌ Grammar test with llama-cli failed!")
                    
            finally:
                # Clean up temporary file
                os.unlink(grammar_file)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_gbnf_generation()) 