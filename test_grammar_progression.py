#!/usr/bin/env python3
"""
Progressive Grammar Testing for ORAC
====================================

This script tests grammars in order of increasing complexity to find the exact
breaking point in llama.cpp v5306's GBNF parser.

Test Progression:
1. hello_world.gbnf - Simple alternations (KNOWN WORKING)
2. simple_json.gbnf - Fixed JSON string (TESTING)
3. single_field.gbnf - One non-terminal (TESTING)
4. two_fields.gbnf - Two non-terminals (TESTING)
5. with_whitespace.gbnf - Non-terminal + whitespace (TESTING)
6. complex_whitespace.gbnf - Multiple non-terminals + whitespace (TESTING)
7. static_actions.gbnf - Complex grammar (KNOWN FAILING)
"""

import subprocess
import json
import os
import sys
from pathlib import Path

class GrammarTester:
    def __init__(self):
        self.model_path = "/models/gguf/Qwen3-0.6B-Q4_K_M.gguf"
        self.llama_cli = "/app/third_party/llama_cpp/bin/llama-cli"
        self.grammars_dir = "/app/data/test_grammars"
        self.results = {}
        
    def test_grammar(self, grammar_file: str, test_prompts: list) -> dict:
        """Test a single grammar file with multiple prompts"""
        grammar_path = os.path.join(self.grammars_dir, grammar_file)
        
        print(f"\n🧪 Testing {grammar_file}")
        print("=" * 50)
        
        # Read and display grammar content
        try:
            with open(grammar_path, 'r') as f:
                grammar_content = f.read().strip()
            print(f"📄 Grammar content ({len(grammar_content)} chars):")
            print(f"   '{grammar_content}'")
        except Exception as e:
            print(f"❌ Error reading grammar file: {e}")
            return {"status": "error", "error": str(e)}
        
        results = {
            "grammar_file": grammar_file,
            "grammar_content": grammar_content,
            "tests": [],
            "passed": 0,
            "failed": 0
        }
        
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n  Testing {i}: {prompt}")
            
            # Build command
            cmd = [
                self.llama_cli,
                "-m", self.model_path,
                "-p", prompt,
                "--grammar-file", grammar_path,
                "-n", "10",
                "--temp", "0.0",
                "--repeat-penalty", "1.1"
            ]
            
            print(f"  Command: {' '.join(cmd[:4])} ... --grammar-file {grammar_path}")
            
            try:
                # Run command
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    output = result.stdout.strip()
                    print(f"    ✅ Output: {output}")
                    
                    # Validate output (basic check)
                    if output and len(output) > 0:
                        print(f"    ✅ Valid output: {output}")
                        results["tests"].append({
                            "prompt": prompt,
                            "status": "passed",
                            "output": output
                        })
                        results["passed"] += 1
                    else:
                        print(f"    ❌ Empty output")
                        results["tests"].append({
                            "prompt": prompt,
                            "status": "failed",
                            "output": output,
                            "error": "Empty output"
                        })
                        results["failed"] += 1
                else:
                    error = result.stderr.strip()
                    print(f"    ❌ Command failed: {error}")
                    results["tests"].append({
                        "prompt": prompt,
                        "status": "failed",
                        "output": None,
                        "error": error
                    })
                    results["failed"] += 1
                    
            except subprocess.TimeoutExpired:
                print(f"    ❌ Command timed out")
                results["tests"].append({
                    "prompt": prompt,
                    "status": "failed",
                    "output": None,
                    "error": "Timeout"
                })
                results["failed"] += 1
            except Exception as e:
                print(f"    ❌ Unexpected error: {e}")
                results["tests"].append({
                    "prompt": prompt,
                    "status": "failed",
                    "output": None,
                    "error": str(e)
                })
                results["failed"] += 1
        
        # Summary
        total = results["passed"] + results["failed"]
        print(f"\n📊 Results: {results['passed']}/{total} tests passed")
        
        if results["failed"] == 0:
            print("✅ Grammar PASSED")
            results["status"] = "passed"
        else:
            print("❌ Grammar FAILED")
            results["status"] = "failed"
        
        return results
    
    def run_progression_test(self):
        """Run the complete progression test"""
        print("🚀 ORAC Grammar Progression Testing")
        print("=" * 60)
        print("Testing grammars in order of increasing complexity...")
        print(f"Using model: {self.model_path}")
        
        # Test progression - ordered by complexity
        test_cases = [
            {
                "file": "hello_world.gbnf",
                "prompts": ["say hello", "say world", "hello", "world"],
                "description": "Simple alternations (baseline)"
            },
            {
                "file": "simple_json.gbnf", 
                "prompts": ["generate json", "create action", "turn on"],
                "description": "Fixed JSON string"
            },
            {
                "file": "single_field.gbnf",
                "prompts": ["turn on lights", "turn off", "toggle"],
                "description": "One non-terminal"
            },
            {
                "file": "two_fields.gbnf",
                "prompts": ["turn on bedroom lights", "turn off kitchen", "toggle"],
                "description": "Two non-terminals"
            },
            {
                "file": "with_whitespace.gbnf",
                "prompts": ["turn on", "turn off", "toggle"],
                "description": "Non-terminal + whitespace"
            },
            {
                "file": "complex_whitespace.gbnf",
                "prompts": ["turn on bedroom lights", "turn off kitchen", "toggle"],
                "description": "Multiple non-terminals + whitespace"
            },
            {
                "file": "static_actions.gbnf",
                "prompts": ["turn on bedroom lights", "turn off kitchen lights", "toggle bathroom lights"],
                "description": "Complex grammar (known failing)"
            }
        ]
        
        breaking_point = None
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{'='*60}")
            print(f"STEP {i}: {test_case['description']}")
            print(f"File: {test_case['file']}")
            print(f"{'='*60}")
            
            result = self.test_grammar(test_case['file'], test_case['prompts'])
            self.results[test_case['file']] = result
            
            # Check if this is the breaking point
            if result["status"] == "failed" and breaking_point is None:
                breaking_point = {
                    "step": i,
                    "file": test_case['file'],
                    "description": test_case['description'],
                    "result": result
                }
                print(f"\n🚨 BREAKING POINT FOUND!")
                print(f"   Step {i}: {test_case['description']}")
                print(f"   File: {test_case['file']}")
                print(f"   Status: {result['failed']}/{result['passed'] + result['failed']} tests failed")
        
        # Final summary
        print(f"\n{'='*60}")
        print("📋 FINAL TEST SUMMARY")
        print(f"{'='*60}")
        
        for i, test_case in enumerate(test_cases, 1):
            result = self.results[test_case['file']]
            status = "✅ PASS" if result["status"] == "passed" else "❌ FAIL"
            print(f"{i:2d}. {status} {test_case['file']} - {test_case['description']}")
        
        if breaking_point:
            print(f"\n🎯 BREAKING POINT ANALYSIS")
            print(f"{'='*60}")
            print(f"Grammar complexity breaks at: {breaking_point['description']}")
            print(f"File: {breaking_point['file']}")
            print(f"Step: {breaking_point['step']}")
            
            # Analyze the failure
            failed_tests = [t for t in breaking_point['result']['tests'] if t['status'] == 'failed']
            if failed_tests:
                print(f"\nFirst failure details:")
                first_failure = failed_tests[0]
                print(f"  Prompt: {first_failure['prompt']}")
                print(f"  Error: {first_failure.get('error', 'Unknown error')}")
        else:
            print(f"\n✅ All grammars passed! No breaking point found.")
        
        return breaking_point

def main():
    tester = GrammarTester()
    breaking_point = tester.run_progression_test()
    
    # Exit with appropriate code
    if breaking_point:
        print(f"\n⚠️  Grammar testing completed with breaking point found.")
        sys.exit(1)
    else:
        print(f"\n✅ All grammar tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    main() 