#!/usr/bin/env python3
"""
Robust grammar testing utility with proper error handling.
"""

import subprocess
import sys
import os
import tempfile
import json
from typing import Optional, Dict, Any, List

class RobustGrammarTester:
    """Robust grammar tester with comprehensive error handling."""
    
    def __init__(self, llama_cli_path: str = "/app/third_party/llama_cpp/bin/llama-cli", 
                 model_path: str = "/app/models/gguf/distilgpt2.Q4_0.gguf"):
        self.llama_cli_path = llama_cli_path
        self.model_path = model_path
        self.test_results = []
    
    def load_grammar_file(self, grammar_file_path: str) -> Optional[str]:
        """Load grammar file with proper error handling.
        
        Args:
            grammar_file_path: Path to the grammar file
            
        Returns:
            Grammar content as string, or None if loading failed
        """
        try:
            if not os.path.exists(grammar_file_path):
                print(f"❌ Grammar file not found: {grammar_file_path}")
                return None
            
            with open(grammar_file_path, 'r') as f:
                content = f.read().strip()
            
            if not content:
                print(f"❌ Grammar file is empty: {grammar_file_path}")
                return None
            
            print(f"✅ Grammar file loaded successfully: {grammar_file_path}")
            print(f"   Size: {len(content)} characters")
            return content
            
        except Exception as e:
            print(f"❌ Error loading grammar file {grammar_file_path}: {e}")
            return None
    
    def validate_grammar_syntax(self, grammar_content: str) -> bool:
        """Validate basic GBNF syntax.
        
        Args:
            grammar_content: Grammar content to validate
            
        Returns:
            True if syntax appears valid, False otherwise
        """
        if not grammar_content:
            print("❌ Grammar content is empty")
            return False
        
        # Check for required elements
        required_elements = ['root ::=', '::=']
        for element in required_elements:
            if element not in grammar_content:
                print(f"❌ Missing required element: {element}")
                return False
        
        # Check for balanced quotes
        quote_count = grammar_content.count('"')
        if quote_count % 2 != 0:
            print(f"❌ Unbalanced quotes detected (count: {quote_count})")
            return False
        
        # Check for basic rule structure
        lines = grammar_content.split('\n')
        rule_count = 0
        for line in lines:
            line = line.strip()
            if '::=' in line:
                rule_count += 1
                # Check if rule has content after ::=
                parts = line.split('::=', 1)
                if len(parts) != 2 or not parts[1].strip():
                    print(f"❌ Invalid rule structure: {line}")
                    return False
        
        if rule_count == 0:
            print("❌ No rules found in grammar")
            return False
        
        print(f"✅ Grammar syntax validation passed ({rule_count} rules)")
        return True
    
    def test_grammar_with_llama(self, grammar_content: str, prompt: str, test_name: str, 
                               grammar_file: Optional[str] = None) -> Dict[str, Any]:
        """Test grammar with llama-cli with comprehensive error handling.
        
        Args:
            grammar_content: Grammar content as string
            prompt: Test prompt
            test_name: Name of the test
            grammar_file: Optional grammar file path
            
        Returns:
            Test result dictionary
        """
        print(f"\n{'='*60}")
        print(f"TEST: {test_name}")
        print(f"{'='*60}")
        
        # Validate inputs
        if not grammar_content and not grammar_file:
            error_msg = "No grammar content or file provided"
            print(f"❌ {error_msg}")
            return {"test_name": test_name, "success": False, "error": error_msg}
        
        if not prompt:
            error_msg = "No prompt provided"
            print(f"❌ {error_msg}")
            return {"test_name": test_name, "success": False, "error": error_msg}
        
        try:
            # Build command
            cmd = [
                self.llama_cli_path,
                "-m", self.model_path,
                "-p", prompt,
                "-n", "10",  # Generate 10 tokens
                "--temp", "0.1",  # Low temperature for predictable output
                "--repeat-penalty", "1.1"
            ]
            
            # Add grammar (either as file or string)
            if grammar_file and os.path.exists(grammar_file):
                cmd.extend(["--grammar-file", grammar_file])
                print(f"Using grammar file: {grammar_file}")
            else:
                cmd.extend(["--grammar", grammar_content.strip()])
                print(f"Using grammar string ({len(grammar_content)} chars)")
            
            print(f"Prompt: '{prompt}'")
            print(f"Command: {' '.join(cmd[:6])} [GRAMMAR] {' '.join(cmd[7:])}")
            print("-" * 40)
            
            # Run llama-cli
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Analyze results
            success = result.returncode == 0
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            
            if success:
                # Extract generated text
                full_output = stdout
                generated = full_output[len(prompt):] if full_output.startswith(prompt) else full_output
                
                # Check grammar compliance
                grammar_compliant = self._check_grammar_compliance(generated, grammar_content)
                
                print(f"✅ SUCCESS")
                print(f"Generated: '{generated}'")
                print(f"Grammar compliant: {'✅' if grammar_compliant else '❌'}")
                
                result_summary = {
                    "test_name": test_name,
                    "success": True,
                    "full_output": full_output,
                    "generated": generated,
                    "grammar_compliant": grammar_compliant
                }
            else:
                print(f"❌ FAILED")
                print(f"Return code: {result.returncode}")
                print(f"STDERR: {stderr}")
                
                result_summary = {
                    "test_name": test_name,
                    "success": False,
                    "error": stderr,
                    "return_code": result.returncode
                }
            
            self.test_results.append(result_summary)
            return result_summary
            
        except subprocess.TimeoutExpired:
            error_msg = "Test timed out after 30 seconds"
            print(f"❌ {error_msg}")
            return {"test_name": test_name, "success": False, "error": error_msg}
        except FileNotFoundError:
            error_msg = f"llama-cli not found at {self.llama_cli_path}"
            print(f"❌ {error_msg}")
            return {"test_name": test_name, "success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            print(f"❌ {error_msg}")
            return {"test_name": test_name, "success": False, "error": error_msg}
    
    def _check_grammar_compliance(self, generated_text: str, grammar_content: str) -> bool:
        """Simple check if generated text contains grammar-compliant tokens."""
        if not generated_text or not grammar_content:
            return False
        
        # Extract expected tokens from grammar (simplified)
        expected_tokens = []
        
        # Look for quoted strings in grammar
        import re
        quoted_strings = re.findall(r'"([^"]*)"', grammar_content)
        expected_tokens.extend(quoted_strings)
        
        # Check if generated text contains any expected tokens
        for token in expected_tokens:
            if token in generated_text:
                return True
        
        return False
    
    def print_summary(self):
        """Print test summary."""
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        
        passed = 0
        total = len(self.test_results)
        
        for result in self.test_results:
            status = "✅ PASS" if result.get("success") else "❌ FAIL"
            print(f"{status}: {result['test_name']}")
            if result.get("success"):
                passed += 1
        
        print(f"\nOverall: {passed}/{total} tests passed")
        print(f"Success rate: {(passed/total)*100:.1f}%" if total > 0 else "No tests run")

def main():
    """Main test function."""
    print("🧪 ROBUST GRAMMAR TESTING")
    print("=" * 60)
    
    tester = RobustGrammarTester()
    
    # Test 1: Load and validate static grammar
    print("\n1. Testing static grammar file...")
    grammar_content = tester.load_grammar_file("data/static_grammar.gbnf")
    
    if grammar_content:
        if tester.validate_grammar_syntax(grammar_content):
            # Test with llama-cli
            tester.test_grammar_with_llama(
                grammar_content,
                '{"action": "turn on", "device": "kitchen lights"}',
                "Static grammar test"
            )
        else:
            print("❌ Grammar syntax validation failed")
    else:
        print("❌ Could not load grammar file")
    
    # Test 2: Test with grammar file
    print("\n2. Testing with grammar file...")
    if os.path.exists("data/static_grammar.gbnf"):
        tester.test_grammar_with_llama(
            None,  # No content, use file
            '{"action": "turn on", "device": "bedroom lights"}',
            "Grammar file test",
            "data/static_grammar.gbnf"
        )
    else:
        print("❌ Grammar file not found")
    
    # Test 3: Test with invalid grammar
    print("\n3. Testing error handling with invalid grammar...")
    invalid_grammar = '''root ::= "hello" | "world"
invalid_rule ::= "test" | "example"'''
    
    tester.test_grammar_with_llama(
        invalid_grammar,
        "hello",
        "Invalid grammar test"
    )
    
    # Print summary
    tester.print_summary()

if __name__ == "__main__":
    main() 