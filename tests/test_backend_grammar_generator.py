#!/usr/bin/env python3
"""
Test script for BackendGrammarGenerator

This script tests the Sprint 3 grammar generation functionality with mock data.
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# Add the orac package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from orac.backend_manager import BackendManager
from orac.backend_grammar_generator import BackendGrammarGenerator


def create_test_backend_data(backend_manager, data_dir):
    """Create test backend with sample device mappings."""
    print("Creating test backend with sample device mappings...")

    # Create a test backend
    backend = backend_manager.create_backend(
        name="Test Home Assistant",
        backend_type="homeassistant",
        connection={
            "url": "http://192.168.8.99:8123",
            "port": 8123,
            "token": "test_token"
        }
    )

    backend_id = backend["id"]

    # Add some sample device mappings (simulating Sprint 2 configuration)
    sample_devices = {
        "light.lounge_lamp": {
            "enabled": True,
            "device_type": "lights",
            "location": "lounge",
            "original_area": "Living Room",
            "original_name": "Lounge Lamp",
            "domain": "light",
            "configured_at": "2024-01-01T10:00:00",
            "state": "off",
            "attributes": {}
        },
        "climate.bedroom_thermostat": {
            "enabled": True,
            "device_type": "heating",
            "location": "bedroom",
            "original_area": "Bedroom",
            "original_name": "Bedroom Thermostat",
            "domain": "climate",
            "configured_at": "2024-01-01T10:00:00",
            "state": "heat",
            "attributes": {}
        },
        "cover.kitchen_blinds": {
            "enabled": True,
            "device_type": "blinds",
            "location": "kitchen",
            "original_area": "Kitchen",
            "original_name": "Kitchen Blinds",
            "domain": "cover",
            "configured_at": "2024-01-01T10:00:00",
            "state": "closed",
            "attributes": {}
        },
        "switch.office_fan": {
            "enabled": False,  # This one is disabled
            "device_type": "switches",
            "location": "office",
            "original_area": "Office",
            "original_name": "Office Fan",
            "domain": "switch",
            "configured_at": None,
            "state": "off",
            "attributes": {}
        },
        "media_player.living_room_tv": {
            "enabled": True,
            "device_type": "media_player",
            "location": "lounge",
            "original_area": "Living Room",
            "original_name": "Living Room TV",
            "domain": "media_player",
            "configured_at": "2024-01-01T10:00:00",
            "state": "standby",
            "attributes": {}
        }
    }

    # Update the backend with device mappings
    backend["device_mappings"] = sample_devices
    backend["device_types"] = ["lights", "heating", "blinds", "switches", "media_player"]
    backend["locations"] = ["lounge", "bedroom", "kitchen", "office"]

    # Update statistics
    enabled_devices = [d for d in sample_devices.values() if d["enabled"]]
    mapped_devices = [d for d in enabled_devices if d.get("device_type") and d.get("location")]

    backend["statistics"] = {
        "total_devices": len(sample_devices),
        "enabled_devices": len(enabled_devices),
        "mapped_devices": len(mapped_devices),
        "last_sync": "2024-01-01T10:00:00"
    }

    # Save the backend
    backend_manager.save_backend(backend_id)

    print(f"✅ Created test backend: {backend_id}")
    print(f"   - Total devices: {len(sample_devices)}")
    print(f"   - Enabled devices: {len(enabled_devices)}")
    print(f"   - Mapped devices: {len(mapped_devices)}")

    return backend_id


def test_grammar_generation(grammar_generator, backend_id):
    """Test grammar generation for the backend."""
    print(f"\n🔍 Testing grammar generation for backend: {backend_id}")

    # Test grammar status
    print("1. Checking grammar status...")
    status = grammar_generator.get_grammar_status(backend_id)
    print(f"   - Grammar file exists: {status.get('grammar_file_exists', False)}")
    print(f"   - Ready for generation: {status.get('ready_for_generation', False)}")
    print(f"   - Device types: {status.get('device_types', [])}")
    print(f"   - Locations: {status.get('locations', [])}")

    # Generate grammar
    print("\n2. Generating grammar...")
    result = grammar_generator.generate_and_save_grammar(backend_id)

    if result["success"]:
        print("   ✅ Grammar generated successfully!")
        print(f"   - Grammar file: {result['grammar_file']}")
        print(f"   - Device types: {result['statistics']['device_types']}")
        print(f"   - Locations: {result['statistics']['locations']}")
        print(f"   - Valid combinations: {result['statistics']['valid_combinations_count']}")

        # Show generated grammar content
        print("\n3. Generated Grammar Content:")
        print("=" * 50)
        print(result["grammar_content"])
        print("=" * 50)

        return True
    else:
        print(f"   ❌ Grammar generation failed: {result['error']}")
        return False


def test_command_validation(grammar_generator, backend_id):
    """Test command validation against generated grammar."""
    print(f"\n🧪 Testing command validation for backend: {backend_id}")

    # Test commands
    test_commands = [
        "turn on the lounge lights",      # Should be valid
        "turn off bedroom heating",       # Should be valid
        "open the kitchen blinds",        # Should be valid
        "turn on lounge media_player",    # Should be valid
        "turn on office switches",        # Should be invalid (disabled device)
        "turn on bathroom lights",        # Should be invalid (location not configured)
        "activate the garage door",       # Should be invalid (device not configured)
    ]

    for command in test_commands:
        print(f"\nTesting: '{command}'")
        result = grammar_generator.test_command_against_grammar(backend_id, command)

        if result["valid"]:
            print(f"   ✅ Valid command")
            print(f"   - Expected JSON: {result['parsed_json']}")
            if result.get("device_mapping"):
                mapping = result["device_mapping"]
                print(f"   - Maps to: {mapping['original_name']} ({mapping['device_id']})")
        else:
            print(f"   ❌ Invalid command")
            print(f"   - Error: {result['error']}")
            if result.get("found_device"):
                print(f"   - Found device: {result['found_device']}")
            if result.get("found_location"):
                print(f"   - Found location: {result['found_location']}")


def main():
    """Main test function."""
    print("🚀 Testing BackendGrammarGenerator (Sprint 3)")
    print("=" * 60)

    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")

        # Initialize backend manager and grammar generator
        backend_manager = BackendManager(data_dir=temp_dir)
        grammar_generator = BackendGrammarGenerator(backend_manager, data_dir=temp_dir)

        # Create test data
        backend_id = create_test_backend_data(backend_manager, temp_dir)

        # Test grammar generation
        grammar_success = test_grammar_generation(grammar_generator, backend_id)

        if grammar_success:
            # Test command validation
            test_command_validation(grammar_generator, backend_id)

        print("\n" + "=" * 60)
        print("🎉 Test completed!")

        # Show final status
        status = grammar_generator.get_grammar_status(backend_id)
        print(f"Final status: {status}")


if __name__ == "__main__":
    main()