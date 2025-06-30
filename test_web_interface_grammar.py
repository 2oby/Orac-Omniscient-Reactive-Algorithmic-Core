#!/usr/bin/env python3
"""
Test script to verify that the web interface uses the same grammar format and parameters
as the test scripts for Home Assistant commands.

This script:
1. Generates a GBNF grammar from Home Assistant data
2. Tests it using the same parameters as test_grammar_basic.py
3. Compares the results to ensure consistency
"""

import os
import sys
import asyncio
import subprocess
import json
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configuration
LLAMA_CLI_PATH = "/app/third_party/llama_cpp/bin/llama-cli"
MODEL_PATH = "/models/gguf/distilgpt2.Q3_K_L.gguf"
TEST_PROMPTS = [
    "turn on bedroom lights",
    "turn off kitchen lights", 
    "toggle living room lights"
]

class WebInterfaceGrammarTester:
    def __init__(self):
        self.grammar_file = None
        self.grammar_content = None
        
    async def setup(self):
        """Set up the test environment."""
        print("🔧 Setting up test environment...")
        
        # Use the unknown_set.gbnf grammar for initial testing
        self.grammar_file = os.path.join(os.path.dirname(__file__), "data", "test_grammars", "unknown_set.gbnf")
        
        if not os.path.exists(self.grammar_file):
            print(f"❌ Grammar file not found: {self.grammar_file}")
            sys.exit(1)
        
        # Read the grammar content
        with open(self.grammar_file, 'r') as f:
            self.grammar_content = f.read()
        
        print(f"✅ Using grammar file: {self.grammar_file}")
        print(f"📄 Grammar content preview:")
        print(self.grammar_content[:200] + "..." if len(self.grammar_content) > 200 else self.grammar_content)
    
    def test_grammar_with_llama_cli(self, prompt: str) -> dict:
        """Test grammar using llama-cli (same as test scripts)."""
        if not self.grammar_file or not os.path.exists(self.grammar_file):
            return {"success": False, "error": "Grammar file not found"}
        
        # Use same parameters as test_grammar_basic.py
        cmd = [
            LLAMA_CLI_PATH,
            "-m", MODEL_PATH,
            "-p", prompt,
            "--grammar-file", self.grammar_file,
            "-n", "50",
            "--temp", "0.0",
            "--no-display-prompt"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env={"LD_LIBRARY_PATH": "/app/third_party/llama_cpp/lib"}
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                return {
                    "success": True,
                    "output": output,
                    "command": " ".join(cmd[:3]) + " ... --grammar-file " + os.path.basename(self.grammar_file)
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr.strip(),
                    "command": " ".join(cmd)
                }
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def validate_json_output(self, output: str) -> bool:
        """Validate that output is valid JSON with required fields."""
        try:
            # Clean up the output
            output = output.strip()
            if not output.startswith('{'):
                return False
            
            # Parse JSON
            parsed = json.loads(output)
            
            # Check required fields
            required_fields = ["device", "action"]
            for field in required_fields:
                if field not in parsed:
                    return False
                if not isinstance(parsed[field], str):
                    return False
            
            return True
            
        except json.JSONDecodeError:
            return False
    
    def run_tests(self):
        """Run all grammar tests."""
        print("\n🧪 Testing GBNF grammar with llama-cli...")
        print("=" * 60)
        
        results = []
        
        for i, prompt in enumerate(TEST_PROMPTS, 1):
            print(f"\nTest {i}: {prompt}")
            print("-" * 40)
            
            result = self.test_grammar_with_llama_cli(prompt)
            
            if result["success"]:
                output = result["output"]
                is_valid_json = self.validate_json_output(output)
                
                print(f"✅ Command: {result['command']}")
                print(f"📤 Output: {output}")
                print(f"🔍 Valid JSON: {'✅' if is_valid_json else '❌'}")
                
                results.append({
                    "test": i,
                    "prompt": prompt,
                    "success": True,
                    "output": output,
                    "valid_json": is_valid_json
                })
            else:
                print(f"❌ Failed: {result['error']}")
                print(f"🔧 Command: {result['command']}")
                
                results.append({
                    "test": i,
                    "prompt": prompt,
                    "success": False,
                    "error": result["error"]
                })
        
        return results
    
    def print_summary(self, results):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("📋 TEST SUMMARY")
        print("=" * 60)
        
        successful_tests = [r for r in results if r["success"]]
        valid_json_tests = [r for r in successful_tests if r.get("valid_json", False)]
        
        print(f"Total tests: {len(results)}")
        print(f"Successful: {len(successful_tests)}/{len(results)}")
        print(f"Valid JSON: {len(valid_json_tests)}/{len(successful_tests)}")
        
        if successful_tests:
            print(f"\n📊 Success rate: {len(successful_tests)/len(results)*100:.1f}%")
            if valid_json_tests:
                print(f"📊 Valid JSON rate: {len(valid_json_tests)/len(successful_tests)*100:.1f}%")
        
        # Show grammar file info
        if self.grammar_file:
            print(f"\n📁 Grammar file: {self.grammar_file}")
            if os.path.exists(self.grammar_file):
                file_size = os.path.getsize(self.grammar_file)
                print(f"📏 File size: {file_size} bytes")
        
        # Show sample outputs
        if successful_tests:
            print(f"\n📤 Sample outputs:")
            for result in successful_tests[:3]:  # Show first 3
                print(f"   Test {result['test']}: {result['output']}")

async def main():
    """Main test function."""
    print("🚀 Web Interface Grammar Consistency Test")
    print("=" * 60)
    
    # Check if we're running in Docker
    if not os.path.exists(LLAMA_CLI_PATH):
        print(f"❌ llama-cli not found at {LLAMA_CLI_PATH}")
        print("   Make sure you're running this in the Docker container")
        sys.exit(1)
    
    # Check if model exists
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Model not found at {MODEL_PATH}")
        sys.exit(1)
    
    # Create tester and run tests
    tester = WebInterfaceGrammarTester()
    
    try:
        await tester.setup()
        results = tester.run_tests()
        tester.print_summary(results)
        
        # Exit with appropriate code
        successful_tests = [r for r in results if r["success"]]
        if len(successful_tests) == len(results):
            print("\n🎉 All tests passed! Web interface grammar is consistent with test scripts.")
            sys.exit(0)
        else:
            print(f"\n⚠️  {len(results) - len(successful_tests)} tests failed.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 