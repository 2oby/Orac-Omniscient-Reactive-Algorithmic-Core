import subprocess
import json
import os
from typing import Dict, Any, Optional

class SmartHomeParser:
    def __init__(self, model_path: str, grammar_path: str = "data/smart_home.gbnf"):
        self.model_path = model_path
        self.grammar_path = grammar_path
        self.system_prompt = (
            "You are a JSON-only formatter. For each user input, respond with a "
            "single-line JSON object containing exactly these keys: \"action\" "
            "and \"device\". Do not include any explanations, comments, or "
            "additional text. Only output the JSON object."
        )
    
    def parse_command(self, user_input: str) -> Dict[str, str]:
        """
        Parse a natural language command into structured JSON.
        
        Args:
            user_input: Natural language command (e.g., "Turn on the bathroom lights")
            
        Returns:
            Dictionary with "action" and "device" keys
        """
        # Construct the full prompt
        full_prompt = (
            f"{self.system_prompt}\n\n"
            f"User: {user_input}\n"
            f"Assistant: {{\"action\": "
        )
        
        # Run llama.cpp
        cmd = [
            'llama-cli',
            '-m', self.model_path,
            '-p', full_prompt,
            '--grammar-file', self.grammar_path,
            '-n', '50',
            '--temp', '0.0',
            '--no-display-prompt'
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            # Complete the JSON
            full_json = '{"action": ' + result.stdout.strip()
            return json.loads(full_json)
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            return {"action": "error", "device": "unknown"}

    def parse_commands_batch(self, commands: list[str]) -> list[Dict[str, str]]:
        """
        Parse multiple commands in batch.
        
        Args:
            commands: List of natural language commands
            
        Returns:
            List of parsed JSON dictionaries
        """
        results = []
        for cmd in commands:
            result = self.parse_command(cmd)
            results.append(result)
        return results


# Usage example
if __name__ == "__main__":
    parser = SmartHomeParser(
        model_path="./model.gguf",
        grammar_path="./data/smart_home.gbnf"
    )
    
    # Test commands
    test_commands = [
        "Turn on the bathroom lights",
        "toggle kitchen lights",
        "Turn off bedroom lights"
    ]
    
    for cmd in test_commands:
        result = parser.parse_command(cmd)
        print(f"Input: {cmd}")
        print(f"Output: {json.dumps(result)}")
        print() 