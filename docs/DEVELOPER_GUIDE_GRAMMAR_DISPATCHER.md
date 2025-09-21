# ORAC Core: Grammar & Dispatcher Developer Guide

## Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Grammar System](#grammar-system)
4. [Dispatcher System](#dispatcher-system)
5. [Mapping System](#mapping-system)
6. [Performance Monitoring](#performance-monitoring)
7. [Command Processing Pipeline](#command-processing-pipeline)
8. [Adding New Dispatchers](#adding-new-dispatchers)
9. [Testing & Debugging](#testing--debugging)
10. [File Reference](#file-reference)

---

## Overview

ORAC Core uses a sophisticated grammar-driven system to process voice commands and dispatch them to various backend services like Home Assistant. This guide explains how the system works from the perspective of a developer who needs to understand, maintain, or extend the codebase.

### Key Concepts

- **Grammar**: GBNF (GGML BNF) files that define the structure and vocabulary of valid commands
- **Dispatcher**: A module that executes actions based on parsed LLM output
- **Mapping**: User-configurable connections between grammar terms and entity IDs
- **Topic**: A complete processing pipeline with its own grammar, LLM settings, and dispatcher

---

## System Architecture

### High-Level Flow

```
Voice Input → STT → LLM (constrained by Grammar) → Dispatcher → Backend Service
                           ↑                           ↑
                      Grammar File               Mapping File
```

### Key Components

1. **Grammar Parser** (`/orac/grammars/parser.py`)
   - Parses GBNF files to extract vocabulary
   - Validates LLM output against constraints
   - Generates valid term combinations

2. **Mapping System** (`/orac/dispatchers/mapping_*.py`)
   - Auto-generates mapping files from grammars
   - Resolves grammar terms to entity IDs
   - Manages entity discovery and validation

3. **Dispatcher** (`/orac/dispatchers/homeassistant.py`)
   - Executes commands on backend services
   - Uses mapping system for entity resolution
   - Records performance metrics

4. **Timing Infrastructure** (`/orac/core/timing.py`)
   - Tracks command flow through pipeline
   - Identifies performance bottlenecks
   - Maintains command history

---

## Grammar System

### GBNF Files

Grammar files are stored in `/data/grammars/` and define the structure of valid commands.

#### Example Grammar (`static_actions.gbnf`)
```gbnf
root ::= "{" ws "action" ws ":" ws action_value "," ws "device" ws ":" ws device_value "}"

action_value ::= "\"" action "\""
device_value ::= "\"" device "\""

action ::= "turn on" | "turn off" | "toggle"
device ::= "bedroom lights" | "bathroom lights" | "kitchen lights"

ws ::= [ \t\n]*
```

### Grammar Parser

**File**: `/orac/grammars/parser.py`

#### Key Class: `GBNFParser`

```python
class GBNFParser:
    def parse_grammar(self, grammar_file: str) -> Dict[str, List[str]]
    def get_combinations(self, grammar: Dict) -> List[str]
    def validate_output_against_grammar(self, output: str, grammar_file: str) -> Tuple[bool, Optional[str]]
```

**Usage Example**:
```python
from orac.grammars import GBNFParser

parser = GBNFParser()
grammar = parser.parse_grammar("data/grammars/static_actions.gbnf")
# Returns: {'action': ['turn on', 'turn off', 'toggle'],
#           'device': ['bedroom lights', 'bathroom lights', ...]}

combinations = parser.get_combinations(grammar)
# Returns: ['bedroom|lights', 'bathroom|lights', ...]
```

### How Grammar Constrains LLM

The grammar file is passed to the LLM (via llama.cpp or similar) to constrain its output to valid JSON structures:

```python
# In /orac/api.py around line 328
if topic.grammar and topic.grammar.grammar_file:
    grammar_path = data_dir / "grammars" / topic.grammar.grammar_file
    grammar_content = grammar_path.read_text()
    # Grammar constrains LLM output during generation
```

---

## Dispatcher System

### Base Dispatcher Interface

**File**: `/orac/dispatchers/base.py`

```python
class BaseDispatcher(ABC):
    @abstractmethod
    def execute(self, llm_output: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute the command from LLM output"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Display name of dispatcher"""
        pass
```

### HomeAssistant Dispatcher

**File**: `/orac/dispatchers/homeassistant.py`

#### Key Features:
- Parses JSON output from LLM
- Resolves entities using mapping system
- Falls back to legacy mappings if needed
- Records timing information
- Calls Home Assistant API

#### Key Methods:

```python
class HomeAssistantDispatcher(BaseDispatcher):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # Initialize mapping system
        self.resolver = MappingResolver(self.ha_url, self.ha_token)
        self.generator = MappingGenerator(self.ha_url, self.ha_token)

    def execute(self, llm_output: str, context: Optional[Dict] = None) -> Dict:
        # 1. Parse JSON from LLM
        # 2. Resolve entity using mapping system
        # 3. Call Home Assistant API
        # 4. Return result with timing data

    def get_mapping_stats(self, topic_id: str) -> Dict:
        # Get statistics about entity mappings

    def refresh_mappings(self, topic_id: str, grammar_file: str) -> bool:
        # Update mappings with new HA entities
```

### Dispatcher Registry

**File**: `/orac/dispatchers/registry.py`

Manages available dispatchers:

```python
class DispatcherRegistry:
    def register(self, name: str, dispatcher_class: Type[BaseDispatcher]):
        """Register a new dispatcher"""

    def get(self, name: str) -> Optional[Type[BaseDispatcher]]:
        """Get dispatcher class by name"""

    def create(self, name: str, config: Dict = None) -> Optional[BaseDispatcher]:
        """Create dispatcher instance"""

# Global registry instance
dispatcher_registry = DispatcherRegistry()

# Registration happens at module load
dispatcher_registry.register('homeassistant', HomeAssistantDispatcher)
```

---

## Mapping System

The mapping system bridges the gap between grammar terms and actual entity IDs.

### Mapping Generator

**File**: `/orac/dispatchers/mapping_generator.py`

#### Key Class: `MappingGenerator`

```python
class MappingGenerator:
    def generate_mapping_file(self, grammar_file: str, topic_id: str, force: bool = False) -> str:
        """Generate YAML mapping file from grammar"""

    def fetch_ha_entities(self) -> Dict[str, List[str]]:
        """Fetch available entities from Home Assistant"""

    def update_with_new_entities(self, mapping_file: str) -> int:
        """Add newly discovered entities to mapping file"""
```

### Mapping Resolver

**File**: `/orac/dispatchers/mapping_resolver.py`

#### Key Class: `MappingResolver`

```python
class MappingResolver:
    def load_mapping_file(self, topic_id: str) -> Dict:
        """Load mapping configuration for a topic"""

    def resolve(self, location: str, device: str, topic_id: str) -> Optional[str]:
        """Resolve location/device to entity ID"""
        # Returns entity ID or raises UnmappedError

    def entity_exists(self, entity_id: str) -> bool:
        """Check if entity exists in Home Assistant"""

    def get_mapping_stats(self, topic_id: str) -> Dict:
        """Get statistics about mappings"""
```

### Generated Mapping File Format

**Location**: `/orac/dispatchers/mappings/topic_{topic_id}.yaml`

```yaml
metadata:
  grammar_file: data/grammars/static_actions.gbnf
  topic_id: home_automation
  generated: 2025-09-15T10:00:00
  unmapped_count: 2

mappings:
  "bedroom|lights": "light.bedroom_lights"     # Mapped
  "kitchen|lights": ""                         # TODO: Map this
  "bathroom|lights": "IGNORE"                  # Explicitly ignored

available_entities:
  lights:
    - light.bedroom_lights
    - light.kitchen_ceiling
  switches:
    - switch.tretakt_smart_plug
```

### Mapping Resolution Flow

```python
# In HomeAssistantDispatcher.execute()

# 1. Try new mapping system
try:
    entity_id = self.resolver.resolve(location, device, topic_id)
    mapping_source = "mapping_file"
except UnmappedError:
    # 2. Fall back to legacy hardcoded mappings
    if location in self.entity_mappings:
        entity_id = self.entity_mappings[location][device]
        mapping_source = "legacy"
    else:
        # 3. Use default fallback
        entity_id = "switch.tretakt_smart_plug"
        mapping_source = "fallback"
```

---

## Performance Monitoring

### Timing Infrastructure

**File**: `/orac/core/timing.py`

#### Key Class: `TimedCommand`

```python
class TimedCommand:
    def mark(self, event: str, timestamp: Optional[datetime] = None):
        """Mark a timing event"""

    def duration(self, start_event: str, end_event: str) -> Optional[float]:
        """Calculate duration between events in milliseconds"""

    def get_bottlenecks(self, threshold_percent: float = 25.0) -> List[Dict]:
        """Identify performance bottlenecks"""

    def format_performance_breakdown(self) -> str:
        """Format human-readable performance report"""
```

#### Usage Example:

```python
from orac.core import TimedCommand

cmd = TimedCommand()
cmd.mark("dispatcher_start")
# ... do work ...
cmd.mark("ha_api_call")
# ... API call ...
cmd.mark("ha_response")
cmd.mark("dispatcher_complete")

print(cmd.format_performance_breakdown())
# Output:
# Performance Breakdown:
#   Dispatcher           [██        ] 22ms (15%)
#   Home Assistant API   [████      ] 156ms (85%)
# Total: 178ms
```

### Command History

```python
class CommandHistory:
    def add(self, command: TimedCommand):
        """Add command to history"""

    def get_average_duration(self) -> Optional[float]:
        """Calculate average command duration"""

    def get_stage_averages(self) -> Dict[str, float]:
        """Get average duration per pipeline stage"""

    def get_performance_trends(self) -> Dict:
        """Analyze performance trends over time"""
```

---

## Command Processing Pipeline

### Complete Flow with File References

1. **Wake Word Detection** (Hey ORAC - separate component)
   - Detects trigger phrase
   - Starts audio recording

2. **Speech to Text** (ORAC STT - separate component)
   - Converts audio to text
   - Sends to ORAC Core

3. **Topic Selection** (`/orac/topic_manager.py`)
   ```python
   class TopicManager:
       def get_topic_for_wake_word(self, wake_word: str) -> Optional[Topic]
   ```

4. **LLM Processing** (`/orac/api.py:process_command()`)
   ```python
   # Load grammar for topic
   grammar_path = data_dir / "grammars" / topic.grammar.grammar_file

   # Process with LLM (constrained by grammar)
   llm_output = await llm.generate(prompt, grammar=grammar_content)
   ```

5. **Dispatcher Execution** (`/orac/dispatchers/homeassistant.py`)
   ```python
   # Create dispatcher
   dispatcher = dispatcher_registry.create(topic.dispatcher)

   # Execute with context
   result = dispatcher.execute(llm_output, {
       'topic_id': topic.id,
       'grammar_file': grammar_path
   })
   ```

6. **Entity Resolution** (`/orac/dispatchers/mapping_resolver.py`)
   ```python
   # Resolve grammar terms to entity ID
   entity_id = resolver.resolve(location, device, topic_id)
   ```

7. **API Call** (`/orac/dispatchers/homeassistant.py:_call_ha_service()`)
   ```python
   response = requests.post(
       f"{self.ha_url}/api/services/{domain}/{service}",
       headers={'Authorization': f'Bearer {self.ha_token}'},
       json={'entity_id': entity_id}
   )
   ```

---

## Adding New Dispatchers

### Step 1: Create Dispatcher Class

Create `/orac/dispatchers/my_dispatcher.py`:

```python
from typing import Any, Dict, Optional
from .base import BaseDispatcher
import logging

logger = logging.getLogger(__name__)

class MyServiceDispatcher(BaseDispatcher):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        # Initialize your service connection
        self.service_url = config.get('url') if config else None

    def execute(self, llm_output: str, context: Optional[Dict] = None) -> Dict:
        try:
            # Parse LLM output
            import json
            command = json.loads(llm_output)

            # Process command
            # ...

            return {
                'success': True,
                'result': {...},
                'error': None
            }
        except Exception as e:
            logger.error(f"Error in MyServiceDispatcher: {e}")
            return {
                'success': False,
                'result': None,
                'error': str(e)
            }

    @property
    def name(self) -> str:
        return "My Service"

    @property
    def description(self) -> str:
        return "Dispatches commands to My Service"
```

### Step 2: Register Dispatcher

In `/orac/dispatchers/registry.py`:

```python
# At the bottom of the file
from .my_dispatcher import MyServiceDispatcher
dispatcher_registry.register('myservice', MyServiceDispatcher)
```

### Step 3: Configure Topic

In topic configuration:

```yaml
topic:
  id: "my_service_control"
  dispatcher: "myservice"  # Use registered name
  grammar:
    grammar_file: "my_service.gbnf"
```

---

## Testing & Debugging

### Unit Testing

**Test Grammar Parser**:
```python
# tests/test_grammar_parser.py
from orac.grammars import GBNFParser

def test_parse_grammar():
    parser = GBNFParser()
    grammar = parser.parse_grammar("data/grammars/static_actions.gbnf")
    assert 'device' in grammar
    assert 'action' in grammar
```

**Test Mapping System**:
```python
# tests/test_mapping_system.py
from orac.dispatchers.mapping_resolver import MappingResolver

def test_resolve_entity():
    resolver = MappingResolver()
    # Test with known mapping
    entity = resolver.resolve("bedroom", "lights", "test_topic")
    assert entity == "light.bedroom_lights"
```

### Integration Testing

Use the provided test script:
```bash
python test_dispatcher_optimization.py
```

This tests:
- Grammar parsing
- Mapping file generation
- Entity resolution
- Dispatcher execution
- Performance monitoring

### Debugging Tips

1. **Enable Debug Logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Check Mapping Files**:
   ```bash
   cat orac/dispatchers/mappings/topic_*.yaml
   ```

3. **Test Grammar Parsing**:
   ```python
   from orac.grammars import GBNFParser
   parser = GBNFParser()
   grammar = parser.parse_grammar("your_grammar.gbnf")
   print(f"Parsed: {grammar}")
   print(f"Combinations: {parser.get_combinations(grammar)}")
   ```

4. **Monitor Performance**:
   ```python
   from orac.core import command_history

   # After processing commands
   print(f"Average duration: {command_history.get_average_duration()}ms")
   print(f"Stage averages: {command_history.get_stage_averages()}")
   ```

---

## File Reference

### Core Files

| File | Purpose | Key Classes/Functions |
|------|---------|----------------------|
| `/orac/grammars/parser.py` | Parse GBNF grammars | `GBNFParser` |
| `/orac/dispatchers/base.py` | Base dispatcher interface | `BaseDispatcher` |
| `/orac/dispatchers/homeassistant.py` | Home Assistant integration | `HomeAssistantDispatcher` |
| `/orac/dispatchers/registry.py` | Dispatcher registration | `DispatcherRegistry` |
| `/orac/dispatchers/mapping_generator.py` | Generate mapping files | `MappingGenerator` |
| `/orac/dispatchers/mapping_resolver.py` | Resolve entities | `MappingResolver` |
| `/orac/core/timing.py` | Performance monitoring | `TimedCommand`, `CommandHistory` |
| `/orac/topic_manager.py` | Topic management | `TopicManager` |
| `/orac/api.py` | Main API endpoints | `process_command()` |

### Data Files

| File | Purpose | Format |
|------|---------|--------|
| `/data/grammars/*.gbnf` | Grammar definitions | GBNF |
| `/orac/dispatchers/mappings/topic_*.yaml` | Entity mappings | YAML |
| `/data/topics/*.yaml` | Topic configurations | YAML |

### Configuration

| Environment Variable | Purpose | Default |
|---------------------|---------|---------|
| `HA_URL` | Home Assistant URL | `http://192.168.8.99:8123` |
| `HA_TOKEN` | Home Assistant API token | None |
| `ORAC_DATA_DIR` | Data directory path | `./data` |

---

## Common Patterns

### Error Handling

```python
try:
    entity = resolver.resolve(location, device, topic_id)
except UnmappedError as e:
    # Handle unmapped combination
    logger.warning(f"Unmapped: {e}")
    # Fall back to default
except InvalidEntityError as e:
    # Handle invalid entity
    logger.error(f"Invalid entity: {e}")
    # Report error to user
```

### Caching

```python
class MappingResolver:
    def __init__(self):
        self.mapping_cache = {}  # Cache loaded mappings
        self.entity_cache = {}   # Cache HA entities
        self.entity_cache_time = None

    def _cache_expired(self) -> bool:
        age = datetime.now() - self.entity_cache_time
        return age > timedelta(seconds=self.cache_ttl)
```

### Async Operations

While the current implementation is synchronous, the system is designed to support async:

```python
# Future async support
async def execute_async(self, llm_output: str, context: Dict) -> Dict:
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            return await response.json()
```

---

## Best Practices

1. **Always validate LLM output** before processing
2. **Use mapping files** instead of hardcoding entities
3. **Record timing information** for performance analysis
4. **Cache frequently accessed data** (mappings, entities)
5. **Provide fallback mechanisms** for unmapped entities
6. **Log errors with context** for debugging
7. **Test with actual grammar files** from production
8. **Document new dispatchers** in this guide

---

## Troubleshooting

### Common Issues

**Issue**: "No mapping found for device in location"
- Check mapping file exists: `ls orac/dispatchers/mappings/`
- Verify mapping file has entry for combination
- Ensure entity exists in Home Assistant

**Issue**: "Grammar parse failed"
- Validate GBNF syntax
- Check file path is correct
- Ensure grammar file is in `/data/grammars/`

**Issue**: "Dispatcher not found"
- Verify dispatcher is registered in registry
- Check spelling of dispatcher name in topic config

**Issue**: "Entity validation failed"
- Check HA_TOKEN is set
- Verify Home Assistant is accessible
- Ensure entity exists in HA

### Debug Commands

```bash
# Check grammar parsing
python -c "from orac.grammars import GBNFParser; p=GBNFParser(); print(p.parse_grammar('data/grammars/static_actions.gbnf'))"

# Test entity resolution
python -c "from orac.dispatchers.mapping_resolver import MappingResolver; r=MappingResolver(); print(r.get_mapping_stats('home_automation'))"

# View dispatcher registry
python -c "from orac.dispatchers.registry import dispatcher_registry; print(dispatcher_registry.list_dispatchers())"
```

---

## Contributing

When contributing to the grammar/dispatcher system:

1. **Write tests** for new functionality
2. **Update mapping files** when adding entities
3. **Document changes** in this guide
4. **Follow existing patterns** for consistency
5. **Add timing marks** for new pipeline stages
6. **Handle errors gracefully** with fallbacks

---

## Future Enhancements

Planned improvements to the system:

1. **Async Dispatcher Support** - Full async/await implementation
2. **Dynamic Grammar Generation** - Auto-generate grammars from HA entities
3. **Multi-Backend Support** - Single dispatcher for multiple services
4. **Advanced Mapping Rules** - Regex patterns, conditions, variables
5. **Real-time Performance Dashboard** - Web UI for monitoring
6. **Automatic Mapping Suggestions** - ML-based entity matching
7. **Grammar Composition** - Combine multiple grammars
8. **Distributed Tracing** - OpenTelemetry integration

---

## Contact & Support

For questions about the grammar and dispatcher system:

1. Check this guide first
2. Review test files for examples
3. Check existing issues in the repository
4. Create a new issue with:
   - Clear problem description
   - Relevant log output
   - Grammar and mapping files
   - Steps to reproduce

---

*Last Updated: September 2025*
*Version: 1.0*