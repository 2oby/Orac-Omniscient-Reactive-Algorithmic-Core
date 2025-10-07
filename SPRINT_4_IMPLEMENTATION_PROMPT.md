# Sprint 4 Implementation Prompt for Next Session

## IMPORTANT: Sprint 3 Status - COMPLETED ✅
Sprint 3 is now fully implemented and working:
1. ✅ BackendGrammarGenerator class for dynamic grammar generation
2. ✅ API endpoints for grammar generation and testing (`/api/backends/{id}/grammar/*`)
3. ✅ Grammar testing interface at `/backends/{id}/test-grammar`
4. ✅ GBNF grammar generation from device mappings
5. ✅ Command validation against generated grammars
6. ✅ Integration with existing backend management system

Sprint 3 creates **dynamic GBNF grammars** from Sprint 2's device mappings, constraining the LLM to only output JSON for devices the user has actually configured.

## Current System Status (Pre-Sprint 4)

### Existing Backend Configuration
You have a working backend already configured:
- **Backend ID**: `homeassistant_8ca84424`
- **Name**: "Test HA Backend"
- **Status**: ✅ Connected to Home Assistant at http://192.168.8.99:8123
- **Location**: `/app/data/backends/homeassistant_8ca84424.json` (in container)
- **Devices**: 30 total entities fetched from Home Assistant
- **Configured Devices**: 1 enabled and fully mapped
  - Entity: `switch.tretakt_smart_plug` (Lounge Lamp Plug)
  - device_type: "lights"
  - location: "lounge"
  - state: "off"
  - This is a REAL device on the network that can be controlled

### Existing Topics
Three topics exist in `/app/data/topics.yaml`:

1. **"computa"** (lowercase) - PRIMARY TOPIC FOR TESTING
   - Currently uses: `grammar.enabled=true, grammar.file="default.gbnf"` (STATIC)
   - Has dispatcher: "homeassistant"
   - Active with 181 trigger counts
   - **This topic should be converted to use backend_id in Sprint 4**

2. **"general"**
   - No grammar enabled
   - Has dispatcher: "homeassistant"

3. **"Computa"** (capitalized - duplicate)
   - No grammar enabled
   - No dispatcher

### Current Topic Configuration UI
The topic configuration page at `http://192.168.8.192:8000/topics/{topic_id}` currently has TWO sections:

1. **Grammar Configuration Section** (TO BE REMOVED)
   - Enable Grammar checkbox
   - Grammar File dropdown (default.gbnf, set_temp.gbnf, etc.)
   - Located in `/orac/templates/topic_config.html`

2. **Dispatcher Section** (TO BE KEPT)
   - Dispatcher dropdown (homeassistant, etc.)
   - This stays unchanged

**CRITICAL**: Sprint 4 will **REMOVE** the Grammar Configuration section and **REPLACE** it with a new Backend Selection section. The Dispatcher section stays as-is.

## Context for Sprint 4
You are implementing Sprint 4 of the ORAC Core system. ORAC Core runs on an **NVIDIA Orin Nano** (hostname: `orin4`) at IP `192.168.8.192`. Sprint 3 is complete - the system can now:
- Generate GBNF grammars dynamically from backend device mappings
- Test commands against generated grammars via web interface
- Cache generated grammars as `backend_{id}.gbnf` files
- Validate commands and show JSON output with device mappings

Sprint 4's goal is to **integrate Topics with Backend Grammar Generation** and **eliminate the static grammar system** to create a unified, dynamic architecture where topics automatically use backend-generated grammars.

## Your Mission
Implement Sprint 4: **Topic ↔ Backend Integration** to replace the static grammar dropdown system with backend-driven dynamic grammar selection. The primary goal is to link topics to backends so grammar constraints are automatically sourced from actual device configurations.

**Key Concept**: Instead of manually selecting `default.gbnf` or `set_temp.gbnf`, topics link to backends and automatically use `backend_{id}.gbnf` grammars that reflect the user's actual configured devices.

**End Goal**: Test command "turn on the lounge lights" through a topic that's linked to a backend and verify it uses the backend's dynamically generated grammar instead of any static grammar file.

## Current System State
- **Completed**:
  - ✅ Backend management with full CRUD operations
  - ✅ Entity fetching and configuration from Home Assistant
  - ✅ Dynamic grammar generation from device mappings
  - ✅ Grammar testing and validation interfaces
  - ✅ Deployed to Jetson Orin at 192.168.8.192

- **Existing Infrastructure**:
  - `BackendGrammarGenerator` in `/orac/backend_grammar_generator.py`
  - Backend data stored in `/data/backends/{backend_id}.json`
  - Generated grammars in `/data/grammars/backend_{backend_id}.gbnf`
  - Topic management system in `/orac/topic_manager.py`
  - Topic configuration UI at `/topics/{topic_id}`

## Sprint 4 Primary Goal: Topic-Backend Integration

By the end of Sprint 4, the system should:
- Link topics to backends through configuration UI
- Automatically use backend-generated grammars instead of static files
- Auto-regenerate grammar when backend device mappings change
- Remove static grammar selection from topic configuration
- Handle backend errors gracefully (offline, deleted, empty)
- Show backend status and grammar statistics in topic interface

## Key Implementation Tasks

### Priority 1: Topic Model and Backend Linkage
1. **Update Topic Model** in `/orac/topic_models/topic.py`
   - Add `backend_id: Optional[str]` field to link topic to backend
   - Remove dependency on static `GrammarConfig` for linked topics
   - Add validation to ensure backend exists when specified

2. **Update Topic Manager** in `/orac/topic_manager.py`
   - Add methods for backend linkage management
   - Validate backend existence during topic operations
   - Handle topic loading with backend references

### Priority 2: Grammar Selection Logic Overhaul
1. **Update Generation Logic** in `/orac/api.py`
   - Replace static grammar file selection with backend grammar lookup
   - Use `backend_{topic.backend_id}.gbnf` when topic has linked backend
   - Remove fallback to static grammar files (`default.gbnf`, `set_temp.gbnf`) for linked topics
   - Add comprehensive error handling for missing/offline backends

2. **Auto-Regeneration Integration**
   - Modify `BackendManager.save_backend()` to trigger grammar regeneration
   - Ensure grammar files are always current when topics use them
   - Handle concurrent access to grammar files

### Priority 3: Topic Configuration UI Replacement
1. **Update Topic Configuration Template** `/orac/templates/topic_config.html`
   - Replace grammar file dropdown with backend selection dropdown
   - Populate dropdown with available backends showing: name, type, device count
   - Add "Create New Backend" option that redirects to backend creation
   - Show linked backend status, statistics, and direct management links
   - Remove all static grammar selection UI components

2. **Update Topic Configuration JavaScript**
   - Handle backend selection changes
   - Fetch and display backend statistics
   - Implement "Create New Backend" workflow
   - Add real-time backend status updates

### Priority 4: API Endpoint Extensions
1. **Add Topic-Backend API Endpoints**
   ```python
   PUT /api/topics/{topic_id}/backend    # Link topic to backend
   GET /api/topics/{topic_id}/backend    # Get topic's backend info
   DELETE /api/topics/{topic_id}/backend # Unlink topic from backend
   ```

2. **Update Existing Topic Endpoints**
   - Include backend information in topic responses
   - Add backend validation in topic update operations
   - Return backend statistics with topic details

### Priority 5: Deprecation and Cleanup
1. **Remove Deprecated Static Grammar Components**
   - Remove static grammar selection logic from topic generation
   - Clean up hardcoded references to `default.gbnf`, `set_temp.gbnf` in topic context
   - Remove grammar file dropdown UI elements
   - Update error messages to reflect backend-driven approach

2. **Code Cleanup**
   - Remove unused static grammar imports in topic-related files
   - Clean up obsolete grammar validation for static files
   - Update comments and documentation to reflect new architecture

## ORAC Core Infrastructure

### NVIDIA Orin Nano Setup
ORAC Core runs on an **NVIDIA Orin Nano** device with these details:
- **Hostname**: `orin4`
- **IP Address**: `192.168.8.192`
- **Web Interface**: http://192.168.8.192:8000
- **Container**: ORAC runs in Docker container named `orac`
- **SSH Access**: Use `ssh orin4` (pre-configured alias on your Mac)

### SSH Access to Orin
```bash
# Connect to the Orin Nano
ssh orin4

# Once connected, useful commands:
docker logs orac --tail 50              # View ORAC container logs
docker exec -it orac bash              # Enter ORAC container shell
docker ps                              # Check container status
docker restart orac                    # Restart ORAC container

# Check generated grammar files
docker exec orac ls -la /app/data/grammars/

# View backend configurations
docker exec orac ls -la /app/data/backends/

# Check topic configurations
docker exec orac cat /app/data/topics.yaml
```

## Deployment Process

### The Deploy Script
The `deploy_and_test.sh` script handles the complete deployment workflow from your Mac to the Orin Nano:

```bash
cd "/Users/2oby/pCloud Box/Projects/ORAC/Orac-Omniscient-Reactive-Algorithmic-Core"
./deploy_and_test.sh "Sprint 4: Topic-Backend integration"
```

### What deploy_and_test.sh Does

1. **Local Git Operations**:
   - Commits all your local changes with the provided message
   - Pushes to GitHub repository (single source of truth)

2. **Remote Deployment via SSH**:
   - Uses `ssh orin4` to connect to the Orin Nano
   - Pulls latest code from GitHub onto the Orin
   - Copies updated files into the running Docker container
   - Restarts the ORAC container to pick up changes
   - Runs automated tests to verify deployment

3. **Real-time Feedback**:
   - Shows deployment progress and test results
   - Displays container logs for debugging
   - Provides rollback instructions if needed

### Why This Process
- **GitHub as Source of Truth**: All changes go through GitHub first
- **Consistent Deployment**: Same process works for all changes
- **Automatic Testing**: Verifies the deployment worked correctly
- **Docker Integration**: Handles container updates seamlessly

## Implementation Guide

### Example: Topic Model Updates
```python
# Before (Sprint 3 and earlier)
class GrammarConfig(BaseModel):
    enabled: bool = Field(default=False)
    file: Optional[str] = Field(default=None)

class Topic(BaseModel):
    name: str
    grammar: GrammarConfig = Field(default_factory=GrammarConfig)

# After (Sprint 4)
class Topic(BaseModel):
    name: str
    backend_id: Optional[str] = Field(default=None, description="Linked backend for dynamic grammar")
    # Remove or deprecate GrammarConfig for linked topics
```

### Example: Updated Generation Logic
```python
# Before (Sprint 3 and earlier)
if not grammar_file and topic.grammar.enabled and topic.grammar.file:
    grammar_path = os.path.join(os.path.dirname(__file__), "..", "data", "grammars", topic.grammar.file)
    if os.path.exists(grammar_path):
        grammar_file = grammar_path

# After (Sprint 4)
if topic.backend_id:
    # Use backend-generated grammar
    backend = backend_manager.get_backend(topic.backend_id)
    if not backend:
        raise HTTPException(status_code=404, detail=f"Linked backend '{topic.backend_id}' not found")

    grammar_file = backend_grammar_generator.get_grammar_file_path(topic.backend_id)
    if not grammar_file.exists():
        # Auto-generate grammar if missing
        result = backend_grammar_generator.generate_and_save_grammar(topic.backend_id)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=f"Failed to generate grammar: {result['error']}")

    grammar_file = str(grammar_file)
    logger.info(f"Using backend grammar for topic '{topic_id}': {grammar_file}")
else:
    raise HTTPException(status_code=400, detail="Topic must be linked to a backend for grammar-constrained generation")
```

### Example: UI Updates

**CRITICAL**: The topic configuration UI has TWO sections. Only ONE gets replaced.

**Current UI Structure (Before Sprint 4):**
```html
<!-- SECTION 1: Grammar Configuration - REMOVE THIS ENTIRE SECTION -->
<div class="grammar-configuration">
    <h3>Grammar Configuration</h3>
    <label>
        <input type="checkbox" name="grammar_enabled" v-model="topic.grammar.enabled">
        Enable Grammar
    </label>
    <select name="grammar_file" v-model="topic.grammar.file">
        <option value="">No Grammar</option>
        <option value="default.gbnf">Default Grammar</option>
        <option value="set_temp.gbnf">Temperature Grammar</option>
        <option value="static_actions.gbnf">Static Actions</option>
    </select>
</div>

<!-- SECTION 2: Dispatcher - KEEP THIS UNCHANGED -->
<div class="dispatcher-configuration">
    <h3>Dispatcher</h3>
    <select name="dispatcher" v-model="topic.dispatcher">
        <option value="">No Dispatcher</option>
        <option value="homeassistant">Home Assistant</option>
    </select>
</div>
```

**New UI Structure (After Sprint 4):**
```html
<!-- NEW SECTION 1: Backend Configuration - REPLACES GRAMMAR SECTION -->
<div class="backend-configuration">
    <h3>Backend Configuration</h3>
    <select name="backend_id" v-model="topic.backend_id" @change="onBackendChange">
        <option value="">Select Backend...</option>
        <!-- This will be populated with actual backend from API -->
        <option value="homeassistant_8ca84424">Test HA Backend (30 devices, 1 enabled)</option>
        <option value="create_new">+ Create New Backend</option>
    </select>

    <div class="backend-status" v-if="topic.backend_id && backendInfo">
        <h4>Backend Status</h4>
        <p>Connection: {{ backendInfo.status.connected ? '✅ Connected' : '❌ Disconnected' }}</p>
        <p>Devices: {{ backendInfo.statistics.total_devices }} total,
           {{ backendInfo.statistics.enabled_devices }} enabled</p>
        <p>Device Types: {{ backendInfo.device_types.join(', ') }}</p>
        <p>Locations: {{ backendInfo.locations.join(', ') }}</p>
        <p>Grammar: {{ grammarGenerated ? '✅ Generated' : '⚠️ Not Generated' }}</p>
        <div class="backend-actions">
            <a :href="'/backends/' + topic.backend_id" class="btn">Configure Backend</a>
            <a :href="'/backends/' + topic.backend_id + '/test-grammar'" class="btn">Test Grammar</a>
        </div>
    </div>
</div>

<!-- SECTION 2: Dispatcher - UNCHANGED FROM BEFORE -->
<div class="dispatcher-configuration">
    <h3>Dispatcher</h3>
    <select name="dispatcher" v-model="topic.dispatcher">
        <option value="">No Dispatcher</option>
        <option value="homeassistant">Home Assistant</option>
    </select>
</div>
```

**Summary of Changes:**
- ❌ **REMOVE**: Grammar Configuration section (enable checkbox + file dropdown)
- ✅ **ADD**: Backend Configuration section (backend dropdown + status display)
- ✅ **KEEP**: Dispatcher section (stays exactly the same)

## API Endpoints to Implement

### New Topic-Backend Integration Endpoints
```python
@app.put("/api/topics/{topic_id}/backend", tags=["Topics"])
async def link_topic_to_backend(topic_id: str, request: Request) -> Dict[str, Any]:
    """Link a topic to a backend for dynamic grammar generation."""

@app.get("/api/topics/{topic_id}/backend", tags=["Topics"])
async def get_topic_backend(topic_id: str) -> Dict[str, Any]:
    """Get backend information for a topic."""

@app.delete("/api/topics/{topic_id}/backend", tags=["Topics"])
async def unlink_topic_from_backend(topic_id: str) -> Dict[str, Any]:
    """Unlink a topic from its backend."""
```

### Updated Existing Endpoints
```python
@app.get("/api/topics/{topic_id}", tags=["Topics"])
async def get_topic(topic_id: str) -> Dict[str, Any]:
    """Get topic with backend information included."""
    # Include backend details and grammar status in response
```

## Files to Review First

### Sprint 4 Core Files
1. **Sprint 4 Specification**: `SPRINT_4_TOPIC_BACKEND_INTEGRATION.md`
2. **Topic Model**: `/orac/topic_models/topic.py` - Current topic structure
3. **Topic Manager**: `/orac/topic_manager.py` - Topic CRUD operations
4. **Topic Configuration UI**: `/orac/templates/topic_config.html` - Current UI
5. **API Generation Logic**: `/orac/api.py` lines 610-750 - Current grammar selection

### Sprint 3 Reference Files
1. **Backend Grammar Generator**: `/orac/backend_grammar_generator.py` - Grammar generation logic
2. **Backend Manager**: `/orac/backend_manager.py` - Backend CRUD operations
3. **Backend Testing UI**: `/orac/templates/backend_grammar_test.html` - UI reference

## Implementation Order

### Day 1-2: Core Integration
1. Update Topic model with `backend_id` field
2. Update TopicManager for backend linkage operations
3. Update API generation logic to use backend grammars
4. Add basic error handling for missing backends

### Day 3-4: UI Transformation
1. Replace grammar dropdown with backend selection in topic config UI
2. Add backend status display and statistics
3. Implement "Create New Backend" workflow from topic configuration
4. Add real-time backend validation

### Day 5-6: Auto-Regeneration and Polish
1. Integrate grammar auto-regeneration with backend saves
2. Add comprehensive error handling and validation
3. Remove deprecated static grammar components
4. Update all references and documentation

### Day 7-8: Testing and Deployment
1. Test end-to-end topic-backend integration
2. Verify grammar auto-generation and command processing
3. Test error scenarios (offline backends, empty backends)
4. Deploy and verify on Orin Nano

## Success Criteria

By the end of Sprint 4, you should be able to:
1. ✅ Create a topic and link it to an existing backend through the UI
2. ✅ Create a new backend directly from topic configuration
3. ✅ Generate text using backend-generated grammar instead of static files
4. ✅ **Test "turn on the lounge lights" through a topic linked to a backend**
5. ✅ See grammar automatically regenerate when backend device mappings change
6. ✅ Handle backend errors gracefully with clear user feedback
7. ✅ Navigate seamlessly between topic and backend management interfaces
8. ✅ Confirm complete removal of static grammar selection from topics

## Testing Checklist

### Sprint 4 Manual Testing
- [ ] **Deploy to Orin**: Use `./deploy_and_test.sh "Sprint 4 implementation"`
- [ ] **SSH to Orin**: Use `ssh orin4` to access the Orin Nano
- [ ] **Create Backend**: Create or verify existing Home Assistant backend with configured devices
- [ ] **Link Topic**: Navigate to `/topics/{topic_id}` and link to backend via dropdown
- [ ] **Test Generation**: Send "turn on the lounge lights" to linked topic
- [ ] **Verify Grammar**: Confirm topic uses `backend_{id}.gbnf` not `default.gbnf`
- [ ] **Test Auto-Regen**: Change backend device mappings, verify grammar updates
- [ ] **Error Handling**: Test behavior with offline/deleted/empty backends
- [ ] **UI Verification**: Confirm no static grammar dropdowns remain in topic config

### Automated Testing
```bash
# After implementation, run tests on Jetson
ssh orin4
docker exec -it orac pytest tests/test_topic_backend_integration.py
```

## Deployment Command

### Deployment Commands

**Deploy Sprint 4 Implementation**:
```bash
cd "/Users/2oby/pCloud Box/Projects/ORAC/Orac-Omniscient-Reactive-Algorithmic-Core"
./deploy_and_test.sh "Sprint 4: Topic-Backend integration with dynamic grammar"
```

**Test Topic-Backend Integration on Orin**:
```bash
# SSH into the Orin Nano
ssh orin4

# Test the integrated system
curl -X POST http://192.168.8.192:8000/v1/generate/home_assistant \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "turn on the lounge lights",
    "json_mode": true
  }'

# Expected: Uses backend grammar, returns constrained JSON
```

## Visual Goal

By sprint end, the topic configuration interface should look like:
```
╔════════════════════════════════════════════════════════════════════════╗
║ TOPIC CONFIGURATION - Home Assistant                                   ║
╠════════════════════════════════════════════════════════════════════════╣
║                                                                        ║
║ BACKEND SELECTION                                                      ║
║ ┌──────────────────────────────────────────────────────────────────┐   ║
║ │ Home Assistant (homeassistant) - 15 devices               ▼     │   ║
║ │ + Create New Backend                                           │   ║
║ └──────────────────────────────────────────────────────────────────┘   ║
║                                                                        ║
║ BACKEND STATUS                                                         ║
║ • Devices: 30 total, 15 enabled, 12 mapped                           ║
║ • Grammar: ✅ Generated (3 device types, 4 locations)                ║
║ • Last Updated: 2024-01-01 10:30:00                                  ║
║                                                                        ║
║ [Configure Backend] [Test Grammar] [Regenerate Grammar]               ║
║                                                                        ║
║ MODEL SETTINGS                                                         ║
║ Model: llama-3.2-3b-instruct.gguf                                    ║
║ Temperature: 0.1    Top-P: 0.9    Max Tokens: 500                   ║
║                                                                        ║
║ No static grammar dropdown - removed in Sprint 4!                     ║
╚════════════════════════════════════════════════════════════════════════╝
```

## Questions to Answer During Implementation

1. Should topics show real-time backend connectivity status?
2. How should we handle topics when their linked backend is temporarily offline?
3. Should we cache backend information in topic configuration for performance?
4. What's the best UX for the "Create New Backend" flow from topic config?
5. Should we show grammar generation progress/status in topic interface?

## The Four Missing Pieces Explained

Sprint 4 requires implementing four interconnected pieces. Here's what each one means:

### 1. Topic Model Has No `backend_id` Field
**Current**: Topic model in `/orac/topic_models/topic.py` has no way to reference a backend
**Needed**: Add `backend_id: Optional[str] = Field(default=None)` to Topic class
**Impact**: Without this, topics can't be linked to backends at the data model level

### 2. Topic Config UI Still Shows Static Grammar Dropdown
**Current**: UI at `/orac/templates/topic_config.html` has grammar file dropdown
**Needed**: Replace grammar section with backend selection dropdown
**Impact**: Users can't select backends through the UI, only static grammar files

### 3. Generation Logic Doesn't Check for Backend-Linked Topics
**Current**: `/orac/api.py` generation endpoint only looks for `topic.grammar.file` (static)
**Needed**: Check if `topic.backend_id` exists and use `backend_{id}.gbnf` grammar
**Impact**: Even if backend_id is set, system won't use backend-generated grammar

### 4. No API Endpoints to Link Topics to Backends
**Current**: No endpoints like `PUT /api/topics/{id}/backend` exist
**Needed**: Add endpoints to create/read/delete topic-backend relationships
**Impact**: Frontend JavaScript can't save backend selection or fetch backend info

**All four pieces must work together**: Model holds the data, UI lets user select it, API saves it, generation logic uses it.

## Sprint 4 Summary

**Primary Goal**: Replace static grammar system with dynamic backend-driven grammar selection for topics.

**Success Test**: Send "turn on the lounge lights" to a topic linked to a backend and receive constrained JSON output using the backend's auto-generated grammar file.

**Infrastructure**: Deploy and test on the NVIDIA Orin Nano using:
1. `deploy_and_test.sh` commits to GitHub and deploys to Orin
2. `ssh orin4` provides access to the Orin Nano
3. ORAC Core runs in Docker container at http://192.168.8.192:8000

## Important Notes

1. **Backend Focus**: All grammar generation now comes from backend device mappings
2. **No Static Fallbacks**: Topics must link to backends - no fallback to static grammar files
3. **Auto-Regeneration**: Grammar updates automatically when device configurations change
4. **Error Handling**: Clear feedback when backends are unavailable or empty
5. **Deployment**: Always use `deploy_and_test.sh` → GitHub → Orin workflow

---

Good luck with Sprint 4! The main goal is to create a seamless integration where topics automatically get grammar constraints from real device configurations, eliminating the need for manual grammar file management.