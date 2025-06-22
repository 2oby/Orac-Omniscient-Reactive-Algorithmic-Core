#!/usr/bin/env python3
"""
Test script for the new discovery service and mapping builder.

This script tests the complete auto-discovery pipeline:
1. HADiscoveryService.discover_all()
2. HAMappingBuilder.build_mapping()
3. Integration with existing components
"""

import asyncio
import logging
import yaml
from pathlib import Path
from orac.homeassistant.client import HomeAssistantClient
from orac.homeassistant.config import HomeAssistantConfig
from orac.homeassistant.discovery_service import HADiscoveryService
from orac.homeassistant.mapping_builder import HAMappingBuilder

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_discovery_pipeline():
    """Test the complete discovery pipeline."""
    
    print("=== Home Assistant Discovery Pipeline Test ===\n")
    
    # Initialize Home Assistant config
    config = HomeAssistantConfig.from_yaml("orac/homeassistant/config.yaml")
    
    async with HomeAssistantClient(config) as client:
        # Initialize discovery service
        discovery_service = HADiscoveryService(client)
        
        # Test connection validation
        print("1. Testing connection validation...")
        connection_valid = await discovery_service.validate_connection()
        if connection_valid:
            print("   ✅ Connection validation successful")
        else:
            print("   ❌ Connection validation failed")
            return
        print()
        
        # Run complete discovery
        print("2. Running complete discovery...")
        try:
            discovery_data = await discovery_service.discover_all()
            print("   ✅ Discovery completed successfully")
        except Exception as e:
            print(f"   ❌ Discovery failed: {e}")
            return
        print()
        
        # Show discovery summary
        print("3. Discovery Summary:")
        summary = discovery_service.get_discovery_summary(discovery_data)
        print(f"   - Total entities: {summary['total_entities']}")
        print(f"   - Total areas: {summary['total_areas']}")
        print(f"   - Total devices: {summary['total_devices']}")
        print(f"   - Entity registry entries: {summary['total_entity_registry_entries']}")
        print(f"   - Entities with area assignments: {summary['entities_with_area_assignments']}")
        print(f"   - Devices with area assignments: {summary['devices_with_area_assignments']}")
        print(f"   - Area names: {', '.join(summary['area_names'])}")
        print()
        
        # Show entities by domain
        print("4. Entities by Domain:")
        for domain, count in summary['entities_by_domain'].items():
            print(f"   - {domain}: {count} entities")
        print()
        
        # Initialize mapping builder
        print("5. Building mapping structure...")
        mapping_builder = HAMappingBuilder()
        
        try:
            mapping = mapping_builder.build_mapping(discovery_data)
            print("   ✅ Mapping structure built successfully")
        except Exception as e:
            print(f"   ❌ Mapping build failed: {e}")
            return
        print()
        
        # Show mapping summary
        print("6. Mapping Summary:")
        mapping_summary = mapping_builder.get_mapping_summary(mapping)
        print(f"   - Device types: {mapping_summary['total_devices']}")
        print(f"   - Actions: {mapping_summary['total_actions']}")
        print(f"   - Locations: {mapping_summary['total_locations']}")
        print(f"   - Entities mapped: {mapping_summary['total_entities_mapped']}")
        print(f"   - Locations with devices: {mapping_summary['locations_with_devices']}")
        print(f"   - Location names: {', '.join(mapping_summary['location_names'])}")
        print()
        
        # Show device types supported
        print("7. Supported Device Types:")
        for device_type in mapping_summary['device_types_supported']:
            print(f"   - {device_type}")
        print()
        
        # Show entity counts by location
        print("8. Entity Counts by Location:")
        for location, device_counts in mapping_summary['entity_counts_by_location'].items():
            print(f"   {location}:")
            for device_type, count in device_counts.items():
                print(f"     - {device_type}: {count} entities")
        print()
        
        # Save mapping to file for inspection
        output_file = "test_mapping_output.yaml"
        print(f"9. Saving mapping to {output_file}...")
        try:
            with open(output_file, 'w') as f:
                yaml.dump(mapping, f, default_flow_style=False, sort_keys=False)
            print(f"   ✅ Mapping saved to {output_file}")
        except Exception as e:
            print(f"   ❌ Failed to save mapping: {e}")
        print()
        
        # Show vocabulary structure
        print("10. Vocabulary Structure:")
        vocabulary = mapping.get('vocabulary', {})
        print(f"   - Devices: {vocabulary.get('devices', [])}")
        print(f"   - Actions: {vocabulary.get('actions', [])}")
        print(f"   - Locations: {vocabulary.get('locations', [])}")
        print()
        
        print("✅ Discovery pipeline test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_discovery_pipeline()) 