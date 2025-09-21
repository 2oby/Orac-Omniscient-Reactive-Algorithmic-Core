# Dispatcher & Grammar Optimization Implementation Prompt

## Context
You are implementing an optimization to the ORAC system's dispatcher and grammar architecture. The goal is to create a user-controlled mapping system that connects grammar-defined terms to Home Assistant entity IDs, with performance monitoring and debugging capabilities.

## Key Files to Review

### Current Implementation Files
- `/orac/dispatchers/homeassistant.py` - Current HA dispatcher with hardcoded mappings
- `/orac/dispatchers/base.py` - Base dispatcher interface
- `/orac/dispatchers/registry.py` - Dispatcher registration system
- `/orac/homeassistant/entity_mappings.yaml` - Existing entity mappings (currently unused)
- `/data/test_grammars/*.gbnf` - Grammar files (to be moved to `/data/grammars/`)
- `/data/grammars.yaml` - Grammar configuration

### Documentation
- `DISPATCHER_GRAMMAR_OPTIMIZATION.md` - The optimization plan (this document's parent)
- `ORAC_SYSTEM_OVERVIEW.md` - System architecture overview
- `CURRENT_FOCUS.md` - Current issues and status

## Implementation Tasks

### Phase 1: Restructure Grammar System
1. **Rename grammar folder**
   - Move `/data/test_grammars/` to `/data/grammars/`
   - Update all import paths and references
   - Search for "test_grammars" in codebase and update

### Phase 2: Grammar-Aware Mapping System

2. **Create GBNF Parser** (`/orac/grammars/parser.py`)
   ```python
   class GBNFParser:
       def parse_grammar(grammar_file: str) -> Dict:
           """Extract devices, locations, actions from GBNF"""
       def get_combinations(grammar: Dict) -> List[str]:
           """Generate all valid location|device combinations"""
   ```

3. **Create Mapping Generator** (`/orac/dispatchers/mapping_generator.py`)
   ```python
   class MappingGenerator:
       def generate_mapping_file(grammar_file: str, topic_id: str):
           """Generate YAML mapping file with all combinations"""
       def fetch_ha_entities() -> Dict:
           """Get all entities from HA API"""
       def update_with_new_entities(mapping_file: str):
           """Add new HA entities as comments"""
   ```

4. **Update HomeAssistantDispatcher** (`/orac/dispatchers/homeassistant.py`)
   - Remove hardcoded mappings
   - Load mapping file based on topic configuration
   - Implement resolve_entity() method
   - Add timing instrumentation
   - Handle IGNORE and unmapped entities

5. **Create Mapping Resolver** (`/orac/dispatchers/mapping_resolver.py`)
   ```python
   class MappingResolver:
       def load_mapping_file(topic_id: str) -> Dict
       def resolve(location: str, device: str) -> str
       def validate_entity_exists(entity_id: str) -> bool
       def get_unmapped_count() -> int
   ```

### Phase 3: Performance Monitoring

6. **Add Timing Infrastructure** (`/orac/core/timing.py`)
   ```python
   class TimedCommand:
       def __init__(command_id: str)
       def mark(event: str)
       def get_duration(start: str, end: str) -> float
       def to_json() -> Dict
   ```

7. **Update Component Communication**
   - Modify Hey ORAC to include timestamps in requests
   - Update ORAC STT to pass through timing data
   - Enhance ORAC Core to track LLM and dispatcher timing
   - Store timing data with command history

### Phase 4: GUI Integration

8. **Add GUI Components**
   - Command detail view with timing breakdown
   - Mapping editor interface
   - Unmapped entity notifications
   - Performance metrics dashboard

## File Structure After Implementation

```
/orac/
├── dispatchers/
│   ├── base.py                    # Existing
│   ├── homeassistant.py          # Modified
│   ├── mapping_generator.py      # New
│   ├── mapping_resolver.py       # New
│   └── mappings/                 # New directory
│       └── topic_{id}.yaml       # Generated per topic
├── grammars/
│   └── parser.py                  # New
├── core/
│   └── timing.py                  # New
└── homeassistant/
    └── entity_mappings.yaml      # Existing (deprecated)

/data/
├── grammars/                      # Renamed from test_grammars
│   ├── static_actions.gbnf
│   ├── default.gbnf
│   └── ...
└── grammars.yaml                  # Existing

```

## Testing Requirements

1. **Unit Tests**
   - GBNF parser correctly extracts terms
   - Mapping generator creates valid YAML
   - Resolver handles all mapping cases (mapped, unmapped, IGNORE)
   - Timing calculations are accurate

2. **Integration Tests**
   - End-to-end command flow with timing
   - Grammar change triggers mapping update
   - New HA entities appear in daily sync
   - GUI correctly displays unmapped count

3. **Performance Tests**
   - Entity resolution < 1ms
   - Mapping file generation < 100ms
   - Command execution < 3s total

## Configuration Changes

### Topic Configuration Update
```yaml
topic:
  id: "home_automation"
  grammar_file: "static_actions.gbnf"
  dispatcher: "HomeAssistantDispatcher"
  mapping_file: "mappings/topic_home_automation.yaml"  # New field
```

### Environment Variables
```bash
# Time sync check
ORAC_REQUIRE_TIME_SYNC=true

# Mapping update frequency
ORAC_HA_SYNC_INTERVAL=86400  # Daily

# Performance thresholds
ORAC_MAX_COMMAND_TIME=3000  # ms
```

## Success Criteria

1. ✅ Grammar files moved to `/data/grammars/`
2. ✅ Mapping files auto-generated from grammar
3. ✅ User can edit mappings via file or GUI
4. ✅ Dispatcher uses mapping file, not hardcoded values
5. ✅ Timing data flows through entire pipeline
6. ✅ GUI shows command details with performance breakdown
7. ✅ New HA entities appear in daily sync
8. ✅ Unmapped entities trigger GUI notification
9. ✅ Entity resolution time < 1ms
10. ✅ Total command execution < 3 seconds

## Notes for Implementation

- Preserve backward compatibility during transition
- Use YAML for mapping files (human-readable/editable)
- Cache parsed grammars and mappings in memory
- Log all mapping resolution failures for debugging
- Consider using asyncio for HA API calls
- Implement graceful degradation if mapping file corrupted

## Questions to Resolve

1. Should mapping files be stored in git or gitignored?
2. How to handle multiple users editing same mapping?
3. Should we support regex patterns in mappings?
4. What happens if grammar and mapping get out of sync?
5. Should we auto-backup mapping files before updates?