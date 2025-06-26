#!/usr/bin/env python3
"""
Test script for ORAC Smart Home Parser

This script demonstrates the smart home parser functionality integrated with
the ORAC LlamaCppClient, including both async and sync versions.
"""

import asyncio
import json
import sys
import os
from typing import List, Dict

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orac.smart_home_parser import (
    SmartHomeParser, 
    SmartHomeParserSync,
    parse_smart_home_command,
    parse_smart_home_command_sync
)

async def test_async_parser():
    """Test the async smart home parser."""
    
    print("🧪 Testing Async Smart Home Parser")
    print("=" * 50)
    
    # Check if model path is provided
    model_path = os.getenv("SMART_HOME_MODEL_PATH")
    if not model_path:
        print("❌ Error: SMART_HOME_MODEL_PATH environment variable not set")
        return False
    
    if not os.path.exists(model_path):
        print(f"❌ Error: Model file not found at {model_path}")
        return False
    
    # Test cases
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
            result = await parser.parse_command(test_case['input'])
            print(f"Actual:   {json.dumps(result)}")
            
            if result == test_case['expected']:
                print("✅ PASS")
                passed += 1
            else:
                print("❌ FAIL")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    # Test validation
    print(f"\n🔍 Testing validation...")
    for test_case in test_cases:
        validation_result = await parser.parse_and_validate(test_case['input'])
        print(f"Input: {validation_result['input']}")
        print(f"Valid: {validation_result['valid']}")
        if not validation_result['valid']:
            print(f"Error: {validation_result['error']}")
    
    # Test batch processing
    print(f"\n📦 Testing batch processing...")
    commands = [tc['input'] for tc in test_cases]
    batch_results = await parser.parse_commands_batch(commands)
    for cmd, result in zip(commands, batch_results):
        print(f"{cmd} -> {json.dumps(result)}")
    
    # Clean up
    await parser.close()
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    return passed == total

def test_sync_parser():
    """Test the synchronous smart home parser."""
    
    print("\n🧪 Testing Sync Smart Home Parser")
    print("=" * 50)
    
    # Check if model path is provided
    model_path = os.getenv("SMART_HOME_MODEL_PATH")
    if not model_path:
        print("❌ Error: SMART_HOME_MODEL_PATH environment variable not set")
        return False
    
    if not os.path.exists(model_path):
        print(f"❌ Error: Model file not found at {model_path}")
        return False
    
    # Test cases
    test_cases = [
        {
            "input": "Turn on the bathroom lights",
            "expected": {"action": "turn on", "device": "bathroom lights"}
        },
        {
            "input": "Turn off the kitchen lights", 
            "expected": {"action": "turn off", "device": "kitchen lights"}
        }
    ]
    
    # Initialize parser
    try:
        parser = SmartHomeParserSync(model_path=model_path)
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
    
    # Test convenience functions
    print(f"\n⚡ Testing convenience functions...")
    for test_case in test_cases:
        result = parse_smart_home_command_sync(test_case['input'], model_path)
        print(f"Convenience: {test_case['input']} -> {json.dumps(result)}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    return passed == total

async def test_convenience_functions():
    """Test the convenience functions."""
    
    print("\n⚡ Testing Convenience Functions")
    print("=" * 40)
    
    model_path = os.getenv("SMART_HOME_MODEL_PATH")
    if not model_path or not os.path.exists(model_path):
        print("❌ Error: Please set SMART_HOME_MODEL_PATH to a valid model file")
        return False
    
    test_input = "Turn on the bathroom lights"
    
    # Test async convenience function
    try:
        result = await parse_smart_home_command(test_input, model_path)
        print(f"Async convenience: {test_input} -> {json.dumps(result)}")
    except Exception as e:
        print(f"❌ Async convenience error: {e}")
    
    # Test sync convenience function
    try:
        result = parse_smart_home_command_sync(test_input, model_path)
        print(f"Sync convenience: {test_input} -> {json.dumps(result)}")
    except Exception as e:
        print(f"❌ Sync convenience error: {e}")
    
    return True

async def interactive_mode():
    """Run the parser in interactive mode."""
    
    model_path = os.getenv("SMART_HOME_MODEL_PATH")
    if not model_path or not os.path.exists(model_path):
        print("❌ Error: Please set SMART_HOME_MODEL_PATH to a valid model file")
        return
    
    parser = SmartHomeParser(model_path=model_path)
    
    print("🎮 Interactive Smart Home Parser (Async)")
    print("=" * 45)
    print("Type natural language commands to parse them into JSON")
    print("Type 'quit' or 'exit' to stop")
    print()
    
    try:
        while True:
            try:
                user_input = input("💬 Command: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                result = await parser.parse_command(user_input)
                validation = await parser.parse_and_validate(user_input)
                
                print(f"📤 Output: {json.dumps(result, indent=2)}")
                print(f"✅ Valid: {validation['valid']}")
                if not validation['valid']:
                    print(f"❌ Error: {validation['error']}")
                print()
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    finally:
        await parser.close()

def show_usage():
    """Show usage information."""
    print("ORAC Smart Home Parser Test Suite")
    print("=" * 35)
    print()
    print("Usage:")
    print("  python test_orac_smart_home_parser.py async      # Test async parser")
    print("  python test_orac_smart_home_parser.py sync       # Test sync parser")
    print("  python test_orac_smart_home_parser.py convenience # Test convenience functions")
    print("  python test_orac_smart_home_parser.py interactive # Interactive mode")
    print("  python test_orac_smart_home_parser.py all         # Run all tests")
    print("  python test_orac_smart_home_parser.py             # Show this help")
    print()
    print("Environment Variables:")
    print("  SMART_HOME_MODEL_PATH  Path to your GGUF model file")
    print()
    print("Examples:")
    print("  export SMART_HOME_MODEL_PATH=./models/qwen2.5-0.5b.gguf")
    print("  python test_orac_smart_home_parser.py all")
    print()

async def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "async":
            success = await test_async_parser()
            sys.exit(0 if success else 1)
        elif command == "sync":
            success = test_sync_parser()
            sys.exit(0 if success else 1)
        elif command == "convenience":
            success = await test_convenience_functions()
            sys.exit(0 if success else 1)
        elif command == "interactive":
            await interactive_mode()
        elif command == "all":
            print("🚀 Running All Tests")
            print("=" * 30)
            
            async_success = await test_async_parser()
            sync_success = test_sync_parser()
            convenience_success = await test_convenience_functions()
            
            all_success = async_success and sync_success and convenience_success
            print(f"\n🎯 Overall Results: {'✅ PASS' if all_success else '❌ FAIL'}")
            sys.exit(0 if all_success else 1)
        else:
            show_usage()
    else:
        show_usage()

if __name__ == "__main__":
    asyncio.run(main()) 