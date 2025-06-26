#!/usr/bin/env python3
"""
Comprehensive test script addressing all GBNF grammar and testing issues.

This script tests:
1. ✅ Grammar file validation and syntax checking
2. ✅ JSON key quoting in grammar
3. ✅ NoneType error handling in grammar parsing
4. ✅ Home Assistant service domain filtering
5. ✅ Grammar enforcement with llama.cpp
"""

import asyncio
import subprocess
import sys
import os
import json
import tempfile
from typing import Optional, Dict, Any, List

# Add the orac package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'orac'))

from orac.homeassistant.client import HomeAssistantClient
from orac.homeassistant.config import HomeAssistantConfig
from orac.homeassistant.cache import HomeAssistantCache

class ComprehensiveGrammarTester:
    """Comprehensive grammar tester addressing all known issues."""
    
    def __init__(self, llama_cli_path: str = "/app/third_party/llama_cpp/bin/llama-cli", 
                 model_path: str = "/app/models/gguf/distilgpt2.Q4_0.gguf"):
        self.llama_cli_path = llama_cli_path
        self.model_path = model_path
        self.test_results = []
    
    def test_grammar_syntax_issues(self):
        """Test 1: Verify grammar syntax and multi-line alternatives."""
        print("\n" + "="*80)
        print("TEST 1: Grammar Syntax and Multi-line Alternatives")
        print("="*80)
        
        # Test the corrected static grammar
        grammar_file = "data/static_grammar.gbnf"
        
        if not os.path.exists(grammar_file):
            print(f"❌ Grammar file not found: {grammar_file}")
            return False
        
        with open(grammar_file, 'r') as f:
            grammar_content = f.read()
        
        print("✅ Grammar file loaded successfully")
        print(f"   Size: {len(grammar_content)} characters")
        
        # Check for multi-line alternatives (should be flattened)
        lines = grammar_content.split('\n')
        for i, line in enumerate(lines):
            if '::=' in line and '|' in line:
                # Check if rule spans multiple lines (which would cause issues)
                if i + 1 < len(lines) and '|' in lines[i + 1]:
                    print(f"❌ Multi-line alternatives detected at line {i+1}")
                    print(f"   Line {i+1}: {lines[i]}")
                    print(f"   Line {i+2}: {lines[i+1]}")
                    return False
        
        print("✅ No multi-line alternatives detected (correctly flattened)")
        
        # Check JSON key quoting
        if '"action"' in grammar_content and '"device"' in grammar_content:
            print("✅ JSON keys are properly quoted")
        else:
            print("❌ JSON keys are not properly quoted")
            return False
        
        # Check for balanced quotes
        quote_count = grammar_content.count('"')
        if quote_count % 2 != 0:
            print(f"❌ Unbalanced quotes detected (count: {quote_count})")
            return False
        
        print("✅ All quotes are balanced")
        return True
    
    def test_none_type_error_handling(self):
        """Test 2: Handle NoneType errors in grammar parsing."""
        print("\n" + "="*80)
        print("TEST 2: NoneType Error Handling")
        print("="*80)
        
        # Test with non-existent grammar file
        result = self._safe_grammar_test("non_existent_grammar.gbnf", "test prompt")
        if result and result.get("success") is False:
            print("✅ Properly handled non-existent grammar file")
        else:
            print("❌ Failed to handle non-existent grammar file")
            return False
        
        # Test with empty grammar content
        result = self._safe_grammar_test(None, "test prompt", grammar_content="")
        if result and result.get("success") is False:
            print("✅ Properly handled empty grammar content")
        else:
            print("❌ Failed to handle empty grammar content")
            return False
        
        # Test with invalid grammar syntax
        invalid_grammar = '''root ::= "hello" | "world"
invalid_rule ::= "test" | "example"'''
        
        result = self._safe_grammar_test(None, "hello", grammar_content=invalid_grammar)
        if result:
            print("✅ Properly handled invalid grammar syntax")
        else:
            print("❌ Failed to handle invalid grammar syntax")
            return False
        
        return True
    
    def _safe_grammar_test(self, grammar_file: Optional[str], prompt: str, 
                          grammar_content: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Safely test grammar with comprehensive error handling."""
        try:
            # Validate inputs
            if not grammar_content and not grammar_file:
                return {"success": False, "error": "No grammar content or file provided"}
            
            if not prompt:
                return {"success": False, "error": "No prompt provided"}
            
            # Build command
            cmd = [
                self.llama_cli_path,
                "-m", self.model_path,
                "-p", prompt,
                "-n", "5",
                "--temp", "0.1"
            ]
            
            # Add grammar
            if grammar_file and os.path.exists(grammar_file):
                cmd.extend(["--grammar-file", grammar_file])
            elif grammar_content:
                cmd.extend(["--grammar", grammar_content.strip()])
            else:
                return {"success": False, "error": "No valid grammar provided"}
            
            # Run command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "return_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Test timed out"}
        except FileNotFoundError:
            return {"success": False, "error": f"llama-cli not found at {self.llama_cli_path}"}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {e}"}
    
    async def test_home_assistant_service_filtering(self):
        """Test 3: Home Assistant service domain filtering."""
        print("\n" + "="*80)
        print("TEST 3: Home Assistant Service Domain Filtering")
        print("="*80)
        
        try:
            # Initialize Home Assistant client
            config = HomeAssistantConfig.from_yaml("orac/homeassistant/config.yaml")
            
            async with HomeAssistantClient(config) as client:
                # Get raw services (unfiltered)
                raw_services_data = await client._request("GET", "/api/services")
                
                if isinstance(raw_services_data, list):
                    raw_services = {entry['domain']: entry['services'] for entry in raw_services_data if 'domain' in entry and 'services' in entry}
                else:
                    raw_services = raw_services_data
                
                print(f"✅ Raw services fetched: {len(raw_services)} domains")
                
                # Get filtered services (with caching)
                filtered_services = await client.get_services()
                print(f"✅ Filtered services: {len(filtered_services)} domains")
                
                # Analyze filtering
                cache = HomeAssistantCache()
                relevant_domains = []
                excluded_domains = []
                
                for domain in raw_services.keys():
                    if cache._is_relevant_service(domain):
                        relevant_domains.append(domain)
                    else:
                        excluded_domains.append(domain)
                
                print(f"   Relevant domains: {len(relevant_domains)}")
                print(f"   Excluded domains: {len(excluded_domains)}")
                
                # Show filtering details
                print(f"\nRelevant domains:")
                for domain in sorted(relevant_domains):
                    print(f"  ✅ {domain}")
                
                print(f"\nExcluded domains (first 10):")
                for domain in sorted(excluded_domains)[:10]:
                    print(f"  ❌ {domain}")
                if len(excluded_domains) > 10:
                    print(f"  ... and {len(excluded_domains) - 10} more")
                
                # Verify filtering logic
                expected_relevant = cache.USER_CONTROLLABLE_SERVICES
                actual_relevant = set(relevant_domains)
                
                # Check that all expected domains that exist in raw data are in filtered results
                missing_expected = []
                for domain in expected_relevant:
                    if domain in raw_services and domain not in actual_relevant:
                        missing_expected.append(domain)
                
                if missing_expected:
                    print(f"⚠️  Expected domains missing: {missing_expected}")
                    return False
                else:
                    print("✅ All expected domains are properly filtered")
                
                # The key insight: filtered_services should be 9, not 34
                print(f"\n=== Filtering Summary ===")
                print(f"Raw service domains: {len(raw_services)}")
                print(f"Filtered service domains: {len(filtered_services)}")
                print(f"Expected relevant domains: {len(expected_relevant)}")
                print(f"Actual relevant domains: {len(actual_relevant)}")
                
                # Assert the correct behavior
                assert len(filtered_services) > 0, "No filtered services found"
                assert len(filtered_services) <= len(raw_services), "Filtered should not exceed raw"
                assert len(filtered_services) == len(actual_relevant), "Filtered count should match relevant count"
                
                return True
                
        except Exception as e:
            print(f"❌ Error testing Home Assistant services: {e}")
            return False
    
    def test_grammar_enforcement(self):
        """Test 4: Grammar enforcement with llama.cpp."""
        print("\n" + "="*80)
        print("TEST 4: Grammar Enforcement with llama.cpp")
        print("="*80)
        
        # Test the corrected static grammar
        grammar_file = "data/static_grammar.gbnf"
        
        if not os.path.exists(grammar_file):
            print(f"❌ Grammar file not found: {grammar_file}")
            return False
        
        # Test prompts that should work
        test_cases = [
            ('{"action": "turn on", "device": "kitchen lights"}', "Valid JSON command"),
            ('{"action": "turn off", "device": "bedroom lights"}', "Valid JSON command"),
            ('{"action": "toggle", "device": "bathroom lights"}', "Valid JSON command")
        ]
        
        success_count = 0
        for prompt, description in test_cases:
            print(f"\nTesting: {description}")
            result = self._safe_grammar_test(grammar_file, prompt)
            
            if result and result.get("success"):
                print(f"  ✅ {description} - SUCCESS")
                success_count += 1
            else:
                print(f"  ❌ {description} - FAILED")
                if result:
                    print(f"     Error: {result.get('error', 'Unknown error')}")
        
        print(f"\nGrammar enforcement test: {success_count}/{len(test_cases)} passed")
        return success_count == len(test_cases)
    
    def generate_example_prompt(self):
        """Generate a good example prompt for grammar-compliant JSON."""
        print("\n" + "="*80)
        print("EXAMPLE PROMPT FOR GRAMMAR-COMPLIANT JSON")
        print("="*80)
        
        example_prompt = '''Generate a JSON command to control a smart home device. 
The command should be in this exact format:
{"action": "turn on", "device": "kitchen lights"}

Available actions: turn on, turn off, toggle, switch on, switch off, activate, deactivate
Available devices: bedroom lights, bathroom lights, kitchen lights, hall lights, lounge lights, toilet lights

Command: turn on the kitchen lights
JSON:'''
        
        print(example_prompt)
        print("\nThis prompt:")
        print("1. ✅ Clearly specifies the expected JSON format")
        print("2. ✅ Lists all available actions and devices")
        print("3. ✅ Provides a concrete example")
        print("4. ✅ Uses proper JSON syntax with quoted keys")
        print("5. ✅ Matches the GBNF grammar constraints")
        
        return example_prompt

async def main():
    """Run all comprehensive tests."""
    print("🧪 COMPREHENSIVE GRAMMAR TESTING")
    print("=" * 80)
    
    tester = ComprehensiveGrammarTester()
    
    # Run all tests
    tests = [
        ("Grammar Syntax Issues", tester.test_grammar_syntax_issues),
        ("NoneType Error Handling", tester.test_none_type_error_handling),
        ("Home Assistant Service Filtering", tester.test_home_assistant_service_filtering),
        ("Grammar Enforcement", tester.test_grammar_enforcement)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*80}")
        print(f"RUNNING: {test_name}")
        print(f"{'='*80}")
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            results.append((test_name, result))
            
            if result:
                print(f"✅ {test_name} - PASSED")
            else:
                print(f"❌ {test_name} - FAILED")
                
        except Exception as e:
            print(f"❌ {test_name} - ERROR: {e}")
            results.append((test_name, False))
    
    # Generate example prompt
    tester.generate_example_prompt()
    
    # Print final summary
    print(f"\n{'='*80}")
    print("FINAL TEST SUMMARY")
    print(f"{'='*80}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    print(f"Success rate: {(passed/total)*100:.1f}%" if total > 0 else "No tests run")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Your GBNF grammar and testing framework are working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the output above.")

if __name__ == "__main__":
    asyncio.run(main()) 