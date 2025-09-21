#!/usr/bin/env python3
"""
Test script to verify that the new set_temp.gbnf grammar works correctly.

This script tests the new grammar file that supports temperature and percentage
commands for Home Assistant devices.
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
GRAMMAR_FILE = "/app/data/grammars/set_temp.gbnf"
API_BASE_URL = "http://localhost:8000"

TEST_PROMPTS = [
    # Temperature commands
    "set heating to 22C",
    "set thermostat to 18C", 
    "set temperature to 25C",
    
    # Percentage commands
    "set lights to 50%",
    "set music volume to 75%",
    "set brightness to 30%",
    
    # Mixed commands
    "turn on bedroom lights",
    "set kitchen heating to 20C",
    "set living room music to 60%"
]

class SetTempGrammarTester:
    def __init__(self):
        self.llama_cli_path = LLAMA_CLI_PATH
        self.model_path = MODEL_PATH
        self.grammar_file = GRAMMAR_FILE
        self.api_base_url = API_BASE_URL
    
    def test_grammar_with_llama_cli(self, prompt: str) -> dict:
        """Test grammar using llama-cli directly."""
        try:
            # Use the optimized system prompt
            system_prompt = "You are a JSON-only formatter. For each user input, accurately interpret the intended command and respond with a single-line JSON object containing the keys: \"device\", \"action\", and \"location\". Match the \"device\" to the user-specified device (e.g., \"heating\" for heating, \"blinds\" for blinds) and select the \"action\" most appropriate for that device (e.g., \"on\", \"off\" for heating; \"open\", \"close\" for blinds) based on the provided grammar. Use \"UNKNOWN\" for unrecognized inputs. Output only the JSON object without explanations or additional text."
            
            # Format prompt like the CLI test
            formatted_prompt = f"{system_prompt}\n\nUser: {prompt}\nAssistant: {{\"device\":\""
            
            cmd = [
                self.llama_cli_path,
                "-m", self.model_path,
                "--grammar-file", self.grammar_file,
                "--temp", "0.1",
                "--top-p", "0.9", 
                "--top-k", "10",
                "--repeat-penalty", "1.1",
                "-n", "50",
                "-p", formatted_prompt
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
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
                f"{self.api_base_url}/v1/generate",
                json={
                    "prompt": prompt,
                    "system_prompt": "You are a JSON-only formatter. For each user input, accurately interpret the intended command and respond with a single-line JSON object containing the keys: \"device\", \"action\", and \"location\". Match the \"device\" to the user-specified device (e.g., \"heating\" for heating, \"blinds\" for blinds) and select the \"action\" most appropriate for that device (e.g., \"on\", \"off\" for heating; \"open\", \"close\" for blinds) based on the provided grammar. Use \"UNKNOWN\" for unrecognized inputs. Output only the JSON object without explanations or additional text.",
                    "json_mode": True,
                    "grammar_file": self.grammar_file,
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "top_k": 10,
                    "max_tokens": 50
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "output": data.get("response", ""),
                    "command": f"POST {self.api_base_url}/v1/generate"
                }
            else:
                return {
                    "success": False,
                    "error": f"API error: {response.status_code} - {response.text}",
                    "command": f"POST {self.api_base_url}/v1/generate"
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
    
    def analyze_temperature_commands(self, output: str) -> dict:
        """Analyze if temperature commands are correctly parsed."""
        try:
            parsed = json.loads(output)
            action = parsed.get("action", "")
            
            # Check for temperature patterns
            if "set" in action and ("C" in action or "%" in action):
                return {
                    "is_temperature": "C" in action,
                    "is_percentage": "%" in action,
                    "value": action.split(" ")[-1] if " " in action else action,
                    "correct_format": True
                }
            else:
                return {
                    "is_temperature": False,
                    "is_percentage": False,
                    "value": None,
                    "correct_format": False
                }
        except:
            return {
                "is_temperature": False,
                "is_percentage": False,
                "value": None,
                "correct_format": False
            }
    
    async def run_tests(self):
        """Run all set_temp grammar tests."""
        print("\n🧪 Testing set_temp.gbnf Grammar")
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
                cli_analysis = self.analyze_temperature_commands(cli_result["output"])
                print(f"   CLI Output: {cli_result['output']}")
                print(f"   CLI Valid JSON: {'✅' if cli_valid else '❌'}")
                if cli_analysis["correct_format"]:
                    print(f"   CLI Analysis: {'🌡️' if cli_analysis['is_temperature'] else '📊' if cli_analysis['is_percentage'] else '⚙️'} {cli_analysis['value']}")
            else:
                print(f"   CLI Error: {cli_result['error']}")
                cli_valid = False
                cli_analysis = {"correct_format": False}
            
            # Test with API
            print("🌐 Testing with API...")
            api_result = await self.test_grammar_with_api(prompt)
            
            if api_result["success"]:
                api_valid = self.validate_json_output(api_result["output"])
                api_analysis = self.analyze_temperature_commands(api_result["output"])
                print(f"   API Output: {api_result['output']}")
                print(f"   API Valid JSON: {'✅' if api_valid else '❌'}")
                if api_analysis["correct_format"]:
                    print(f"   API Analysis: {'🌡️' if api_analysis['is_temperature'] else '📊' if api_analysis['is_percentage'] else '⚙️'} {api_analysis['value']}")
            else:
                print(f"   API Error: {api_result['error']}")
                api_valid = False
                api_analysis = {"correct_format": False}
            
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
                "cli_analysis": cli_analysis,
                "api_success": api_result["success"],
                "api_valid": api_valid,
                "api_analysis": api_analysis,
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
        
        # Temperature/Percentage analysis
        temp_commands = sum(1 for r in results if r["api_analysis"]["is_temperature"])
        pct_commands = sum(1 for r in results if r["api_analysis"]["is_percentage"])
        
        print(f"Total Tests: {total_tests}")
        print(f"CLI Success: {cli_success}/{total_tests}")
        print(f"CLI Valid JSON: {cli_valid}/{total_tests}")
        print(f"API Success: {api_success}/{total_tests}")
        print(f"API Valid JSON: {api_valid}/{total_tests}")
        print(f"Outputs Match: {outputs_match}/{total_tests}")
        print(f"Temperature Commands: {temp_commands}/{total_tests}")
        print(f"Percentage Commands: {pct_commands}/{total_tests}")
        
        if api_valid == total_tests:
            print("\n🎉 SUCCESS: set_temp.gbnf grammar is working correctly!")
            return True
        else:
            print("\n⚠️  ISSUES: Some tests failed.")
            return False

async def main():
    """Main test function."""
    print("🚀 set_temp.gbnf Grammar Testing")
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
    tester = SetTempGrammarTester()
    success = await tester.run_tests()
    
    if success:
        print("\n✅ All tests passed! The set_temp.gbnf grammar is working correctly.")
        return 0
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 