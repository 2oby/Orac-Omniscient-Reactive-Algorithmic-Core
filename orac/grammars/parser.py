"""GBNF Grammar Parser for extracting vocabulary from grammar files."""

import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class GBNFParser:
    """Parser for GBNF (GGML BNF) grammar files to extract vocabulary."""

    def __init__(self):
        self.grammar_cache = {}

    def parse_grammar(self, grammar_file: str) -> Dict[str, List[str]]:
        """
        Extract devices, locations, actions from GBNF grammar file.

        Args:
            grammar_file: Path to the GBNF file

        Returns:
            Dictionary with keys 'devices', 'locations', 'actions', etc.
            containing lists of allowed values
        """
        if grammar_file in self.grammar_cache:
            return self.grammar_cache[grammar_file]

        grammar_path = Path(grammar_file)
        if not grammar_path.exists():
            logger.error(f"Grammar file not found: {grammar_file}")
            return {}

        content = grammar_path.read_text()
        vocabulary = self._extract_vocabulary(content)

        # Cache the parsed result
        self.grammar_cache[grammar_file] = vocabulary
        return vocabulary

    def _extract_vocabulary(self, content: str) -> Dict[str, List[str]]:
        """
        Extract vocabulary from GBNF content.

        Looks for patterns like:
        device ::= "lights" | "heating" | "blinds"
        location ::= "bedroom" | "kitchen" | "lounge"
        """
        vocabulary = {}

        # Pattern to match rule definitions
        # Matches: rulename ::= "value1" | "value2" | ...
        rule_pattern = r'(\w+)\s*::=\s*([^#\n]+)'

        for match in re.finditer(rule_pattern, content):
            rule_name = match.group(1)
            rule_definition = match.group(2)

            # Extract quoted strings from the rule definition
            values = self._extract_quoted_values(rule_definition)

            if values:
                vocabulary[rule_name] = values
                logger.debug(f"Extracted {rule_name}: {values}")

        return vocabulary

    def _extract_quoted_values(self, definition: str) -> List[str]:
        """
        Extract quoted string values from a rule definition.

        Args:
            definition: Rule definition string like '"value1" | "value2"'

        Returns:
            List of extracted values
        """
        # Pattern to match quoted strings
        quote_pattern = r'"([^"]+)"'
        values = re.findall(quote_pattern, definition)

        # Remove duplicates while preserving order
        seen = set()
        unique_values = []
        for value in values:
            if value not in seen:
                seen.add(value)
                unique_values.append(value)

        return unique_values

    def get_combinations(self, grammar: Dict[str, List[str]]) -> List[str]:
        """
        Generate all valid location|device combinations from grammar.

        Args:
            grammar: Parsed grammar dictionary

        Returns:
            List of combinations in format "location|device"
        """
        combinations = []

        # Check if we have separate location and device fields
        if 'location' in grammar and 'device' in grammar:
            # Grammar has separate location and device
            locations = grammar.get('location', [])
            devices = grammar.get('device', [])

            # Generate all combinations
            for location in locations:
                for device in devices:
                    combination = f"{location}|{device}"
                    combinations.append(combination)
        elif 'device' in grammar:
            # Grammar has compound device names (e.g., "bedroom lights")
            # Parse location from device name
            devices = grammar.get('device', [])
            for device in devices:
                # Try to split device into location and device type
                parts = device.rsplit(' ', 1)
                if len(parts) == 2:
                    location, device_type = parts
                    combination = f"{location}|{device_type}"
                    combinations.append(combination)
                else:
                    # Can't split, use as is
                    combination = f"default|{device}"
                    combinations.append(combination)

        return combinations

    def extract_json_structure(self, grammar_file: str) -> Optional[Dict]:
        """
        Extract JSON structure from grammar if present.

        Args:
            grammar_file: Path to the GBNF file

        Returns:
            Dictionary describing JSON structure or None
        """
        grammar_path = Path(grammar_file)
        if not grammar_path.exists():
            return None

        content = grammar_path.read_text()

        # Look for JSON object patterns
        if '"device"' in content and '"action"' in content and '"location"' in content:
            # This appears to be a home automation grammar
            return {
                "type": "home_automation",
                "fields": ["device", "action", "location"],
                "format": "json"
            }
        elif '"temperature"' in content:
            # Temperature control grammar
            return {
                "type": "temperature_control",
                "fields": ["temperature", "unit"],
                "format": "json"
            }

        return None

    def validate_output_against_grammar(
        self,
        output: str,
        grammar_file: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that LLM output conforms to grammar constraints.

        Args:
            output: LLM output to validate
            grammar_file: Path to grammar file

        Returns:
            Tuple of (is_valid, error_message)
        """
        grammar = self.parse_grammar(grammar_file)

        if not grammar:
            return True, None  # No constraints to validate against

        # Try to parse as JSON
        try:
            import json
            data = json.loads(output)

            # Validate against vocabulary
            for field, value in data.items():
                if field in grammar:
                    allowed_values = grammar[field]
                    if value not in allowed_values:
                        return False, f"Invalid {field}: '{value}'. Allowed: {allowed_values}"

            return True, None

        except json.JSONDecodeError:
            # Not JSON, validate as plain text
            words = output.lower().split()

            # Check if any constrained terms are violated
            for rule_name, allowed_values in grammar.items():
                for word in words:
                    if word in self._get_all_possible_values(rule_name):
                        if word not in allowed_values:
                            return False, f"Invalid {rule_name}: '{word}'"

            return True, None

    def _get_all_possible_values(self, rule_name: str) -> Set[str]:
        """
        Get all possible values that could match a rule type.

        This is a heuristic based on common patterns.
        """
        common_values = {
            'device': {'lights', 'heating', 'blinds', 'music', 'alarm', 'door', 'window'},
            'location': {'bedroom', 'kitchen', 'lounge', 'bathroom', 'hall', 'garage', 'office'},
            'action': {'on', 'off', 'toggle', 'set', 'increase', 'decrease', 'open', 'close'}
        }

        return common_values.get(rule_name, set())


def test_parser():
    """Test the GBNF parser with a sample grammar."""
    parser = GBNFParser()

    # Test with actual grammar file
    test_file = "/Users/2oby/pCloud Box/Projects/ORAC/Orac-Omniscient-Reactive-Algorithmic-Core/data/grammars/static_actions.gbnf"

    if Path(test_file).exists():
        grammar = parser.parse_grammar(test_file)
        print(f"Parsed grammar: {grammar}")

        combinations = parser.get_combinations(grammar)
        print(f"Generated {len(combinations)} combinations")
        print(f"Sample combinations: {combinations[:5]}")

        # Test validation
        test_output = '{"device": "lights", "action": "on", "location": "bedroom"}'
        valid, error = parser.validate_output_against_grammar(test_output, test_file)
        print(f"Validation result: {valid}, Error: {error}")
    else:
        print(f"Test file not found: {test_file}")


if __name__ == "__main__":
    test_parser()