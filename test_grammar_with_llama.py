#!/usr/bin/env python3
"""
Test script to test the generated grammar with llama-cli.
"""

import asyncio
import subprocess
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orac.homeassistant.client import HomeAssistantClient
from orac.homeassistant.config import HomeAssistantConfig
from orac.homeassistant.grammar_manager import HomeAssistantGrammarManager

async def test_grammar_with_llama():
    """Test the generated grammar with llama-cli."""
    
    print("Testing generated grammar with llama-cli...")
    
    try:
        # Initialize Home Assistant components
        config = HomeAssistantConfig.from_yaml("orac/homeassistant/config.yaml")
        
        async with HomeAssistantClient(config) as client:
            # Initialize grammar manager
            grammar_manager = HomeAssistantGrammarManager(client)
            
            print("Generating grammar...")
            
            # Generate grammar dictionary
            grammar_dict = await grammar_manager.generate_grammar()
            
            # Generate GBNF grammar string
            gbnf_grammar = grammar_manager.generate_gbnf_grammar(grammar_dict)
            
            print(f"Grammar length: {len(gbnf_grammar)}")
            print("First 200 chars of grammar:")
            print(repr(gbnf_grammar[:200]))
            
            # Test with llama-cli
            print("\nTesting with llama-cli...")
            
            cmd = [
                "/app/third_party/llama_cpp/bin/llama-cli",
                "-m", "/app/models/gguf/distilgpt2.Q4_0.gguf",
                "-p", '{"device": "bedroom lights", "action": "turn on"}',
                "--grammar", gbnf_grammar,
                "-n", "1",
                "--temp", "0.1"
            ]
            
            print(f"Command: {' '.join(cmd[:6])} [GRAMMAR] {' '.join(cmd[7:])}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            print(f"Return code: {result.returncode}")
            print(f"STDOUT:\n{result.stdout}")
            print(f"STDERR:\n{result.stderr}")
            
            if result.returncode == 0:
                print("✅ Grammar test PASSED!")
            else:
                print("❌ Grammar test FAILED!")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_grammar_with_llama()) 