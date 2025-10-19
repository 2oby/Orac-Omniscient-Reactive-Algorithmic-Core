#!/usr/bin/env python3
"""
Simple test for BackendGrammarGenerator without complex dependencies.
"""

import os
import sys
import json
import tempfile
from pathlib import Path

# Add the orac package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

# Mock the BackendManager for testing
class MockBackendManager:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.backends_dir = self.data_dir / "backends"
        self.backends_dir.mkdir(parents=True, exist_ok=True)

        # Create mock backend data
        self.backends = {
            "homeassistant_test123": {
                "id": "homeassistant_test123",
                "name": "Test Home Assistant",
                "type": "homeassistant",
                "device_mappings": {
                    "light.lounge_lamp": {
                        "enabled": True,
                        "device_type": "lights",
                        "location": "lounge",
                        "original_name": "Lounge Lamp"
                    },
                    "climate.bedroom_thermostat": {
                        "enabled": True,
                        "device_type": "heating",
                        "location": "bedroom",
                        "original_name": "Bedroom Thermostat"
                    },
                    "cover.kitchen_blinds": {
                        "enabled": True,
                        "device_type": "blinds",
                        "location": "kitchen",
                        "original_name": "Kitchen Blinds"
                    },
                    "switch.office_fan": {
                        "enabled": False,  # Disabled device
                        "device_type": "switches",
                        "location": "office",
                        "original_name": "Office Fan"
                    }
                },
                "device_types": ["lights", "heating", "blinds", "switches"],
                "locations": ["lounge", "bedroom", "kitchen", "office"]
            }
        }

    def get_backend(self, backend_id):
        return self.backends.get(backend_id)


# Import our grammar generator
from orac.backend_grammar_generator import BackendGrammarGenerator


def test_grammar_generation():
    """Test the grammar generation functionality."""
    print("🚀 Testing BackendGrammarGenerator")
    print("=" * 50)

    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")

        # Create mock backend manager
        mock_manager = MockBackendManager(temp_dir)

        # Create grammar generator
        generator = BackendGrammarGenerator(mock_manager, temp_dir)

        backend_id = "homeassistant_test123"

        print(f"\n1. Testing device type extraction...")
        device_types = generator.extract_configured_device_types(backend_id)
        print(f"   Device types: {device_types}")

        print(f"\n2. Testing location extraction...")
        locations = generator.extract_configured_locations(backend_id)
        print(f"   Locations: {locations}")

        print(f"\n3. Testing valid combinations...")
        combinations = generator.get_valid_device_location_combinations(backend_id)
        print(f"   Valid combinations: {len(combinations)}")
        for combo in combinations:
            print(f"     - {combo['device_type']} in {combo['location']} ({combo['original_name']})")

        print(f"\n4. Testing grammar generation...")
        result = generator.generate_and_save_grammar(backend_id)

        if result["success"]:
            print("   ✅ Grammar generated successfully!")
            print(f"   - File: {result['grammar_file']}")
            print(f"   - Device types: {result['statistics']['device_types_count']}")
            print(f"   - Locations: {result['statistics']['locations_count']}")

            print(f"\n5. Generated Grammar:")
            print("-" * 30)
            print(result["grammar_content"])
            print("-" * 30)

            print(f"\n6. Testing command validation...")
            test_commands = [
                "turn on the lounge lights",      # Should be valid
                "turn off bedroom heating",       # Should be valid
                "open the kitchen blinds",        # Should be valid
                "turn on office switches",        # Should be invalid (disabled)
                "turn on bathroom lights",        # Should be invalid (no bathroom)
            ]

            for command in test_commands:
                print(f"\n   Testing: '{command}'")
                validation = generator.test_command_against_grammar(backend_id, command)

                if validation["valid"]:
                    print(f"     ✅ Valid")
                    print(f"     - JSON: {validation['parsed_json']}")
                    if validation.get("device_mapping"):
                        print(f"     - Maps to: {validation['device_mapping']['original_name']}")
                else:
                    print(f"     ❌ Invalid: {validation['error']}")

            print(f"\n7. Testing grammar status...")
            status = generator.get_grammar_status(backend_id)
            print(f"   - Grammar exists: {status['grammar_file_exists']}")
            print(f"   - Ready for generation: {status['ready_for_generation']}")
            print(f"   - Mapped devices: {status['mapped_devices']}")

        else:
            print(f"   ❌ Grammar generation failed: {result['error']}")

    print("\n" + "=" * 50)
    print("🎉 Test completed!")


if __name__ == "__main__":
    test_grammar_generation()