#!/usr/bin/env python3
"""
Test script for LocationDetector functionality.

This script demonstrates how the LocationDetector works with real Home Assistant data,
showing how it enables room-based commands like "turn off everything in the bedroom".
"""

import asyncio
import logging
from orac.homeassistant.client import HomeAssistantClient
from orac.homeassistant.config import HomeAssistantConfig
from orac.homeassistant.location_detector import LocationDetector
from orac.homeassistant.domain_mapper import DomainMapper

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_location_detection():
    """Test the LocationDetector with real Home Assistant data."""
    
    print("=== Home Assistant Location Detection Test ===\n")
    
    # Load configuration from the correct path
    config = HomeAssistantConfig(_env_file="/app/orac/homeassistant/config.yaml")
    
    # Initialize client and detector
    async with HomeAssistantClient(config) as client:
        detector = LocationDetector()
        domain_mapper = DomainMapper()
        
        print("1. Fetching Home Assistant data...")
        
        # Get all required data
        entities = await client.get_states()
        areas = await client.get_areas()
        entity_registry = await client.get_entity_registry()
        device_registry = await client.get_device_registry()
        
        print(f"   - Found {len(entities)} entities")
        print(f"   - Found {len(areas)} areas")
        print(f"   - Found {len(entity_registry)} entity registry entries")
        print(f"   - Found {len(device_registry)} device registry entries")
        
        # Build area mappings
        print("\n2. Building area mappings...")
        
        # Entity area mapping
        entity_area_map = {}
        for reg_entity in entity_registry:
            if reg_entity.get('area_id'):
                entity_area_map[reg_entity['entity_id']] = reg_entity['area_id']
        
        # Device area mapping
        device_area_map = {}
        for device in device_registry:
            if device.get('area_id'):
                device_area_map[device['id']] = device['area_id']
        
        print(f"   - {len(entity_area_map)} entities with area assignments")
        print(f"   - {len(device_area_map)} devices with area assignments")
        
        # Filter for relevant entities
        print("\n3. Filtering relevant entities...")
        
        relevant_entities = []
        for entity in entities:
            entity_id = entity['entity_id']
            domain = entity_id.split('.')[0]
            
            if not domain_mapper.is_supported_domain(domain):
                continue
            
            device_type = domain_mapper.determine_device_type(entity, domain)
            if device_type:
                relevant_entities.append(entity)
        
        print(f"   - Found {len(relevant_entities)} relevant entities")
        
        # Test location detection
        print("\n4. Testing location detection...")
        
        location_results = {}
        entities_with_locations = 0
        entities_without_locations = 0
        
        for entity in relevant_entities:
            entity_id = entity['entity_id']
            location = detector.detect_location(
                entity, entity_area_map, device_area_map, areas, entity_registry
            )
            
            if location:
                entities_with_locations += 1
                if location not in location_results:
                    location_results[location] = []
                location_results[location].append(entity_id)
            else:
                entities_without_locations += 1
        
        print(f"   - Entities with locations: {entities_with_locations}")
        print(f"   - Entities without locations: {entities_without_locations}")
        
        # Show location breakdown
        print("\n5. Location breakdown:")
        for location, entity_ids in sorted(location_results.items()):
            print(f"   - {location}: {len(entity_ids)} entities")
            for entity_id in entity_ids[:3]:  # Show first 3
                print(f"     • {entity_id}")
            if len(entity_ids) > 3:
                print(f"     • ... and {len(entity_ids) - 3} more")
        
        # Build location mapping for room-based commands
        print("\n6. Building location mapping for room-based commands...")
        
        location_mapping = detector.build_location_mapping(
            relevant_entities, 
            entity_area_map=entity_area_map,
            device_area_map=device_area_map,
            areas=areas,
            entity_registry=entity_registry
        )
        
        print("   Location mapping structure:")
        for location, device_types in location_mapping.items():
            print(f"   - {location}:")
            for device_type, entity_ids in device_types.items():
                print(f"     • {device_type}: {len(entity_ids)} entities")
                for entity_id in entity_ids[:2]:  # Show first 2
                    print(f"       - {entity_id}")
                if len(entity_ids) > 2:
                    print(f"       - ... and {len(entity_ids) - 2} more")
        
        # Demonstrate room-based commands
        print("\n7. Example room-based commands enabled:")
        
        for location, device_types in location_mapping.items():
            if 'lights' in device_types:
                print(f"   • 'Turn on all lights in the {location}'")
                print(f"   • 'Turn off all lights in the {location}'")
            
            if len(device_types) > 1:
                print(f"   • 'Turn off everything in the {location}'")
        
        # Global commands
        all_device_types = set()
        for device_types in location_mapping.values():
            all_device_types.update(device_types.keys())
        
        print(f"\n   Global commands enabled:")
        for device_type in sorted(all_device_types):
            print(f"   • 'Turn on all {device_type}'")
            print(f"   • 'Turn off all {device_type}'")
        
        print(f"   • 'Turn off everything, everywhere'")
        
        # Summary
        print(f"\n8. Summary:")
        print(f"   - Total locations discovered: {len(location_mapping)}")
        print(f"   - Total device types: {len(all_device_types)}")
        print(f"   - Location detection success rate: {entities_with_locations / len(relevant_entities) * 100:.1f}%")
        
        if entities_without_locations > 0:
            print(f"\n   Entities without location detection:")
            for entity in relevant_entities:
                entity_id = entity['entity_id']
                location = detector.detect_location(
                    entity, entity_area_map, device_area_map, areas, entity_registry
                )
                if not location:
                    print(f"     • {entity_id}")
        
        print(f"\n✅ Location detection test complete!")
        print(f"   The system is now ready for room-based voice commands!")

if __name__ == "__main__":
    asyncio.run(test_location_detection()) 