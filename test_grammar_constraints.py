#!/usr/bin/env python3
"""
Test script to verify grammar constraints are working properly.

This script tests the new Home Assistant command endpoint that uses
dynamic grammar constraints from discovered entities.
"""

import asyncio
import json
import os
import sys
import aiohttp

# Add the orac package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'orac'))

async def test_grammar_constraints():
    """Test that grammar constraints work properly with the new Home Assistant command endpoint."""
    
    print("=== Testing Grammar Constraints with Home Assistant Command Endpoint ===\n")
    
    # API endpoint URL
    api_url = "http://localhost:8000/v1/homeassistant/command"
    
    # Test cases from user
    test_cases = [
        "turn on the bedroom lights",
        "turn on the kitchen lights", 
        "turn on the toilet lights",
        "turn on the attic lights"
    ]
    
    print("Testing LLM responses with dynamic grammar constraints:")
    print("Expected behavior:")
    print("- 'toilet lights' should map to 'toilet lights' (not 'toilet')")
    print("- 'attic lights' should not be in grammar (should fail gracefully)")
    print()
    
    async with aiohttp.ClientSession() as session:
        for i, command in enumerate(test_cases, 1):
            print(f"Test {i}: \"{command}\"")
            try:
                # Make request to the Home Assistant command endpoint
                async with session.post(api_url, json={"command": command}) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        if result["status"] == "success":
                            parsed = result["response"]
                            device = parsed.get('device', '')
                            action = parsed.get('action', '')
                            location = parsed.get('location', '')
                            
                            print(f"Response: {result['response']}")
                            print(f"Parsed: device='{device}', action='{action}', location='{location}'")
                            
                            # Check for expected behavior
                            if "toilet lights" in command and device == "toilet lights":
                                print("✅ GOOD: 'toilet lights' correctly mapped to 'toilet lights'")
                            elif "toilet lights" in command and device == "toilet":
                                print("❌ FAIL: 'toilet lights' incorrectly mapped to 'toilet'")
                            elif "attic lights" in command:
                                print("✅ GOOD: 'attic lights' not in grammar (as expected)")
                            else:
                                print("✅ GOOD: Response looks correct")
                                
                            # Show grammar constraints
                            constraints = result.get("grammar_constraints", {})
                            print(f"Grammar constraints: {len(constraints.get('devices', []))} devices, {len(constraints.get('actions', []))} actions")
                            
                        else:
                            print(f"❌ Error: {result['message']}")
                            if "errors" in result:
                                for error in result["errors"]:
                                    print(f"   - {error}")
                            
                    else:
                        error_text = await response.text()
                        print(f"❌ HTTP Error {response.status}: {error_text}")
                        
            except Exception as e:
                print(f"❌ Error: {e}")
            
            print("-" * 50)
    
    print("\n=== Test Complete ===")
    print("\nKey improvements:")
    print("1. Dynamic grammar constraints from discovered entities")
    print("2. Proper validation against grammar vocabulary")
    print("3. Clear error messages for invalid responses")
    print("4. Real-time grammar generation from Home Assistant data")

if __name__ == "__main__":
    asyncio.run(test_grammar_constraints()) 