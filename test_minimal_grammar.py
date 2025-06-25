#!/usr/bin/env python3
"""
Minimal grammar test for Qwen3-0.6B model.
Tests if the model can respect basic GBNF constraints.
"""

import asyncio
import json
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orac.llama_cpp_client import LlamaCppClient

async def test_minimal_grammar():
    """Test minimal grammar with Qwen3-0.6B model."""
    
    print("=== Minimal Grammar Test with Qwen3-0.6B ===\n")
    
    # Initialize client
    model_path = "/app/models/gguf"
    client = LlamaCppClient(model_path=model_path)
    
    # Test 1: Very simple grammar - just device names
    print("Test 1: Simple device selection")
    print("-" * 50)
    
    simple_grammar = '''root ::= object
object ::= "{" ws devicestring ws "}"
devicestring ::= "\\"device\\"" ":" ws "\\"" devicevalue "\\""
devicevalue ::= "kitchen lights" | "bedroom lights" | "bathroom lights"
ws ::= [ \\t\\n\\r]*'''
    
    system_prompt = "You are a JSON formatter. Respond with a JSON object containing only a 'device' field. Use only the allowed device names."
    
    try:
        response = await client.generate_with_custom_grammar(
            prompt="turn on the kitchen lights",
            model="Qwen3-0.6B-Q4_K_M.gguf",
            custom_grammar=simple_grammar,
            system_prompt=system_prompt,
            temperature=0.1,
            top_p=0.8,
            top_k=30,
            max_tokens=50
        )
        
        print(f"Grammar:\n{simple_grammar}")
        print(f"Prompt: 'turn on the kitchen lights'")
        print(f"Response: {response.text}")
        print(f"Success: {'✅' if 'kitchen lights' in response.text else '❌'}")
        
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "="*80 + "\n")
    
    # Test 2: Device + Action grammar
    print("Test 2: Device + Action selection")
    print("-" * 50)
    
    device_action_grammar = '''root ::= object
object ::= "{" ws devicestring "," ws actionstring ws "}"
devicestring ::= "\\"device\\"" ":" ws "\\"" devicevalue "\\""
actionstring ::= "\\"action\\"" ":" ws "\\"" actionvalue "\\""
devicevalue ::= "kitchen lights" | "bedroom lights"
actionvalue ::= "turn on" | "turn off"
ws ::= [ \\t\\n\\r]*'''
    
    system_prompt = "You are a JSON formatter. Respond with a JSON object containing 'device' and 'action' fields. Use only the allowed values."
    
    try:
        response = await client.generate_with_custom_grammar(
            prompt="turn on the kitchen lights",
            model="Qwen3-0.6B-Q4_K_M.gguf",
            custom_grammar=device_action_grammar,
            system_prompt=system_prompt,
            temperature=0.1,
            top_p=0.8,
            top_k=30,
            max_tokens=50
        )
        
        print(f"Grammar:\n{device_action_grammar}")
        print(f"Prompt: 'turn on the kitchen lights'")
        print(f"Response: {response.text}")
        
        # Check if response contains expected values
        success = True
        if 'kitchen lights' not in response.text:
            print("❌ Missing 'kitchen lights'")
            success = False
        if 'turn on' not in response.text:
            print("❌ Missing 'turn on'")
            success = False
        if 'turn_on' in response.text:
            print("❌ Contains 'turn_on' (should be 'turn on')")
            success = False
        if 'kitchen_lights' in response.text:
            print("❌ Contains 'kitchen_lights' (should be 'kitchen lights')")
            success = False
            
        print(f"Success: {'✅' if success else '❌'}")
        
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "="*80 + "\n")
    
    # Test 3: Full Home Assistant grammar (simplified)
    print("Test 3: Full Home Assistant grammar (simplified)")
    print("-" * 50)
    
    full_grammar = '''root ::= object
object ::= "{" ws devicestring "," ws actionstring "," ws locationstring ws "}"
devicestring ::= "\\"device\\"" ":" ws "\\"" devicevalue "\\""
actionstring ::= "\\"action\\"" ":" ws "\\"" actionvalue "\\""
locationstring ::= "\\"location\\"" ":" ws "\\"" locationvalue "\\""
devicevalue ::= "kitchen lights" | "bedroom lights" | "bathroom lights"
actionvalue ::= "turn on" | "turn off" | "toggle"
locationvalue ::= "kitchen" | "bedroom" | "bathroom"
ws ::= [ \\t\\n\\r]*'''
    
    system_prompt = """You are a Home Assistant command processor. Respond with a JSON object containing:
- device: the device name (from allowed list)
- action: the action to perform (from allowed list)  
- location: the location (from allowed list)

Use only the allowed values. Do not use underscores."""
    
    try:
        response = await client.generate_with_custom_grammar(
            prompt="turn on the kitchen lights",
            model="Qwen3-0.6B-Q4_K_M.gguf",
            custom_grammar=full_grammar,
            system_prompt=system_prompt,
            temperature=0.1,
            top_p=0.8,
            top_k=30,
            max_tokens=100
        )
        
        print(f"Grammar:\n{full_grammar}")
        print(f"Prompt: 'turn on the kitchen lights'")
        print(f"Response: {response.text}")
        
        # Check if response contains expected values
        success = True
        if 'kitchen lights' not in response.text:
            print("❌ Missing 'kitchen lights'")
            success = False
        if 'turn on' not in response.text:
            print("❌ Missing 'turn on'")
            success = False
        if 'kitchen' not in response.text:
            print("❌ Missing 'kitchen' location")
            success = False
        if 'turn_on' in response.text:
            print("❌ Contains 'turn_on' (should be 'turn on')")
            success = False
        if 'kitchen_lights' in response.text:
            print("❌ Contains 'kitchen_lights' (should be 'kitchen lights')")
            success = False
            
        print(f"Success: {'✅' if success else '❌'}")
        
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "="*80 + "\n")
    
    # Test 4: Test with different model (distilgpt2)
    print("Test 4: Compare with distilgpt2 model")
    print("-" * 50)
    
    try:
        response = await client.generate_with_custom_grammar(
            prompt="turn on the kitchen lights",
            model="distilgpt2.Q4_0.gguf",
            custom_grammar=full_grammar,
            system_prompt=system_prompt,
            temperature=0.1,
            top_p=0.8,
            top_k=30,
            max_tokens=100
        )
        
        print(f"Model: distilgpt2.Q4_0.gguf")
        print(f"Prompt: 'turn on the kitchen lights'")
        print(f"Response: {response.text}")
        
        # Check if response contains expected values
        success = True
        if 'kitchen lights' not in response.text:
            print("❌ Missing 'kitchen lights'")
            success = False
        if 'turn on' not in response.text:
            print("❌ Missing 'turn on'")
            success = False
        if 'turn_on' in response.text:
            print("❌ Contains 'turn_on' (should be 'turn on')")
            success = False
        if 'kitchen_lights' in response.text:
            print("❌ Contains 'kitchen_lights' (should be 'kitchen lights')")
            success = False
            
        print(f"Success: {'✅' if success else '❌'}")
        
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_minimal_grammar()) 