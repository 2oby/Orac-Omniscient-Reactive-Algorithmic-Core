# Sprint 3 Implementation Prompt for Next Session

## IMPORTANT: Sprint 2 Status - COMPLETED ✅
Sprint 2 is now fully implemented and working:
1. ✅ Device fetching from Home Assistant (30 devices)
2. ✅ Manual enable/disable of devices via card interface
3. ✅ Drag-and-drop device type assignment (lights, heating, blinds, etc.)
4. ✅ Drag-and-drop location assignment (lounge, bedroom, kitchen, etc.)
5. ✅ Save configuration functionality
6. ✅ Device validation and search/filter

Sprint 2 creates a **curated device registry** where users manually configure which devices are active and assign them types and locations.

## Context for Sprint 3
You are implementing Sprint 3 of the ORAC Core system. ORAC Core runs on an **NVIDIA Orin Nano** (hostname: `orin4`) at IP `192.168.8.192`. Sprint 2 is complete - users can now:
- Fetch devices from Home Assistant
- Enable/disable devices manually
- Assign device types (lights, heating, blinds, music)
- Assign locations (bedroom, kitchen, lounge, etc.)
- Save these configurations

Sprint 3's goal is to **generate GBNF grammar from these device mappings** to constrain the LLM so it can only output JSON for devices the user has actually configured.

## Your Mission
Implement Sprint 3: **Dynamic Grammar Generation** from Sprint 2's device mappings. The primary goal is to generate GBNF grammars that constrain the LLM to only output JSON for devices the user has actually enabled and configured.

**Key Concept**: If user only configured a light in the lounge and heating in the bedroom, the grammar should ONLY allow those combinations and block everything else.

**End Goal**: Test command "turn on the lounge lights" through ORAC Core's LLM and verify it generates valid JSON like `{"device":"lights","action":"on","location":"lounge"}` using the dynamically generated grammar.

## Current System State
- **Completed**:
  - ✅ Backend management with full CRUD operations
  - ✅ Entity fetching and configuration from Home Assistant
  - ✅ Entity enable/disable with friendly names and aliases
  - ✅ Deployed to Jetson Orin at 192.168.8.192

- **Existing Infrastructure**:
  - `HomeAssistantGrammarManager` in `/orac/homeassistant/grammar_manager.py`
  - Dispatcher registry system in `/orac/dispatchers/`
  - Backend data stored in `/data/backends/{backend_id}.json`
  - Topic management system operational

## Sprint 3 Primary Goal: Dynamic Grammar Generation

By the end of Sprint 3, the system should:
- Generate GBNF grammar files based on Sprint 2's device mappings
- Constrain LLM to only output JSON for configured devices
- Provide grammar testing interface
- Link topics to backend-generated grammars
- Block invalid device/location combinations at grammar level

## Key Implementation Tasks

### Priority 1: Backend Grammar Generator
1. Create `BackendGrammarGenerator` class in `/orac/backend_grammar_generator.py`
2. Read Sprint 2 device mappings (enabled devices with device_type + location)
3. Generate dynamic GBNF grammar based on `/data/grammars/default.gbnf` template
4. Extract unique device types and locations from user configuration
5. Create constraint-based grammar that only allows configured combinations

### Priority 2: Grammar Generation Logic
**Template**: Based on existing `/data/grammars/default.gbnf`
```gbnf
root ::= "{\"device\":\"" device "\",\"action\":\"" action "\",\"location\":\"" location "\"}"
# Dynamic rules generated from Sprint 2 mappings:
device ::= "lights" | "heating" | "blinds" | "UNKNOWN"  # Only configured device_types
location ::= "lounge" | "bedroom" | "kitchen" | "UNKNOWN"  # Only configured locations
# Static action rules (same as default.gbnf):
action ::= "on" | "off" | "toggle" | "set 50%" | "warm" | "cold" | ...
```

### Priority 3: Grammar Testing Interface
1. Create grammar test console at `/backends/{id}/test-grammar`
2. Test commands like "turn on the lounge lights"
3. Show if grammar allows/blocks the command
4. Display which specific device mapping will be used
5. Show generated JSON output

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

# Check grammar files
docker exec orac ls -la /app/data/grammars/

# View backend configurations
docker exec orac ls -la /app/data/backends/
```

## Deployment Process

### The Deploy Script
The `deploy_and_test.sh` script handles the complete deployment workflow from your Mac to the Orin Nano:

```bash
cd "/Users/2oby/pCloud Box/Projects/ORAC/Orac-Omniscient-Reactive-Algorithmic-Core"
./deploy_and_test.sh "Sprint 3: Dynamic grammar generation"
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

## Grammar Generation Implementation Guide

### Example: Sprint 2 Device Mappings
```json
{
  "switch.lounge_lamp": {
    "enabled": true,
    "device_type": "lights",
    "location": "lounge"
  },
  "climate.bedroom_thermostat": {
    "enabled": true,
    "device_type": "heating",
    "location": "bedroom"
  },
  "cover.kitchen_blinds": {
    "enabled": true,
    "device_type": "blinds",
    "location": "kitchen"
  }
}
```

### Generated Grammar Output
```gbnf
root ::= "{\"device\":\"" device "\",\"action\":\"" action "\",\"location\":\"" location "\"}"

# Generated from user's configured device_types only
device ::= "lights" | "heating" | "blinds" | "UNKNOWN"

# Generated from user's configured locations only
location ::= "lounge" | "bedroom" | "kitchen" | "UNKNOWN"

# Standard action rules (copied from default.gbnf)
action ::= "on" | "off" | "toggle" | "open" | "close" | "set 50%" | "warm" | "cold" | "UNKNOWN" | set-action | set-temp-action
pct ::= "0%" | "10%" | "20%" | ... | "100%"
temp ::= "5C" | "6C" | ... | "30C"
set-action ::= "set " pct
set-temp-action ::= "set " temp
```

### API Endpoints Needed
```python
# Generate grammar from backend device mappings
POST /api/backends/{id}/grammar/generate

# Get generated grammar file
GET /api/backends/{id}/grammar

# Test command against backend's grammar
POST /api/backends/{id}/grammar/test
Body: {
  "command": "turn on the lounge lights"
}

# Get grammar generation status
GET /api/backends/{id}/grammar/status
```

### Grammar Testing Interface
```javascript
// Test command against generated grammar
async function testCommand() {
  const command = document.getElementById('test-command').value;
  const response = await fetch(`/api/backends/${backendId}/grammar/test`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({command})
  });

  const result = await response.json();

  if (result.valid) {
    showResult(`✅ Valid: ${JSON.stringify(result.parsed_json)}`);
    showMappedDevice(result.device_mapping);
  } else {
    showResult(`❌ Invalid: ${result.error}`);
  }
}
```

## Files to Review First

### Sprint 2 Testing
1. **SPRINT_2_TEST.md** - Complete testing guide for Sprint 2
2. **SPRINT_2_TEST.md#troubleshooting** - If anything doesn't work

### Sprint 3 Implementation
1. **Sprint 3 Specification**: `/SPRINT_3_GRAMMAR_DISPATCHER_INTEGRATION.md`
2. **Backend Manager**: `/orac/backend_manager.py` - Understand entity storage
3. **Grammar Manager**: `/orac/homeassistant/grammar_manager.py` - Existing grammar generation
4. **Backend Entities Page**: `/orac/templates/backend_entities.html` - Current entity UI
5. **Home Assistant Client**: `/orac/homeassistant/client.py` - HA API integration

## Implementation Order

### Day 0: Sprint 2 Testing (MUST DO FIRST)
1. Follow `SPRINT_2_TEST.md` completely
2. Create and configure a Home Assistant backend
3. Fetch and configure entities
4. Document any issues found
5. Fix any bugs before proceeding

### Day 1-2: Backend Grammar Generator
1. Create `BackendGrammarGenerator` class
2. Read Sprint 2 device mappings from backend JSON files
3. Extract unique device_types and locations from enabled devices
4. Generate dynamic GBNF grammar based on default.gbnf template

### Day 3-4: Grammar Generation Logic
1. Implement device and location rule generation
2. Copy action rules from existing default.gbnf
3. Add grammar validation and error handling
4. Store generated grammars in `/data/grammars/backend_{id}.gbnf`

### Day 5-6: Grammar Testing Interface
1. Create test console template at `/backends/{id}/test-grammar`
2. Implement command testing against generated grammar
3. Show JSON parsing results and device mappings
4. Display grammar generation status and statistics

### Day 7-8: Topic Integration & Polish
1. Link topics to backend-generated grammars
2. Add grammar regeneration on device mapping changes
3. Implement grammar caching and performance optimization
4. Test end-to-end grammar constraint functionality

## Success Criteria

By the end of Sprint 3, you should be able to:
1. ✅ Generate GBNF grammar dynamically from Sprint 2 device mappings
2. ✅ Constrain ORAC Core's LLM to only output JSON for configured device/location combinations
3. ✅ **Test "turn on the lounge lights" through ORAC Core and get valid JSON response**
4. ✅ Verify grammar blocks invalid commands (e.g., "kitchen heating" if not configured)
5. ✅ Link topics to backend-generated grammars
6. ✅ Deploy and test on the Orin Nano using `deploy_and_test.sh`
7. ✅ Demonstrate end-to-end LLM constraint functionality working on ORAC Core

## Testing Checklist

### Sprint 2 Status (✅ COMPLETED)
- [✅] Home Assistant backend created and working
- [✅] Device fetching working (30 devices)
- [✅] Enable/disable functionality working
- [✅] Device type assignment via drag-and-drop working
- [✅] Location assignment via drag-and-drop working
- [✅] Save configuration working
- [✅] Search/filter functionality working

### Sprint 3 Manual Testing
- [ ] **Deploy to Orin**: Use `./deploy_and_test.sh "Sprint 3 implementation"`
- [ ] **SSH to Orin**: Use `ssh orin4` to access the Orin Nano
- [ ] **Generate Grammar**: Navigate to `/backends/{id}/test-grammar` and generate grammar
- [ ] **Test Valid Command**: "turn on the lounge lights" (should work if configured)
- [ ] **Test Invalid Command**: "turn on kitchen heating" (should fail if not configured)
- [ ] **Verify Grammar Rules**: Check generated grammar only contains configured device types/locations
- [ ] **Test ORAC Core LLM**: Send "turn on the lounge lights" to ORAC Core's LLM endpoint
- [ ] **Verify JSON Output**: Confirm LLM returns `{"device":"lights","action":"on","location":"lounge"}`
- [ ] **Test Grammar Constraint**: Verify invalid commands are blocked at grammar level

### Automated Testing
```bash
# After implementation, run tests on Jetson
ssh orin4
docker exec -it orac pytest tests/test_backend_grammar_generator.py
docker exec -it orac pytest tests/test_grammar_constraints.py
```

## Deployment Command

### Deployment Commands

**Deploy Sprint 3 Implementation**:
```bash
cd "/Users/2oby/pCloud Box/Projects/ORAC/Orac-Omniscient-Reactive-Algorithmic-Core"
./deploy_and_test.sh "Sprint 3: Dynamic grammar generation from device mappings"
```

**Test Grammar on Orin**:
```bash
# SSH into the Orin Nano
ssh orin4

# Test the ORAC Core LLM endpoint with generated grammar
curl -X POST http://192.168.8.192:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "turn on the lounge lights"}],
    "grammar": "backend_homeassistant_123.gbnf"
  }'

# Expected response: {"device":"lights","action":"on","location":"lounge"}
```

## Visual Goal

By sprint end, the grammar testing interface should look like:
```
╔════════════════════════════════════════════════════════════════════════╗
║ GRAMMAR TESTING - Home Assistant Backend                               ║
╠════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║ CONFIGURED DEVICES (from Sprint 2)                                     ║
║ • switch.lounge_lamp → lights + lounge                               ║
║ • climate.bedroom_thermostat → heating + bedroom                       ║
║ • cover.kitchen_blinds → blinds + kitchen                             ║
║                                                                          ║
║ GENERATED GRAMMAR RULES                                                 ║
║ device ::= "lights" | "heating" | "blinds" | "UNKNOWN"                 ║
║ location ::= "lounge" | "bedroom" | "kitchen" | "UNKNOWN"               ║
║                                                                          ║
║ TEST COMMAND                                                            ║
║ ┌──────────────────────────────────────────────────────────────────┐ ║
║ │ turn on the lounge lights                                      │ ║
║ └──────────────────────────────────────────────────────────────────┘ ║
║                                                                          ║
║ [TEST COMMAND] [REGENERATE GRAMMAR]                                    ║
║                                                                          ║
║ RESULT                                                                  ║
║ ✅ VALID - Grammar allows this command                                ║
║ Generated JSON:                                                         ║
║ {"device":"lights","action":"on","location":"lounge"}               ║
║ Maps to: switch.lounge_lamp                                             ║
║                                                                          ║
║ Try invalid: "turn on kitchen heating" → ❌ BLOCKED (not configured)   ║
╚════════════════════════════════════════════════════════════════════════╝
```

## Sprint 2 Prerequisites

### Home Assistant Access Requirements
1. **URL**: Your HA instance at `http://192.168.8.99:8123`
2. **Token**: Get from HA Profile → Long-Lived Access Tokens → Create Token
3. **Access**: Ensure Jetson can reach HA (same network)

### Quick Sprint 2 Test Commands
```bash
# Check if Sprint 2 is deployed
curl http://192.168.8.192:8000/api/backends

# SSH to Orin to check logs if needed
ssh orin4
docker logs orac --tail 50

# Check backend data files
docker exec -it orac ls -la /app/data/backends/
```

## Sprint 3 Summary

**Primary Goal**: Generate dynamic GBNF grammar from Sprint 2's device mappings to create a **constrained ORAC Core LLM** that can only output JSON for devices the user has actually configured.

**Success Test**: Send "turn on the lounge lights" to ORAC Core's LLM and receive `{"device":"lights","action":"on","location":"lounge"}` as a valid JSON response using the dynamically generated grammar.

**Infrastructure**: Deploy and test on the NVIDIA Orin Nano using:
1. `deploy_and_test.sh` commits to GitHub and deploys to Orin
2. `ssh orin4` provides access to the Orin Nano
3. ORAC Core runs in Docker container at http://192.168.8.192:8000

## Important Notes

1. **Grammar Focus**: Base generation on existing `/data/grammars/default.gbnf` structure
2. **Device Types**: Only include device_types from enabled Sprint 2 devices
3. **Locations**: Only include locations from enabled Sprint 2 devices
4. **LLM Testing**: The ultimate test is ORAC Core LLM producing valid JSON
5. **Deployment**: Always use `deploy_and_test.sh` → GitHub → Orin workflow

## Questions to Answer During Implementation

1. How many entities should load at once in tile view?
2. Should tiles auto-refresh or require manual refresh?
3. How to handle entities that go offline?
4. Should grammar regenerate automatically on entity changes?
5. What's the optimal tile size for different screen sizes?

---

Good luck with Sprint 3! The main goal is to create a visual, interactive dashboard showing Home Assistant entities as tiles that can be controlled directly from the ORAC interface.