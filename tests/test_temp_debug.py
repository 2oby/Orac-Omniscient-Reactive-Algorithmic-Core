#!/usr/bin/env python3
"""
Debug script to test temperature command parsing.
"""

import requests
import json

API_BASE_URL = "http://localhost:8000"

# Test specific temperature commands
test_commands = [
    "set heating to 22C",
    "set thermostat to 18C", 
    "set temperature to 25C",
    "set to 7C",
    "set heating to 20C",
    "set kitchen heating to 20C"
]

print("🔍 Temperature Command Debug Test")
print("=" * 50)

for i, command in enumerate(test_commands, 1):
    print(f"\n📝 Test {i}: {command}")
    print("-" * 40)
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/v1/generate",
            json={
                "prompt": command,
                "json_mode": True,
                "grammar_file": "data/test_grammars/set_temp.gbnf",
                "temperature": 0.1,
                "top_p": 0.9,
                "top_k": 10,
                "max_tokens": 50
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            api_output = result.get("response", "")
            print(f"✅ API Response: {api_output}")
            
            # Try to parse as JSON
            try:
                parsed = json.loads(api_output)
                print(f"✅ Valid JSON: {parsed}")
                
                # Check if it's a temperature command
                action = parsed.get("action", "")
                if "set" in action and ("C" in action or "%" in action):
                    print(f"🌡️  Temperature/Percentage detected: {action}")
                else:
                    print(f"❌ No temperature/percentage in action: {action}")
                    
            except json.JSONDecodeError:
                print(f"❌ Invalid JSON: {api_output}")
        else:
            print(f"❌ API Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

print("\n" + "=" * 50)
print("🎯 Debug test complete!") 