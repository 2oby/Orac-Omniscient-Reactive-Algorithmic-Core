# Sprint 5 Implementation Prompt: Backend-Dispatcher Integration

## Context
You are implementing Sprint 5 of the ORAC Core system. The system runs on an NVIDIA Orin Nano (hostname: `orin4`) at IP `192.168.8.192`. Sprint 4 successfully implemented topic-backend linkage for dynamic grammar generation. However, the UI still shows both "Backend Configuration" and "Dispatcher Configuration" separately, which is confusing for users.

## Your Mission
Refactor the architecture to encapsulate dispatchers within backends. Users should only see and configure backends - the dispatcher becomes an internal implementation detail. Each backend type will internally manage its appropriate dispatcher.

## Current System State

### What's Working (Sprint 4 Complete)
- Topics can link to backends for dynamic grammar generation
- Backend grammar generation from device mappings works
- Command execution works through dispatchers
- Test device configured: "Lounge Lamp Plug" (lights/lounge)

### The Problem
Users currently see both:
1. **Backend Configuration** - for grammar generation
2. **Dispatcher Configuration** - for command execution

This is confusing because:
- A Home Assistant backend ALWAYS uses a Home Assistant dispatcher
- Users shouldn't need to understand this internal architecture
- It's error-prone (users could select incompatible combinations)

## Development Environment

### Access and Deployment

**Your Development Machine**: Mac with project at:
```bash
cd "/Users/2oby/pCloud Box/Projects/ORAC/Orac-Omniscient-Reactive-Algorithmic-Core"
```

**Target System**: NVIDIA Orin Nano
- **SSH Access**: `ssh orin4` (pre-configured alias)
- **IP Address**: `192.168.8.192`
- **Web Interface**: http://192.168.8.192:8000
- **Container Name**: `orac`

### Deployment Process

**CRITICAL**: Use the `deploy_and_test.sh` script for ALL deployments:

```bash
cd "/Users/2oby/pCloud Box/Projects/ORAC/Orac-Omniscient-Reactive-Algorithmic-Core"
./deploy_and_test.sh "Sprint 5: Encapsulate dispatcher within backend"
```

**What deploy_and_test.sh does**:
1. Commits your changes to Git with the provided message
2. Pushes to GitHub (single source of truth)
3. SSHs to `orin4` and pulls from GitHub
4. Copies files into the Docker container
5. Restarts the ORAC container
6. Runs automated tests
7. Shows deployment status

**NEVER**:
- Manually copy files to the Orin
- Edit files directly on the Orin
- Skip the deployment script

### Useful Commands

```bash
# View logs
ssh orin4 'docker logs orac --tail 50'

# Enter container shell
ssh orin4 'docker exec -it orac bash'

# Check file in container
ssh orin4 'docker exec orac cat /app/data/topics.yaml'

# Test API endpoint
curl http://192.168.8.192:8000/api/topics

# Restart container manually (if needed)
ssh orin4 'docker restart orac'
```

## Implementation Requirements

### 1. Create Abstract Backend System

Create `/orac/backends/abstract_backend.py`:

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class AbstractBackend(ABC):
    """Base class for all backend implementations"""

    def __init__(self, backend_id: str, config: Dict):
        self.backend_id = backend_id
        self.config = config
        self.name = config.get('name', backend_id)
        self.type = config.get('type')

    @abstractmethod
    async def fetch_entities(self) -> List[Dict]:
        """Fetch available entities from the backend system"""
        pass

    @abstractmethod
    def generate_grammar(self) -> Dict:
        """Generate GBNF grammar from configured devices"""
        pass

    @abstractmethod
    async def dispatch_command(self, command: Dict, context: Dict = None) -> Dict:
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

### 2. Create HomeAssistant Implementation

Create `/orac/backends/homeassistant_backend.py`:

```python
from .abstract_backend import AbstractBackend
from orac.ha_client import HomeAssistantClient
from orac.dispatchers.homeassistant import HomeAssistantDispatcher
from orac.backend_grammar_generator import BackendGrammarGenerator

class HomeAssistantBackend(AbstractBackend):
    def __init__(self, backend_id: str, config: Dict):
        super().__init__(backend_id, config)
        self.client = self._create_client()
        # Dispatcher is now internal!
        self.dispatcher = HomeAssistantDispatcher()
        self.grammar_generator = BackendGrammarGenerator()

    async def dispatch_command(self, command: Dict, context: Dict = None) -> Dict:
        """Execute command through internal dispatcher"""
        return self.dispatcher.execute(command, context)

    # ... implement other abstract methods
```

### 3. Update Topic Model

Modify `/orac/topic_models/topic.py`:

```python
class Topic(BaseModel):
    name: str
    description: str
    enabled: bool
    model: str
    settings: TopicSettings

    # Sprint 5: Only backend_id needed, no dispatcher field
    backend_id: Optional[str] = Field(default=None, description="Linked backend for grammar and execution")

    # REMOVE: dispatcher field
    # dispatcher: Optional[str] = Field(...)  # DELETE THIS

    grammar: GrammarConfig  # Keep for backward compatibility, deprecated
```

### 4. Update API Generation Logic

Modify `/orac/api.py` generation endpoint:

```python
# Old approach (REMOVE):
if topic.dispatcher:
    dispatcher = dispatcher_registry.create(topic.dispatcher)
    result = dispatcher.execute(response_text, context)

# New approach (ADD):
if topic.backend_id:
    backend = backend_factory.create(topic.backend_id)
    result = await backend.dispatch_command(parsed_json, {'topic': topic})
```

### 5. Update UI

Modify `/orac/templates/topic_config.html`:

Remove this entire section:
```html
<!-- REMOVE THIS ENTIRE SECTION -->
<div class="form-section">
    <h2 class="section-title">Dispatcher Configuration</h2>
    <select id="dispatcher" class="form-select">
        <option value="">None (Display Only)</option>
    </select>
</div>
```

Keep only the Backend Configuration section.

### 6. Migration Logic

Add to `/orac/topic_manager.py`:

```python
def load_topics(self):
    """Load topics with migration"""
    # ... existing code ...

    for topic_id, topic_data in topics_data.items():
        # Sprint 5 Migration: Move dispatcher to backend
        if 'dispatcher' in topic_data and topic_data['dispatcher']:
            if topic_data.get('backend_id'):
                # Ensure backend knows its dispatcher type
                backend = self.backend_manager.get_backend(topic_data['backend_id'])
                if backend:
                    backend['dispatcher_type'] = topic_data['dispatcher']
                    self.backend_manager.save_backend(topic_data['backend_id'])
            # Remove dispatcher from topic
            del topic_data['dispatcher']

        self.topics[topic_id] = Topic(**topic_data)
```

## Testing Checklist

### Before Starting
- [ ] Check current setup works: `curl http://192.168.8.192:8000/v1/generate/computa -d '{"prompt":"turn on lights","json_mode":true}'`
- [ ] Backup current configuration: `ssh orin4 'docker exec orac cp -r /app/data /app/data_backup_sprint5'`

### After Each Major Change
- [ ] Deploy using: `./deploy_and_test.sh "Sprint 5: [specific change]"`
- [ ] Check logs: `ssh orin4 'docker logs orac --tail 50'`
- [ ] Test API still works

### Final Testing
- [ ] Topic configuration UI shows only Backend (no Dispatcher)
- [ ] Can select backend from dropdown
- [ ] Command "turn on the lounge lights" still works
- [ ] Backend status shows correctly
- [ ] No errors in logs

## Common Issues and Solutions

### Issue: Import errors after refactoring
```bash
ssh orin4 'docker logs orac --tail 100 | grep -i error'
```
Solution: Check import paths and ensure all new directories have `__init__.py`

### Issue: Commands stop working
Check if backend has dispatcher internally:
```python
ssh orin4 'docker exec orac python3 -c "
from orac.backends.backend_factory import BackendFactory
backend = BackendFactory.create(\"homeassistant_8ca84424\")
print(hasattr(backend, \"dispatcher\"))
"'
```

### Issue: UI still shows dispatcher
Clear browser cache and check HTML was updated:
```bash
ssh orin4 'docker exec orac grep -n "Dispatcher Configuration" /app/orac/templates/topic_config.html'
```

## File Locations in Container

```
/app/orac/
├── backends/                 # NEW: Backend implementations
│   ├── __init__.py
│   ├── abstract_backend.py
│   └── homeassistant_backend.py
├── topic_models/
│   └── topic.py             # UPDATE: Remove dispatcher field
├── api.py                   # UPDATE: Use backend.dispatch_command()
├── templates/
│   └── topic_config.html    # UPDATE: Remove dispatcher UI
├── static/js/
│   └── topic_config.js      # UPDATE: Remove dispatcher logic
└── backend_manager.py       # UPDATE: Use new backend classes

/app/data/
├── topics.yaml              # Will be auto-migrated
├── backends/
│   └── homeassistant_*.json
└── grammars/
    └── backend_*.gbnf
```

## Sprint 5 Success Criteria

1. **No Dispatcher in UI**: Topic configuration shows only Backend selection
2. **Commands Still Work**: "turn on the lounge lights" executes correctly
3. **Automatic Migration**: Existing topics work without manual intervention
4. **Clean Architecture**: Dispatcher exists only inside backend implementation
5. **No User Confusion**: Single backend selection instead of backend+dispatcher

## Important Notes

1. **Always use deploy_and_test.sh** - This ensures GitHub is the source of truth
2. **Test incrementally** - Deploy after each major change
3. **Preserve backward compatibility** - Migration must be automatic
4. **Keep grammar generation** - Backends still generate grammar AND dispatch
5. **Document changes** - Update code comments explaining the new architecture

## Commit Message Examples

Use clear, specific commit messages:
```bash
./deploy_and_test.sh "Sprint 5: Create abstract backend base class"
./deploy_and_test.sh "Sprint 5: Implement HomeAssistantBackend with internal dispatcher"
./deploy_and_test.sh "Sprint 5: Remove dispatcher field from Topic model"
./deploy_and_test.sh "Sprint 5: Update UI to remove dispatcher configuration"
./deploy_and_test.sh "Sprint 5: Add migration logic for existing topics"
```

## When Complete

The system should:
1. Show only backend configuration in the UI
2. Execute commands through `backend.dispatch_command()`
3. No longer have any user-visible dispatcher configuration
4. Still successfully control the "Lounge Lamp Plug"

Remember: The dispatcher isn't being removed - it's being encapsulated within the backend where it belongs!