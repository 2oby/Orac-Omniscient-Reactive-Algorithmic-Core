#!/usr/bin/env python3
"""
Smart Home Parser Demo

This script demonstrates the smart home parser functionality with mock responses
to show how the system works without requiring an actual model.
"""

import json
import sys
import os

def mock_parse_command(user_input: str) -> dict:
    """
    Mock parser that simulates the smart home parser behavior.
    
    This function demonstrates what the real parser would return
    without requiring an actual model file.
    """
    
    # Simple keyword matching for demonstration
    user_input_lower = user_input.lower()
    
    # Extract action
    if "turn on" in user_input_lower or "switch on" in user_input_lower:
        action = "turn on"
    elif "turn off" in user_input_lower or "switch off" in user_input_lower:
        action = "turn off"
    elif "toggle" in user_input_lower:
        action = "toggle"
    else:
        return {"action": "error", "device": "unknown"}
    
    # Extract device
    if "bathroom" in user_input_lower and "light" in user_input_lower:
        device = "bathroom lights"
    elif "bedroom" in user_input_lower and "light" in user_input_lower:
        device = "bedroom lights"
    elif "kitchen" in user_input_lower and "light" in user_input_lower:
        device = "kitchen lights"
    elif "living room" in user_input_lower and "light" in user_input_lower:
        device = "living room lights"
    else:
        return {"action": "error", "device": "unknown"}
    
    return {"action": action, "device": device}

def validate_command(parsed_result: dict) -> bool:
    """Validate that a parsed result contains valid action and device."""
    valid_actions = {"turn on", "turn off", "toggle"}
    valid_devices = {
        "bedroom lights", "bathroom lights", 
        "kitchen lights", "living room lights"
    }
    
    action = parsed_result.get("action")
    device = parsed_result.get("device")
    
    return (action in valid_actions and device in valid_devices)

def demo_basic_parsing():
    """Demonstrate basic command parsing."""
    print("🧪 Smart Home Parser Demo")
    print("=" * 40)
    print()
    
    # Test cases
    test_cases = [
        "Turn on the bathroom lights",
        "Turn off the kitchen lights",
        "Toggle bedroom lights",
        "turn on living room lights",
        "switch off bathroom lights",
        "Invalid command"
    ]
    
    print("📝 Testing Command Parsing:")
    print("-" * 30)
    
    for i, command in enumerate(test_cases, 1):
        print(f"\n{i}. Input: {command}")
        
        # Parse the command
        result = mock_parse_command(command)
        print(f"   Output: {json.dumps(result)}")
        
        # Validate the result
        is_valid = validate_command(result)
        print(f"   Valid: {'✅ Yes' if is_valid else '❌ No'}")
        
        if is_valid:
            print(f"   Action: {result['action']}")
            print(f"   Device: {result['device']}")

def demo_grammar_structure():
    """Demonstrate the grammar structure."""
    print("\n🧠 Grammar Structure:")
    print("-" * 25)
    
    grammar = """
root ::= ws action_value "," ws "\"device\"" ws ":" ws device_value ws "}"

action_value ::= "\"" action "\""
device_value ::= "\"" device "\""

action ::= "turn on" | "turn off" | "toggle"

device ::= "bedroom lights" | "bathroom lights" | "kitchen lights" | "living room lights"

ws ::= [ \t\n]*
"""
    
    print("GBNF Grammar:")
    print(grammar)
    
    print("This grammar ensures:")
    print("• Only valid actions are allowed (turn on, turn off, toggle)")
    print("• Only valid devices are allowed (bedroom lights, bathroom lights, etc.)")
    print("• Output is always valid JSON with exactly 'action' and 'device' keys")
    print("• Whitespace is properly handled")

def demo_system_prompt():
    """Demonstrate the system prompt."""
    print("\n🔧 System Prompt:")
    print("-" * 20)
    
    system_prompt = """You are a JSON-only formatter. For each user input, respond with a single-line JSON object containing exactly these keys: "action" and "device". Do not include any explanations, comments, or additional text. Only output the JSON object."""
    
    print(system_prompt)
    print()
    print("This prompt ensures:")
    print("• The model outputs only JSON")
    print("• No explanations or commentary")
    print("• Consistent structure with required keys")

def demo_integration_example():
    """Demonstrate integration with Home Assistant."""
    print("\n🏠 Home Assistant Integration Example:")
    print("-" * 40)
    
    # Example parsed result
    parsed = {"action": "turn on", "device": "bathroom lights"}
    
    print(f"Parsed command: {json.dumps(parsed)}")
    print()
    
    # Device mapping
    device_mapping = {
        "bathroom lights": [
            "light.bathroom_main",
            "light.bathroom_mirror"
        ]
    }
    
    print("Device mapping:")
    for generic, entities in device_mapping.items():
        print(f"  '{generic}' -> {entities}")
    
    print()
    
    # Action mapping
    action_mapping = {
        "turn on": "light.turn_on",
        "turn off": "light.turn_off",
        "toggle": "light.toggle"
    }
    
    print("Action mapping:")
    for action, service in action_mapping.items():
        print(f"  '{action}' -> {service}")
    
    print()
    
    # Example service call
    device = parsed["device"]
    action = parsed["action"]
    
    if device in device_mapping and action in action_mapping:
        entities = device_mapping[device]
        service = action_mapping[action]
        
        print("Resulting Home Assistant service calls:")
        for entity in entities:
            service_call = {
                "service": service,
                "target": {"entity_id": entity}
            }
            print(f"  {json.dumps(service_call, indent=2)}")

def demo_usage_examples():
    """Show usage examples."""
    print("\n💡 Usage Examples:")
    print("-" * 20)
    
    examples = [
        {
            "description": "Basic command parsing",
            "code": """
from smart_home_parser import SmartHomeParser

parser = SmartHomeParser("./models/model.gguf")
result = await parser.parse_command("Turn on the bathroom lights")
print(result)  # {"action": "turn on", "device": "bathroom lights"}
"""
        },
        {
            "description": "CLI usage",
            "code": """
# Set model path
export SMART_HOME_MODEL_PATH=./models/qwen2.5-0.5b.gguf

# Parse a command
python smart_home_cli.py "Turn on the bathroom lights"

# Interactive mode
python smart_home_cli.py --interactive
"""
        },
        {
            "description": "Batch processing",
            "code": """
commands = [
    "Turn on the bathroom lights",
    "toggle kitchen lights",
    "Turn off bedroom lights"
]

results = await parser.parse_commands_batch(commands)
for cmd, result in zip(commands, results):
    print(f"{cmd} -> {result}")
"""
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['description']}:")
        print(example['code'])

def main():
    """Run the demo."""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Smart Home Parser Demo")
        print("=" * 25)
        print()
        print("This demo shows how the smart home parser works without requiring a model.")
        print()
        print("Usage:")
        print("  python demo_smart_home_parser.py          # Run full demo")
        print("  python demo_smart_home_parser.py --help   # Show this help")
        return
    
    # Run all demo sections
    demo_basic_parsing()
    demo_grammar_structure()
    demo_system_prompt()
    demo_integration_example()
    demo_usage_examples()
    
    print("\n" + "=" * 50)
    print("🎉 Demo Complete!")
    print()
    print("To use the real parser:")
    print("1. Set SMART_HOME_MODEL_PATH to your GGUF model")
    print("2. Run: python test_smart_home_parser.py test")
    print("3. Or use: python smart_home_cli.py --interactive")
    print()
    print("For more information, see SMART_HOME_GRAMMAR_README.md")

if __name__ == "__main__":
    main() 