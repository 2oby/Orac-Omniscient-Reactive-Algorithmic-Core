# Home Assistant Auto-Discovery Implementation Plan

## Overview

This document outlines the implementation plan for transforming ORAC's Home Assistant integration from a static, manually-configured grammar system into a dynamic, auto-discovering system that automatically generates grammar mappings by querying Home Assistant's APIs.

## Current State Analysis

### Existing Components
- **Basic API Client** (`orac/homeassistant/client.py`) - Fetches entities, services, and areas
- **Stub Grammar Manager** (`orac/homeassistant/grammar_manager.py`) - Currently just logs data (needs replacement)
- **Static Grammar File** (`data/grammars.yaml`) - Manual configuration
- **Data Models** (`orac/homeassistant/models.py`) - Good foundation for structured data
- **Raw Data Files** - `ha_entities.json`, `ha_services.json` (areas returns 404)

### Key Limitations
1. Grammar manager is a stub that only logs data
2. Manual configuration required for all mappings
3. No automatic discovery of Home Assistant setup
4. Static grammar constraints that don't reflect actual devices
5. No integration with Home Assistant's area registry and device registry

## Implementation Phases

### Phase 1: Core Discovery Infrastructure ✅ **IN PROGRESS**
**Duration**: 1-2 weeks
**Goal**: Implement the foundational discovery services

#### 1.1 Enhanced API Client (`orac/homeassistant/client.py`) ✅ **COMPLETED**
- ✅ Add new API endpoints for entity registry and device registry
- ✅ Implement `get_entity_registry()` method
- ✅ Implement `get_device_registry()` method
- ✅ Update constants to include new endpoints
- ✅ Add error handling for missing endpoints

**Status**: All API endpoints implemented and tested. Entity and device registry methods added to client with proper error handling and caching support.

#### 1.2 Discovery Service (`orac/homeassistant/discovery_service.py`) 🔄 **PENDING**
- Implement `HADiscoveryService` class
- Add `discover_all()` method for complete discovery process
- Add individual discovery methods for each API endpoint
- Implement connection validation and error handling

#### 1.3 Mapping Builder (`orac/homeassistant/mapping_builder.py`) 🔄 **PENDING**
- Implement `HAMappingBuilder` class
- Add domain-to-device-type mapping logic
- Implement smart location detection algorithms
- Add device type determination logic
- Include action mapping for each domain

### Phase 2: Grammar Manager Overhaul
**Duration**: 1 week
**Goal**: Replace stub grammar manager with auto-discovery capabilities

#### 2.1 Complete Grammar Manager Replacement (`orac/homeassistant/grammar_manager.py`)
- Replace stub implementation with `HAMappingBuilder` integration
- Implement `generate_grammar()` method using discovered data
- Add `update_grammar()` method for dynamic updates
- Include mapping structure generation
- Add support for manual overrides

#### 2.2 Enhanced Data Models (`orac/homeassistant/models.py`)
- Add models for mapping structure (vocabulary, device_actions, device_locations, entity_mappings)
- Add models for entity registry and device registry entries
- Include models for complete grammar mapping structure
- Add validation for auto-discovered data

### Phase 3: CLI and API Integration
**Duration**: 1 week
**Goal**: Add discovery commands and API endpoints

#### 3.1 CLI Integration (`orac/cli.py`)
- Add `discover` command for full auto-discovery process
- Add `generate-mapping` command for mapping file generation
- Add `update-grammar` command for grammar constraint updates
- Add `validate-mapping` command for mapping validation
- Include progress reporting and error handling

#### 3.2 API Integration (`orac/api.py`)
- Add `/api/discovery/run` endpoint for triggering discovery
- Add `/api/discovery/status` endpoint for discovery status
- Add `/api/mapping/generate` endpoint for mapping generation
- Add `/api/grammar/update` endpoint for grammar updates
- Include authentication and rate limiting

### Phase 4: Dynamic Grammar Generation
**Duration**: 1 week
**Goal**: Implement dynamic grammar constraint updates

#### 4.1 Grammar File Evolution (`data/grammars.yaml`)
- Maintain backward compatibility with existing structure
- Add auto-discovery metadata section
- Implement dynamic constraint generation
- Add versioning and discovery timestamps

#### 4.2 Grammar Generator (`orac/homeassistant/grammar_generator.py`)
- Implement dynamic grammar rule generation
- Add constraint validation and optimization
- Include grammar rule caching
- Add grammar validation and testing

### Phase 5: Advanced Features and Polish
**Duration**: 1 week
**Goal**: Add manual overrides and advanced customization

#### 5.1 Manual Override Support
- Implement manual override file format
- Add override merging logic
- Include override validation
- Add override conflict resolution

#### 5.2 Configuration Updates (`orac/homeassistant/config.py`)
- Add discovery-specific configuration options
- Add mapping file paths and auto-discovery settings
- Include manual override file paths
- Add discovery frequency and caching settings

#### 5.3 Testing and Validation
- Add comprehensive test suite for discovery process
- Implement mapping validation tests
- Add grammar generation tests
- Include integration tests with real Home Assistant instances

## Success Criteria

### Phase 1 Success Criteria
- [ ] Discovery service can fetch all required Home Assistant data
- [ ] Mapping builder generates valid mapping structures
- [ ] All API endpoints are properly handled with error recovery
- [ ] Basic mapping generation works with sample data

### Phase 2 Success Criteria
- [ ] Grammar manager generates complete grammar mappings
- [ ] Data models provide type safety for all structures
- [ ] Manual overrides can be applied to auto-discovered data
- [ ] Grammar generation is consistent and reliable

### Phase 3 Success Criteria
- [ ] CLI commands work end-to-end
- [ ] API endpoints are functional and secure
- [ ] Discovery process can be triggered programmatically
- [ ] Status reporting works correctly

### Phase 4 Success Criteria
- [ ] Dynamic grammar constraints reflect actual Home Assistant setup
- [ ] Grammar files are automatically updated
- [ ] Backward compatibility is maintained
- [ ] Grammar validation passes for generated rules

### Phase 5 Success Criteria
- [ ] Manual overrides work seamlessly with auto-discovery
- [ ] Configuration system supports all discovery options
- [ ] Comprehensive test coverage is achieved
- [ ] Documentation is complete and accurate

## Risk Mitigation

### Technical Risks
1. **API Changes**: Home Assistant API endpoints may change
   - *Mitigation*: Implement version detection and fallback mechanisms
2. **Performance**: Large Home Assistant setups may be slow to discover
   - *Mitigation*: Implement caching and incremental updates
3. **Data Quality**: Auto-discovered data may be incomplete or incorrect
   - *Mitigation*: Add validation and manual override capabilities

### Integration Risks
1. **Backward Compatibility**: Existing grammar files may break
   - *Mitigation*: Maintain compatibility layer and migration tools
2. **User Adoption**: Users may prefer manual configuration
   - *Mitigation*: Provide both auto-discovery and manual options

## Testing Strategy

### Unit Testing
- Test each discovery service method independently
- Test mapping builder logic with various input scenarios
- Test grammar generation with different Home Assistant setups

### Integration Testing
- Test with real Home Assistant instances
- Test with various Home Assistant configurations
- Test with different device types and area setups

### End-to-End Testing
- Test complete discovery-to-grammar generation pipeline
- Test CLI and API integration
- Test manual override functionality

## Documentation Requirements

### Technical Documentation
- API reference for new discovery services
- Configuration guide for auto-discovery settings
- Migration guide from manual to auto-discovery
- Troubleshooting guide for common issues

### User Documentation
- Getting started guide for auto-discovery
- Manual override configuration guide
- CLI command reference
- API endpoint documentation

## Timeline Summary

- **Phase 1**: Weeks 1-2 - Core discovery infrastructure
- **Phase 2**: Week 3 - Grammar manager overhaul
- **Phase 3**: Week 4 - CLI and API integration
- **Phase 4**: Week 5 - Dynamic grammar generation
- **Phase 5**: Week 6 - Advanced features and polish

**Total Duration**: 6 weeks

## Appendix A: Original Auto-Discovery Proposal

### Home Assistant API Discovery Process

The original proposal outlined a comprehensive approach to automatically generate mapping/grammar files by querying Home Assistant's APIs. This process involves discovering entities, organizing them by type and location, and building the complete mapping structure.

#### Required Imports
```python
import aiohttp
import asyncio
import yaml
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
```

#### 1. Entity Discovery

Home Assistant provides several APIs to discover entities and their relationships:

```python
class HADiscoveryService:
    def __init__(self, ha_url: str, token: str):
        self.ha_url = ha_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    async def discover_all(self):
        """Complete discovery process"""
        # 1. Get all entities
        entities = await self.get_entities()
        
        # 2. Get areas (rooms)
        areas = await self.get_areas()
        
        # 3. Get devices and their area assignments
        devices = await self.get_devices()
        
        # 4. Get entity registry for area assignments
        entity_registry = await self.get_entity_registry()
        
        # 5. Build the mapping structure
        return self.build_mapping(entities, areas, devices, entity_registry)
```

#### 2. Key Home Assistant APIs

**States API** - Get all current entities and their states:
```python
async def get_entities(self):
    """Get all entities from Home Assistant"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{self.ha_url}/api/states",
            headers=self.headers
        ) as response:
            response.raise_for_status()
            return await response.json()
```

**Area Registry** - Get defined areas/rooms:
```python
async def get_areas(self):
    """Get all areas (rooms) from Home Assistant"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{self.ha_url}/api/config/area_registry/list",
            headers=self.headers
        ) as response:
            response.raise_for_status()
            data = await response.json()
            return {area['area_id']: area['name'] for area in data}
```

**Device Registry** - Get devices and their area assignments:
```python
async def get_devices(self):
    """Get all devices and their area assignments"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{self.ha_url}/api/config/device_registry/list",
            headers=self.headers
        ) as response:
            response.raise_for_status()
            return await response.json()
```

**Entity Registry** - Get entity-to-area mappings:
```python
async def get_entity_registry(self):
    """Get entity registry with area assignments"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{self.ha_url}/api/config/entity_registry/list",
            headers=self.headers
        ) as response:
            response.raise_for_status()
            return await response.json()
```

#### 3. Building the Mapping Structure

The `HAMappingBuilder` class implements the complete process to build the mapping file:

```python
class HAMappingBuilder:
    # Mapping of HA domains to our simplified device types
    DOMAIN_TO_DEVICE_TYPE = {
        'light': 'lights',
        'switch': 'lights',  # Many switches control lights
        'climate': 'thermostat',
        'fan': 'fan',
        'cover': 'blinds',
        'media_player': 'tv',  # or 'music' based on device_class
        'alarm_control_panel': 'alarm'
    }
    
    # Actions available for each HA domain
    DOMAIN_ACTIONS = {
        'light': ["turn on", "turn off", "toggle", "dim", "brighten", "set to %"],
        'switch': ["turn on", "turn off", "toggle"],
        'climate': ["turn on", "turn off", "set to %", "increase", "decrease"],
        'fan': ["turn on", "turn off", "toggle", "set to %"],
        'cover': ["open", "close", "raise", "lower", "set to %"],
        'media_player': ["turn on", "turn off", "play", "pause", "stop", "set to %"],
        'alarm_control_panel': ["turn on", "turn off", "toggle"]
    }
    
    def _get_service_mappings(self):
        """Get service mappings for actions"""
        return {
            "turn on": ["light.turn_on", "switch.turn_on", "climate.set_hvac_mode"],
            "turn off": ["light.turn_off", "switch.turn_off", "climate.set_hvac_mode"],
            "toggle": ["light.toggle", "switch.toggle"],
            "dim": ["light.turn_on"],
            "brighten": ["light.turn_on"],
            "set to %": ["light.turn_on", "climate.set_temperature", "fan.set_percentage"],
            "increase": ["climate.set_temperature"],
            "decrease": ["climate.set_temperature"],
            "open": ["cover.open_cover"],
            "close": ["cover.close_cover"],
            "raise": ["cover.open_cover"],
            "lower": ["cover.close_cover"],
            "play": ["media_player.media_play"],
            "pause": ["media_player.media_pause"],
            "stop": ["media_player.media_stop"]
        }
    
    def _parse_location_from_name(self, entity):
        """Parse location from entity name or ID"""
        common_locations = [
            'bedroom', 'kitchen', 'living room', 'bathroom',
            'garage', 'office', 'basement', 'hallway',
            'dining room', 'guest room', 'master bedroom'
        ]
        
        # Check friendly name first
        friendly_name = entity.get('attributes', {}).get('friendly_name', '').lower()
        entity_id = entity['entity_id'].lower()
        
        for location in common_locations:
            # Handle multi-word locations
            location_variants = [
                location,
                location.replace(' ', '_'),
                location.replace(' ', '-')
            ]
            
            for variant in location_variants:
                if variant in friendly_name or variant in entity_id:
                    return location
        
        return 'unknown'
    
    def build_mapping(self, entities, areas, devices, entity_registry):
        """Build the complete mapping structure"""
        # Initialize structure
        mapping = {
            "version": "1.0",
            "last_updated": datetime.now().isoformat() + "Z",
            "auto_discovered": True,
            "vocabulary": {
                "devices": ["lights", "thermostat", "fan", "blinds", "tv", "music", "alarm"],
                "actions": [
                    "turn on", "turn off", "toggle", "dim", "brighten", "set to %",
                    "increase", "decrease", "open", "close", "lock", "unlock",
                    "play", "pause", "stop", "raise", "lower"
                ],
                "locations": ["all", "everywhere"]
            },
            "device_actions": {},
            "device_locations": {"all": [], "everywhere": []},
            "entity_mappings": {},
            "service_mappings": self._get_service_mappings()
        }
        
        # Build entity registry lookup
        entity_area_map = {}
        for entry in entity_registry:
            if entry.get('area_id'):
                entity_area_map[entry['entity_id']] = entry['area_id']
        
        # Build device area lookup
        device_area_map = {}
        for device in devices:
            if device.get('area_id'):
                device_area_map[device['id']] = device['area_id']
        
        # Process each entity
        discovered_locations = set()
        entity_by_location_and_type = {}
        
        for entity in entities:
            entity_id = entity['entity_id']
            domain = entity_id.split('.')[0]
            
            # Skip domains we don't handle
            if domain not in self.DOMAIN_TO_DEVICE_TYPE:
                continue
            
            # Determine device type
            device_type = self._determine_device_type(entity, domain)
            if not device_type:
                continue
            
            # Determine location
            location = self._determine_location(
                entity, entity_id, entity_area_map, 
                device_area_map, areas, entity_registry
            )
            
            if location and location not in ['unknown', 'all', 'everywhere']:
                discovered_locations.add(location)
                
                # Store entity by location and type
                if location not in entity_by_location_and_type:
                    entity_by_location_and_type[location] = {}
                if device_type not in entity_by_location_and_type[location]:
                    entity_by_location_and_type[location][device_type] = []
                
                entity_by_location_and_type[location][device_type].append(entity_id)
        
        # Update vocabulary with discovered locations
        mapping['vocabulary']['locations'].extend(sorted(discovered_locations))
        
        # Build device_actions (which actions each device type supports)
        for device_type in mapping['vocabulary']['devices']:
            actions = set()
            # Find which domains map to this device type
            for domain, dev_type in self.DOMAIN_TO_DEVICE_TYPE.items():
                if dev_type == device_type:
                    actions.update(self.DOMAIN_ACTIONS.get(domain, []))
            mapping['device_actions'][device_type] = sorted(list(actions))
        
        # Build device_locations (which devices exist in which locations)
        for location in discovered_locations:
            mapping['device_locations'][location] = sorted(
                list(entity_by_location_and_type.get(location, {}).keys())
            )
            # Also add to 'all' and 'everywhere'
            for device_type in entity_by_location_and_type.get(location, {}).keys():
                if device_type not in mapping['device_locations']['all']:
                    mapping['device_locations']['all'].append(device_type)
                if device_type not in mapping['device_locations']['everywhere']:
                    mapping['device_locations']['everywhere'].append(device_type)
        
        # Build entity_mappings (actual entity IDs for each location/device combo)
        mapping['entity_mappings'] = entity_by_location_and_type
        
        return mapping
```

#### 4. Smart Device Type and Location Detection

The system includes intelligent algorithms for determining device types and locations:

```python
def _determine_device_type(self, entity, domain):
    """Determine our simplified device type from HA entity"""
    # Check device_class for media players
    if domain == 'media_player':
        device_class = entity.get('attributes', {}).get('device_class', '')
        if 'tv' in device_class.lower() or 'tv' in entity['entity_id']:
            return 'tv'
        else:
            return 'music'
    
    # Check if a switch is actually controlling lights
    if domain == 'switch':
        # Common patterns for light switches
        if any(word in entity['entity_id'].lower() for word in ['light', 'lamp']):
            return 'lights'
        # Skip other switches
        return None
    
    return self.DOMAIN_TO_DEVICE_TYPE.get(domain)

def _determine_location(self, entity, entity_id, entity_area_map, 
                      device_area_map, areas, entity_registry):
    """Determine location of an entity using multiple strategies"""
    
    # Strategy 1: Check entity registry for direct area assignment
    if entity_id in entity_area_map:
        area_id = entity_area_map[entity_id]
        if area_id in areas:
            return areas[area_id].lower().replace('_', ' ')
    
    # Strategy 2: Check device registry
    for reg_entity in entity_registry:
        if reg_entity['entity_id'] == entity_id and reg_entity.get('device_id'):
            device_id = reg_entity['device_id']
            if device_id in device_area_map:
                area_id = device_area_map[device_id]
                if area_id in areas:
                    return areas[area_id].lower().replace('_', ' ')
    
    # Strategy 3: Parse from entity_id or friendly_name
    return self._parse_location_from_name(entity)
```

#### 5. Complete Discovery and Generation Script

The system provides a complete script for generating mappings:

```python
async def generate_ha_mapping(ha_url: str, token: str, output_file: str = "ha_grammar_mapping.yaml"):
    """Complete process to generate mapping file from Home Assistant"""
    
    print("🔍 Discovering Home Assistant configuration...")
    
    discovery = HADiscoveryService(ha_url, token)
    builder = HAMappingBuilder()
    
    try:
        # Discover all components
        print("  - Fetching entities...")
        entities = await discovery.get_entities()
        print(f"    Found {len(entities)} entities")
        
        print("  - Fetching areas...")
        areas = await discovery.get_areas()
        print(f"    Found {len(areas)} areas")
        
        print("  - Fetching devices...")
        devices = await discovery.get_devices()
        print(f"    Found {len(devices)} devices")
        
        print("  - Fetching entity registry...")
        entity_registry = await discovery.get_entity_registry()
        
        # Build mapping
        print("\n🔨 Building mapping structure...")
        mapping = builder.build_mapping(entities, areas, devices, entity_registry)
        
        # Summary
        print("\n📊 Discovery Summary:")
        print(f"  - Locations: {len(mapping['vocabulary']['locations'])}")
        print(f"  - Device Types: {len(mapping['vocabulary']['devices'])}")
        print(f"  - Total Entities Mapped: {sum(len(devices) for loc in mapping['entity_mappings'].values() for devices in loc.values())}")
        
        # Save to file
        print(f"\n💾 Saving to {output_file}...")
        with open(output_file, 'w') as f:
            yaml.dump(mapping, f, default_flow_style=False, sort_keys=False)
        
        print("✅ Complete!")
        return mapping
        
    except aiohttp.ClientError as e:
        print(f"❌ API Error: {e}")
        raise
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        raise
```

#### 6. Manual Overrides and Customization

The system supports manual overrides for customization:

```python
def merge_with_manual_overrides(auto_mapping: dict, manual_file: str = "manual_overrides.yaml"):
    """Merge auto-discovered mapping with manual overrides"""
    
    if os.path.exists(manual_file):
        with open(manual_file, 'r') as f:
            manual = yaml.safe_load(f)
        
        # Merge entity mappings
        for location, devices in manual.get('entity_mappings', {}).items():
            if location not in auto_mapping['entity_mappings']:
                auto_mapping['entity_mappings'][location] = {}
            for device_type, entities in devices.items():
                if device_type not in auto_mapping['entity_mappings'][location]:
                    auto_mapping['entity_mappings'][location][device_type] = []
                # Add manual entities
                for entity in entities:
                    if entity not in auto_mapping['entity_mappings'][location][device_type]:
                        auto_mapping['entity_mappings'][location][device_type].append(entity)
        
        # Update device_locations based on new entities
        for location, devices in auto_mapping['entity_mappings'].items():
            auto_mapping['device_locations'][location] = sorted(list(devices.keys()))
    
    return auto_mapping
```

### Key Benefits of Auto-Discovery

1. **Always Up-to-Date**: Run the discovery whenever you add new devices
2. **Accurate Area Mapping**: Uses HA's area registry for correct room assignments
3. **Smart Type Detection**: Identifies device types from domains and device classes
4. **Handles Edge Cases**: Switches that control lights, media players that are TVs vs speakers
5. **Manual Override Support**: Can merge with manual configurations

The discovery process ensures your grammar constraints exactly match your actual Home Assistant setup, preventing the LLM from generating commands for devices that don't exist or aren't in the specified location. 