# Home Assistant Caching Strategy

## Overview

This document outlines the intelligent caching strategy for Home Assistant objects in ORAC, designed to optimize performance while only caching objects that are likely to be used in user commands.

## Caching Categories

### ✅ **High Priority - Always Cached**

#### 1. **User-Controllable Entities**
Entities that users directly control via voice commands:
- `light.*` - Lights, lamps, bulbs
- `switch.*` - Power switches, outlets, appliances
- `climate.*` - Thermostats, heating, cooling systems
- `cover.*` - Blinds, garage doors, curtains
- `media_player.*` - TVs, speakers, audio systems
- `fan.*` - Ceiling fans, exhaust fans
- `lock.*` - Door locks, smart locks
- `vacuum.*` - Robot vacuums
- `scene.*` - Pre-configured lighting/device states

**Example Commands:**
- "Turn on the bedroom lights"
- "Set thermostat to 72 degrees"
- "Open the garage door"
- "Play music in the living room"

#### 2. **Input Helpers (User-Configurable Controls)**
Virtual controls created by users for complex automations:
- `input_boolean.*` - Virtual on/off switches (e.g., "Guest Mode", "Vacation Mode")
- `input_select.*` - Virtual dropdown menus (e.g., "House Mode": Normal/Party/Sleep)
- `input_number.*` - Virtual sliders (e.g., "Target Temperature", "Brightness Level")
- `input_text.*` - Virtual text inputs (e.g., "Custom Message")
- `input_datetime.*` - Virtual date/time inputs

**Example Commands:**
- "Turn on Guest Mode"
- "Set House Mode to Party"
- "Set brightness to 80%"
- "Set custom message to 'Welcome home'"

#### 3. **Automations (Pre-configured Rules)**
Automation entities that can be manually triggered:
- `automation.*` - Pre-configured automation rules

**Example Commands:**
- "Run morning routine"
- "Trigger movie mode"
- "Start evening automation"

#### 4. **Areas/Locations (For Room-Based Commands)**
Geographic locations for room-based control:
- All areas from `/api/areas` endpoint

**Example Commands:**
- "Turn on all lights in the bedroom"
- "What's the temperature in the kitchen?"
- "Close all blinds in the living room"

#### 5. **Essential Services (For Command Execution)**
Service calls needed to execute user commands:
- `light.turn_on`, `light.turn_off`, `light.toggle`
- `switch.turn_on`, `switch.turn_off`, `switch.toggle`
- `climate.set_temperature`, `climate.set_hvac_mode`
- `cover.open_cover`, `cover.close_cover`
- `media_player.play`, `media_player.pause`
- `scene.turn_on`
- `automation.trigger`
- `input_*.set_*` services
- `homeassistant.turn_on`, `homeassistant.turn_off`, `homeassistant.toggle` (generic)

### ✅ **Medium Priority - Cached with Values**

#### 6. **Status Entities (For Queries)**
Sensors and binary sensors for status queries:
- `sensor.*` - Temperature, humidity, energy usage, etc.
- `binary_sensor.*` - Motion, door/window, presence, etc.

**Note:** These are cached with their current values and may be refreshed more frequently than controllable entities.

**Example Commands:**
- "What's the temperature in the bedroom?"
- "Is anyone in the living room?"
- "What's the energy usage today?"

### ❌ **Excluded from Caching**

#### 7. **System Entities (Rarely Used in User Commands)**
System-level entities that are rarely controlled by users:
- `sun.*` - Sun position and timing
- `zone.*` - Geographic zones
- `conversation.*` - Conversation management
- `weather.*` - Weather data (unless weather-based commands are desired)
- `tts.*` - Text-to-speech services
- `todo.*` - Todo lists
- `person.*` - Person tracking (unless presence-based commands are desired)

#### 8. **Scripts**
Reusable action sequences (not manually triggerable like automations):
- `script.*` - Script entities

#### 9. **Triggers**
External events that trigger automations (not manually triggerable):
- Time-based triggers
- State change triggers
- Event triggers

## Caching Implementation

### **Persistent Storage**
- **Location**: `cache/homeassistant/` directory (configurable)
- **Format**: JSON files with TTL and metadata
- **Structure**: One file per cache key (entities.json, services.json, areas.json)

### **Cache Behavior**
- **TTL**: 5 minutes (configurable)
- **Memory Cache**: Fast access for active session
- **Disk Cache**: Persistence across application restarts
- **Automatic Cleanup**: Expired entries removed from both memory and disk
- **Corruption Handling**: Corrupted cache files automatically removed

### **Filtering Logic**
```python
def _is_relevant_entity(entity_id: str) -> bool:
    domain = entity_id.split('.')[0]
    
    # Don't cache system entities
    if domain in SYSTEM_ENTITIES:
        return False
    
    # Cache user-controllable entities, input helpers, automation entities, and status entities
    return (domain in USER_CONTROLLABLE_ENTITIES or 
            domain in INPUT_HELPERS or 
            domain in AUTOMATION_ENTITIES or 
            domain in STATUS_ENTITIES)
```

## Entity Mapping UI Integration

### **NULL Value Handling**

When auto-discovery finds entities without friendly names, the system generates "NULL" values that require user input to complete the mapping. This requires a UI popup system to prompt users for friendly names.

#### **UI Popup Requirements**

**Trigger Conditions:**
- Auto-discovery completes and finds entities with "NULL" friendly names
- User accesses the ORAC application for the first time with new entities
- Manual refresh of entity mappings reveals new unmapped entities

**Popup Behavior:**
- **Modal Dialog**: Non-dismissible until all NULL values are resolved
- **Progressive Disclosure**: Show one entity at a time to avoid overwhelming the user
- **Smart Suggestions**: Provide intelligent suggestions based on entity_id parsing
- **Validation**: Ensure friendly names are unique and appropriate

**UI Components Needed:**
```html
<!-- Entity Mapping Popup -->
<div id="entityMappingPopup" class="modal-popup">
    <div class="popup-content">
        <h3>Complete Entity Mapping</h3>
        <p>Found new Home Assistant entities that need friendly names:</p>
        
        <div class="entity-mapping-form">
            <div class="entity-info">
                <strong>Entity ID:</strong> <span id="currentEntityId"></span>
                <br>
                <strong>Device Type:</strong> <span id="currentDeviceType"></span>
            </div>
            
            <div class="friendly-name-input">
                <label for="friendlyNameInput">Friendly Name:</label>
                <input type="text" id="friendlyNameInput" placeholder="Enter a friendly name...">
                <div class="suggestions" id="nameSuggestions"></div>
            </div>
            
            <div class="popup-actions">
                <button id="skipEntity">Skip</button>
                <button id="saveEntityMapping">Save & Continue</button>
            </div>
        </div>
        
        <div class="progress-indicator">
            <span id="mappingProgress">1 of 3 entities mapped</span>
        </div>
    </div>
</div>
```

**JavaScript Integration:**
```javascript
// Check for NULL mappings on app startup
async function checkForNullMappings() {
    const response = await fetch('/api/mapping/check-null');
    const data = await response.json();
    
    if (data.entities_needing_names.length > 0) {
        showEntityMappingPopup(data.entities_needing_names);
    }
}

// Show popup for entity mapping
function showEntityMappingPopup(entities) {
    let currentIndex = 0;
    
    function showCurrentEntity() {
        const entity = entities[currentIndex];
        document.getElementById('currentEntityId').textContent = entity.entity_id;
        document.getElementById('currentDeviceType').textContent = entity.device_type;
        document.getElementById('mappingProgress').textContent = 
            `${currentIndex + 1} of ${entities.length} entities mapped`;
        
        // Generate suggestions
        const suggestions = generateNameSuggestions(entity.entity_id);
        displaySuggestions(suggestions);
    }
    
    // Handle save action
    document.getElementById('saveEntityMapping').onclick = async () => {
        const friendlyName = document.getElementById('friendlyNameInput').value;
        if (friendlyName.trim()) {
            await saveEntityMapping(entities[currentIndex].entity_id, friendlyName);
            currentIndex++;
            
            if (currentIndex < entities.length) {
                showCurrentEntity();
            } else {
                hideEntityMappingPopup();
                location.reload(); // Refresh to use new mappings
            }
        }
    };
    
    showCurrentEntity();
    document.getElementById('entityMappingPopup').style.display = 'block';
}
```

#### **API Endpoints Required**

**Check for NULL Mappings:**
```
GET /api/mapping/check-null
Response: {
    "entities_needing_names": [
        {
            "entity_id": "light.living_room_lamp",
            "device_type": "light",
            "suggested_name": "living room lamp"
        }
    ]
}
```

**Save Entity Mapping:**
```
POST /api/mapping/save
Body: {
    "entity_id": "light.living_room_lamp",
    "friendly_name": "living room lamp"
}
Response: {
    "success": true,
    "message": "Mapping saved successfully"
}
```

#### **Integration with Auto-Discovery**

The UI popup system integrates seamlessly with the auto-discovery process:

1. **Auto-Discovery Phase**: System discovers entities and generates initial mappings
2. **NULL Detection**: System identifies entities with "NULL" friendly names
3. **UI Trigger**: Application startup or manual refresh triggers popup
4. **User Input**: Users provide friendly names through progressive dialog
5. **Mapping Update**: New mappings are saved to `entity_mappings.yaml`
6. **Grammar Update**: LLM grammar constraints are updated with new friendly names

#### **User Experience Flow**

```
1. User starts ORAC application
2. System runs auto-discovery in background
3. If NULL mappings found → Show popup
4. User provides friendly names one by one
5. System saves mappings and updates grammar
6. User can now use natural language commands
```

#### **Fallback Handling**

- **Skip Option**: Users can skip entities they don't want to control
- **Batch Import**: Option to import mappings from existing Home Assistant configuration
- **Manual Edit**: Direct access to `entity_mappings.yaml` for advanced users
- **Validation**: Ensures friendly names are unique and appropriate

## Benefits

### **Performance**
- **Reduced API Calls**: Subsequent requests use cache instead of API
- **Faster Response**: Memory cache provides sub-millisecond access
- **Lower Network Load**: Fewer requests to Home Assistant

### **Intelligence**
- **Smart Filtering**: Only caches objects likely to be used in commands
- **Automatic Categorization**: Entities grouped by type and purpose
- **System Exclusion**: Avoids caching rarely-used system entities

### **Reliability**
- **Persistence**: Cache survives application restarts
- **Graceful Degradation**: Handles missing endpoints gracefully
- **Error Recovery**: Automatically removes corrupted cache files

### **Scalability**
- **Memory Efficient**: Only relevant objects stored in memory
- **Disk Efficient**: Persistent storage with automatic cleanup
- **Configurable**: TTL and cache size can be adjusted

## Example Cache Output

Based on your current Home Assistant setup:

```
=== Cached Data Summary ===

Relevant Entities (0):
  No relevant entities found (this is normal if no lights, switches, etc. are configured)

Relevant Service Domains (15):
  - light: 3 services
  - switch: 3 services
  - climate: 5 services
  - cover: 4 services
  - media_player: 8 services
  - fan: 3 services
  - lock: 3 services
  - vacuum: 4 services
  - scene: 3 services
  - automation: 4 services
  - input_boolean: 3 services
  - input_select: 3 services
  - input_number: 3 services
  - homeassistant: 3 services

Areas (0):
  No areas found (areas might not be configured)
```

## Configuration

### **Cache Settings in `config.yaml`**
```yaml
# Cache Settings
cache_ttl: 300  # 5 minutes
cache_max_size: 1000
```

## Cache Categories Summary

| Category | Cached | Examples | Refresh Rate |
|----------|--------|----------|--------------|
| User Controllable | ✅ | lights, switches, climate | 5 minutes |
| Input Helpers | ✅ | input_boolean, input_select | 5 minutes |
| Automations | ✅ | automation.* | 5 minutes |
| Areas | ✅ | All areas | 5 minutes |
| Status Entities | ✅ | sensors, binary_sensors | 2 minutes |
| System Entities | ❌ | sun, weather, person | Never |
| Scripts | ❌ | script.* | Never |
| Triggers | ❌ | External events | Never |

## Example User Commands Using Cached Data

### Direct Control
- "Turn on the bedroom lights" → Uses cached `light.bedroom` entity
- "Set thermostat to 22°C" → Uses cached `climate.thermostat` entity
- "Open garage door" → Uses cached `cover.garage_door` entity

### Input Helpers
- "Enable guest mode" → Uses cached `input_boolean.guest_mode`
- "Set house mode to party" → Uses cached `input_select.house_mode`

### Automations
- "Run morning routine" → Uses cached `automation.morning_routine`

### Area-Based
- "Turn on all lights in the living room" → Uses cached area data
- "What's the temperature in the kitchen?" → Uses cached sensor data

### Status Queries
- "Is the front door open?" → Uses cached `binary_sensor.front_door`
- "Show me the energy usage" → Uses cached `sensor.energy_usage`

## Current Home Assistant Setup Analysis

### **Current Entity Inventory (June 2025)**

Based on the latest API fetch from Home Assistant at `192.168.8.99:8123`, our caching strategy is working as designed:

**Total Entities Found:** 21 entities across all domains

**Cached Controllable Entities (7):**
- `light.bedroom_lights` (Bedroom Lights) - Philips Hue light group
- `light.bathroom_lights` (Bathroom Lights) - Philips Hue light group  
- `light.hall_lights` (Hall Lights) - Philips Hue light group
- `light.kitchen_lights` (Kitchen Lights) - Philips Hue light group
- `light.lounge_lights` (Lounge Lights) - Philips Hue light group
- `input_button.bathroom_scene_good_night` (Good Night) - Scene trigger
- `input_button.bedroom_scene_good_night` (Good Night) - Scene trigger

**Cached Status Entities (7):**
- `sensor.z_wave_usb_stick_status` (Z-Wave USB Stick Status) - System status
- `sensor.sun_next_dawn` through `sensor.sun_next_setting` - Sun timing data

**Excluded System Entities (7):**
- `person.niederdorf`, `conversation.home_assistant`, `zone.home`, `sun.sun`, `todo.shopping_list`, `tts.google_translate_en_com`, `weather.home`

### **Caching Strategy Validation**

Our intelligent filtering approach is performing optimally:

1. **✅ Smart Entity Selection**: Only 7 out of 21 entities are cached as controllable, focusing on the Philips Hue light groups and scene buttons that users will actually control via voice commands.

2. **✅ System Entity Exclusion**: 7 system entities (sun, weather, person, etc.) are correctly excluded from caching as they're rarely used in direct user commands.

3. **✅ Room-Based Organization**: The cached entities are organized by room (bedroom, bathroom, hall, kitchen, lounge), enabling natural language commands like "turn on the bedroom lights" or "activate the good night scene in the bathroom."

4. **✅ Service Discovery**: The system has discovered 15+ service domains with 50+ individual services available for command execution, ensuring comprehensive control capabilities.

### **Current Command Capabilities**

With the current cached entities, users can execute commands such as:
- "Turn on the bedroom lights" → `light.turn_on` service on `light.bedroom_lights`
- "Activate the good night scene in the bathroom" → `input_button.press` service on `input_button.bathroom_scene_good_night`
- "Turn off all lights in the lounge" → `light.turn_off` service on `light.lounge_lights`
- "Toggle the kitchen lights" → `light.toggle` service on `light.kitchen_lights`

### **Future Expansion Readiness**

The caching system is designed to automatically discover and cache new entities as they're added to Home Assistant. When additional devices are integrated (Z-Wave blinds, thermostats, Sonos speakers, individual Philips Hue bulbs), they will be automatically categorized and cached according to their domain type, maintaining the same intelligent filtering approach without requiring configuration changes. 