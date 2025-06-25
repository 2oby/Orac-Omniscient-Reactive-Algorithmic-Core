#!/usr/bin/env python3
"""
Comprehensive debug script to test GBNF grammar format and identify parsing issues with llama.cpp.
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

class GBNFTester:
    def __init__(self):
        self.llama_cli_path = "/app/third_party/llama_cpp/bin/llama-cli"
        self.model_path = "/app/models/gguf/distilgpt2.Q4_0.gguf"
        self.test_results = []
        
    def test_grammar_with_llama(self, grammar_content, prompt, test_name, expected_outputs=None):
        """Test a grammar with llama-cli and return results."""
        print(f"\n🧪 Testing: {test_name}")
        print("=" * 60)
        
        # Create temporary grammar file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.gbnf', delete=False) as f:
            f.write(grammar_content)
            grammar_path = f.name
        
        try:
            # Build command
            cmd = [
                self.llama_cli_path,
                "-m", self.model_path,
                "-p", prompt,
                "--grammar", grammar_path,
                "-n", "5",  # Generate 5 tokens
                "--temp", "0.1",  # Low temperature for more predictable output
                "--repeat-penalty", "1.1",
                "--verbose"
            ]
            
            print(f"Command: {' '.join(cmd)}")
            print(f"Grammar:\n{grammar_content}")
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
            
            print(f"Return code: {result.returncode}")
            print(f"Execution time: {end_time - start_time:.2f}s")
            print(f"STDOUT:\n{stdout}")
            print(f"STDERR:\n{stderr}")
            
            # Check if grammar was parsed successfully
            grammar_parsed = "Failed to parse grammar" not in stderr
            grammar_used = "grammar" in stdout.lower() or "constraint" in stdout.lower()
            
            # Check if output matches expected
            output_matches = False
            if expected_outputs and stdout:
                for expected in expected_outputs:
                    if expected.lower() in stdout.lower():
                        output_matches = True
                        break
            
            result_summary = {
                "test_name": test_name,
                "success": success,
                "grammar_parsed": grammar_parsed,
                "grammar_used": grammar_used,
                "output_matches": output_matches,
                "stdout": stdout,
                "stderr": stderr,
                "execution_time": end_time - start_time
            }
            
            self.test_results.append(result_summary)
            
            # Print summary
            status_emoji = "✅" if success and grammar_parsed else "❌"
            print(f"\n{status_emoji} Test Result: {'PASS' if success and grammar_parsed else 'FAIL'}")
            print(f"   - Grammar parsed: {'✅' if grammar_parsed else '❌'}")
            print(f"   - Grammar used: {'✅' if grammar_used else '❌'}")
            print(f"   - Output matches: {'✅' if output_matches else '❌'}")
            
            return result_summary
            
        except subprocess.TimeoutExpired:
            print("❌ Test timed out after 30 seconds")
            return {"test_name": test_name, "success": False, "error": "timeout"}
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            return {"test_name": test_name, "success": False, "error": str(e)}
        finally:
            # Clean up temporary file
            try:
                os.unlink(grammar_path)
            except:
                pass

async def debug_gbnf():
    """Debug the GBNF grammar format."""
    
    print("=== Comprehensive GBNF Grammar Debug ===\n")
    
    tester = GBNFTester()
    
    # Test 1: Simplest possible grammar
    print("\n" + "="*80)
    print("TEST 1: Simplest Grammar")
    print("="*80)
    
    simple_grammar = '''root ::= word
word ::= "hello" | "world" | "test"'''
    
    tester.test_grammar_with_llama(
        simple_grammar,
        "hello",
        "Simple word selection",
        ["hello", "world", "test"]
    )
    
    # Test 2: JSON object grammar
    print("\n" + "="*80)
    print("TEST 2: JSON Object Grammar")
    print("="*80)
    
    json_grammar = '''root ::= object
object ::= "{" ws (string ":" ws value ("," ws string ":" ws value)*)? ws "}"
value ::= string | number | boolean | null
string ::= "\\"" ([^"\\\\] | "\\\\" (["\\\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F]))* "\\""
number ::= "-"? ([0-9] | [1-9] [0-9]*) ("." [0-9]+)? ([eE] [-+]? [0-9]+)?
boolean ::= "true" | "false"
null ::= "null"
ws ::= [ \\t\\n\\r]*'''
    
    tester.test_grammar_with_llama(
        json_grammar,
        '{"name": "test"}',
        "JSON object generation",
        ["{", "}", "name", "test"]
    )
    
    # Test 3: Device-specific grammar
    print("\n" + "="*80)
    print("TEST 3: Device-Specific Grammar")
    print("="*80)
    
    device_grammar = '''root ::= object
object ::= "{" ws device_string "," ws action_string ws "}"
device_string ::= "\"device\"" ":" ws "\"" device_value "\""
action_string ::= "\"action\"" ":" ws "\"" action_value "\""
device_value ::= "bedroom lights" | "bathroom lights" | "kitchen lights"
action_value ::= "turn on" | "turn off" | "toggle"
ws ::= [ \t\n\r]*'''
    
    tester.test_grammar_with_llama(
        device_grammar,
        '{"device": "bedroom lights", "action": "turn on"}',
        "Device control generation",
        ["bedroom lights", "bathroom lights", "kitchen lights", "turn on", "turn off"]
    )
    
    # Test 4: Complex Home Assistant grammar
    print("\n" + "="*80)
    print("TEST 4: Complex Home Assistant Grammar")
    print("="*80)
    
    try:
        # Initialize Home Assistant components
        config = HomeAssistantConfig.from_yaml("orac/homeassistant/config.yaml")
        
        async with HomeAssistantClient(config) as client:
            # Initialize mapping config and grammar manager
            mapping_config = EntityMappingConfig(client=client)
            grammar_manager = HomeAssistantGrammarManager(client, mapping_config)
            
            print("Generating Home Assistant grammar...")
            
            # Generate grammar dictionary
            grammar_dict = await grammar_manager.generate_grammar()
            
            # Extract vocabulary for analysis
            device_vocab = grammar_dict.get("properties", {}).get("device", {}).get("enum", [])
            action_vocab = grammar_dict.get("properties", {}).get("action", {}).get("enum", [])
            location_vocab = grammar_dict.get("properties", {}).get("location", {}).get("enum", [])
            
            print(f"Vocabulary sizes: {len(device_vocab)} devices, {len(action_vocab)} actions, {len(location_vocab)} locations")
            
            # Generate GBNF grammar string
            gbnf_grammar = grammar_manager.generate_gbnf_grammar(grammar_dict)
            
            # Test with a simple prompt
            tester.test_grammar_with_llama(
                gbnf_grammar,
                '{"device": "bedroom lights", "action": "turn on"}',
                "Full Home Assistant grammar",
                device_vocab[:3] + action_vocab[:3]  # Check for first few items
            )
            
    except Exception as e:
        print(f"❌ Error generating Home Assistant grammar: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 5: Grammar with special characters
    print("\n" + "="*80)
    print("TEST 5: Grammar with Special Characters")
    print("="*80)
    
    special_grammar = '''root ::= object
object ::= "{" ws string ":" ws value ws "}"
string ::= "\"" string_content "\""
string_content ::= "device" | "action" | "location"
value ::= "\"" value_content "\""
value_content ::= "bedroom\\"lights" | "bathroom\\"lights" | "kitchen\\"lights"
ws ::= [ \t\n\r]*'''
    
    tester.test_grammar_with_llama(
        special_grammar,
        '{"device": "bedroom\\"lights"}',
        "Grammar with escaped quotes",
        ["bedroom\"lights", "bathroom\"lights"]
    )
    
    # Test 6: Very long alternation rule
    print("\n" + "="*80)
    print("TEST 6: Long Alternation Rule")
    print("="*80)
    
    # Create a grammar with many alternatives
    long_alternatives = [f"device{i}" for i in range(50)]
    device_rule_parts = [f'"{d}"' for d in long_alternatives]
    long_grammar = f'''root ::= device_value
device_value ::= {" | ".join(device_rule_parts)}'''
    
    tester.test_grammar_with_llama(
        long_grammar,
        "device1",
        "Long alternation rule (50 devices)",
        long_alternatives[:5]  # Check for first few
    )
    
    # Test 7: Most minimal grammar (letters and digits)
    print("\n" + "="*80)
    print("TEST 7: Most Minimal Grammar (letters and digits)")
    print("="*80)
    
    minimal_grammar = '''root ::= "a" | "b" | "c" | "1" | "2" | "3"'''
    
    tester.test_grammar_with_llama(
        minimal_grammar,
        "a",
        "Most minimal grammar (a, b, c, 1, 2, 3)",
        ["a", "b", "c", "1", "2", "3"]
    )
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = 0
    total = len(tester.test_results)
    
    for result in tester.test_results:
        status = "✅ PASS" if result.get("success") and result.get("grammar_parsed") else "❌ FAIL"
        print(f"{status}: {result['test_name']}")
        if result.get("success") and result.get("grammar_parsed"):
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    # Recommendations
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    
    if passed == 0:
        print("❌ All tests failed - Check llama.cpp installation and GBNF support")
        print("   - Verify llama.cpp version supports GBNF")
        print("   - Check if llama-cli binary is working")
        print("   - Try running llama-cli without grammar first")
    elif passed < total:
        print("⚠️  Some tests failed - Grammar complexity may be the issue")
        print("   - Simplify complex grammars")
        print("   - Check for special characters in vocabulary")
        print("   - Reduce vocabulary size")
    else:
        print("✅ All tests passed - Grammar system is working correctly")
    
    print("\n=== GBNF Debug Complete ===")

if __name__ == "__main__":
    asyncio.run(debug_gbnf()) 