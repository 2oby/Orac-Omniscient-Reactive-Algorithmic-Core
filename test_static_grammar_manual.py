#!/usr/bin/env python3
"""
Manual test script for static grammar with proper prompts.
"""

import subprocess
import sys
import os

def test_static_grammar():
    """Test the static grammar with proper prompts."""
    
    # Configuration
    llama_cli_path = "/app/third_party/llama_cpp/bin/llama-cli"
    model_path = "/app/models/gguf/Qwen3-1.7B-Q4_K_M.gguf"
    grammar_file = "/app/data/static_grammar.gbnf"
    
    # Test prompts that users would actually provide
    test_prompts = [
        "turn on the kitchen lights",      # ✅ Natural language prompt
        "switch off the bedroom lights",   # ✅ Natural language prompt  
        "toggle the bathroom lights",      # ✅ Natural language prompt
        "activate the hall lights"         # ✅ Natural language prompt
    ]
    
    print("🧪 Testing Static Grammar: Natural Language → JSON Output")
    print("=" * 60)
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n📝 Test {i}: '{prompt}'")
        print("-" * 40)
        
        # Build command
        cmd = [
            llama_cli_path,
            "-m", model_path,
            "-p", prompt,
            "--grammar-file", grammar_file,
            "-n", "20",  # Generate more tokens for JSON
            "--temp", "0.1",
            "--repeat-penalty", "1.1"
        ]
        
        try:
            # Run test
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"✅ SUCCESS")
                print(f"Generated: '{result.stdout.strip()}'")
            else:
                print(f"❌ FAILED")
                print(f"Error: {result.stderr.strip()}")
                
        except subprocess.TimeoutExpired:
            print("❌ TIMEOUT")
        except Exception as e:
            print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_static_grammar() 