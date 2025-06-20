#!/usr/bin/env python3
"""
Script to analyze Home Assistant entities and extract relevant ones for home automation.
"""

import json
from typing import Dict, List, Set

def analyze_entities():
    """Analyze the fetched Home Assistant entities."""
    
    # Load entities
    with open('ha_entities_formatted.json', 'r') as f:
        entities = json.load(f)
    
    # Categories for analysis
    controllable_entities = {
        'light', 'switch', 'climate', 'cover', 'media_player', 
        'fan', 'lock', 'vacuum', 'scene', 'input_button', 'input_boolean'
    }
    
    status_entities = {
        'binary_sensor', 'sensor'
    }
    
    system_entities = {
        'sun', 'zone', 'conversation', 'weather', 'tts', 'todo', 'person'
    }
    
    # Categorize entities
    controllable = []
    status = []
    system = []
    other = []
    
    for entity in entities:
        entity_id = entity['entity_id']
        domain = entity_id.split('.')[0]
        friendly_name = entity.get('attributes', {}).get('friendly_name', entity_id)
        state = entity.get('state', 'unknown')
        
        entity_info = {
            'entity_id': entity_id,
            'friendly_name': friendly_name,
            'state': state,
            'domain': domain
        }
        
        if domain in controllable_entities:
            controllable.append(entity_info)
        elif domain in status_entities:
            status.append(entity_info)
        elif domain in system_entities:
            system.append(entity_info)
        else:
            other.append(entity_info)
    
    # Print summary
    print("=== HOME ASSISTANT ENTITIES ANALYSIS ===\n")
    
    print(f"Total entities found: {len(entities)}")
    print(f"Controllable entities: {len(controllable)}")
    print(f"Status entities: {len(status)}")
    print(f"System entities: {len(system)}")
    print(f"Other entities: {len(other)}\n")
    
    print("=== CONTROLLABLE ENTITIES ===")
    for entity in controllable:
        print(f"• {entity['entity_id']} ({entity['friendly_name']}) - State: {entity['state']}")
    
    print(f"\n=== STATUS ENTITIES ({len(status)}) ===")
    for entity in status:
        print(f"• {entity['entity_id']} ({entity['friendly_name']}) - State: {entity['state']}")
    
    print(f"\n=== SYSTEM ENTITIES ({len(system)}) ===")
    for entity in system:
        print(f"• {entity['entity_id']} ({entity['friendly_name']}) - State: {entity['state']}")
    
    # Group by location/room
    print(f"\n=== ENTITIES BY LOCATION ===")
    location_groups = {}
    
    for entity in controllable + status:
        friendly_name = entity['friendly_name'].lower()
        entity_id = entity['entity_id']
        
        # Extract location from friendly name or entity ID
        location = None
        if 'bedroom' in friendly_name or 'bedroom' in entity_id:
            location = 'Bedroom'
        elif 'bathroom' in friendly_name or 'bathroom' in entity_id:
            location = 'Bathroom'
        elif 'kitchen' in friendly_name or 'kitchen' in entity_id:
            location = 'Kitchen'
        elif 'hall' in friendly_name or 'hall' in entity_id:
            location = 'Hall'
        elif 'lounge' in friendly_name or 'lounge' in entity_id:
            location = 'Lounge'
        elif 'living' in friendly_name or 'living' in entity_id:
            location = 'Living Room'
        else:
            location = 'Other'
        
        if location not in location_groups:
            location_groups[location] = []
        
        location_groups[location].append(entity)
    
    for location, entities in location_groups.items():
        print(f"\n{location}:")
        for entity in entities:
            print(f"  • {entity['entity_id']} ({entity['friendly_name']}) - {entity['state']}")

if __name__ == "__main__":
    analyze_entities() 