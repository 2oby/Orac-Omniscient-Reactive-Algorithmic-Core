# Dispatcher & Grammar Optimization Plan

## Overview
Align the grammar system with the dispatcher to create an efficient, maintainable command processing pipeline where grammars define the valid vocabulary and dispatchers map these terms to actual entity IDs.

## Current Issues
1. **Hardcoded entity mappings** in dispatcher (not using entity_mappings.yaml)
2. **Grammar files in misleading location** (`test_grammars/` instead of `grammars/`)
3. **No connection** between grammar constraints and dispatcher mappings
4. **No entity discovery** from Home Assistant API

## Implementation Plan

### Phase 1: Restructure Grammar System
- [ ] Rename `data/test_grammars/` to `data/grammars/`
- [ ] Update all code references to new path
- [ ] Update import paths in topic configurations

### Phase 2: Grammar-Aware Dispatcher
Create a dispatcher that understands and uses grammar constraints:

#### 2.1 Grammar Parser
- [ ] Implement GBNF parser to extract allowed values from grammar files
- [ ] Extract device, location, and action vocabularies from grammar
- [ ] Cache parsed grammar structure per topic

#### 2.2 Entity Mapping System
- [ ] Load `entity_mappings.yaml` on dispatcher init
- [ ] Implement mapping: grammar term → HA entity ID
- [ ] Support both direct and pattern-based mappings

#### 2.3 Dynamic Entity Discovery
- [ ] Fetch entities from HA API on startup (`/api/states`)
- [ ] Build reverse mapping: friendly name → entity ID
- [ ] Implement periodic refresh (5-minute TTL)

### Phase 3: Validation Layer
- [ ] Validate LLM output against grammar-defined terms
- [ ] Provide meaningful errors for invalid terms
- [ ] Log unmapped terms for future configuration

## Architecture

```
Topic Grammar (GBNF)          Dispatcher
┌─────────────────┐           ┌──────────────────────┐
│ Defines:        │           │ 1. Parse grammar     │
│ - devices       │ ────────> │ 2. Load mappings     │
│ - locations     │           │ 3. Validate output   │
│ - actions       │           │ 4. Map to entity IDs │
└─────────────────┘           │ 5. Execute on HA     │
                              └──────────────────────┘
```

## Mapping Strategy: User-Controlled Configuration

### The Approach
Users explicitly map grammar combinations to HA entities through an auto-generated configuration file.

### Workflow

1. **Grammar Selection** → User selects a grammar file for their topic
2. **Mapping File Generation** → System creates a mapping file with:
   - All possible combinations from the grammar
   - List of available HA entities
   - TODO markers for unmapped items
3. **User Configuration** → User edits the file to map or ignore combinations
4. **Daily Sync** → System checks for new HA entities and adds them as comments
5. **GUI Notifications** → Alert users about unmapped combinations

### Generated Mapping File Example

```yaml
# dispatcher_mapping_home_automation.yaml
# Auto-generated from: static_actions.gbnf
# Generated: 2025-09-15
# Last HA Sync: 2025-09-15 10:00

metadata:
  grammar_file: "static_actions.gbnf"
  topic_id: "home_automation"
  unmapped_count: 2  # Shown in GUI

mappings:
  # Generated from grammar combinations
  "lounge|lights": "switch.tretakt_smart_plug"    # User mapped
  "bedroom|lights": "light.bedroom_lights"        # User mapped
  "kitchen|lights": ""                            # TODO: Map this
  "bathroom|lights": "IGNORE"                     # User marked ignore
  "hall|lights": ""                                # TODO: Map this

# NEW ENTITIES (Added 2025-09-16)
# Uncomment and map if needed:
# "garage|lights": ""  # light.garage_overhead detected

# AVAILABLE HOME ASSISTANT ENTITIES
# Fetched: 2025-09-15 10:00
available_entities:
  lights:
    - light.bedroom_lights
    - light.bathroom_lights
    - light.hall_lights
    - light.kitchen_lights
    - light.garage_overhead  # NEW
  switches:
    - switch.tretakt_smart_plug  # (Lounge Lamp)
    - switch.bathroom_fan_light
  climate:
    - climate.lounge_thermostat
    - climate.bedroom_thermostat
```

### Mapping Resolution

```python
class MappingResolver:
    def __init__(self, mapping_file: str):
        self.mappings = self.load_mapping_file(mapping_file)
        self.check_unmapped()

    def resolve(self, location: str, device: str) -> str:
        key = f"{location}|{device}"

        # Check user mapping
        if key not in self.mappings:
            raise UnmappedError(f"No mapping for {key}")

        mapping = self.mappings[key]

        # Handle special cases
        if mapping == "":
            raise UnmappedError(f"TODO: Map {key}")
        if mapping == "IGNORE":
            return None

        # Validate entity exists
        if not self.entity_exists(mapping):
            raise InvalidEntityError(f"Entity {mapping} not found")

        return mapping

    def check_unmapped(self):
        """Count unmapped entries for GUI notification"""
        unmapped = [k for k, v in self.mappings.items() if v == ""]
        if unmapped:
            self.notify_gui(f"{len(unmapped)} unmapped combinations")
```

### Benefits of User-Controlled Mapping
- **Explicit control** - No guessing or fuzzy matching
- **Clear workflow** - Users know exactly what needs configuration
- **Traceability** - All mappings are documented and version controlled
- **Helpful scaffolding** - Auto-generated with all needed information
- **Fail-safe** - System won't execute unmapped commands

## Benefits
1. **Single source of truth** - Grammar defines valid commands
2. **Efficient lookups** - In-memory mapping cache
3. **Dynamic updates** - Discover new HA entities automatically
4. **Better error handling** - Validate before API calls
5. **Maintainable** - Change mappings without code updates

## Command Debugging & Performance Monitoring

### GUI Enhancement: Command Detail View
Click on the last command tile to see detailed debugging information.

### Implementation Approach

#### 1. Time Synchronization
```bash
# Use NTP to sync all components
# Run on all devices (Pi, Orin, etc.)
sudo timedatectl set-ntp true
```

#### 2. Timing Data Structure
Each command carries timing metadata through the pipeline:

```json
{
  "command_id": "cmd_123456",
  "original_audio_start": "2025-09-15T10:30:00.123Z",
  "timestamps": {
    "wake_word_detected": "2025-09-15T10:30:00.123Z",
    "audio_capture_start": "2025-09-15T10:30:00.523Z",
    "audio_capture_end": "2025-09-15T10:30:03.234Z",
    "stt_request_sent": "2025-09-15T10:30:03.245Z",
    "stt_transcription_received": "2025-09-15T10:30:04.567Z",
    "orac_core_received": "2025-09-15T10:30:04.589Z",
    "llm_inference_start": "2025-09-15T10:30:04.601Z",
    "llm_inference_end": "2025-09-15T10:30:05.234Z",
    "dispatcher_start": "2025-09-15T10:30:05.245Z",
    "ha_api_call": "2025-09-15T10:30:05.267Z",
    "ha_response": "2025-09-15T10:30:05.423Z",
    "command_complete": "2025-09-15T10:30:05.445Z"
  },
  "data": {
    "original_text": "turn on the lounge lamp",
    "llm_output": "{\"device\":\"lights\",\"action\":\"on\",\"location\":\"lounge\"}",
    "entity_resolved": "switch.tretakt_smart_plug",
    "ha_response": {"status": "success"}
  }
}
```

#### 3. GUI Debug View Layout
```
┌─────────────────────────────────────────────┐
│ Command Details - ID: cmd_123456            │
├─────────────────────────────────────────────┤
│ Original Text: "turn on the lounge lamp"    │
│ LLM Output: {"device":"lights",...}         │
│ Entity: switch.tretakt_smart_plug           │
│ Status: ✓ Success                            │
├─────────────────────────────────────────────┤
│ Performance Breakdown:                       │
│                                              │
│ Wake Word Detection      [█] 400ms          │
│ Audio Capture           [███] 2,711ms       │
│ Speech-to-Text          [██] 1,322ms        │
│ ORAC Core Processing     [█] 645ms          │
│   ├─ LLM Inference       [█] 633ms          │
│   └─ Dispatcher           [·] 22ms          │
│ Home Assistant API       [·] 156ms          │
│                                              │
│ Total: 5.3 seconds                          │
├─────────────────────────────────────────────┤
│ Bottlenecks:                                 │
│ ⚠ Audio Capture: 2.7s (51% of total)       │
│ ⚠ STT: 1.3s (25% of total)                 │
└─────────────────────────────────────────────┘
```

#### 4. Implementation Details

**Component Updates:**
- **Hey ORAC**: Add timestamp when wake word detected
- **ORAC STT**: Include timing in transcription response
- **ORAC Core**: Track LLM and dispatcher timing
- **Dispatcher**: Log HA API call timing

**Data Flow:**
```python
# Each component adds its timing
class TimedCommand:
    def __init__(self, command_id: str):
        self.id = command_id
        self.timestamps = {}

    def mark(self, event: str):
        self.timestamps[event] = datetime.utcnow().isoformat()

    def duration(self, start: str, end: str) -> float:
        """Calculate duration between two events in ms"""
        t1 = self.timestamps[start]
        t2 = self.timestamps[end]
        return (t2 - t1).total_seconds() * 1000
```

**Storage:**
- Store last 100 commands with full timing data
- Aggregate metrics for performance trends
- Alert if component consistently slow

### Benefits
- **Identify bottlenecks** - See which component is slowest
- **Debug issues** - Full visibility into command flow
- **Performance monitoring** - Track degradation over time
- **User transparency** - Show exactly what's happening

## Success Metrics
- Entity resolution time < 1ms (in-memory lookup)
- Zero failed HA API calls due to invalid entities
- Support for new devices without code changes
- Grammar changes automatically reflected in dispatcher behavior
- Full command execution < 3 seconds (wake word to action)
- Complete timing visibility for every command