# Sprint 5: Backend-Dispatcher Integration

## Executive Summary
Sprint 5 refactors the architecture to encapsulate dispatchers within backends, creating a unified backend system that handles both grammar generation AND command execution. Users will only need to configure a backend - the dispatcher becomes an internal implementation detail.

## Current Architecture Problems
1. **Confusing UX**: Users must understand and configure both backends and dispatchers separately
2. **Coupling Issues**: A Home Assistant backend MUST use a Home Assistant dispatcher - why make users configure both?
3. **Error Prone**: Users could misconfigure by selecting incompatible backend/dispatcher combinations
4. **Redundant Configuration**: The dispatcher type is always determined by the backend type

## Sprint 5 Goal
Transform the dispatcher from a user-facing configuration into an internal component of the backend system. Each backend type will internally manage its own dispatcher, providing a single, unified interface for both grammar generation and command execution.

## Architectural Vision

### Abstract Backend Pattern
```python
from abc import ABC, abstractmethod

class AbstractBackend(ABC):
    """Base class for all backend implementations"""

    @abstractmethod
    async def fetch_entities(self) -> List[Dict]:
        """Fetch available entities from the backend system"""
        pass

    @abstractmethod
    def generate_grammar(self) -> str:
        """Generate GBNF grammar from configured devices"""
        pass

    @abstractmethod
    async def dispatch_command(self, command: Dict) -> Dict:
        """Execute the LLM-generated command on the backend system"""
        pass

    @abstractmethod
    async def test_connection(self) -> Dict:
        """Verify backend connectivity and configuration"""
        pass

    @abstractmethod
    def get_statistics(self) -> Dict:
        """Get backend statistics and status"""
        pass
```

### Concrete Implementation Example
```python
class HomeAssistantBackend(AbstractBackend):
    def __init__(self, backend_id: str, config: Dict):
        self.backend_id = backend_id
        self.config = config
        self.client = HomeAssistantClient(config)
        # Dispatcher is now internal!
        self.dispatcher = HomeAssistantDispatcher(self.client)
        self.grammar_generator = BackendGrammarGenerator()

    async def dispatch_command(self, command: Dict) -> Dict:
        """Backend handles dispatching internally"""
        return await self.dispatcher.execute(command)

    def generate_grammar(self) -> str:
        """Generate grammar from configured devices"""
        return self.grammar_generator.generate(self.get_mapped_devices())
```

## Key Changes Required

### 1. Backend Model Updates
- Add `dispatcher_type` as an internal field (not user-configurable)
- Remove dispatcher from topic configuration UI
- Backend type automatically determines dispatcher type

### 2. Topic Model Simplification
- Remove `dispatcher` field from Topic model
- Topics only need `backend_id`
- Backend handles all execution internally

### 3. API Updates
- Generation endpoint uses backend's `dispatch_command()` method
- Remove separate dispatcher configuration endpoints
- Simplify topic configuration endpoints

### 4. UI Simplification
Before:
```
┌─────────────────────────────────────┐
│ Backend Configuration               │
│ • Select Backend: [Home Assistant]  │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Dispatcher                          │  ← REMOVE THIS
│ • Select: [homeassistant ▼]         │
└─────────────────────────────────────┘
```

After:
```
┌─────────────────────────────────────┐
│ Backend Configuration               │
│ • Select Backend: [Home Assistant]  │
│ • Status: ✅ Connected              │
│ • Devices: 30 configured            │
└─────────────────────────────────────┘
```

## Implementation Tasks

### Phase 1: Create Abstract Backend System
1. Create `/orac/backends/abstract_backend.py` with base class
2. Create `/orac/backends/homeassistant_backend.py` implementing the abstract class
3. Move dispatcher logic into HomeAssistantBackend class
4. Update BackendManager to use new backend classes

### Phase 2: Update Models and Database
1. Add `dispatcher_type` to backend configuration (internal)
2. Remove `dispatcher` field from Topic model
3. Update migration logic for existing topics
4. Ensure backward compatibility during transition

### Phase 3: Update API Layer
1. Modify generation endpoint to use `backend.dispatch_command()`
2. Remove dispatcher-specific endpoints
3. Update topic endpoints to remove dispatcher configuration
4. Simplify backend status endpoints

### Phase 4: Update UI
1. Remove dispatcher dropdown from topic configuration
2. Remove dispatcher section from HTML templates
3. Update JavaScript to not handle dispatcher selection
4. Simplify backend status display

### Phase 5: Testing and Migration
1. Test command execution through new integrated backends
2. Migrate existing configurations automatically
3. Ensure backward compatibility
4. Update documentation

## Migration Strategy

### Automatic Migration
When loading existing configurations:
```python
def migrate_topic_config(topic: Dict) -> Dict:
    """Migrate old topic with dispatcher to new backend-only model"""
    if 'dispatcher' in topic and topic['dispatcher']:
        # Ensure backend has correct dispatcher type internally
        if topic.get('backend_id'):
            backend = backend_manager.get_backend(topic['backend_id'])
            backend['dispatcher_type'] = topic['dispatcher']
        # Remove dispatcher from topic
        del topic['dispatcher']
    return topic
```

## File Structure Changes

### New Files
```
/orac/backends/
    __init__.py
    abstract_backend.py       # Abstract base class
    homeassistant_backend.py  # HA implementation
    backend_factory.py        # Factory for creating backends
```

### Modified Files
- `/orac/topic_models/topic.py` - Remove dispatcher field
- `/orac/api.py` - Update generation logic
- `/orac/templates/topic_config.html` - Remove dispatcher UI
- `/orac/static/js/topic_config.js` - Remove dispatcher logic
- `/orac/backend_manager.py` - Use new backend classes

### Deprecated Files
- `/orac/dispatchers/*` - Move logic into backend implementations

## Success Criteria

1. **Unified Interface**: Users only configure backends, not dispatchers
2. **Automatic Dispatch**: Commands execute through backend without separate dispatcher configuration
3. **Simplified UI**: No dispatcher dropdown in topic configuration
4. **Backward Compatible**: Existing configurations automatically migrate
5. **Clean Architecture**: Dispatcher is encapsulated within backend implementation
6. **Working Commands**: "turn on the lounge lights" still works through new system

## Testing Plan

### Unit Tests
```python
def test_backend_includes_dispatcher():
    backend = HomeAssistantBackend(config)
    command = {"device": "lights", "action": "on", "location": "lounge"}
    result = await backend.dispatch_command(command)
    assert result['success'] == True

def test_backend_grammar_generation():
    backend = HomeAssistantBackend(config)
    grammar = backend.generate_grammar()
    assert "lights" in grammar
    assert "lounge" in grammar
```

### Integration Tests
1. Create topic with backend only (no dispatcher)
2. Generate command through topic
3. Verify command executes on Home Assistant
4. Verify grammar constraints work
5. Test migration of old configurations

### Manual Testing
1. Configure backend through UI
2. Link topic to backend
3. Test "turn on the lounge lights"
4. Verify light responds
5. Check no dispatcher configuration visible

## Benefits

1. **Simpler Mental Model**: "I have a Home Assistant backend" not "backend + dispatcher"
2. **Reduced Errors**: No incompatible backend/dispatcher combinations
3. **Better Encapsulation**: Implementation details hidden from users
4. **Easier Extension**: New backend types self-contained
5. **Cleaner UI**: Fewer configuration options to understand

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing configs | Automatic migration on load |
| Complex refactoring | Incremental implementation with tests |
| User confusion during transition | Clear documentation and UI hints |
| Backend-specific features lost | Ensure all dispatcher features move to backend |

## Future Extensibility

With this architecture, adding new backend types becomes straightforward:

```python
class ZigbeeBackend(AbstractBackend):
    """Zigbee implementation with built-in dispatch"""
    async def dispatch_command(self, command):
        return self.zigbee_client.send(command)

class KNXBackend(AbstractBackend):
    """KNX implementation with built-in dispatch"""
    async def dispatch_command(self, command):
        return self.knx_bus.execute(command)
```

## Sprint Timeline

- **Day 1-2**: Create abstract backend system and HA implementation
- **Day 3-4**: Update models and API layer
- **Day 5-6**: Update UI and remove dispatcher UI elements
- **Day 7**: Testing and migration logic
- **Day 8**: Documentation and deployment

## Definition of Done

- [ ] Abstract backend class created and implemented
- [ ] HomeAssistantBackend includes dispatcher internally
- [ ] Topic model no longer has dispatcher field
- [ ] UI shows only backend configuration (no dispatcher)
- [ ] Existing configurations automatically migrate
- [ ] Commands execute through backend.dispatch_command()
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Deployed to Orin Nano and tested