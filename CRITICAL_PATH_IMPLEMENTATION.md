# Critical Path Implementation Plan

## Overview

This document focuses on the three most critical components that must be implemented correctly for the Home Assistant auto-discovery system to work:


TEMP: Prio 1, we are working on this now


Step-by-Step Implementation Plan: Improved Git Submodule Approach
Phase 1: Preparation & Coordination
Step 1.1: Verify current state on both machines
Confirm both machines are at the same commit (40678b3 + our reset commit)
Ensure both have the same manual binaries in place
Check that .gitmodules is removed on both
Step 1.2: Decide on target version
Choose specific tag/commit from llama-cpp-jetson repo
Options: main branch, specific tag (e.g., v1.0.0), or specific commit hash
Phase 2: Set up Submodule on Local Machine
Step 2.1: Add submodule to local machine
Apply to CRITICAL_PAT...
Run
llama_cpp
Step 2.2: Checkout specific version
Apply to CRITICAL_PAT...
Run
.
Step 2.3: Commit the submodule setup
Apply to CRITICAL_PAT...
Run
"
Phase 3: Sync to Test Machine
Step 3.1: Push changes from local machine
Apply to CRITICAL_PAT...
Run
Grammar
Step 3.2: Pull changes on test machine
Apply to CRITICAL_PAT...
Run
"
Step 3.3: Initialize submodule on test machine
Apply to CRITICAL_PAT...
Run
"
Phase 4: Verification & Testing
Step 4.1: Verify submodule status on both machines
Apply to CRITICAL_PAT...
Run
"
Step 4.2: Test that binaries work
Run a simple test to ensure llama.cpp binaries are functional
Verify the correct version is installed
Phase 5: Create Management Scripts
Step 5.1: Create binary update script
Apply to CRITICAL_PAT...
Run
]
Step 5.2: Create binary version check script
Apply to CRITICAL_PAT...
Run
versions
Phase 6: Documentation & Cleanup
Step 6.1: Update documentation
Document the new submodule approach
Add instructions for updating binaries
Update setup scripts
Step 6.2: Clean up any temporary files
Remove backup directories
Clean up any temporary build artifacts
Questions to Resolve:
What specific version should we target initially? (main, a tag, or specific commit?)
Should we implement the management scripts immediately, or set up the basic submodule first?
Do you want to test the binaries after each step, or complete the full setup first?
Which step would you like to start with, and what version should we target?




-----


1. **Entity Registry API Integration** - Room/area assignments
2. **Domain-to-Device Mapping Logic** - Simplification heart
3. **Location Detection Algorithm** - Multiple fallback strategies

## 1. Entity Registry API Integration ✅ **COMPLETED**

### Current State
- ✅ Current client fetches `/api/states`, `/api/services`, `/api/areas`
- ✅ Added entity registry and device registry endpoints
- ✅ Area assignment data now available

### Implementation Priority: **HIGHEST** ✅ **COMPLETED**

#### 1.1 Add New API Endpoints to Constants ✅ **COMPLETED**
```python
# orac/homeassistant/constants.py
API_ENTITY_REGISTRY = "/api/config/entity_registry/list"
API_DEVICE_REGISTRY = "/api/config/device_registry/list"
```

#### 1.2 Extend Client with Entity Registry Methods ✅ **COMPLETED**
```python
# orac/homeassistant/client.py
async def get_entity_registry(self, use_cache: bool = True) -> List[Dict[str, Any]]:
    """Get entity registry with area assignments"""
    if use_cache:
        cached_registry = self._cache.get_entity_registry()
        if cached_registry is not None:
            return cached_registry
    
    try:
        registry = await self._request("GET", API_ENTITY_REGISTRY)
        self._cache.set_entity_registry(registry)
        return registry
    except aiohttp.ClientError as e:
        logger.warning(f"Failed to fetch entity registry: {e}")
        return []

async def get_device_registry(self, use_cache: bool = True) -> List[Dict[str, Any]]:
    """Get device registry with area assignments"""
    if use_cache:
        cached_devices = self._cache.get_device_registry()
        if cached_devices is not None:
            return cached_devices
    
    try:
        devices = await self._request("GET", API_DEVICE_REGISTRY)
        self._cache.set_device_registry(devices)
        return devices
    except aiohttp.ClientError as e:
        logger.warning(f"Failed to fetch device registry: {e}")
        return []
```

#### 1.3 Add Cache Support for New Endpoints ✅ **COMPLETED**
```python
# orac/homeassistant/cache.py
def set_entity_registry(self, registry: List[Dict[str, Any]]) -> None:
    """Cache entity registry data"""
    self._cache['entity_registry'] = {
        'data': registry,
        'timestamp': time.time()
    }

def get_entity_registry(self) -> Optional[List[Dict[str, Any]]]:
    """Get cached entity registry data"""
    return self._get_cached_data('entity_registry')

def set_device_registry(self, devices: List[Dict[str, Any]]) -> None:
    """Cache device registry data"""
    self._cache['device_registry'] = {
        'data': devices,
        'timestamp': time.time()
    }

def get_device_registry(self) -> Optional[List[Dict[str, Any]]]:
    """Get cached device registry data"""
    return self._get_cached_data('device_registry')
```

### Success Criteria ✅ **ALL COMPLETED**
- ✅ Entity registry endpoint returns area assignments
- ✅ Device registry endpoint returns device area mappings
- ✅ Cache properly stores and retrieves registry data
- ✅ Error handling for missing endpoints

## 2. Domain-to-Device Mapping Logic

### Current State
- No domain mapping logic exists
- Need to convert complex HA domains to simple device types
- Must handle edge cases (switches that control lights, media players that are TVs vs speakers)

### Implementation Priority: **HIGHEST**

#### 2.1 Create Domain Mapping Class
```python
# orac/homeassistant/domain_mapper.py
from typing import Dict, List, Optional, Any
from enum import Enum

class DeviceType(str, Enum):
    """Simplified device types for user-friendly commands"""
    LIGHTS = "lights"
    THERMOSTAT = "thermostat"
    FAN = "fan"
    BLINDS = "blinds"
    TV = "tv"
    MUSIC = "music"
    ALARM = "alarm"
    SWITCH = "switch"  # Generic switches not controlling lights

class DomainMapper:
    """Maps Home Assistant domains to simplified device types"""
    
    # Core domain mappings
    DOMAIN_TO_DEVICE_TYPE = {
        'light': DeviceType.LIGHTS,
        'climate': DeviceType.THERMOSTAT,
        'fan': DeviceType.FAN,
        'cover': DeviceType.BLINDS,
        'alarm_control_panel': DeviceType.ALARM,
    }
    
    # Actions available for each domain
    DOMAIN_ACTIONS = {
        'light': ["turn on", "turn off", "toggle", "dim", "brighten", "set to %"],
        'switch': ["turn on", "turn off", "toggle"],
        'climate': ["turn on", "turn off", "set to %", "increase", "decrease"],
        'fan': ["turn on", "turn off", "toggle", "set to %"],
        'cover': ["open", "close", "raise", "lower", "set to %"],
        'media_player': ["turn on", "turn off", "play", "pause", "stop", "set to %"],
        'alarm_control_panel': ["turn on", "turn off", "toggle"]
    }
    
    def determine_device_type(self, entity: Dict[str, Any], domain: str) -> Optional[DeviceType]:
        """Determine simplified device type from HA entity"""
        
        # Handle media players (TV vs Music)
        if domain == 'media_player':
            return self._determine_media_player_type(entity)
        
        # Handle switches (lights vs generic)
        if domain == 'switch':
            return self._determine_switch_type(entity)
        
        # Handle covers (blinds vs other covers)
        if domain == 'cover':
            return self._determine_cover_type(entity)
        
        # Default domain mapping
        return self.DOMAIN_TO_DEVICE_TYPE.get(domain)
    
    def _determine_media_player_type(self, entity: Dict[str, Any]) -> DeviceType:
        """Determine if media player is TV or music device"""
        entity_id = entity['entity_id'].lower()
        friendly_name = entity.get('attributes', {}).get('friendly_name', '').lower()
        device_class = entity.get('attributes', {}).get('device_class', '').lower()
        
        # TV indicators
        tv_indicators = ['tv', 'television', 'display', 'monitor', 'screen']
        if any(indicator in entity_id for indicator in tv_indicators):
            return DeviceType.TV
        if any(indicator in friendly_name for indicator in tv_indicators):
            return DeviceType.TV
        if 'tv' in device_class:
            return DeviceType.TV
        
        # Music indicators
        music_indicators = ['speaker', 'audio', 'sound', 'music', 'amp', 'receiver']
        if any(indicator in entity_id for indicator in music_indicators):
            return DeviceType.MUSIC
        if any(indicator in friendly_name for indicator in music_indicators):
            return DeviceType.MUSIC
        
        # Default to music for unknown media players
        return DeviceType.MUSIC
    
    def _determine_switch_type(self, entity: Dict[str, Any]) -> Optional[DeviceType]:
        """Determine if switch controls lights or is generic"""
        entity_id = entity['entity_id'].lower()
        friendly_name = entity.get('attributes', {}).get('friendly_name', '').lower()
        
        # Light control indicators
        light_indicators = ['light', 'lamp', 'bulb', 'ceiling', 'wall', 'floor']
        if any(indicator in entity_id for indicator in light_indicators):
            return DeviceType.LIGHTS
        if any(indicator in friendly_name for indicator in light_indicators):
            return DeviceType.LIGHTS
        
        # Skip generic switches (don't include in mapping)
        return None
    
    def _determine_cover_type(self, entity: Dict[str, Any]) -> DeviceType:
        """Determine cover type (default to blinds)"""
        entity_id = entity['entity_id'].lower()
        friendly_name = entity.get('attributes', {}).get('friendly_name', '').lower()
        
        # Non-blind indicators
        non_blind_indicators = ['garage', 'door', 'gate', 'shutter']
        if any(indicator in entity_id for indicator in non_blind_indicators):
            return DeviceType.SWITCH  # Treat as generic switch
        
        return DeviceType.BLINDS
    
    def get_actions_for_device_type(self, device_type: DeviceType) -> List[str]:
        """Get available actions for a device type"""
        actions = set()
        
        # Find which domains map to this device type
        for domain, mapped_type in self.DOMAIN_TO_DEVICE_TYPE.items():
            if mapped_type == device_type:
                actions.update(self.DOMAIN_ACTIONS.get(domain, []))
        
        # Handle special cases
        if device_type == DeviceType.TV:
            actions.update(self.DOMAIN_ACTIONS.get('media_player', []))
        elif device_type == DeviceType.MUSIC:
            actions.update(self.DOMAIN_ACTIONS.get('media_player', []))
        
        return sorted(list(actions))
```

#### 2.2 Add Data Models for Device Types
```python
# orac/homeassistant/models.py
class DeviceMapping(BaseModel):
    """Model for device type mapping"""
    entity_id: str
    device_type: DeviceType
    domain: str
    friendly_name: Optional[str] = None
    area_id: Optional[str] = None
    location: Optional[str] = None
    supported_actions: List[str] = Field(default_factory=list)
```

### Success Criteria
- [ ] All major HA domains mapped to simplified device types
- [ ] Smart detection for media players (TV vs Music)
- [ ] Smart detection for switches (lights vs generic)
- [ ] Proper action mapping for each device type
- [ ] Edge cases handled correctly

## 3. Location Detection Algorithm

### Current State
- No location detection logic exists
- Need multiple fallback strategies
- Must handle missing area assignments gracefully

### Implementation Priority: **HIGHEST**

#### 3.1 Create Location Detection Class
```python
# orac/homeassistant/location_detector.py
from typing import Dict, List, Optional, Any, Set
import re

class LocationDetector:
    """Detects entity locations using multiple strategies"""
    
    def __init__(self):
        # Common location patterns
        self.common_locations = {
            'bedroom': ['bedroom', 'master', 'guest', 'kids', 'child'],
            'kitchen': ['kitchen', 'cooking', 'pantry'],
            'living room': ['living', 'lounge', 'family', 'sitting'],
            'bathroom': ['bathroom', 'toilet', 'shower', 'washroom'],
            'office': ['office', 'study', 'workspace', 'desk'],
            'garage': ['garage', 'carport'],
            'basement': ['basement', 'cellar'],
            'attic': ['attic', 'loft'],
            'hallway': ['hall', 'corridor', 'passage'],
            'dining room': ['dining', 'dinner'],
            'laundry': ['laundry', 'utility', 'washer'],
            'outdoor': ['outdoor', 'outside', 'exterior', 'garden', 'patio']
        }
    
    def detect_location(self, 
                       entity: Dict[str, Any],
                       entity_area_map: Dict[str, str],
                       device_area_map: Dict[str, str],
                       areas: Dict[str, str],
                       entity_registry: List[Dict[str, Any]]) -> Optional[str]:
        """Detect entity location using multiple strategies"""
        
        entity_id = entity['entity_id']
        
        # Strategy 1: Direct entity area assignment
        location = self._check_entity_area_assignment(entity_id, entity_area_map, areas)
        if location:
            return location
        
        # Strategy 2: Device area assignment
        location = self._check_device_area_assignment(entity_id, device_area_map, areas, entity_registry)
        if location:
            return location
        
        # Strategy 3: Parse from entity ID
        location = self._parse_from_entity_id(entity_id)
        if location:
            return location
        
        # Strategy 4: Parse from friendly name
        location = self._parse_from_friendly_name(entity)
        if location:
            return location
        
        # Strategy 5: Parse from device info
        location = self._parse_from_device_info(entity, entity_registry)
        if location:
            return location
        
        return None
    
    def _check_entity_area_assignment(self, entity_id: str, entity_area_map: Dict[str, str], areas: Dict[str, str]) -> Optional[str]:
        """Check if entity has direct area assignment"""
        if entity_id in entity_area_map:
            area_id = entity_area_map[entity_id]
            if area_id in areas:
                return self._normalize_location_name(areas[area_id])
        return None
    
    def _check_device_area_assignment(self, entity_id: str, device_area_map: Dict[str, str], areas: Dict[str, str], entity_registry: List[Dict[str, Any]]) -> Optional[str]:
        """Check if entity's device has area assignment"""
        # Find device ID for this entity
        device_id = None
        for reg_entity in entity_registry:
            if reg_entity['entity_id'] == entity_id and reg_entity.get('device_id'):
                device_id = reg_entity['device_id']
                break
        
        if device_id and device_id in device_area_map:
            area_id = device_area_map[device_id]
            if area_id in areas:
                return self._normalize_location_name(areas[area_id])
        
        return None
    
    def _parse_from_entity_id(self, entity_id: str) -> Optional[str]:
        """Parse location from entity ID"""
        entity_id_lower = entity_id.lower()
        
        for location, patterns in self.common_locations.items():
            for pattern in patterns:
                if pattern in entity_id_lower:
                    return location
        
        return None
    
    def _parse_from_friendly_name(self, entity: Dict[str, Any]) -> Optional[str]:
        """Parse location from friendly name"""
        friendly_name = entity.get('attributes', {}).get('friendly_name', '').lower()
        if not friendly_name:
            return None
        
        for location, patterns in self.common_locations.items():
            for pattern in patterns:
                if pattern in friendly_name:
                    return location
        
        return None
    
    def _parse_from_device_info(self, entity: Dict[str, Any], entity_registry: List[Dict[str, Any]]) -> Optional[str]:
        """Parse location from device information"""
        entity_id = entity['entity_id']
        
        # Find device info for this entity
        for reg_entity in entity_registry:
            if reg_entity['entity_id'] == entity_id:
                device_name = reg_entity.get('name', '').lower()
                if device_name:
                    for location, patterns in self.common_locations.items():
                        for pattern in patterns:
                            if pattern in device_name:
                                return location
                break
        
        return None
    
    def _normalize_location_name(self, area_name: str) -> str:
        """Normalize area name to standard location format"""
        # Convert to lowercase and replace underscores/hyphens with spaces
        normalized = area_name.lower().replace('_', ' ').replace('-', ' ')
        
        # Map common variations to standard names
        location_mapping = {
            'living': 'living room',
            'lounge': 'living room',
            'family room': 'living room',
            'sitting room': 'living room',
            'dining': 'dining room',
            'dinner room': 'dining room',
            'master bedroom': 'bedroom',
            'guest bedroom': 'bedroom',
            'kids bedroom': 'bedroom',
            'child bedroom': 'bedroom',
            'utility room': 'laundry',
            'washer room': 'laundry',
            'garden': 'outdoor',
            'patio': 'outdoor',
            'backyard': 'outdoor',
            'front yard': 'outdoor'
        }
        
        return location_mapping.get(normalized, normalized)
    
    def get_discovered_locations(self, entities: List[Dict[str, Any]], **kwargs) -> Set[str]:
        """Get all discovered locations from entities"""
        locations = set()
        
        for entity in entities:
            location = self.detect_location(entity, **kwargs)
            if location and location not in ['unknown', 'all', 'everywhere']:
                locations.add(location)
        
        return locations
```

#### 3.2 Add Location Validation
```python
def validate_location_detection(self, entities: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
    """Validate location detection results"""
    results = {
        'total_entities': len(entities),
        'entities_with_locations': 0,
        'entities_without_locations': 0,
        'detection_methods': {
            'entity_area': 0,
            'device_area': 0,
            'entity_id_parse': 0,
            'friendly_name_parse': 0,
            'device_info_parse': 0
        },
        'locations_found': set(),
        'entities_without_location': []
    }
    
    for entity in entities:
        # Track which method was used (simplified)
        location = self.detect_location(entity, **kwargs)
        if location:
            results['entities_with_locations'] += 1
            results['locations_found'].add(location)
        else:
            results['entities_without_locations'] += 1
            results['entities_without_location'].append(entity['entity_id'])
    
    return results
```

### Success Criteria
- [ ] Multiple detection strategies implemented
- [ ] Graceful fallback when area assignments missing
- [ ] Location name normalization
- [ ] Validation and reporting capabilities
- [ ] Handles edge cases and variations

## Integration Testing Plan

### Test Scenarios
1. **Complete Setup**: Entity with area assignment
2. **Device Assignment**: Entity without direct area but device has area
3. **Name Parsing**: Entity with location in name/ID
4. **Missing Data**: Entity with no location information
5. **Edge Cases**: Unusual naming patterns

### Validation Metrics
- Location detection success rate > 90%
- Device type mapping accuracy > 95%
- API endpoint reliability > 99%

## Implementation Order

1. **Week 1**: Entity Registry API Integration ✅ **COMPLETED**
2. **Week 2**: Domain-to-Device Mapping Logic 🔄 **NEXT**
3. **Week 3**: Location Detection Algorithm 🔄 **PENDING**
4. **Week 4**: Integration and Testing 🔄 **PENDING**

## Progress Summary

### ✅ **COMPLETED - Entity Registry API Integration**
- **Constants Updated**: Added `API_ENTITY_REGISTRY` and `API_DEVICE_REGISTRY` endpoints
- **Client Enhanced**: Added `get_entity_registry()` and `get_device_registry()` methods with proper error handling
- **Cache Extended**: Added `set_entity_registry()`, `get_entity_registry()`, `set_device_registry()`, `get_device_registry()` methods
- **Testing**: Updated `test_connection.py` to test new endpoints
- **Error Handling**: Graceful fallback when endpoints are not available (404 errors)

### 🔄 **NEXT STEPS - Domain-to-Device Mapping Logic**
1. Create `orac/homeassistant/domain_mapper.py` with `DomainMapper` class
2. Implement domain-to-device-type mapping logic
3. Add smart detection for media players (TV vs Music)
4. Add smart detection for switches (lights vs generic)
5. Add action mapping for each device type

### 🔄 **PENDING - Location Detection Algorithm**
1. Create `orac/homeassistant/location_detector.py` with `LocationDetector` class
2. Implement multiple fallback strategies for location detection
3. Add location name normalization
4. Add validation and reporting capabilities

This focused approach ensures the core functionality works before adding additional features. 