#!/usr/bin/env python3
"""
Test script for temperature grammar functionality.
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orac.llama_cpp_client import LlamaCppClient
from orac.config import load_favorites

async def test_temperature_grammar():
    """Test temperature commands with the grammar."""
    print("=== Testing Temperature Grammar ===\n")
    
    client = None
    try:
        # Initialize client
        client = LlamaCppClient()
        await client.__aenter__()
        
        # Get default model
        favorites = load_favorites()
        model = favorites['default_model']
        print(f"Using model: {model}")
        
        # Test temperature commands
        test_prompts = [
            "set the bedroom temperature to 22 degrees",
            "set bathroom heating to 20C",
            "set kitchen temperature to 25 degrees",
            "turn on bedroom heating",
            "set living room temp to 18C"
        ]
        
        for prompt in test_prompts:
            print(f"\nTesting: '{prompt}'")
            try:
                response = await client.generate(
                    model=model,
                    prompt=prompt,
                    json_mode=True,
                    grammar_file='/app/data/test_grammars/default.gbnf',
                    temperature=0.1,
                    top_p=0.9,
                    top_k=10,
                    max_tokens=50
                )
                print(f"Response: {response.response}")
                
                # Try to parse JSON to validate
                import json
                try:
                    parsed = json.loads(response.response)
                    print(f"✅ Valid JSON: {parsed}")
                    
                    # Check if temperature was captured
                    if 'set' in parsed.get('action', '') and 'C' in parsed.get('action', ''):
                        print(f"✅ Temperature detected: {parsed['action']}")
                    elif parsed.get('device') == 'heating':
                        print(f"✅ Heating device detected")
                    else:
                        print(f"⚠️  No temperature action detected")
                        
                except json.JSONDecodeError:
                    print(f"❌ Invalid JSON: {response.response}")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                
    except Exception as e:
        print(f"❌ Setup error: {e}")
    finally:
        if client:
            await client.__aexit__(None, None, None)

if __name__ == "__main__":
    asyncio.run(test_temperature_grammar()) 