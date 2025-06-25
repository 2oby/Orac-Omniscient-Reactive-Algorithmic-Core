#!/usr/bin/env python3
"""
Test script to test basic grammar functionality with llama-cli.
"""

import subprocess
import sys
import os

def test_simple_grammar():
    """Test simple grammar with llama-cli."""
    
    print("Testing simple grammar with llama-cli...")
    
    # Test 1: Simplest possible grammar
    print("\n=== Test 1: Simple word selection ===")
    simple_grammar = 'root ::= "hello" | "world"'
    
    cmd = [
        "/app/third_party/llama_cpp/bin/llama-cli",
        "-m", "/app/models/gguf/distilgpt2.Q4_0.gguf",
        "-p", "hello",
        "--grammar", simple_grammar,
        "-n", "1",
        "--temp", "0.1"
    ]
    
    print(f"Command: {' '.join(cmd[:6])} [GRAMMAR] {' '.join(cmd[7:])}")
    print(f"Grammar: {simple_grammar}")
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    
    print(f"Return code: {result.returncode}")
    if result.returncode == 0:
        print("✅ Simple grammar test PASSED!")
        print(f"Output: {result.stdout.strip()}")
    else:
        print("❌ Simple grammar test FAILED!")
        print(f"STDERR: {result.stderr}")
    
    # Test 2: JSON-like grammar
    print("\n=== Test 2: JSON-like grammar ===")
    json_grammar = '''root ::= object
object ::= "{" ws string ":" ws value ws "}"
string ::= "\"" ([^"\\] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F]))* "\""
value ::= "\"" ([^"\\] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F]))* "\""
ws ::= [ \t\n\r]*'''
    
    cmd = [
        "/app/third_party/llama_cpp/bin/llama-cli",
        "-m", "/app/models/gguf/distilgpt2.Q4_0.gguf",
        "-p", '{"',
        "--grammar", json_grammar,
        "-n", "1",
        "--temp", "0.1"
    ]
    
    print(f"Command: {' '.join(cmd[:6])} [GRAMMAR] {' '.join(cmd[7:])}")
    print(f"Grammar length: {len(json_grammar)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    
    print(f"Return code: {result.returncode}")
    if result.returncode == 0:
        print("✅ JSON grammar test PASSED!")
        print(f"Output: {result.stdout.strip()}")
    else:
        print("❌ JSON grammar test FAILED!")
        print(f"STDERR: {result.stderr}")
    
    # Test 3: Device-specific grammar (similar to our generated one)
    print("\n=== Test 3: Device-specific grammar ===")
    device_grammar = '''root ::= object
object ::= "{" ws device_string "," ws action_string ws "}"
device_string ::= "\"device\"" ":" ws "\"" device_value "\""
action_string ::= "\"action\"" ":" ws "\"" action_value "\""
device_value ::= "bedroom lights" | "bathroom lights" | "kitchen lights"
action_value ::= "turn on" | "turn off" | "toggle"
ws ::= [ \t\n\r]*'''
    
    cmd = [
        "/app/third_party/llama_cpp/bin/llama-cli",
        "-m", "/app/models/gguf/distilgpt2.Q4_0.gguf",
        "-p", '{"device": "bedroom lights", "action": "turn on"}',
        "--grammar", device_grammar,
        "-n", "1",
        "--temp", "0.1"
    ]
    
    print(f"Command: {' '.join(cmd[:6])} [GRAMMAR] {' '.join(cmd[7:])}")
    print(f"Grammar length: {len(device_grammar)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    
    print(f"Return code: {result.returncode}")
    if result.returncode == 0:
        print("✅ Device grammar test PASSED!")
        print(f"Output: {result.stdout.strip()}")
    else:
        print("❌ Device grammar test FAILED!")
        print(f"STDERR: {result.stderr}")

if __name__ == "__main__":
    test_simple_grammar() 