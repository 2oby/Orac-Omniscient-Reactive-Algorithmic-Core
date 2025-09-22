# Sprint 3: Grammar Generation & Dispatcher Integration

## Overview
Sprint 3 bridges the gap between configured entities (Sprint 2) and actual voice command processing. This sprint implements grammar generation from backend entities, dispatcher configuration, and topic-backend association to enable end-to-end voice command execution.

## Current State
- ✅ Backend management system complete (Sprint 2)
- ✅ Entity configuration with friendly names and aliases
- ✅ Existing grammar generation infrastructure (`HomeAssistantGrammarManager`)
- ✅ Dispatcher registry system in place
- ✅ Topic management system operational

## Sprint Goals

### Primary Objectives
1. **Grammar Generation**: Generate GBNF grammars from Device Type + Location mappings
2. **Dispatcher Configuration**: Enable backend-specific dispatcher configuration
3. **Topic-Backend Association**: Link topics to specific backends for command routing
4. **Command Testing Interface**: Test voice commands against generated grammars
5. **Unambiguous Mapping**: Ensure each Device Type + Location combination is unique

### User Stories
1. **As a user**, I want my Device Type and Location mappings to generate unambiguous grammars
2. **As a user**, I want to associate backends with topics for proper command routing
3. **As a user**, I want to test voice commands before using them in production
4. **As a user**, I want each location to have only one device of each type for clarity
5. **As a user**, I want to see which grammars are active for each topic

## Implementation Design

### 1. Grammar Generation from Device Type + Location Mappings

#### Architecture
```
Device Mappings (Type + Location) → Grammar Generator → GBNF File → Topic Assignment
```

#### Grammar Generator Component
**Location**: `/orac/backend_grammar_generator.py`

```python
class BackendGrammarGenerator:
    def __init__(self, backend_manager):
        self.backend_manager = backend_manager

    def generate_grammar_for_backend(self, backend_id: str) -> str:
        """Generate GBNF grammar from device mappings"""
        # Get enabled devices with their Type + Location mappings
        # Validate uniqueness of Type + Location combinations
        # Generate action rules based on Device Types
        # Generate location rules from assigned Locations
        # Return GBNF string

    def generate_location_rules(self, mappings: Dict) -> str:
        """Generate location-based rules from device locations"""
        # Extract unique locations from mappings
        # Create location alternatives for grammar

    def generate_device_type_rules(self, mappings: Dict) -> str:
        """Generate device type specific action rules"""
        # Create actions based on device types (lights, heating, etc.)

    def validate_uniqueness(self, mappings: Dict) -> List[str]:
        """Ensure no duplicate Type + Location combinations"""
        # Return list of conflicts if any
```

#### GBNF Output Format
```gbnf
root ::= command
command ::= action " the " device_type " in the " location | action " " location " " device_type

# Actions based on Device Types
action ::= light_action | heating_action | media_action | blind_action
light_action ::= "turn on" | "turn off" | "dim" | "brighten" | "set to"
heating_action ::= "set temperature to" | "turn on" | "turn off" | "increase" | "decrease"
media_action ::= "play" | "pause" | "stop" | "volume up" | "volume down"
blind_action ::= "open" | "close" | "raise" | "lower" | "set to"

# Device Types from user mappings (guaranteed unique per location)
device_type ::= "lights" | "heating" | "media player" | "blinds" | ...

# Locations from user assignments (HA areas + custom)
location ::= "lounge" | "bedroom" | "kitchen" | ...
```

### 2. Enhanced Backend Configuration UI

#### Backend Details Page
**Location**: `/orac/templates/backend_details.html`

```
╔════════════════════════════════════════════════════════════════════════════╗
║ BACKEND: Home Assistant Main                                                ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║ CONNECTION STATUS: ● Connected                                              ║
║ Entities: 156 total | 45 enabled | 32 configured                           ║
║                                                                              ║
║ ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐   ║
║ │  MANAGE ENTITIES    │ │  GENERATE GRAMMAR   │ │  TEST COMMANDS      │   ║
║ └─────────────────────┘ └─────────────────────┘ └─────────────────────┘   ║
║                                                                              ║
║ DISPATCHER CONFIGURATION                                                    ║
║ ─────────────────────────                                                  ║
║ Type: [Home Assistant ▼]                                                   ║
║ Priority: [5] (1-10)                                                       ║
║ Timeout: [5000] ms                                                         ║
║ [ ] Enable debug logging                                                   ║
║                                                                              ║
║ GRAMMAR STATUS                                                             ║
║ ─────────────                                                             ║
║ Generated: 2024-09-21 14:30:00                                            ║
║ File: /data/grammars/backend_ha_main.gbnf                                 ║
║ Size: 12.5 KB                                                              ║
║ Entities Included: 45                                                      ║
║                                                                              ║
║ ASSOCIATED TOPICS                                                          ║
║ ─────────────────                                                          ║
║ ✓ general (default)                                                        ║
║ ✓ smart_home                                                              ║
║ ○ kitchen_assistant                                                        ║
║ ○ bedroom_control                                                          ║
║                                                                              ║
║ [SAVE CONFIGURATION]                                                        ║
║                                                                              ║
╚════════════════════════════════════════════════════════════════════════════╝
```

### 3. Topic-Backend Association

#### Topic Configuration Enhancement
**Modify**: `/orac/topic_models/topic.py`

```python
class Topic:
    # Add new fields
    backend_id: Optional[str] = None
    grammar_file: Optional[str] = None
    dispatcher_config: Optional[Dict] = None
```

#### Association UI
**Location**: Add to `/orac/templates/topic_config.html`

```
BACKEND ASSOCIATION
───────────────────
Backend: [Select Backend ▼]
         - Home Assistant Main
         - Home Assistant Remote
         - None (Manual Grammar)

Grammar Source:
○ Auto-generate from backend
● Custom grammar file: [________________]

Dispatcher Override:
○ Use backend default
● Custom: [_______________]
```

### 4. Grammar Testing Interface

#### Test Console
**Location**: `/orac/templates/grammar_test.html`

```
╔════════════════════════════════════════════════════════════════════════════╗
║ GRAMMAR TEST CONSOLE                                                        ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║ Backend: [Home Assistant Main ▼]                                           ║
║ Topic: [smart_home ▼]                                                      ║
║                                                                              ║
║ Test Command:                                                              ║
║ ┌──────────────────────────────────────────────────────────────────────┐  ║
║ │ turn on the living room light                                        │  ║
║ └──────────────────────────────────────────────────────────────────────┘  ║
║                                                                              ║
║ [PARSE] [VALIDATE] [EXECUTE (DRY RUN)]                                     ║
║                                                                              ║
║ RESULTS                                                                     ║
║ ────────                                                                    ║
║ ✓ Grammar Match: SUCCESS                                                   ║
║ Parsed Output:                                                             ║
║ {                                                                          ║
║   "action": "turn_on",                                                    ║
║   "device": "light.living_room_main",                                     ║
║   "location": "living_room"                                               ║
║ }                                                                          ║
║                                                                              ║
║ Dispatcher: homeassistant                                                  ║
║ Target Entity: light.living_room_main                                      ║
║ Service Call: light.turn_on                                               ║
║                                                                              ║
║ [COPY JSON] [VIEW GRAMMAR] [TRY ANOTHER]                                  ║
║                                                                              ║
╚════════════════════════════════════════════════════════════════════════════╝
```

### 5. Device Mapping Interface

#### Drag-and-Drop Configuration
**Enhancement to**: `/orac/templates/backend_entities.html`

```
╔════════════════════════════════════════════════════════════════════╗
║ DEVICE CONFIGURATION                                               ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                     ║
║ DEVICE TYPES            LOCATIONS                                  ║
║ ┌──────────┐           ┌──────────┐                              ║
║ │ Lights   │           │ Lounge   │                              ║
║ │ Heating  │           │ Bedroom  │                              ║
║ │ Media    │           │ Kitchen  │                              ║
║ │ Blinds   │           │ + Add    │                              ║
║ └──────────┘           └──────────┘                              ║
║                                                                     ║
║ DEVICES                                                            ║
║ ┌─────────────────────────────────────────────────────────────┐  ║
║ │ ☑ switch.lounge_lamp  [Type: Lights ] [Loc: Lounge  ]      │  ║
║ │ ☑ light.lounge_lights [Type: _______ ] [Loc: _______ ]      │  ║
║ │ ☐ cover.bedroom_blind [Type: _______ ] [Loc: _______ ]      │  ║
║ │                                                              │  ║
║ │ ⚠ Conflict: "Lights + Lounge" already assigned              │  ║
║ └─────────────────────────────────────────────────────────────┘  ║
║                                                                     ║
║ [VALIDATE MAPPINGS] [GENERATE GRAMMAR]                            ║
╚════════════════════════════════════════════════════════════════════╝
```

## API Endpoints

### New Endpoints
```python
# Grammar Generation
POST /api/backends/{id}/grammar/generate     # Generate grammar from entities
GET  /api/backends/{id}/grammar              # Get current grammar
PUT  /api/backends/{id}/grammar              # Update grammar manually

# Dispatcher Configuration
GET  /api/backends/{id}/dispatcher           # Get dispatcher config
PUT  /api/backends/{id}/dispatcher           # Update dispatcher config

# Topic Association
PUT  /api/topics/{id}/backend                # Associate backend with topic
DELETE /api/topics/{id}/backend              # Remove backend association

# Testing
POST /api/grammar/test                       # Test command against grammar
POST /api/grammar/validate                   # Validate grammar syntax
```

## Data Model Updates

### Backend Configuration Extension
```json
{
  "id": "ha_main",
  "name": "Home Assistant Main",
  // ... existing fields ...
  "device_mappings": {
    "switch.lounge_lamp": {
      "enabled": true,
      "device_type": "lights",
      "location": "lounge"
    },
    "climate.bedroom_thermostat": {
      "enabled": true,
      "device_type": "heating",
      "location": "bedroom"
    }
  },
  "device_types": ["lights", "heating", "media_player", "blinds"],
  "locations": ["lounge", "bedroom", "kitchen"],
  "dispatcher": {
    "type": "homeassistant",
    "priority": 5,
    "timeout": 5000,
    "debug": false
  },
  "grammar": {
    "file": "/data/grammars/backend_ha_main.gbnf",
    "generated_at": "2024-09-21T14:30:00Z",
    "mappings_count": 45,
    "auto_generate": true,
    "validate_uniqueness": true
  },
  "associations": {
    "topics": ["general", "smart_home"]
  }
}
```

### Topic Model Extension
```json
{
  "id": "smart_home",
  "name": "Smart Home Control",
  // ... existing fields ...
  "backend_id": "ha_main",
  "grammar_source": "backend",  // "backend" | "custom" | "default"
  "grammar_file": "/data/grammars/backend_ha_main.gbnf",
  "dispatcher_override": null   // Use backend default
}
```

## Implementation Tasks

### Task 1: Device Mapping Interface
1. Create drag-and-drop UI for Device Type assignment
2. Create drag-and-drop UI for Location assignment
3. Implement uniqueness validation (Type + Location)
4. Add custom Device Type and Location creation
5. Show conflict warnings in real-time

### Task 2: Grammar Generator Implementation
1. Create `BackendGrammarGenerator` class
2. Generate GBNF from Device Type + Location mappings
3. Validate uniqueness before generation
4. Create action rules based on Device Types
5. Generate location-specific commands

### Task 3: Backend Details Page
1. Create backend details template
2. Add dispatcher configuration form
3. Display grammar generation status
4. Show device mapping statistics
5. Add mapping validation status

### Task 4: Topic-Backend Integration
1. Extend Topic model with backend fields
2. Update topic configuration UI
3. Implement association endpoints
4. Modify topic manager for backend support

### Task 5: Grammar Testing Console
1. Create test console template
2. Test commands against Type + Location grammar
3. Show which device will be controlled
4. Display parsed Device Type and Location
5. Validate against uniqueness constraints

### Task 6: Integration & Polish
1. Connect all components
2. Add real-time grammar regeneration
3. Implement caching for performance
4. Add progress indicators
5. Error handling and validation

## Testing Requirements

### Unit Tests
- Grammar generation for different entity types
- GBNF syntax validation
- Topic-backend association logic
- Dispatcher configuration validation

### Integration Tests
- End-to-end grammar generation flow
- Command parsing and routing
- Backend-topic-dispatcher chain
- Grammar caching and updates

### Manual Testing Checklist
- [ ] Drag Device Type to device and assignment works
- [ ] Drag Location to device and assignment works
- [ ] Uniqueness validation prevents duplicate Type + Location
- [ ] Custom Device Types and Locations can be added
- [ ] Grammar generates from Device Type + Location mappings
- [ ] Commands like "turn on lights in lounge" work correctly
- [ ] Topic uses correct backend grammar
- [ ] Dispatcher routes to correct backend
- [ ] Test console validates Type + Location commands
- [ ] Grammar regenerates on mapping changes
- [ ] Conflict warnings appear for duplicate mappings

## Success Criteria

### Sprint Completion
- ✅ Grammar auto-generates from enabled entities
- ✅ Topics can be associated with backends
- ✅ Commands route through correct dispatcher
- ✅ Test console validates grammar
- ✅ Entity grouping improves organization
- ✅ All API endpoints functional
- ✅ UI maintains cyberpunk aesthetic
- ✅ Performance targets met

### Metrics
- Grammar generation < 2 seconds for 200 entities
- Command parsing < 100ms
- Grammar file size < 100KB for typical setup
- Test console response < 500ms

## Dependencies

### From Previous Sprints
- Backend management system (Sprint 2)
- Entity configuration (Sprint 2)
- Navigation infrastructure (Sprint 1)

### External Dependencies
- GBNF grammar format specification
- LLama.cpp grammar support
- Existing dispatcher system

## Risk Mitigation

### Identified Risks
1. **Grammar Complexity**: Keep initial grammar simple, iterate
2. **Performance**: Implement caching and incremental updates
3. **Large Entity Sets**: Paginate and filter aggressively
4. **Grammar Conflicts**: Validate uniqueness of names/aliases
5. **Backward Compatibility**: Maintain manual grammar option

## Sprint Timeline

### Week 1
- Days 1-2: Grammar generator implementation
- Days 3-4: Backend details page and UI
- Days 5: Topic-backend association

### Week 2
- Days 6-7: Grammar testing console
- Days 8-9: Entity grouping features
- Days 10: Integration and testing

### Week 3
- Days 11-12: Performance optimization
- Days 13: Bug fixes and polish
- Day 14: Documentation and deployment

## Next Sprint Preview (Sprint 4)

Sprint 4 will focus on advanced features:
- Multi-backend command routing
- Conditional grammar rules
- Context-aware commands
- Voice feedback configuration
- Command history and analytics
- Batch command support
- Integration with automation systems

## Notes for Implementation

### Grammar Generation Strategy
1. Parse Device Type + Location mappings
2. Generate action rules per Device Type (lights → on/off/dim, heating → temperature, etc.)
3. Create location-specific grammar branches
4. Ensure each Type + Location combo maps to exactly one device
5. Support natural language variations ("turn on the lights in the lounge", "lounge lights on")

### Performance Considerations
- Cache generated grammars
- Incremental updates on entity changes
- Lazy load grammar files
- Background grammar generation
- Compress large grammar files

### User Experience
- Show grammar generation progress
- Provide grammar preview/editor
- Clear error messages for conflicts
- Suggest entity naming improvements
- Visual grammar complexity indicator

## Definition of Done

1. All planned features implemented
2. Unit tests pass with >80% coverage
3. Integration tests pass
4. Manual testing checklist complete
5. Performance targets met
6. Documentation updated
7. Code reviewed and approved
8. Deployed to production
9. User can generate grammar and test commands
10. End-to-end voice command flow works