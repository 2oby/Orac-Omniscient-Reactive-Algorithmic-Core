#!/usr/bin/env python3
"""
Test script to check grammar generation output.
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orac.homeassistant.client import HomeAssistantClient
from orac.homeassistant.config import HomeAssistantConfig
from orac.homeassistant.grammar_manager import HomeAssistantGrammarManager

async def test_grammar_generation():
    """Test grammar generation and output the result."""
    
    print("Testing grammar generation...")
    
    try:
        # Initialize Home Assistant components
        config = HomeAssistantConfig.from_yaml("orac/homeassistant/config.yaml")
        
        async with HomeAssistantClient(config) as client:
            # Initialize grammar manager
            grammar_manager = HomeAssistantGrammarManager(client)
            
            print("Generating grammar...")
            
            # Generate grammar dictionary
            grammar_dict = await grammar_manager.generate_grammar()
            
            # Generate GBNF grammar string
            gbnf_grammar = grammar_manager.generate_gbnf_grammar(grammar_dict)
            
            print("\n=== GENERATED GRAMMAR ===")
            print("Length:", len(gbnf_grammar))
            print("First 500 chars:")
            print(repr(gbnf_grammar[:500]))
            print("\nFull grammar:")
            print(gbnf_grammar)
            print("=== END GRAMMAR ===")
            
            # Check for potential issues
            print("\n=== GRAMMAR ANALYSIS ===")
            print("Contains 'root ::=':", "root ::=" in gbnf_grammar)
            print("Number of 'root ::=' occurrences:", gbnf_grammar.count("root ::="))
            print("Number of newlines:", gbnf_grammar.count("\n"))
            print("Number of '::=' occurrences:", gbnf_grammar.count("::="))
            
            # Check for duplicate rules
            lines = gbnf_grammar.split("\n")
            rule_names = []
            for line in lines:
                if "::=" in line:
                    rule_name = line.split("::=")[0].strip()
                    rule_names.append(rule_name)
            
            print("Rule names found:", rule_names)
            print("Duplicate rules:", [name for name in set(rule_names) if rule_names.count(name) > 1])
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_grammar_generation()) 