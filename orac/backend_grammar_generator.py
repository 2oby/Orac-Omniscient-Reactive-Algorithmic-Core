"""
Backend Grammar Generator for Sprint 3.

This module generates GBNF grammars dynamically from Backend device mappings
created in Sprint 2. It constraints the LLM to only output JSON for devices
the user has actually enabled and configured.

The key concept: If user only configured a light in the lounge and heating
in the bedroom, the grammar should ONLY allow those combinations and block
everything else.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Set
from pathlib import Path

logger = logging.getLogger(__name__)


class BackendGrammarGenerator:
    """Generates GBNF grammars from Sprint 2 backend device mappings."""

    def __init__(self, backend_manager, data_dir: str = None):
        """Initialize the grammar generator.

        Args:
            backend_manager: BackendManager instance for accessing device mappings
            data_dir: Directory to store generated grammars (optional)
        """
        self.backend_manager = backend_manager

        # Set up grammar storage directory
        if data_dir is None:
            data_dir = os.getenv('DATA_DIR')
            if not data_dir:
                base_dir = Path(__file__).parent.parent
                data_dir = base_dir / "data"

        self.data_dir = Path(data_dir)
        self.grammars_dir = self.data_dir / "grammars"

        # Ensure grammars directory exists
        self.grammars_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"BackendGrammarGenerator using grammars directory: {self.grammars_dir}")

    def get_grammar_file_path(self, backend_id: str) -> Path:
        """Get the path for a backend's generated grammar file.

        Args:
            backend_id: The backend ID

        Returns:
            Path to the backend's grammar file
        """
        return self.grammars_dir / f"backend_{backend_id}.gbnf"

    def extract_configured_device_types(self, backend_id: str) -> Set[str]:
        """Extract unique device types from enabled device mappings.

        Args:
            backend_id: The backend ID

        Returns:
            Set of configured device types
        """
        device_types = set()

        backend = self.backend_manager.get_backend(backend_id)
        if not backend:
            logger.error(f"Backend {backend_id} not found")
            return device_types

        device_mappings = backend.get('device_mappings', {})

        for device_id, mapping in device_mappings.items():
            if mapping.get('enabled') and mapping.get('device_type'):
                device_types.add(mapping['device_type'])

        logger.info(f"Extracted {len(device_types)} device types: {list(device_types)}")
        return device_types

    def extract_configured_locations(self, backend_id: str) -> Set[str]:
        """Extract unique locations from enabled device mappings.

        Args:
            backend_id: The backend ID

        Returns:
            Set of configured locations
        """
        locations = set()

        backend = self.backend_manager.get_backend(backend_id)
        if not backend:
            logger.error(f"Backend {backend_id} not found")
            return locations

        device_mappings = backend.get('device_mappings', {})

        for device_id, mapping in device_mappings.items():
            if mapping.get('enabled') and mapping.get('location'):
                locations.add(mapping['location'])

        logger.info(f"Extracted {len(locations)} locations: {list(locations)}")
        return locations

    def get_valid_device_location_combinations(self, backend_id: str) -> List[Dict[str, str]]:
        """Get valid device type + location combinations from device mappings.

        Args:
            backend_id: The backend ID

        Returns:
            List of valid combinations with device type and location
        """
        combinations = []

        backend = self.backend_manager.get_backend(backend_id)
        if not backend:
            logger.error(f"Backend {backend_id} not found")
            return combinations

        device_mappings = backend.get('device_mappings', {})

        for device_id, mapping in device_mappings.items():
            if (mapping.get('enabled') and
                mapping.get('device_type') and
                mapping.get('location')):
                combinations.append({
                    'device_id': device_id,
                    'device_type': mapping['device_type'],
                    'location': mapping['location'],
                    'original_name': mapping.get('original_name', device_id)
                })

        logger.info(f"Found {len(combinations)} valid device+location combinations")
        return combinations

    def load_default_grammar_template(self) -> str:
        """Load the default.gbnf template to use as base for generation.

        Returns:
            Content of default.gbnf file
        """
        default_grammar_path = self.grammars_dir / "default.gbnf"

        try:
            with open(default_grammar_path, 'r') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to load default.gbnf template: {e}")
            # Return a basic template as fallback
            return self._get_fallback_template()

    def _get_fallback_template(self) -> str:
        """Get a fallback grammar template if default.gbnf is not available.

        Returns:
            Basic GBNF grammar template
        """
        return '''root ::= "{\"device\":\"" device "\",\"action\":\"" action "\",\"location\":\"" location "\"}"
device ::= "lights" | "heating" | "blinds" | "music" | "UNKNOWN"
action ::= "on" | "off" | "toggle" | "open" | "close" | "high" | "low" | "medium" | "warm" | "cold" | "hot" | "up" | "down" | "loud" | "quiet" | "UNKNOWN" | set-action | set-temp-action
location ::= "bedroom" | "bathroom" | "kitchen" | "hall" | "living room" | "any" | "all" | "UNKNOWN"
pct ::= "0%" | "10%" | "20%" | "30%" | "40%" | "50%" | "60%" | "70%" | "80%" | "90%" | "100%"
temp ::= "5C" | "6C" | "7C" | "8C" | "9C" | "10C" | "11C" | "12C" | "13C" | "14C" | "15C" | "16C" | "17C" | "18C" | "19C" | "20C" | "21C" | "22C" | "23C" | "24C" | "25C" | "26C" | "27C" | "28C" | "29C" | "30C"
set-action ::= "set " pct
set-temp-action ::= "set " temp'''

    def generate_dynamic_grammar(self, backend_id: str) -> str:
        """Generate GBNF grammar based on backend device mappings.

        Args:
            backend_id: The backend ID

        Returns:
            Generated GBNF grammar string
        """
        logger.info(f"Generating dynamic grammar for backend {backend_id}")

        # Extract configured device types and locations
        device_types = self.extract_configured_device_types(backend_id)
        locations = self.extract_configured_locations(backend_id)

        # Ensure we always have UNKNOWN as fallback
        device_types.add("UNKNOWN")
        locations.add("UNKNOWN")

        # Load default action rules from template
        template = self.load_default_grammar_template()

        # Extract action rules from template (everything after device and location rules)
        action_rules = self._extract_action_rules_from_template(template)

        # Generate device rule
        device_rule = "device ::= " + " | ".join(f'"{dt}"' for dt in sorted(device_types))

        # Generate location rule
        location_rule = "location ::= " + " | ".join(f'"{loc}"' for loc in sorted(locations))

        # Combine everything
        grammar_lines = [
            'root ::= "{\\"device\\":\\"" device "\\",\\"action\\":\\"" action "\\",\\"location\\":\\"" location "\\"}"',
            "",
            device_rule,
            location_rule,
            "",
            action_rules
        ]

        grammar = "\n".join(grammar_lines)
        logger.info(f"Generated grammar with {len(device_types)} device types and {len(locations)} locations")
        return grammar

    def _extract_action_rules_from_template(self, template: str) -> str:
        """Extract action-related rules from the grammar template.

        Args:
            template: The template grammar content

        Returns:
            Action rules portion of the template
        """
        lines = template.split('\n')
        action_lines = []

        # Find lines that don't start with 'root', 'device', or 'location'
        for line in lines:
            line = line.strip()
            if (line and
                not line.startswith('root ') and
                not line.startswith('device ') and
                not line.startswith('location ')):
                action_lines.append(line)

        return "\n".join(action_lines)

    def generate_and_save_grammar(self, backend_id: str) -> Dict[str, Any]:
        """Generate and save grammar for a backend.

        Args:
            backend_id: The backend ID

        Returns:
            Result dictionary with status and details
        """
        try:
            # Validate backend exists
            backend = self.backend_manager.get_backend(backend_id)
            if not backend:
                return {
                    "success": False,
                    "error": f"Backend {backend_id} not found"
                }

            # Check if backend has any enabled devices
            device_mappings = backend.get('device_mappings', {})
            enabled_devices = [m for m in device_mappings.values() if m.get('enabled')]

            if not enabled_devices:
                return {
                    "success": False,
                    "error": "No enabled devices found in backend configuration"
                }

            # Generate grammar
            grammar = self.generate_dynamic_grammar(backend_id)

            # Save to file
            grammar_file = self.get_grammar_file_path(backend_id)
            with open(grammar_file, 'w') as f:
                f.write(grammar)

            # Get statistics
            device_types = self.extract_configured_device_types(backend_id)
            locations = self.extract_configured_locations(backend_id)
            combinations = self.get_valid_device_location_combinations(backend_id)

            logger.info(f"Generated and saved grammar for backend {backend_id} to {grammar_file}")

            return {
                "success": True,
                "grammar_file": str(grammar_file),
                "grammar_content": grammar,
                "statistics": {
                    "device_types": list(device_types),
                    "locations": list(locations),
                    "device_types_count": len(device_types),
                    "locations_count": len(locations),
                    "valid_combinations_count": len(combinations),
                    "valid_combinations": combinations
                }
            }

        except Exception as e:
            logger.error(f"Error generating grammar for backend {backend_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def test_command_against_grammar(self, backend_id: str, command: str) -> Dict[str, Any]:
        """Test a command against the generated grammar.

        Args:
            backend_id: The backend ID
            command: The command to test

        Returns:
            Test result with validation status
        """
        try:
            # Check if grammar exists
            grammar_file = self.get_grammar_file_path(backend_id)
            if not grammar_file.exists():
                return {
                    "valid": False,
                    "error": "Grammar file not found. Generate grammar first.",
                    "command": command
                }

            # For now, implement basic validation logic
            # In a full implementation, this would use a proper GBNF parser

            # Get valid device types and locations
            device_types = self.extract_configured_device_types(backend_id)
            locations = self.extract_configured_locations(backend_id)
            combinations = self.get_valid_device_location_combinations(backend_id)

            # Simple heuristic validation
            command_lower = command.lower()

            # Check if command contains configured device types
            found_device = None
            for device_type in device_types:
                if device_type.lower() in command_lower:
                    found_device = device_type
                    break

            # Check if command contains configured locations
            found_location = None
            for location in locations:
                if location.lower() in command_lower:
                    found_location = location
                    break

            # Check if the combination is valid
            valid_combination = False
            mapped_device = None

            if found_device and found_location:
                for combo in combinations:
                    if (combo['device_type'].lower() == found_device.lower() and
                        combo['location'].lower() == found_location.lower()):
                        valid_combination = True
                        mapped_device = combo
                        break

            # Determine overall validity
            if valid_combination:
                # Generate expected JSON output
                expected_json = {
                    "device": found_device,
                    "action": "on",  # Default action for demo
                    "location": found_location
                }

                return {
                    "valid": True,
                    "command": command,
                    "parsed_json": expected_json,
                    "device_mapping": mapped_device,
                    "message": f"✅ Valid command - maps to {mapped_device['original_name']}"
                }
            else:
                error_msg = "❌ Invalid command"
                if not found_device:
                    error_msg += " - no configured device type found"
                elif not found_location:
                    error_msg += " - no configured location found"
                else:
                    error_msg += " - device/location combination not configured"

                return {
                    "valid": False,
                    "command": command,
                    "error": error_msg,
                    "found_device": found_device,
                    "found_location": found_location,
                    "configured_devices": list(device_types),
                    "configured_locations": list(locations)
                }

        except Exception as e:
            logger.error(f"Error testing command against grammar: {e}")
            return {
                "valid": False,
                "error": str(e),
                "command": command
            }

    def get_grammar_status(self, backend_id: str) -> Dict[str, Any]:
        """Get the status of grammar generation for a backend.

        Args:
            backend_id: The backend ID

        Returns:
            Status dictionary with grammar information
        """
        try:
            # Check if backend exists
            backend = self.backend_manager.get_backend(backend_id)
            if not backend:
                return {
                    "exists": False,
                    "error": f"Backend {backend_id} not found"
                }

            # Check if grammar file exists
            grammar_file = self.get_grammar_file_path(backend_id)
            grammar_exists = grammar_file.exists()

            # Get device mapping statistics
            device_mappings = backend.get('device_mappings', {})
            enabled_devices = [m for m in device_mappings.values() if m.get('enabled')]
            mapped_devices = [m for m in enabled_devices if m.get('device_type') and m.get('location')]

            device_types = self.extract_configured_device_types(backend_id)
            locations = self.extract_configured_locations(backend_id)

            status = {
                "backend_exists": True,
                "grammar_file_exists": grammar_exists,
                "grammar_file_path": str(grammar_file),
                "total_devices": len(device_mappings),
                "enabled_devices": len(enabled_devices),
                "mapped_devices": len(mapped_devices),
                "device_types_count": len(device_types),
                "locations_count": len(locations),
                "device_types": list(device_types),
                "locations": list(locations),
                "ready_for_generation": len(mapped_devices) > 0
            }

            if grammar_exists:
                try:
                    stat = grammar_file.stat()
                    status["grammar_file_size"] = stat.st_size
                    status["grammar_file_modified"] = stat.st_mtime
                except Exception as e:
                    logger.error(f"Error getting grammar file stats: {e}")

            return status

        except Exception as e:
            logger.error(f"Error getting grammar status: {e}")
            return {
                "exists": False,
                "error": str(e)
            }

    def regenerate_grammar_on_mapping_change(self, backend_id: str) -> Dict[str, Any]:
        """Regenerate grammar when device mappings change.

        Args:
            backend_id: The backend ID

        Returns:
            Result of grammar regeneration
        """
        logger.info(f"Regenerating grammar for backend {backend_id} due to mapping change")
        return self.generate_and_save_grammar(backend_id)