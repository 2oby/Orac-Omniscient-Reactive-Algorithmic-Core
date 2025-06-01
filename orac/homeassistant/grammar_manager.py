# This file will contain the HomeAssistantGrammarManager class that handles the generation
# and management of grammars for Home Assistant commands. It will discover entities and
# services, generate appropriate grammar rules, and maintain the grammar files used
# by the LLM for understanding and validating Home Assistant commands.

"""
Grammar management for Home Assistant integration.

This module handles the generation and management of JSON grammars for LLM inference,
including:
- Dynamic grammar generation from Home Assistant entities and services
- Constraint management for devices, actions, and locations
- Mapping between generic terms and specific entity IDs
- Integration with grammars.yaml for configuration
- Support for manual additions and auto-discovery

The grammar manager ensures that LLM outputs are constrained to valid
Home Assistant commands while maintaining user-friendly terminology.
"""
