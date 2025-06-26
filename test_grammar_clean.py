#!/usr/bin/env python3
"""
Clean grammar testing script with clear prompt/response visibility.
"""

import asyncio
import json
import sys
import os
import subprocess
import tempfile
import time

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orac.homeassistant.client import HomeAssistantClient
from orac.homeassistant.config import HomeAssistantConfig
from orac.homeassistant.mapping_config import EntityMappingConfig
from orac.homeassistant.grammar_manager import HomeAssistantGrammarManager

class CleanGrammarTester:
    def __init__(self):
        # Use Qwen3 0.6B model instead of distilgpt2
        self.llama_cli_path = "/app/third_party/llama_cpp/bin/llama-cli"
        self.model_path = "/app/models/gguf/Qwen3-0.6B-Q4_K_M.gguf"
        self.test_results = []
        
    def test_grammar_with_llama(self, grammar_content, prompt, test_name, grammar_file=None):
        """Test a grammar with llama-cli and return clean results."""
        print(f"\n============================================================")
        print(f"TEST: {test_name}")
        print(f"============================================================")
        
        try:
            # Build command
            cmd = [
                self.llama_cli_path,
                "-m", self.model_path,
                "-p", prompt,
                "-n", "5",  # Generate 5 tokens
                "--temp", "0.1",  # Low temperature for more predictable output
                "--repeat-penalty", "1.1"
            ]
            
            # Add grammar (either as file or string)
            if grammar_file:
                cmd.extend(["--grammar-file", grammar_file])
                print(f"Grammar file: {grammar_file}")
            else:
                cmd.extend(["--grammar", grammar_content.strip()])
                print(f"Grammar string: {grammar_content}")
            
            print(f"Prompt: '{prompt}'")
            print("-" * 40)
            
            # Run llama-cli
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            end_time = time.time()
            
            # Analyze results
            success = result.returncode == 0
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            
            if success:
                # Extract the generated text (everything after the prompt)
                full_output = stdout
                generated = full_output[len(prompt):] if full_output.startswith(prompt) else full_output
                
                # Check if generated text is grammar compliant
                grammar_compliant = self._check_grammar_compliance(generated, grammar_content)
                
                print(f"✅ SUCCESS")
                print(f"Full output: '{full_output}'")
                print(f"Generated: '{generated}'")
                print(f"Grammar compliant: {'✅' if grammar_compliant else '❌'}")
                
                result_summary = {
                    "test_name": test_name,
                    "success": True,
                    "full_output": full_output,
                    "generated": generated,
                    "grammar_compliant": grammar_compliant,
                    "execution_time": end_time - start_time
                }
            else:
                print(f"❌ FAILED")
                print(f"Error: {stderr}")
                
                result_summary = {
                    "test_name": test_name,
                    "success": False,
                    "error": stderr,
                    "execution_time": end_time - start_time
                }
            
            self.test_results.append(result_summary)
            return result_summary
            
        except subprocess.TimeoutExpired:
            print("❌ Test timed out after 30 seconds")
            return {"test_name": test_name, "success": False, "error": "timeout"}
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            return {"test_name": test_name, "success": False, "error": str(e)}
    
    def _check_grammar_compliance(self, generated_text, grammar_content):
        """Simple check if generated text contains grammar-compliant tokens."""
        # Extract tokens from grammar (simplified check)
        if '"hello"' in grammar_content and '"world"' in grammar_content:
            return generated_text.strip() in ['hello', 'world', 'hello world', 'world hello']
        return True  # Default to True if we can't determine

async def test_clean_grammar():
    """Test grammar with clean output."""
    
    print("🧪 CLEAN GRAMMAR TESTING")
    print("=" * 60)
    
    tester = CleanGrammarTester()
    
    # Create a simple grammar file
    grammar_content = '''root ::= "hello" | "world"'''
    grammar_file = "/app/data/hello_world.gbnf"
    
    with open(grammar_file, 'w') as f:
        f.write(grammar_content)
    
    # Test 1: Grammar as string
    tester.test_grammar_with_llama(
        grammar_content,
        "hello",
        "Grammar as string (hello prompt)"
    )
    
    # Test 2: Grammar as file
    tester.test_grammar_with_llama(
        None,
        "hello",
        "Grammar as file (hello prompt)",
        grammar_file
    )
    
    # Test 3: Non-compliant prompt
    tester.test_grammar_with_llama(
        None,
        "test",
        "Grammar as file (test prompt - should show non-compliance)",
        grammar_file
    )
    
    # Test 4: Another non-compliant prompt
    tester.test_grammar_with_llama(
        None,
        "start",
        "Grammar as file (start prompt - should show non-compliance)",
        grammar_file
    )
    
    # Test 5: Empty prompt
    tester.test_grammar_with_llama(
        None,
        "",
        "Grammar as file (empty prompt)",
        grammar_file
    )
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(tester.test_results)
    
    for result in tester.test_results:
        status = "✅ PASS" if result.get("success") else "❌ FAIL"
        print(f"{status}: {result['test_name']}")
        if result.get("success"):
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    print(f"Model used: {tester.model_path}")

if __name__ == "__main__":
    asyncio.run(test_clean_grammar()) 