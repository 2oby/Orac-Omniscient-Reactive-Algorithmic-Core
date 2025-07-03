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
7. wildcard_json.gbnf - Wildcard patterns (NEW TESTING)
8. flexible_json.gbnf - Character classes (NEW TESTING)
9. constrained_wildcard.gbnf - Constrained wildcards (NEW TESTING)
10. static_actions.gbnf - Complex grammar (KNOWN FAILING)
"""

import subprocess
import json
import os
import sys
from pathlib import Path

class GrammarTester:
    def __init__(self):
        self.model_path = "/models/gguf/Qwen3-0.6B-Q4_K_M.gguf"
        self.grammar_dir = "/app/data/test_grammars"
        self.llama_cli = "/app/third_party/llama_cpp/bin/llama-cli"
        
        # Test grammars in order of complexity
        self.test_grammars = [
            "hello_world.gbnf",
            "simple_json.gbnf", 
            "single_field.gbnf",
            "two_fields.gbnf",
            "with_whitespace.gbnf",
            "complex_whitespace.gbnf",
            "wildcard_json.gbnf",
            "flexible_json.gbnf", 
            "constrained_wildcard.gbnf",
            "static_actions.gbnf"
        ]
        
        self.test_prompts = [
            "say hello",
            "turn on bedroom lights",
            "turn on bedroom lights",
            "turn on bedroom lights", 
            "turn on bedroom lights",
            "turn on bedroom lights",
            "turn on bedroom lights",
            "turn on bedroom lights",
            "turn on bedroom lights",
            "turn on bedroom lights"
        ]

    def test_grammar(self, grammar_file, prompt, test_num):
        """Test a single grammar file"""
        print(f"\n{'='*60}")
        print(f"TEST {test_num}: {grammar_file}")
        print(f"{'='*60}")
        
        grammar_path = os.path.join(self.grammar_dir, grammar_file)
        
        # Check if grammar file exists
        if not os.path.exists(grammar_path):
            print(f"❌ Grammar file not found: {grammar_path}")
            return False
            
        # Display grammar content
        print(f"📄 Grammar content:")
        with open(grammar_path, 'r') as f:
            print(f.read())
        
        # Test command
        cmd = [
            self.llama_cli,
            '-m', self.model_path,
            '-p', prompt,
            '--grammar-file', grammar_path,
            '-n', '10',
            '--temp', '0.0'
        ]
        
        print(f"\n🔧 Test command:")
        print(f"   {' '.join(cmd)}")
        
        try:
            # Run the test
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            print(f"\n📊 Results:")
            print(f"   Exit code: {result.returncode}")
            
            if result.returncode == 0:
                print(f"   ✅ SUCCESS")
                print(f"   Output: {result.stdout.strip()}")
                return True
            else:
                print(f"   ❌ FAILED")
                print(f"   Error: {result.stderr.strip()}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"   ⏰ TIMEOUT")
            return False
        except Exception as e:
            print(f"   💥 EXCEPTION: {e}")
            return False

    def run_progression_test(self):
        """Run all grammar tests in progression"""
        print("🚀 Starting Progressive Grammar Testing")
        print(f"📁 Grammar directory: {self.grammar_dir}")
        print(f"🤖 Model: {self.model_path}")
        
        results = []
        
        for i, (grammar, prompt) in enumerate(zip(self.test_grammars, self.test_prompts), 1):
            success = self.test_grammar(grammar, prompt, i)
            results.append({
                'test_num': i,
                'grammar': grammar,
                'success': success
            })
            
            # Stop if we find the breaking point
            if not success:
                print(f"\n🎯 BREAKING POINT FOUND at test {i}: {grammar}")
                break
        
        # Summary
        print(f"\n{'='*60}")
        print("📋 TEST SUMMARY")
        print(f"{'='*60}")
        
        for result in results:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"   Test {result['test_num']:2d}: {result['grammar']:<25} {status}")
        
        # Analysis
        working_count = sum(1 for r in results if r['success'])
        total_count = len(results)
        
        print(f"\n📈 Analysis:")
        print(f"   Working grammars: {working_count}/{total_count}")
        print(f"   Breaking point: Test {working_count + 1} ({self.test_grammars[working_count] if working_count < len(self.test_grammars) else 'N/A'})")
        
        return results

if __name__ == "__main__":
    tester = GrammarTester()
    results = tester.run_progression_test() 