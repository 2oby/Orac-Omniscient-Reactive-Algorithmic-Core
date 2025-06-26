#!/usr/bin/env python3
"""
Clean grammar test script - shows prompts and responses clearly.
"""

import subprocess
import os

def test_grammar_clean(grammar_arg, prompt, test_name):
    """Test grammar with clean output."""
    llama_cli_path = "/app/third_party/llama_cpp/bin/llama-cli"
    model_path = "/app/models/gguf/distilgpt2.Q4_0.gguf"
    
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"{'='*60}")
    
    if os.path.isfile(grammar_arg):
        print(f"Grammar file: {grammar_arg}")
        cmd = [llama_cli_path, "-m", model_path, "-p", prompt, "--grammar-file", grammar_arg, "-n", "3", "--temp", "0.1"]
    else:
        print(f"Grammar string: {grammar_arg}")
        cmd = [llama_cli_path, "-m", model_path, "-p", prompt, "--grammar", grammar_arg, "-n", "3", "--temp", "0.1"]
    
    print(f"Prompt: '{prompt}'")
    print("-" * 40)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            # Extract just the generated text (remove prompt)
            output = result.stdout.strip()
            if output.startswith(prompt):
                generated = output[len(prompt):]
            else:
                generated = output
            
            print(f"✅ SUCCESS")
            print(f"Full output: '{output}'")
            print(f"Generated: '{generated}'")
            print(f"Grammar compliant: {'✅' if all(word in ['hello', 'world'] for word in generated.split()) else '❌'}")
        else:
            print(f"❌ FAILED")
            print(f"Error: {result.stderr.strip()}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")

def main():
    print("🧪 CLEAN GRAMMAR TESTING")
    print("=" * 60)
    
    # Test 1: Grammar as string
    test_grammar_clean(
        'root ::= "hello" | "world"',
        "hello",
        "Grammar as string (hello prompt)"
    )
    
    # Test 2: Grammar as file
    test_grammar_clean(
        "/app/data/hello_world.gbnf",
        "hello", 
        "Grammar as file (hello prompt)"
    )
    
    # Test 3: Non-compliant prompt
    test_grammar_clean(
        "/app/data/hello_world.gbnf",
        "test",
        "Grammar as file (test prompt - should show non-compliance)"
    )
    
    # Test 4: Different prompt
    test_grammar_clean(
        "/app/data/hello_world.gbnf",
        "start",
        "Grammar as file (start prompt - should show non-compliance)"
    )
    
    # Test 5: Empty prompt
    test_grammar_clean(
        "/app/data/hello_world.gbnf",
        "",
        "Grammar as file (empty prompt)"
    )

if __name__ == "__main__":
    main() 