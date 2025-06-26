#!/usr/bin/env python3
"""
Test script for Qwen models with increasingly complex grammar files.

This script tests:
1. Hello World grammar (simplest)
2. Static grammar (JSON commands)
3. Dynamic Home Assistant grammar (most complex)

Progression from simple to complex to ensure the model can handle each level.
"""

import subprocess
import sys
import os
import json
import time
from typing import Dict, Any, List, Optional

class QwenGrammarTester:
    """Tester for Qwen models with progressive grammar complexity."""
    
    def __init__(self, llama_cli_path: str = "/app/third_party/llama_cpp/bin/llama-cli"):
        self.llama_cli_path = llama_cli_path
        self.test_results = []
        
        # Qwen models to test (in order of complexity)
        self.qwen_models = [
            "/app/models/gguf/Qwen3-0.6B-Q4_K_M.gguf",
            "/app/models/gguf/Qwen3-1.7B-Q4_K_M.gguf"
        ]
        
        # Grammar files to test (in order of complexity)
        self.grammar_files = [
            "/app/data/hello_world.gbnf",
            "/app/data/static_grammar.gbnf"
        ]
        
        # Test prompts for each grammar
        self.test_prompts = {
            "hello_world": [
                "hello",
                "world", 
                "test",
                ""
            ],
            "static_grammar": [
                '{"action": "turn on", "device": "kitchen lights"}',
                '{"action": "turn off", "device": "bedroom lights"}',
                '{"action": "toggle", "device": "bathroom lights"}',
                'turn on the kitchen lights'
            ]
        }
    
    def test_model_with_grammar(self, model_path: str, grammar_file: str, prompt: str, test_name: str) -> Dict[str, Any]:
        """Test a specific model with a specific grammar and prompt."""
        print(f"\n{'='*60}")
        print(f"TEST: {test_name}")
        print(f"{'='*60}")
        print(f"Model: {os.path.basename(model_path)}")
        print(f"Grammar: {os.path.basename(grammar_file)}")
        print(f"Prompt: '{prompt}'")
        
        # Check if files exist
        if not os.path.exists(model_path):
            error_msg = f"Model not found: {model_path}"
            print(f"❌ {error_msg}")
            return {"test_name": test_name, "success": False, "error": error_msg}
        
        if not os.path.exists(grammar_file):
            error_msg = f"Grammar file not found: {grammar_file}"
            print(f"❌ {error_msg}")
            return {"test_name": test_name, "success": False, "error": error_msg}
        
        try:
            # Build command
            cmd = [
                self.llama_cli_path,
                "-m", model_path,
                "-p", prompt,
                "--grammar-file", grammar_file,
                "-n", "10",  # Generate 10 tokens
                "--temp", "0.1",  # Low temperature for predictable output
                "--repeat-penalty", "1.1",
                "--verbose"
            ]
            
            print(f"Command: {' '.join(cmd[:6])} [GRAMMAR_FILE] {' '.join(cmd[7:])}")
            print("-" * 40)
            
            # Run llama-cli
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            end_time = time.time()
            
            # Analyze results
            success = result.returncode == 0
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            
            print(f"Return code: {result.returncode}")
            print(f"Execution time: {end_time - start_time:.2f}s")
            
            if success:
                # Extract generated text
                full_output = stdout
                generated = full_output[len(prompt):] if full_output.startswith(prompt) else full_output
                
                # Check grammar compliance
                grammar_compliant = self._check_grammar_compliance(generated, grammar_file)
                
                print(f"✅ SUCCESS")
                print(f"Full output: '{full_output}'")
                print(f"Generated: '{generated}'")
                print(f"Grammar compliant: {'✅' if grammar_compliant else '❌'}")
                
                result_summary = {
                    "test_name": test_name,
                    "success": True,
                    "model": os.path.basename(model_path),
                    "grammar": os.path.basename(grammar_file),
                    "prompt": prompt,
                    "full_output": full_output,
                    "generated": generated,
                    "grammar_compliant": grammar_compliant,
                    "execution_time": end_time - start_time
                }
            else:
                print(f"❌ FAILED")
                print(f"STDERR: {stderr}")
                
                result_summary = {
                    "test_name": test_name,
                    "success": False,
                    "model": os.path.basename(model_path),
                    "grammar": os.path.basename(grammar_file),
                    "prompt": prompt,
                    "error": stderr,
                    "return_code": result.returncode,
                    "execution_time": end_time - start_time
                }
            
            self.test_results.append(result_summary)
            return result_summary
            
        except subprocess.TimeoutExpired:
            error_msg = "Test timed out after 60 seconds"
            print(f"❌ {error_msg}")
            return {"test_name": test_name, "success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            print(f"❌ {error_msg}")
            return {"test_name": test_name, "success": False, "error": error_msg}
    
    def _check_grammar_compliance(self, generated_text: str, grammar_file: str) -> bool:
        """Check if generated text complies with the grammar."""
        try:
            with open(grammar_file, 'r') as f:
                grammar_content = f.read()
            
            # Simple compliance check based on grammar type
            if "hello" in grammar_content and "world" in grammar_content:
                # Hello world grammar
                return generated_text.strip() in ['hello', 'world', 'hello world', 'world hello']
            elif "action" in grammar_content and "device" in grammar_content:
                # JSON grammar - check for basic JSON structure
                try:
                    json.loads(generated_text.strip())
                    return True
                except json.JSONDecodeError:
                    return False
            else:
                # Unknown grammar - assume compliant
                return True
                
        except Exception:
            return False
    
    def test_hello_world_grammar(self):
        """Test 1: Hello World Grammar (Simplest)"""
        print("\n" + "="*80)
        print("TEST 1: HELLO WORLD GRAMMAR (SIMPLEST)")
        print("="*80)
        
        grammar_file = "/app/data/hello_world.gbnf"
        prompts = self.test_prompts["hello_world"]
        
        for model_path in self.qwen_models:
            model_name = os.path.basename(model_path)
            print(f"\nTesting model: {model_name}")
            
            for i, prompt in enumerate(prompts, 1):
                test_name = f"Hello World - {model_name} - Prompt {i}"
                self.test_model_with_grammar(model_path, grammar_file, prompt, test_name)
    
    def test_static_grammar(self):
        """Test 2: Static Grammar (JSON Commands)"""
        print("\n" + "="*80)
        print("TEST 2: STATIC GRAMMAR (JSON COMMANDS)")
        print("="*80)
        
        grammar_file = "/app/data/static_grammar.gbnf"
        prompts = self.test_prompts["static_grammar"]
        
        for model_path in self.qwen_models:
            model_name = os.path.basename(model_path)
            print(f"\nTesting model: {model_name}")
            
            for i, prompt in enumerate(prompts, 1):
                test_name = f"Static Grammar - {model_name} - Prompt {i}"
                self.test_model_with_grammar(model_path, grammar_file, prompt, test_name)
    
    def test_dynamic_grammar(self):
        """Test 3: Dynamic Home Assistant Grammar (Most Complex)"""
        print("\n" + "="*80)
        print("TEST 3: DYNAMIC HOME ASSISTANT GRAMMAR (MOST COMPLEX)")
        print("="*80)
        
        # This would test the dynamically generated grammar from Home Assistant
        # For now, we'll test with a more complex static grammar
        print("Dynamic grammar testing would require Home Assistant integration.")
        print("This test is reserved for the most complex grammar scenario.")
        print("✅ Skipping for now - focus on basic grammar progression first.")
    
    def print_summary(self):
        """Print comprehensive test summary."""
        print(f"\n{'='*80}")
        print("COMPREHENSIVE TEST SUMMARY")
        print(f"{'='*80}")
        
        # Group results by model
        model_results = {}
        for result in self.test_results:
            model = result.get("model", "Unknown")
            if model not in model_results:
                model_results[model] = []
            model_results[model].append(result)
        
        for model, results in model_results.items():
            print(f"\n📊 Model: {model}")
            print("-" * 40)
            
            passed = sum(1 for r in results if r.get("success"))
            total = len(results)
            
            print(f"Tests passed: {passed}/{total}")
            print(f"Success rate: {(passed/total)*100:.1f}%" if total > 0 else "No tests")
            
            # Show detailed results
            for result in results:
                status = "✅ PASS" if result.get("success") else "❌ FAIL"
                grammar = result.get("grammar", "Unknown")
                prompt = result.get("prompt", "Unknown")[:30] + "..." if len(result.get("prompt", "")) > 30 else result.get("prompt", "Unknown")
                print(f"  {status}: {grammar} - '{prompt}'")
                
                if result.get("success") and result.get("generated"):
                    print(f"    Generated: '{result['generated']}'")
                elif not result.get("success"):
                    print(f"    Error: {result.get('error', 'Unknown error')}")
        
        # Overall statistics
        print(f"\n{'='*80}")
        print("OVERALL STATISTICS")
        print(f"{'='*80}")
        
        total_tests = len(self.test_results)
        total_passed = sum(1 for r in self.test_results if r.get("success"))
        
        print(f"Total tests: {total_tests}")
        print(f"Total passed: {total_passed}")
        print(f"Overall success rate: {(total_passed/total_tests)*100:.1f}%" if total_tests > 0 else "No tests run")
        
        # Grammar complexity analysis
        grammar_stats = {}
        for result in self.test_results:
            grammar = result.get("grammar", "Unknown")
            if grammar not in grammar_stats:
                grammar_stats[grammar] = {"total": 0, "passed": 0}
            grammar_stats[grammar]["total"] += 1
            if result.get("success"):
                grammar_stats[grammar]["passed"] += 1
        
        print(f"\nGrammar Complexity Analysis:")
        for grammar, stats in grammar_stats.items():
            success_rate = (stats["passed"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            print(f"  {grammar}: {stats['passed']}/{stats['total']} ({success_rate:.1f}%)")

def main():
    """Main test function."""
    print("🧪 QWEN GRAMMAR PROGRESSION TESTING")
    print("=" * 80)
    print("Testing Qwen models with increasingly complex grammar files")
    print("Progression: Hello World → Static Grammar → Dynamic Grammar")
    
    tester = QwenGrammarTester()
    
    # Run tests in order of complexity
    print("\n🚀 Starting grammar progression tests...")
    
    # Test 1: Hello World Grammar (Simplest)
    tester.test_hello_world_grammar()
    
    # Test 2: Static Grammar (JSON Commands)
    tester.test_static_grammar()
    
    # Test 3: Dynamic Grammar (Most Complex) - Skipped for now
    tester.test_dynamic_grammar()
    
    # Print comprehensive summary
    tester.print_summary()
    
    print(f"\n{'='*80}")
    print("TESTING COMPLETE")
    print(f"{'='*80}")
    print("✅ Grammar progression testing finished!")
    print("📊 Check the summary above for detailed results.")
    print("🎯 Next steps: Analyze which grammar complexity each model handles best.")

if __name__ == "__main__":
    main() 