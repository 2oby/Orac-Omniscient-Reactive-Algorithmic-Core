#!/usr/bin/env python3
"""
Test script for static GBNF grammar file.
"""

import subprocess
import sys
import os

def test_static_grammar():
    """Test the static grammar file with llama.cpp."""
    
    # Paths
    llama_cli_path = "/app/third_party/llama_cpp/bin/llama-cli"
    model_path = "/app/models/gguf/distilgpt2.Q4_0.gguf"
    grammar_file = "/app/data/static_grammar.gbnf"
    
    print("=== Testing Static GBNF Grammar ===")
    print(f"Grammar file: {grammar_file}")
    print(f"Model: {model_path}")
    print()
    
    # Read the grammar file
    try:
        with open(grammar_file, 'r') as f:
            grammar_content = f.read()
        print("Grammar content:")
        print("-" * 40)
        print(grammar_content)
        print("-" * 40)
        print()
    except Exception as e:
        print(f"❌ Error reading grammar file: {e}")
        return False
    
    # Test cases - JSON formatted
    test_cases = [
        '{"action": "turn on", "device": "bedroom lights"}',
        '{"action": "switch off", "device": "kitchen lights"}', 
        '{"action": "toggle", "device": "bathroom lights"}',
        '{"action": "turn on", "device": "hall lights"}',
        '{"action": "switch off", "device": "lounge lights"}'
    ]
    
    success_count = 0
    total_count = len(test_cases)
    
    for i, prompt in enumerate(test_cases, 1):
        print(f"Test {i}/{total_count}: '{prompt}'")
        
        try:
            # Build command
            cmd = [
                llama_cli_path,
                "-m", model_path,
                "-p", prompt,
                "--grammar", grammar_file,
                "-n", "3",  # Generate 3 tokens
                "--temp", "0.1",
                "--repeat-penalty", "1.1"
            ]
            
            # Run llama-cli
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Check results
            if result.returncode == 0:
                print(f"  ✅ Success: {result.stdout.strip()}")
                success_count += 1
            else:
                print(f"  ❌ Failed: {result.stderr.strip()}")
                
        except subprocess.TimeoutExpired:
            print(f"  ❌ Timeout")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        print()
    
    # Summary
    print("=== Test Summary ===")
    print(f"Passed: {success_count}/{total_count}")
    print(f"Success rate: {(success_count/total_count)*100:.1f}%")
    
    if success_count == total_count:
        print("🎉 All tests passed! Static grammar is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check grammar syntax.")
        return False

if __name__ == "__main__":
    success = test_static_grammar()
    sys.exit(0 if success else 1) 