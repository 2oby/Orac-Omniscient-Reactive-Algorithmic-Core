#!/usr/bin/env python3
"""
Basic Grammar Testing Script for Orac

This script tests grammar functionality with llama.cpp using simple subprocess calls.
It's designed to be run independently to validate grammar constraints work correctly.

Usage:
    docker exec orac python test_grammar_basic.py
"""

import subprocess
import json
import os
import sys
from pathlib import Path

# Configuration
LLAMA_CLI_PATH = "/app/third_party/llama_cpp/bin/llama-cli"
MODELS_PATH = "/models/gguf"
TEST_GRAMMARS_PATH = "/app/data/test_grammars"

# Test cases
HELLO_WORLD_TESTS = [
    "say hello",
    "say world", 
    "hello",
    "world"
]

STATIC_ACTIONS_TESTS = [
    "turn on bedroom lights",
    "turn off kitchen lights", 
    "toggle bathroom lights",
    "switch on hall lights",
    "activate lounge lights",
    "deactivate toilet lights"
]

def find_model():
    """Find the first available model in the models directory."""
    models_dir = Path(MODELS_PATH)
    if not models_dir.exists():
        print(f"❌ Models directory not found: {MODELS_PATH}")
        return None
    
    # Look for .gguf files
    gguf_files = list(models_dir.glob("*.gguf"))
    if not gguf_files:
        print(f"❌ No .gguf files found in {MODELS_PATH}")
        return None
    
    # Use the first available model
    model_path = str(gguf_files[0])
    print(f"✅ Using model: {model_path}")
    return model_path

def run_grammar_test(grammar_file, prompt, model_path, max_tokens=20):
    """Run a single grammar test using llama-cli."""
    
    # Construct the system prompt
    if "hello_world" in grammar_file:
        system_prompt = "You are a simple responder. Respond with either 'hello' or 'world' only."
        full_prompt = f"{system_prompt}\n\nUser: {prompt}\nAssistant: "
    else:
        system_prompt = "You are a JSON-only formatter. Respond with a JSON object containing 'action' and 'device' keys."
        full_prompt = f"{system_prompt}\n\nUser: {prompt}\nAssistant: {{\"action\": "
    
    # Construct the llama-cli command
    cmd = [
        LLAMA_CLI_PATH,
        "-m", model_path,
        "-p", full_prompt,
        "--grammar-file", grammar_file,
        "-n", str(max_tokens),
        "--temp", "0.0",
        "--no-display-prompt"
    ]
    
    try:
        print(f"  Testing: {prompt}")
        print(f"  Command: {' '.join(cmd[:3])} ... --grammar-file {grammar_file}")
        
        # Run the command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            env={"LD_LIBRARY_PATH": "/app/third_party/llama_cpp/lib"}
        )
        
        if result.returncode != 0:
            print(f"    ❌ Command failed: {result.stderr}")
            return None
        
        output = result.stdout.strip()
        
        # For static_actions grammar, complete the JSON
        if "static_actions" in grammar_file:
            output = '{"action": ' + output
        
        print(f"    ✅ Output: {output}")
        return output
        
    except subprocess.TimeoutExpired:
        print(f"    ❌ Command timed out")
        return None
    except Exception as e:
        print(f"    ❌ Error: {str(e)}")
        return None

def validate_hello_world_output(output):
    """Validate that output is either 'hello' or 'world'."""
    if not output:
        return False
    output = output.strip().lower()
    return output in ["hello", "world"]

def validate_static_actions_output(output):
    """Validate that output is valid JSON with action and device keys."""
    if not output:
        return False
    
    try:
        # Try to parse as JSON
        parsed = json.loads(output)
        
        # Check required keys
        if "action" not in parsed or "device" not in parsed:
            return False
        
        # Check that values are strings
        if not isinstance(parsed["action"], str) or not isinstance(parsed["device"], str):
            return False
        
        # Check that action is valid
        valid_actions = ["turn on", "turn off", "toggle", "switch on", "switch off", "activate", "deactivate"]
        if parsed["action"] not in valid_actions:
            return False
        
        # Check that device is valid
        valid_devices = ["bedroom lights", "bathroom lights", "kitchen lights", "hall lights", "lounge lights", "toilet lights"]
        if parsed["device"] not in valid_devices:
            return False
        
        return True
        
    except json.JSONDecodeError:
        return False

def test_hello_world_grammar(model_path):
    """Test the hello_world grammar."""
    print("\n🧪 Testing hello_world.gbnf grammar")
    print("=" * 50)
    
    grammar_file = os.path.join(TEST_GRAMMARS_PATH, "hello_world.gbnf")
    
    if not os.path.exists(grammar_file):
        print(f"❌ Grammar file not found: {grammar_file}")
        return False
    
    success_count = 0
    total_count = len(HELLO_WORLD_TESTS)
    
    for test_prompt in HELLO_WORLD_TESTS:
        output = run_grammar_test(grammar_file, test_prompt, model_path)
        
        if output and validate_hello_world_output(output):
            success_count += 1
            print(f"    ✅ Valid output: {output}")
        else:
            print(f"    ❌ Invalid output: {output}")
    
    print(f"\n📊 Results: {success_count}/{total_count} tests passed")
    return success_count == total_count

def test_static_actions_grammar(model_path):
    """Test the static_actions grammar."""
    print("\n🧪 Testing static_actions.gbnf grammar")
    print("=" * 50)
    
    grammar_file = os.path.join(TEST_GRAMMARS_PATH, "static_actions.gbnf")
    
    if not os.path.exists(grammar_file):
        print(f"❌ Grammar file not found: {grammar_file}")
        return False
    
    success_count = 0
    total_count = len(STATIC_ACTIONS_TESTS)
    
    for test_prompt in STATIC_ACTIONS_TESTS:
        output = run_grammar_test(grammar_file, test_prompt, model_path)
        
        if output and validate_static_actions_output(output):
            success_count += 1
            print(f"    ✅ Valid JSON: {output}")
        else:
            print(f"    ❌ Invalid JSON: {output}")
    
    print(f"\n📊 Results: {success_count}/{total_count} tests passed")
    return success_count == total_count

def main():
    """Main test function."""
    print("🚀 Orac Grammar Testing")
    print("=" * 50)
    
    # Check if we're running in Docker
    if not os.path.exists(LLAMA_CLI_PATH):
        print(f"❌ llama-cli not found at {LLAMA_CLI_PATH}")
        print("   Make sure you're running this in the Docker container")
        sys.exit(1)
    
    # Find a model to use
    model_path = find_model()
    if not model_path:
        print("❌ No model found for testing")
        sys.exit(1)
    
    # Check test grammar files
    test_grammars_dir = Path(TEST_GRAMMARS_PATH)
    if not test_grammars_dir.exists():
        print(f"❌ Test grammars directory not found: {TEST_GRAMMARS_PATH}")
        sys.exit(1)
    
    print(f"✅ Test grammars directory found: {TEST_GRAMMARS_PATH}")
    
    # Run tests
    hello_world_success = test_hello_world_grammar(model_path)
    static_actions_success = test_static_actions_grammar(model_path)
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 TEST SUMMARY")
    print("=" * 50)
    print(f"hello_world.gbnf: {'✅ PASSED' if hello_world_success else '❌ FAILED'}")
    print(f"static_actions.gbnf: {'✅ PASSED' if static_actions_success else '❌ FAILED'}")
    
    if hello_world_success and static_actions_success:
        print("\n🎉 All grammar tests passed! Grammar functionality is working correctly.")
        return 0
    else:
        print("\n⚠️  Some grammar tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 