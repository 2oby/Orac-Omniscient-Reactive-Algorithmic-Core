#!/usr/bin/env python3
"""
Test script to verify that the API grammar fix works correctly.

This script compares the output of the API with the CLI test to ensure
they produce the same results when using grammar files.
"""

import os
import sys
import asyncio
import subprocess
import json
import requests
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configuration
LLAMA_CLI_PATH = "/app/third_party/llama_cpp/bin/llama-cli"
MODEL_PATH = "/models/gguf/distilgpt2.Q3_K_L.gguf"
GRAMMAR_FILE = "/app/data/grammars/unknown_set.gbnf"
API_BASE_URL = "http://localhost:8000"

TEST_PROMPTS = [
    "turn on bedroom lights",
    "turn off kitchen lights", 
    "toggle living room lights"
]

class APIGrammarTester:
    def __init__(self):
        self.grammar_file = GRAMMAR_FILE
        
    def test_grammar_with_llama_cli(self, prompt: str) -> dict:
        """Test grammar using llama-cli (same as test scripts)."""
        if not os.path.exists(self.grammar_file):
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
    
    async def test_grammar_with_api(self, prompt: str) -> dict:
        """Test grammar using the API."""
        try:
            response = requests.post(
                f"{API_BASE_URL}/v1/generate",
                json={
                    "prompt": prompt,
                    "system_prompt": "You are a Home Assistant command parser. Parse the user's command into a JSON object with device, action, and location fields.",
                    "json_mode": True,
                    "grammar_file": self.grammar_file,
                    "temperature": 0.0,
                    "top_p": 0.8,
                    "top_k": 30,
                    "max_tokens": 50
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "output": data.get("response", ""),
                    "command": f"POST {API_BASE_URL}/v1/generate"
                }
            else:
                return {
                    "success": False,
                    "error": f"API error: {response.status_code} - {response.text}",
                    "command": f"POST {API_BASE_URL}/v1/generate"
                }
                
        except requests.exceptions.Timeout:
            return {"success": False, "error": "API request timed out"}
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
            required_fields = ["device", "action", "location"]
            for field in required_fields:
                if field not in parsed:
                    return False
                if not isinstance(parsed[field], str):
                    return False
            
            return True
            
        except json.JSONDecodeError:
            return False
    
    async def run_tests(self):
        """Run all grammar tests."""
        print("\n🧪 Testing API Grammar Fix")
        print("=" * 60)
        
        results = []
        
        for i, prompt in enumerate(TEST_PROMPTS, 1):
            print(f"\n📝 Test {i}: {prompt}")
            print("-" * 40)
            
            # Test with CLI
            print("🔧 Testing with llama-cli...")
            cli_result = self.test_grammar_with_llama_cli(prompt)
            
            if cli_result["success"]:
                cli_valid = self.validate_json_output(cli_result["output"])
                print(f"   CLI Output: {cli_result['output']}")
                print(f"   CLI Valid JSON: {'✅' if cli_valid else '❌'}")
            else:
                print(f"   CLI Error: {cli_result['error']}")
                cli_valid = False
            
            # Test with API
            print("🌐 Testing with API...")
            api_result = await self.test_grammar_with_api(prompt)
            
            if api_result["success"]:
                api_valid = self.validate_json_output(api_result["output"])
                print(f"   API Output: {api_result['output']}")
                print(f"   API Valid JSON: {'✅' if api_valid else '❌'}")
            else:
                print(f"   API Error: {api_result['error']}")
                api_valid = False
            
            # Compare results
            if cli_result["success"] and api_result["success"]:
                outputs_match = cli_result["output"] == api_result["output"]
                print(f"   Outputs Match: {'✅' if outputs_match else '❌'}")
                
                if not outputs_match:
                    print(f"   CLI: {cli_result['output']}")
                    print(f"   API: {api_result['output']}")
            else:
                outputs_match = False
            
            results.append({
                "prompt": prompt,
                "cli_success": cli_result["success"],
                "cli_valid": cli_valid,
                "api_success": api_result["success"],
                "api_valid": api_valid,
                "outputs_match": outputs_match
            })
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(results)
        cli_success = sum(1 for r in results if r["cli_success"])
        cli_valid = sum(1 for r in results if r["cli_valid"])
        api_success = sum(1 for r in results if r["api_success"])
        api_valid = sum(1 for r in results if r["api_valid"])
        outputs_match = sum(1 for r in results if r["outputs_match"])
        
        print(f"Total Tests: {total_tests}")
        print(f"CLI Success: {cli_success}/{total_tests}")
        print(f"CLI Valid JSON: {cli_valid}/{total_tests}")
        print(f"API Success: {api_success}/{total_tests}")
        print(f"API Valid JSON: {api_valid}/{total_tests}")
        print(f"Outputs Match: {outputs_match}/{total_tests}")
        
        if api_valid == total_tests and outputs_match == total_tests:
            print("\n🎉 SUCCESS: API grammar fix is working correctly!")
            return True
        else:
            print("\n⚠️  ISSUES: Some tests failed or outputs don't match.")
            return False

async def main():
    """Main test function."""
    print("🚀 API Grammar Fix Testing")
    print("=" * 50)
    
    # Check if we're running in Docker
    if not os.path.exists(LLAMA_CLI_PATH):
        print(f"❌ llama-cli not found at {LLAMA_CLI_PATH}")
        print("   Make sure you're running this in the Docker container")
        sys.exit(1)
    
    # Check if grammar file exists
    if not os.path.exists(GRAMMAR_FILE):
        print(f"❌ Grammar file not found: {GRAMMAR_FILE}")
        sys.exit(1)
    
    # Check if API is running
    try:
        response = requests.get(f"{API_BASE_URL}/v1/status", timeout=5)
        if response.status_code != 200:
            print(f"❌ API is not responding correctly: {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Cannot connect to API at {API_BASE_URL}: {e}")
        print("   Make sure the API server is running")
        sys.exit(1)
    
    print(f"✅ API is running at {API_BASE_URL}")
    print(f"✅ Grammar file found: {GRAMMAR_FILE}")
    
    # Run tests
    tester = APIGrammarTester()
    success = await tester.run_tests()
    
    if success:
        print("\n✅ All tests passed! The API grammar fix is working correctly.")
        return 0
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 