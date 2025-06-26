#!/usr/bin/env python3
"""
Test script for static GBNF grammar file.
"""

import subprocess
import sys
import os

def run_llama_with_grammar(grammar_arg, prompt, test_name):
    llama_cli_path = "/app/third_party/llama_cpp/bin/llama-cli"
    model_path = "/app/models/gguf/distilgpt2.Q4_0.gguf"
    print(f"\n=== {test_name} ===")
    print(f"Prompt: {prompt}")
    if os.path.isfile(grammar_arg):
        print(f"Grammar file: {grammar_arg}")
        cmd = [llama_cli_path, "-m", model_path, "-p", prompt, "--grammar-file", grammar_arg, "-n", "5", "--temp", "0.1"]
    else:
        print(f"Grammar string: {grammar_arg}")
        cmd = [llama_cli_path, "-m", model_path, "-p", prompt, "--grammar", grammar_arg, "-n", "5", "--temp", "0.1"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
    except Exception as e:
        print(f"Exception: {e}")

def main():
    # 1. Grammar as string (hello/world)
    hello_world_grammar = 'root ::= "hello" | "world"'
    run_llama_with_grammar(hello_world_grammar, "hello", "Test 1: Grammar as string (hello/world)")

    # 2. Grammar as file (hello_world.gbnf)
    run_llama_with_grammar("/app/data/hello_world.gbnf", "hello", "Test 2: Grammar as file (hello_world.gbnf)")

    # 3. Grammar as file (static_grammar.gbnf)
    run_llama_with_grammar("/app/data/static_grammar.gbnf", '{"action": "turn on", "device": "bedroom lights"}', "Test 3: Grammar as file (static_grammar.gbnf)")

if __name__ == "__main__":
    main() 