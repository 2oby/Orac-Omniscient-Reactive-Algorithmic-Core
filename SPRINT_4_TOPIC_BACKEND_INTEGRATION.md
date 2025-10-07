# Sprint 4: Topic ↔ Backend Integration

## IMPORTANT: Sprint 3 Status - COMPLETED ✅
Sprint 3 is now fully implemented and working:
1. ✅ BackendGrammarGenerator class for dynamic grammar generation
2. ✅ API endpoints for grammar generation and testing
3. ✅ Grammar testing interface at `/backends/{id}/test-grammar`
4. ✅ GBNF grammar generation from device mappings
5. ✅ Command validation against generated grammars
6. ✅ Deployed and committed to GitHub (commit 171ffd8)

Sprint 3 creates **dynamic GBNF grammars** from Sprint 2's device mappings, constraining the LLM to only output JSON for devices the user has actually configured.

## Current System Status (Pre-Sprint 4)

### Existing Backend Configuration
- **Backend ID**: `homeassistant_8ca84424`
- **Name**: "Test HA Backend"
- **Status**: ✅ Connected to Home Assistant at http://192.168.8.99:8123
- **Devices**: 30 total fetched from HA
- **Configured Devices**: 1 enabled and mapped
  - `switch.tretakt_smart_plug` (Lounge Lamp Plug)
    - device_type: "lights"
    - location: "lounge"
    - state: off

### Existing Topics
Three topics currently exist:
1. **"computa"** (lowercase)
   - Uses static grammar: `enabled: true, file: "default.gbnf"`
   - Has dispatcher: "homeassistant"
   - Active with 181 trigger counts

2. **"general"**
   - No grammar enabled
   - Has dispatcher: "homeassistant"

3. **"Computa"** (capitalized)
   - No grammar enabled
   - No dispatcher

### Current Topic Configuration UI
The topic configuration page at `/topics/{topic_id}` currently shows:
- **Grammar Configuration Section**: Dropdown to select static grammar files (default.gbnf, set_temp.gbnf, etc.)
- **Dispatcher Selection**: Dropdown to select dispatcher (homeassistant, etc.)

**IMPORTANT**: Sprint 4 will REPLACE the grammar dropdown with a backend selection dropdown. The dispatcher dropdown stays but becomes linked to the selected backend.

## Context for Sprint 4
You are implementing Sprint 4 of the ORAC Core system. ORAC Core runs on an **NVIDIA Orin Nano** (hostname: `orin4`) at IP `192.168.8.192`. Sprint 3 is complete - the system can now:
- Generate GBNF grammars dynamically from backend device mappings
- Test commands against generated grammars
- Constrain LLM output to only configured device/location combinations
- Cache generated grammars for performance

Sprint 4's goal is to **integrate Topics with Backend Grammar Generation** and **deprecate the static grammar system** to create a unified, dynamic grammar architecture.

## Your Mission
Implement Sprint 4: **Topic ↔ Backend Integration** to replace the static grammar system with backend-driven dynamic grammar generation. The primary goal is to link topics to backends so that grammar constraints are automatically generated from actual device configurations.

**Key Concept**: Topics should use backend-generated grammars instead of static grammar files. When a user configures devices in a backend, any topics linked to that backend automatically get updated grammar constraints.

**End Goal**: Test command "turn on the lounge lights" through a topic linked to a backend and verify it uses the backend's dynamically generated grammar instead of static `default.gbnf`.

## Current System State
- **Completed**:
  - ✅ Backend management with full CRUD operations (Sprint 2)
  - ✅ Dynamic grammar generation from device mappings (Sprint 3)
  - ✅ Grammar testing and validation (Sprint 3)
  - ✅ Topic management system with static grammar selection

- **Current Topic System (To Be Modified)**:
  - Topics have `GrammarConfig` with static file selection
  - Manual selection of `default.gbnf`, `set_temp.gbnf`, etc.
  - No connection to actual device configurations
  - Grammar dropdown in topic configuration UI

## Sprint 4 Primary Goal: Dynamic Topic-Backend Integration

By the end of Sprint 4, the system should:
- Link topics to backends for automatic grammar generation
- Eliminate static grammar file selection from topics
- Auto-regenerate grammar when backend device mappings change
- Show backend status in topic configuration
- Provide unified grammar testing through topics
- Remove deprecated static grammar components

## Key Implementation Tasks

### Priority 1: Topic Model Updates
1. **Update Topic Model** in `/orac/topic_models/topic.py`
   - Add `backend_id: Optional[str]` field to link topic to backend
   - Remove or deprecate `GrammarConfig` class
   - Add backend-related status fields
   - Ensure backward compatibility during transition

2. **Update Topic Manager** in `/orac/topic_manager.py`
   - Handle backend linkage in topic CRUD operations
   - Validate backend exists when linking
   - Add methods for backend-topic relationship management

### Priority 2: Grammar Selection Logic Overhaul
1. **Update Generation Logic** in `/orac/api.py`
   - Replace static grammar selection with backend grammar lookup
   - Use `backend_{topic.backend_id}.gbnf` when topic has linked backend
   - Remove fallbacks to static grammar files for linked topics
   - Add error handling for missing/offline backends

2. **Auto-Grammar Regeneration**
   - Trigger grammar regeneration when backend device mappings change
   - Update `BackendManager.save_backend()` to regenerate grammar
   - Ensure all linked topics get updated grammar automatically

### Priority 3: Topic Configuration UI Updates

**CRITICAL UI CHANGE**: The topic configuration page currently has TWO separate sections:
1. **Grammar Configuration** - Dropdown with static grammar files (default.gbnf, etc.) → **REMOVE THIS**
2. **Dispatcher Selection** - Dropdown with dispatchers (homeassistant, etc.) → **KEEP THIS**

Sprint 4 will **REPLACE** the Grammar Configuration section with a new **Backend Selection** section.

**Current UI Structure:**
```
┌─────────────────────────────────────┐
│ Grammar Configuration               │  ← REMOVE THIS ENTIRE SECTION
│ • Enable Grammar: [✓]               │
│ • Grammar File: [default.gbnf ▼]    │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Dispatcher                          │  ← KEEP THIS (dispatcher stays)
│ • Select: [homeassistant ▼]         │
└─────────────────────────────────────┘
```

**New UI Structure (Sprint 4):**
```
┌─────────────────────────────────────────────────┐
│ Backend Configuration                           │  ← NEW SECTION (replaces grammar)
│ • Select Backend: [Test HA Backend ▼]          │
│ • Status: ✅ Connected (30 devices, 1 enabled) │
│ • Device Types: lights                         │
│ • Locations: lounge                            │
│ • Grammar: ✅ Generated                        │
│ [Configure Backend] [Test Grammar]              │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Dispatcher                          │  ← UNCHANGED (dispatcher stays)
│ • Select: [homeassistant ▼]         │
└─────────────────────────────────────┘
```

**Implementation Tasks:**

1. **Update Topic Configuration Page** `/orac/templates/topic_config.html`
   - **REMOVE**: Grammar Configuration section (grammar enable checkbox, grammar file dropdown)
   - **ADD**: Backend Selection section with backend dropdown
   - **KEEP**: Dispatcher selection (this stays as-is)
   - Add "Create New Backend" option in backend dropdown
   - Show linked backend status and statistics
   - Add direct link to backend configuration page

2. **Backend Selection Logic**
   - Populate dropdown with available backends
   - Show backend name, type, and device count
   - Allow creation of new backend from topic configuration
   - Validate backend compatibility with topic
   - Auto-populate dispatcher based on backend type (optional)

### Priority 4: Deprecation and Cleanup
1. **Identify Deprecated Components**
   - `GrammarConfig` class (if not used elsewhere)
   - Static grammar file selection logic in topics
   - Grammar file dropdown UI components
   - Hardcoded references to `default.gbnf`, `set_temp.gbnf` in topic context

2. **Remove Deprecated Functionality**
   - Clean up unused grammar selection code
   - Remove static grammar UI elements
   - Update error messages to reflect new backend-driven approach
   - Clean up unused imports and references

### Priority 5: Error Handling and Validation
1. **Backend Validation**
   - Check backend exists when topic is used for generation
   - Handle deleted/offline backends gracefully
   - Show clear error messages when backend is unavailable
   - Prevent generation when backend has no configured devices

2. **Grammar Validation**
   - Ensure backend has generated grammar before topic use
   - Trigger grammar generation if needed
   - Handle empty backends (no enabled devices)

## ORAC Core Infrastructure

### NVIDIA Orin Nano Setup
ORAC Core runs on an **NVIDIA Orin Nano** device with these details:
- **Hostname**: `orin4`
- **IP Address**: `192.168.8.192`
- **Web Interface**: http://192.168.8.192:8000
- **Container**: ORAC runs in Docker container named `orac`
- **SSH Access**: Use `ssh orin4` (pre-configured alias on your Mac)

### Deployment Process
The `deploy_and_test.sh` script handles the complete deployment workflow:

```bash
cd "/Users/2oby/pCloud Box/Projects/ORAC/Orac-Omniscient-Reactive-Algorithmic-Core"
./deploy_and_test.sh "Sprint 4: Topic-Backend integration"
```

## Implementation Workflow

### New Topic Configuration Flow
1. **User visits `/topics/{topic_id}` configuration page**
2. **Backend Selection Section shows:**
   - Dropdown with available backends (name, type, device count)
   - "Create New Backend" option
   - Current backend status (if linked)
3. **When backend is selected:**
   - Topic links to backend
   - Grammar automatically generated from backend device mappings
   - Grammar statistics shown in topic interface
4. **When "Create New Backend" is selected:**
   - Modal/redirect to backend creation flow
   - Return to topic configuration with new backend pre-selected

### Grammar Generation Integration
```python
# Topic generation flow (updated)
topic = get_topic(topic_id)
if topic.backend_id:
    # Use backend-generated grammar
    backend = backend_manager.get_backend(topic.backend_id)
    if not backend:
        raise HTTPException(404, "Linked backend not found")

    grammar_file = f"/data/grammars/backend_{topic.backend_id}.gbnf"
    if not os.path.exists(grammar_file):
        # Auto-generate grammar if missing
        backend_grammar_generator.generate_and_save_grammar(topic.backend_id)
else:
    raise HTTPException(400, "Topic must be linked to a backend")
```

### Auto-Regeneration Trigger
```python
# Updated backend save method
def save_backend(self, backend_id: str) -> bool:
    success = super().save_backend(backend_id)
    if success:
        # Auto-regenerate grammar for all linked topics
        backend_grammar_generator.regenerate_grammar_on_mapping_change(backend_id)
    return success
```

## API Updates Needed

### New Topic Endpoints
```python
# Link topic to backend
PUT /api/topics/{topic_id}/backend
Body: {"backend_id": "homeassistant_123"}

# Get topic's backend information
GET /api/topics/{topic_id}/backend

# Unlink topic from backend
DELETE /api/topics/{topic_id}/backend
```

### Updated Generation Logic
```python
# Generation with backend grammar
POST /v1/generate/{topic}
# Automatically uses linked backend's grammar
# No grammar_file parameter needed
```

## UI/UX Changes

### Topic Configuration Page Updates

**IMPORTANT**: The grammar configuration section must be REMOVED, not just hidden. The dispatcher section stays.

**Current HTML Structure to REMOVE:**
```html
<!-- REMOVE THIS ENTIRE SECTION -->
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
<!-- END REMOVE -->
```

**New HTML Structure to ADD (replaces grammar section):**
```html
<!-- ADD THIS NEW SECTION (in place of grammar configuration) -->
<div class="backend-configuration">
    <h3>Backend Configuration</h3>
    <select name="backend_id" v-model="topic.backend_id" @change="onBackendChange">
        <option value="">Select Backend...</option>
        <option value="homeassistant_8ca84424">Test HA Backend (30 devices, 1 enabled)</option>
        <option value="create_new">+ Create New Backend</option>
    </select>

    <div class="backend-status" v-if="topic.backend_id && backendInfo">
        <h4>Backend Status</h4>
        <p>Connection: {{ backendInfo.status.connected ? '✅ Connected' : '❌ Disconnected' }}</p>
        <p>Devices: {{ backendInfo.statistics.total_devices }} total,
           {{ backendInfo.statistics.enabled_devices }} enabled,
           {{ backendInfo.statistics.mapped_devices }} mapped</p>
        <p>Device Types: {{ backendInfo.device_types.join(', ') }}</p>
        <p>Locations: {{ backendInfo.locations.join(', ') }}</p>
        <p>Grammar: {{ grammarGenerated ? '✅ Generated' : '⚠️ Not Generated' }}</p>
        <div class="backend-actions">
            <a :href="'/backends/' + topic.backend_id" class="btn">Configure Backend</a>
            <a :href="'/backends/' + topic.backend_id + '/test-grammar'" class="btn">Test Grammar</a>
        </div>
    </div>
</div>
<!-- END ADD -->

<!-- KEEP THIS SECTION UNCHANGED -->
<div class="dispatcher-configuration">
    <h3>Dispatcher</h3>
    <select name="dispatcher" v-model="topic.dispatcher">
        <option value="">No Dispatcher</option>
        <option value="homeassistant">Home Assistant</option>
    </select>
</div>
<!-- END KEEP -->
```

### Topic List Page Updates
```html
<!-- Show backend linkage in topic list -->
<div class="topic-card">
    <h3>Home Assistant</h3>
    <p class="topic-backend">Backend: Home Assistant (15 devices)</p>
    <p class="topic-grammar">Grammar: ✅ 3 types, 4 locations</p>
</div>
```

## Testing Strategy

### Sprint 4 Manual Testing Checklist
- [ ] **Create New Topic**: Can select backend from dropdown
- [ ] **Link Existing Topic**: Can change backend linkage
- [ ] **Create Backend from Topic**: "Create New Backend" flow works
- [ ] **Grammar Auto-Generation**: Grammar updates when backend devices change
- [ ] **Command Generation**: Topic uses backend grammar, not static files
- [ ] **Error Handling**: Clear errors when backend is offline/deleted
- [ ] **UI Updates**: No static grammar selection visible
- [ ] **Backend Status**: Topic shows linked backend information

### Automated Testing
```bash
# Test topic-backend integration
ssh orin4
docker exec -it orac pytest tests/test_topic_backend_integration.py
```

## Success Criteria

By the end of Sprint 4, you should be able to:
1. ✅ Link topics to backends through configuration UI
2. ✅ Generate text using backend-generated grammar instead of static files
3. ✅ **Test "turn on the lounge lights" through a topic linked to a backend**
4. ✅ Auto-regenerate grammar when backend device mappings change
5. ✅ Show backend status and grammar statistics in topic interface
6. ✅ Handle backend errors gracefully (offline, deleted, empty)
7. ✅ Complete removal of static grammar selection from topics
8. ✅ Unified grammar testing through both topic and backend interfaces

## Deprecated Components to Remove

### Files/Classes to Deprecate
1. **`GrammarConfig` class** in `/orac/topic_models/topic.py` (if only used for static grammar)
2. **Static grammar selection logic** in topic configuration
3. **Grammar file dropdown UI** in `/orac/templates/topic_config.html`
4. **Hardcoded `default.gbnf` references** in topic generation logic

### Code Sections to Clean Up
1. **Topic grammar file selection** in `/orac/api.py` lines 667-689
2. **Static grammar fallback logic** for topics
3. **Grammar file validation** for static files in topic context
4. **UI elements** for grammar file selection

## Implementation Order

### Phase 1: Backend Integration (Days 1-2)
1. Update Topic model with `backend_id` field
2. Update TopicManager for backend linkage
3. Update generation logic to use backend grammar
4. Add basic error handling

### Phase 2: UI Updates (Days 3-4)
1. Update topic configuration page
2. Replace grammar dropdown with backend selection
3. Add backend status display
4. Implement "Create New Backend" flow

### Phase 3: Auto-Regeneration (Days 5-6)
1. Trigger grammar regeneration on backend save
2. Update all linked topics automatically
3. Add grammar validation and status tracking

### Phase 4: Cleanup and Testing (Days 7-8)
1. Remove deprecated static grammar components
2. Clean up unused code and UI elements
3. Test end-to-end topic-backend integration
4. Verify error handling and edge cases

## What Needs to Be Built: The Four Missing Pieces

Sprint 4 requires implementing four interconnected pieces:

### 1. ❌ Topic Model Has No `backend_id` Field
**File**: `/orac/topic_models/topic.py`
**Current State**: Topic class has `grammar: GrammarConfig` for static files
**What's Needed**: Add `backend_id: Optional[str]` field to link topics to backends
**Why It Matters**: Without this field, the data model can't represent topic-backend relationships

### 2. ❌ Topic Config UI Still Shows Static Grammar Dropdown
**File**: `/orac/templates/topic_config.html`
**Current State**: UI has "Grammar Configuration" section with file dropdown
**What's Needed**: Remove grammar section, add "Backend Configuration" section with backend dropdown
**Why It Matters**: Users need a way to select backends instead of static grammar files

### 3. ❌ Generation Logic Doesn't Check for Backend-Linked Topics
**File**: `/orac/api.py` (around lines 667-689)
**Current State**: Generation endpoint only checks `topic.grammar.file` (static)
**What's Needed**: Check if `topic.backend_id` exists and use `backend_{id}.gbnf`
**Why It Matters**: Even if UI sets backend_id, generation won't use backend grammar without this

### 4. ❌ No API Endpoints to Link Topics to Backends
**File**: `/orac/api.py` (new endpoints needed)
**Current State**: No endpoints like `PUT /api/topics/{id}/backend` exist
**What's Needed**: Add endpoints to manage topic-backend relationships
**Why It Matters**: Frontend can't save user's backend selection without these endpoints

**Integration**: All four pieces must work together:
1. Model stores `backend_id`
2. UI lets user select backend and calls API
3. API saves `backend_id` to model
4. Generation logic reads `backend_id` and uses backend grammar

## Sprint 4 Summary

**Primary Goal**: Replace static grammar system with dynamic backend-driven grammar generation for topics.

**Success Test**: Send "turn on the lounge lights" to a topic linked to a backend and receive `{"device":"lights","action":"on","location":"lounge"}` using the backend's dynamically generated grammar.

**Architecture**: Topics ↔ Backends (1:1 linkage, N:1 backend sharing) → Dynamic Grammar Generation → Constrained LLM Output

**Key Innovation**: Grammar constraints automatically update when users modify their device configurations, eliminating manual grammar management.