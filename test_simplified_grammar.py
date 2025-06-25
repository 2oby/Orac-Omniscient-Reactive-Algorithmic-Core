#!/usr/bin/env python3
"""
Test script to verify simplified GBNF grammar works with llama.cpp.
"""

import subprocess
import sys
import os

def test_simplified_grammar():
    """Test simplified grammar with llama-cli."""
    
    print("Testing simplified GBNF grammar with llama-cli...")
    
    # Test 1: Simplified device grammar (no underscores in rule names)
    print("\n=== Test 1: Simplified Device Grammar ===")
    simplified_grammar = '''root ::= object
object ::= "{" ws devicestring "," ws actionstring ws "}"
devicestring ::= "\\"device\\"" ":" ws "\\"" devicevalue "\\""
actionstring ::= "\\"action\\"" ":" ws "\\"" actionvalue "\\""
devicevalue ::= "bedroom lights" | "bathroom lights" | "kitchen lights"
actionvalue ::= "turn on" | "turn off" | "toggle"
ws ::= [ \\t\\n\\r]*'''
    
    cmd = [
        "/app/third_party/llama_cpp/bin/llama-cli",
        "-m", "/app/models/gguf/distilgpt2.Q4_0.gguf",
        "-p", '{"device": "bedroom lights", "action": "turn on"}',
        "--grammar", simplified_grammar,
        "-n", "1",
        "--temp", "0.1"
    ]
    
    print(f"Command: {' '.join(cmd[:6])} [GRAMMAR] {' '.join(cmd[7:])}")
    print(f"Grammar length: {len(simplified_grammar)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    
    print(f"Return code: {result.returncode}")
    if result.returncode == 0:
        print("✅ Simplified grammar test PASSED!")
        print(f"Output: {result.stdout.strip()}")
    else:
        print("❌ Simplified grammar test FAILED!")
        print(f"STDERR: {result.stderr}")
    
    # Test 2: Even simpler grammar with minimal vocabulary
    print("\n=== Test 2: Minimal Vocabulary Grammar ===")
    minimal_grammar = '''root ::= object
object ::= "{" ws devicestring "," ws actionstring ws "}"
devicestring ::= "\\"device\\"" ":" ws "\\"" devicevalue "\\""
actionstring ::= "\\"action\\"" ":" ws "\\"" actionvalue "\\""
devicevalue ::= "bedroom" | "kitchen" | "bathroom"
actionvalue ::= "on" | "off" | "toggle"
ws ::= [ \\t\\n\\r]*'''
    
    cmd = [
        "/app/third_party/llama_cpp/bin/llama-cli",
        "-m", "/app/models/gguf/distilgpt2.Q4_0.gguf",
        "-p", '{"device": "bedroom", "action": "on"}',
        "--grammar", minimal_grammar,
        "-n", "1",
        "--temp", "0.1"
    ]
    
    print(f"Command: {' '.join(cmd[:6])} [GRAMMAR] {' '.join(cmd[7:])}")
    print(f"Grammar length: {len(minimal_grammar)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    
    print(f"Return code: {result.returncode}")
    if result.returncode == 0:
        print("✅ Minimal grammar test PASSED!")
        print(f"Output: {result.stdout.strip()}")
    else:
        print("❌ Minimal grammar test FAILED!")
        print(f"STDERR: {result.stderr}")
    
    # Test 3: Test the actual Home Assistant grammar generation
    print("\n=== Test 3: Home Assistant Grammar Generation ===")
    
    try:
        # Import and test the grammar manager
        sys.path.insert(0, '/app')
        from orac.homeassistant.client import HomeAssistantClient
        from orac.homeassistant.config import HomeAssistantConfig
        from orac.homeassistant.mapping_config import EntityMappingConfig
        from orac.homeassistant.grammar_manager import HomeAssistantGrammarManager
        
        # Initialize components
        config = HomeAssistantConfig.from_yaml("orac/homeassistant/config.yaml")
        
        async def test_ha_grammar():
            async with HomeAssistantClient(config) as client:
                mapping_config = EntityMappingConfig(client=client)
                grammar_manager = HomeAssistantGrammarManager(client, mapping_config)
                
                # Generate grammar
                grammar_dict = await grammar_manager.generate_grammar()
                gbnf_grammar = grammar_manager.generate_gbnf_grammar(grammar_dict)
                
                print(f"Generated grammar length: {len(gbnf_grammar)}")
                print("Generated grammar:")
                print(gbnf_grammar)
                
                # Test the generated grammar
                cmd = [
                    "/app/third_party/llama_cpp/bin/llama-cli",
                    "-m", "/app/models/gguf/distilgpt2.Q4_0.gguf",
                    "-p", '{"device": "bedroom lights", "action": "turn on"}',
                    "--grammar", gbnf_grammar,
                    "-n", "1",
                    "--temp", "0.1"
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                print(f"Return code: {result.returncode}")
                if result.returncode == 0:
                    print("✅ Home Assistant grammar test PASSED!")
                    print(f"Output: {result.stdout.strip()}")
                else:
                    print("❌ Home Assistant grammar test FAILED!")
                    print(f"STDERR: {result.stderr}")
        
        import asyncio
        asyncio.run(test_ha_grammar())
        
    except Exception as e:
        print(f"❌ Error testing Home Assistant grammar: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simplified_grammar() 