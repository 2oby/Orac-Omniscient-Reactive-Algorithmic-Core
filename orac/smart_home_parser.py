"""
orac.smart_home_parser
---------------------
Smart Home JSON Grammar Parser for ORAC

This module provides a specialized parser for converting natural language
commands into structured JSON format using llama.cpp with GBNF grammar.
It integrates seamlessly with the existing ORAC LlamaCppClient.
"""

import json
import os
from typing import Dict, List, Optional, Any
from pathlib import Path

from orac.llama_cpp_client import LlamaCppClient
from orac.logger import get_logger

logger = get_logger(__name__)

class SmartHomeParser:
    """
    Smart Home JSON Grammar Parser
    
    Converts natural language commands into structured JSON format using
    llama.cpp with GBNF grammar constraints.
    """
    
    def __init__(self, model_path: str, grammar_path: str = "data/smart_home.gbnf"):
        """
        Initialize the Smart Home Parser.
        
        Args:
            model_path: Path to the GGUF model file
            grammar_path: Path to the GBNF grammar file
        """
        self.model_path = model_path
        self.grammar_path = grammar_path
        self.model_name = os.path.basename(model_path)
        
        # System prompt for JSON-only formatting
        self.system_prompt = (
            "You are a JSON-only formatter. For each user input, respond with a "
            "single-line JSON object containing exactly these keys: \"action\" "
            "and \"device\". Do not include any explanations, comments, or "
            "additional text. Only output the JSON object."
        )
        
        # Initialize the LlamaCppClient
        self.client = LlamaCppClient(model_path=model_path)
        
        # Load the grammar
        self.grammar = self._load_grammar()
        
        logger.info(f"SmartHomeParser initialized with model: {model_path}")
    
    def _load_grammar(self) -> str:
        """Load the GBNF grammar from file."""
        try:
            with open(self.grammar_path, 'r') as f:
                grammar = f.read()
            logger.debug(f"Loaded grammar from {self.grammar_path}")
            return grammar
        except FileNotFoundError:
            logger.error(f"Grammar file not found: {self.grammar_path}")
            raise
        except Exception as e:
            logger.error(f"Error loading grammar: {e}")
            raise
    
    async def parse_command(self, user_input: str) -> Dict[str, str]:
        """
        Parse a natural language command into structured JSON.
        
        Args:
            user_input: Natural language command (e.g., "Turn on the bathroom lights")
            
        Returns:
            Dictionary with "action" and "device" keys
        """
        try:
            # Construct the full prompt
            full_prompt = (
                f"{self.system_prompt}\n\n"
                f"User: {user_input}\n"
                f"Assistant: {{\"action\": "
            )
            
            # Generate response using custom grammar
            response = await self.client.generate_with_custom_grammar(
                prompt=full_prompt,
                model=self.model_name,
                custom_grammar=self.grammar,
                temperature=0.0,
                max_tokens=50,
                system_prompt=self.system_prompt,
                verbose=False
            )
            
            # Complete the JSON
            full_json = '{"action": ' + response.text.strip()
            
            # Parse the JSON
            result = json.loads(full_json)
            
            logger.debug(f"Parsed '{user_input}' -> {result}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for input '{user_input}': {e}")
            return {"action": "error", "device": "unknown"}
        except Exception as e:
            logger.error(f"Error parsing command '{user_input}': {e}")
            return {"action": "error", "device": "unknown"}
    
    async def parse_commands_batch(self, commands: List[str]) -> List[Dict[str, str]]:
        """
        Parse multiple commands in batch.
        
        Args:
            commands: List of natural language commands
            
        Returns:
            List of parsed JSON dictionaries
        """
        results = []
        for cmd in commands:
            result = await self.parse_command(cmd)
            results.append(result)
        return results
    
    def validate_command(self, parsed_result: Dict[str, str]) -> bool:
        """
        Validate that a parsed result contains valid action and device.
        
        Args:
            parsed_result: Parsed JSON result
            
        Returns:
            True if valid, False otherwise
        """
        valid_actions = {"turn on", "turn off", "toggle"}
        valid_devices = {
            "bedroom lights", "bathroom lights", 
            "kitchen lights", "living room lights"
        }
        
        action = parsed_result.get("action")
        device = parsed_result.get("device")
        
        return (action in valid_actions and device in valid_devices)
    
    async def parse_and_validate(self, user_input: str) -> Dict[str, Any]:
        """
        Parse a command and validate the result.
        
        Args:
            user_input: Natural language command
            
        Returns:
            Dictionary with parsed result and validation status
        """
        parsed = await self.parse_command(user_input)
        is_valid = self.validate_command(parsed)
        
        return {
            "input": user_input,
            "parsed": parsed,
            "valid": is_valid,
            "error": None if is_valid else "Invalid action or device"
        }
    
    async def close(self):
        """Clean up resources."""
        if hasattr(self.client, 'close'):
            await self.client.close()


class SmartHomeParserSync:
    """
    Synchronous wrapper for SmartHomeParser.
    
    Provides the same functionality as SmartHomeParser but with synchronous
    methods for easier integration with non-async code.
    """
    
    def __init__(self, model_path: str, grammar_path: str = "data/smart_home.gbnf"):
        """Initialize the synchronous parser."""
        self.parser = SmartHomeParser(model_path, grammar_path)
    
    def parse_command(self, user_input: str) -> Dict[str, str]:
        """Synchronous version of parse_command."""
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, we need to create a new task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run, 
                        self.parser.parse_command(user_input)
                    )
                    return future.result()
            else:
                return asyncio.run(self.parser.parse_command(user_input))
        except Exception as e:
            logger.error(f"Error in sync parse_command: {e}")
            return {"action": "error", "device": "unknown"}
    
    def parse_commands_batch(self, commands: List[str]) -> List[Dict[str, str]]:
        """Synchronous version of parse_commands_batch."""
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run, 
                        self.parser.parse_commands_batch(commands)
                    )
                    return future.result()
            else:
                return asyncio.run(self.parser.parse_commands_batch(commands))
        except Exception as e:
            logger.error(f"Error in sync parse_commands_batch: {e}")
            return [{"action": "error", "device": "unknown"}] * len(commands)
    
    def validate_command(self, parsed_result: Dict[str, str]) -> bool:
        """Validate a parsed result."""
        return self.parser.validate_command(parsed_result)
    
    def parse_and_validate(self, user_input: str) -> Dict[str, Any]:
        """Synchronous version of parse_and_validate."""
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run, 
                        self.parser.parse_and_validate(user_input)
                    )
                    return future.result()
            else:
                return asyncio.run(self.parser.parse_and_validate(user_input))
        except Exception as e:
            logger.error(f"Error in sync parse_and_validate: {e}")
            return {
                "input": user_input,
                "parsed": {"action": "error", "device": "unknown"},
                "valid": False,
                "error": str(e)
            }


# Convenience functions for quick usage
async def parse_smart_home_command(user_input: str, model_path: str) -> Dict[str, str]:
    """
    Quick function to parse a single smart home command.
    
    Args:
        user_input: Natural language command
        model_path: Path to GGUF model
        
    Returns:
        Parsed JSON result
    """
    parser = SmartHomeParser(model_path)
    try:
        return await parser.parse_command(user_input)
    finally:
        await parser.close()


def parse_smart_home_command_sync(user_input: str, model_path: str) -> Dict[str, str]:
    """
    Synchronous version of parse_smart_home_command.
    
    Args:
        user_input: Natural language command
        model_path: Path to GGUF model
        
    Returns:
        Parsed JSON result
    """
    parser = SmartHomeParserSync(model_path)
    return parser.parse_command(user_input) 