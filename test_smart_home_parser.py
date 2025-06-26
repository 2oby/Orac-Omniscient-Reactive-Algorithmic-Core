#!/usr/bin/env python3
"""
Test script for Smart Home JSON Grammar Implementation

This script demonstrates the smart home parser functionality by:
1. Testing the parser with various natural language commands
2. Showing the expected vs actual outputs
3. Providing a CLI interface for interactive testing
"""

import json
import sys
import os
from smart_home_parser import SmartHomeParser

def test_parser():
    """Test the smart home parser with predefined test cases."""
    
    # Test cases from the requirements
    test_cases = [
        {
            "input": "Turn on the bathroom lights",
            "expected": {"action": "turn on", "device": "bathroom lights"}
        },
        {
            "input": "Turn off the kitchen lights", 
            "expected": {"action": "turn off", "device": "kitchen lights"}
        },
        {
            "input": "Toggle bedroom lights",
            "expected": {"action": "toggle", "device": "bedroom lights"}
        },
        {
            "input": "turn on living room lights",
            "expected": {"action": "turn on", "device": "living room lights"}
        }
    ]
    
    print("🧪 Testing Smart Home Parser")
    print("=" * 50)
    
    # Check if model path is provided
    model_path = os.getenv("SMART_HOME_MODEL_PATH")
    if not model_path:
        print("❌ Error: SMART_HOME_MODEL_PATH environment variable not set")
        print("Please set it to the path of your GGUF model file")
        print("Example: export SMART_HOME_MODEL_PATH=./models/model.gguf")
        return False
    
    if not os.path.exists(model_path):
        print(f"❌ Error: Model file not found at {model_path}")
        return False
    
    # Initialize parser
    try:
        parser = SmartHomeParser(model_path=model_path)
        print(f"✅ Parser initialized with model: {model_path}")
    except Exception as e:
        print(f"❌ Error initializing parser: {e}")
        return False
    
    # Run test cases
    passed = 0
    total = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}/{total}")
        print(f"Input: {test_case['input']}")
        print(f"Expected: {json.dumps(test_case['expected'])}")
        
        try:
            result = parser.parse_command(test_case['input'])
            print(f"Actual:   {json.dumps(result)}")
            
            if result == test_case['expected']:
                print("✅ PASS")
                passed += 1
            else:
                print("❌ FAIL")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    return passed == total

def interactive_mode():
    """Run the parser in interactive mode for manual testing."""
    
    model_path = os.getenv("SMART_HOME_MODEL_PATH")
    if not model_path or not os.path.exists(model_path):
        print("❌ Error: Please set SMART_HOME_MODEL_PATH to a valid model file")
        return
    
    parser = SmartHomeParser(model_path=model_path)
    
    print("🎮 Interactive Smart Home Parser")
    print("=" * 40)
    print("Type natural language commands to parse them into JSON")
    print("Type 'quit' or 'exit' to stop")
    print()
    
    while True:
        try:
            user_input = input("💬 Command: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not user_input:
                continue
            
            result = parser.parse_command(user_input)
            print(f"📤 Output: {json.dumps(result, indent=2)}")
            print()
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def show_usage():
    """Show usage information."""
    print("Smart Home JSON Grammar Parser")
    print("=" * 35)
    print()
    print("Usage:")
    print("  python test_smart_home_parser.py test     # Run automated tests")
    print("  python test_smart_home_parser.py interactive  # Run interactive mode")
    print("  python test_smart_home_parser.py          # Show this help")
    print()
    print("Environment Variables:")
    print("  SMART_HOME_MODEL_PATH  Path to your GGUF model file")
    print()
    print("Examples:")
    print("  export SMART_HOME_MODEL_PATH=./models/qwen2.5-0.5b.gguf")
    print("  python test_smart_home_parser.py test")
    print()

def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "test":
            success = test_parser()
            sys.exit(0 if success else 1)
        elif command in ["interactive", "i"]:
            interactive_mode()
        else:
            show_usage()
    else:
        show_usage()

if __name__ == "__main__":
    main() 