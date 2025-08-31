# Critical Path Implementation Plan

> **Development Setup**: For environment setup, deployment procedures, and SSH access to the Jetson Orin, see [ORAC Development Instructions](instructions.md).

## 🚀 **CURRENT PRIORITY - Complete ORAC Core Integration**

### Goal: Enable end-to-end voice command pipeline
Complete the integration so ORAC STT forwards transcribed text to ORAC Core, which generates JSON commands for Home Assistant. Test command: "Computer, turn on the bedroom lights"

### Current Implementation Status (August 31, 2025)
- ✅ Hey ORAC → ORAC STT: **WORKING** (with topics & heartbeats)
- ✅ ORAC STT: **WORKING** (transcribes audio, receives topics)
- ✅ ORAC STT → ORAC Core: **FORWARDING TRANSCRIPTIONS** (with topic parameter)
- ✅ ORAC Core Topic System: **IMPLEMENTED** on feature/topic-system-mvp branch
  - `topic_manager.py` - Complete topic management system
  - `api_topics.py` - Topic API endpoints
  - `api_heartbeat.py` - Heartbeat support
  - Grammar files ready (`default.gbnf` for home automation)
- ⏳ ORAC Core: **NEEDS DEPLOYMENT** on 192.168.8.191:8000
- ⏳ Home Assistant Topic: **NEEDS CONFIGURATION**

### Available Home Assistant Entities
From `entity_mappings.yaml`:
- `light.bedroom_lights` → "bedroom lights" ✅ (perfect for our test)
- `light.bathroom_lights` → "bathroom lights"
- `light.kitchen_lights` → "kitchen lights"
- `light.lounge_lights` → "lounge lights"
- `light.hall_lights` → "hall lights"

### Implementation Mini-Sprints

Each sprint is designed to be independently testable with clear success criteria.

---

## 🚀 HOME ASSISTANT INTEGRATION ROADMAP

### Sprint 1: Deploy and Verify ORAC Core (4 hours)
**Goal**: Get ORAC Core operational with topic support

#### Implementation Steps:
1. **Deploy ORAC Core**
   ```bash
   cd /Users/2oby/pCloud Box/Projects/ORAC/Orac-Omniscient-Reactive-Algorithmic-Core
   ./scripts/deploy_and_test.sh "Deploy topic system" feature/topic-system-mvp
   ```

2. **Verify Endpoints**
   ```bash
   # Health check
   curl http://192.168.8.191:8000/health
   
   # Heartbeat (for Hey ORAC integration)
   curl http://192.168.8.191:8000/api/v1/heartbeat
   
   # List topics (should show 'general' and auto-create 'home_assistant')
   curl http://192.168.8.191:8000/api/v1/topics
   ```

3. **Test Topic-Based Generation**
   ```bash
   curl -X POST http://192.168.8.191:8000/v1/generate \
     -H "Content-Type: application/json" \
     -d '{
       "prompt": "turn on bedroom lights",
       "topic": "home_assistant"
     }'
   ```

#### Success Criteria:
- ✅ Container running on 192.168.8.191:8000
- ✅ All endpoints responding
- ✅ Topic auto-discovery working
- ✅ JSON output: `{"device":"lights","action":"on","location":"bedroom"}`

---

### Sprint 2: Grammar Testing & Optimization (2 hours)
**Goal**: Validate grammar produces correct JSON for all command types

#### Test Matrix:
```bash
# Lights control
"turn on bedroom lights" → {"device":"lights","action":"on","location":"bedroom"}
"turn off kitchen lights" → {"device":"lights","action":"off","location":"kitchen"}
"toggle bathroom lights" → {"device":"lights","action":"toggle","location":"bathroom"}
"set living room lights 75%" → {"device":"lights","action":"set 75%","location":"living room"}

# Temperature control
"set bedroom heating to 22C" → {"device":"heating","action":"set 22C","location":"bedroom"}
"turn on hall heating" → {"device":"heating","action":"on","location":"hall"}

# Blinds control
"open bedroom blinds" → {"device":"blinds","action":"open","location":"bedroom"}
"close all blinds" → {"device":"blinds","action":"close","location":"all"}
```

#### Grammar Optimization:
1. Review `default.gbnf` for completeness
2. Add missing actions/locations as needed
3. Test edge cases and ambiguous commands
4. Document supported command patterns

---

### Sprint 3: Home Assistant Integration (4 hours)
**Goal**: Connect ORAC Core to Home Assistant for actual device control

#### Implementation Tasks:

1. **HA Connection Module** (`orac/homeassistant/ha_executor.py`)
   ```python
   class HAExecutor:
       def __init__(self, ha_url, ha_token):
           self.ha_url = ha_url
           self.headers = {"Authorization": f"Bearer {ha_token}"}
       
       def execute_command(self, json_command):
           # Parse JSON command
           # Map to HA service call
           # Execute via REST API
           # Return success/failure
   ```

2. **Entity Mapping**
   - Load entity mappings from YAML
   - Map grammar locations to HA entity IDs
   - Handle unmapped entities gracefully

3. **Service Call Mapping**
   ```python
   # Example mappings
   {
       "lights": {
           "on": "light.turn_on",
           "off": "light.turn_off",
           "toggle": "light.toggle",
           "set %": "light.turn_on" # with brightness
       },
       "heating": {
           "on": "climate.turn_on",
           "set C": "climate.set_temperature"
       }
   }
   ```

4. **Integration Points**
   - Add HA executor to topic handler
   - Execute after successful generation
   - Log all commands and results

---

### Sprint 4: End-to-End Testing (2 hours)
**Goal**: Validate complete voice → action pipeline

#### Test Scenarios:

1. **Basic Light Control**
   ```
   Say: "Computer, turn on bedroom lights"
   Expected: 
   - Wake word detected (Hey ORAC)
   - Audio streamed with topic=home_assistant
   - Transcribed: "turn on bedroom lights" (ORAC STT)
   - Generated: {"device":"lights","action":"on","location":"bedroom"}
   - Executed: light.bedroom_lights turns on
   - Time: < 3 seconds
   ```

2. **Complex Commands**
   - Dimming: "Set living room lights to 50 percent"
   - Multiple: "Turn off all lights"
   - Temperature: "Set bedroom heating to 22 degrees"

3. **Error Cases**
   - Unknown location: "turn on garage lights"
   - Ambiguous: "make it brighter"
   - HA offline: Connection refused

#### Monitoring Setup:
```bash
# Watch all components simultaneously
tmux new-session -d -s orac-monitor
tmux send-keys -t orac-monitor:0 'ssh pi "docker logs -f hey-orac"' C-m
tmux split-window -t orac-monitor:0 -h
tmux send-keys -t orac-monitor:0.1 'ssh orin3 "docker logs -f orac-stt"' C-m
tmux split-window -t orac-monitor:0 -v
tmux send-keys -t orac-monitor:0.2 'ssh orin3 "docker logs -f orac-core"' C-m
tmux attach -t orac-monitor
```

---

### Sprint 5: Production Hardening (4 hours)
**Goal**: Make system reliable and maintainable

#### Tasks:

1. **Robustness**
   - Connection retry logic (3 attempts, exponential backoff)
   - Timeout handling (5 second max per stage)
   - Circuit breaker for HA failures
   - Graceful degradation

2. **Observability**
   - Structured logging (JSON format)
   - Metrics collection (Prometheus format)
   - Command history persistence
   - Performance tracking dashboard

3. **Configuration**
   - Environment variables for all settings
   - Docker secrets for API tokens
   - Configuration hot-reload
   - Multi-environment support

4. **User Experience**
   - Audio feedback options
   - Error messages via TTS
   - Visual indicators in web UIs
   - Command confirmation modes

---

## ✅ MVP ARCHITECTURE DECISIONS

### 1. **Execution Location**: ORAC Core
- ORAC Core will execute HA commands directly
- Centralized logic for easier debugging
- HA executor module within ORAC Core

### 2. **User Feedback**: GUI Only (MVP)
- Visual feedback in ORAC Core web interface
- Clickable "Last Command" showing:
  - Original text from ORAC STT
  - Generated JSON
  - HA API call and response
  - Red text on failure with error details
- No audio feedback in MVP

### 3. **Grammar**: Static Files
- Use `default.gbnf` for home_assistant topic
- Static grammar checked into git
- Dynamic generation planned for future

### 4. **Security**: Simple for MVP
- HA token in Docker environment variable
- HTTP on local network
- No auth between components initially

### 5. **Error Handling**: Simple Retry
- Retry HA connection every minute
- Log all failures
- Show errors in GUI (red text)

---

## 🚀 MVP IMPLEMENTATION CHECKLIST

### Step 1: Deploy ORAC Core (30 minutes)
```bash
cd Orac-Omniscient-Reactive-Algorithmic-Core
./scripts/deploy_and_test.sh "Deploy MVP with HA support" feature/topic-system-mvp
```
- [ ] Verify deployment successful
- [ ] Check health endpoint: `curl http://192.168.8.191:8000/health`
- [ ] Verify topics work: `curl http://192.168.8.191:8000/api/v1/topics`

### Step 2: Add HA Executor to ORAC Core (2 hours)
**File**: `orac/homeassistant/ha_executor.py`
```python
import os
import json
import requests
from typing import Dict, Any

class HAExecutor:
    def __init__(self):
        self.ha_url = os.getenv('HA_URL', 'http://192.168.8.100:8123')
        self.ha_token = os.getenv('HA_TOKEN', '')
        self.headers = {"Authorization": f"Bearer {self.ha_token}"}
        
    def execute_json_command(self, command: Dict[str, str]) -> Dict[str, Any]:
        """
        Execute a JSON command from grammar generation
        Returns: {success: bool, details: {...}, error: str|None}
        """
        # Map device/action/location to HA service call
        # Call HA API
        # Return result with full details for GUI
```
- [ ] Create ha_executor.py
- [ ] Add entity mapping logic
- [ ] Add service call mapping
- [ ] Test with curl commands

### Step 3: Enhance ORAC Core GUI (2 hours)
**Files**: `orac/templates/index.html`, `orac/static/js/main.js`

1. **Make Last Command Clickable**:
   - Add click handler to last command text
   - Create modal/popup for details
   - Style: Normal (green) for success, Red for errors

2. **Command Details Modal**:
   ```javascript
   // Show:
   // - Original text: "turn on bedroom lights"
   // - Generated JSON: {"device":"lights","action":"on","location":"bedroom"}
   // - HA Request: POST /api/services/light/turn_on
   // - HA Response: {success: true, entity_id: "light.bedroom_lights"}
   // - Error (if any): Connection refused, etc.
   ```
- [ ] Add modal HTML structure
- [ ] Add click handler to last command
- [ ] Style success/error states
- [ ] Test with mock data

### Step 4: Integrate HA Executor with Generation (1 hour)
**File**: `orac/api.py`
- [ ] Import HAExecutor
- [ ] After successful generation with home_assistant topic:
  - Parse generated JSON
  - Call ha_executor.execute_json_command()
  - Store result for GUI display
- [ ] Add result to API response
- [ ] Handle errors gracefully

### Step 5: Test End-to-End (1 hour)
1. **Basic Test**:
   ```bash
   # Say: "Computer, turn on bedroom lights"
   # Monitor logs
   ssh pi "docker logs -f hey-orac"
   ssh orin3 "docker logs -f orac-stt"
   ssh orin3 "docker logs -f orac-core"
   ```

2. **Verify Flow**:
   - [ ] Wake word detected
   - [ ] Audio sent with topic=home_assistant
   - [ ] Transcription received at ORAC Core
   - [ ] JSON generated correctly
   - [ ] HA API called
   - [ ] GUI shows success/failure
   - [ ] Actual lights respond

### Step 6: Add Docker Environment Variables (30 minutes)
**File**: `docker-compose.yml`
```yaml
services:
  orac:
    environment:
      - HA_URL=${HA_URL:-http://192.168.8.100:8123}
      - HA_TOKEN=${HA_TOKEN}
```
- [ ] Update docker-compose.yml
- [ ] Create .env file with actual values
- [ ] Redeploy with environment variables

---

## 📊 MVP Success Criteria

1. **Voice Command Works**: "Computer, turn on bedroom lights" → lights turn on
2. **GUI Feedback**: Last Command clickable, shows all details
3. **Error Handling**: HA offline shows red error in GUI
4. **Performance**: < 5 seconds from wake word to action
5. **Logging**: All commands logged with timestamps

## 🔄 Next Iteration (Post-MVP)

1. Dynamic grammar from HA entities
2. Audio feedback via TTS
3. More complex commands (scenes, automations)
4. Security hardening
5. Performance optimization (< 2 seconds target)

## Sprint 2: Add Topic Support to ORAC Core
**Goal**: Enable ORAC Core to accept and handle topic-based requests

#### Step 2.1: Create Topic Configuration
**Location**: `Orac-Omniscient-Reactive-Algorithmic-Core/data/topics.yaml` (new file)
```yaml
topics:
  home_assistant:
    model: "default"  # Use configured default model
    grammar: "default.gbnf"
    temperature: 0.1
    max_tokens: 100
    system_prompt: "Convert natural language commands to JSON format for home automation"
  
  general:
    model: "default"
    grammar: null
    temperature: 0.7
    max_tokens: 500
    system_prompt: "You are a helpful AI assistant"
```

#### Step 2.2: Modify Generate Endpoint
**Location**: `orac/api.py` - Update `/v1/generate` endpoint
```python
# Add topic parameter to GenerationRequest model
# Load topic config if topic is provided
# Override request parameters with topic settings
```

#### Step 2.3: Test Topic-Based Generation
```bash
# Test with home_assistant topic
curl -X POST http://192.168.8.191:8000/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "turn on bedroom lights",
    "topic": "home_assistant"
  }'

# Test with general topic (no grammar)
curl -X POST http://192.168.8.191:8000/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is the weather like?",
    "topic": "general"
  }'
```

#### Sprint 2 Success Criteria:
- ✅ Topic configuration file is loaded
- ✅ API accepts topic parameter
- ✅ Topic settings override request parameters
- ✅ Different topics produce different response styles

---

## Sprint 3: Add ORAC Core Settings to ORAC STT UI
**Goal**: Enable users to configure ORAC Core URL in ORAC STT

#### Step 3.1: Add Settings UI Components
**Location**: ORAC STT Web Interface
1. Add settings icon (⚙️) to header
2. Create settings modal with:
   - ORAC Core URL input field
   - Enable/disable forwarding toggle
   - Test connection button
   - Save button

#### Step 3.2: Add Settings Storage
**Location**: `ORAC STT/src/orac_stt/config/settings.py`
```python
@dataclass
class ORACCoreConfig:
    enabled: bool = False
    url: str = "http://192.168.8.191:8000"
    timeout: float = 10.0
```

#### Step 3.3: Deploy and Test
```bash
cd /Users/2oby/pCloud Box/Projects/ORAC/ORAC STT
./deploy_and_test.sh
```

#### Sprint 3 Success Criteria:
- ✅ Settings icon appears in ORAC STT UI
- ✅ Settings modal opens and closes properly
- ✅ Settings are saved and persisted
- ✅ Test connection button works

---

## Sprint 4: Implement Command Forwarding
**Goal**: ORAC STT forwards transcriptions to ORAC Core

#### Step 4.1: Create ORAC Core Client
**Location**: `ORAC STT/src/orac_stt/integrations/orac_core_client.py` (new file)
- Extract topic from request URL parameters
- Forward transcription with topic to ORAC Core
- Handle errors gracefully

#### Step 4.2: Integrate Client into STT Handler
**Location**: `ORAC STT/src/orac_stt/api/stt.py`
- Import ORAC Core client
- After transcription, check if forwarding is enabled
- Extract topic from request URL
- Forward to ORAC Core with topic

#### Step 4.3: Test Forwarding
```bash
# Deploy ORAC STT
cd /Users/2oby/pCloud Box/Projects/ORAC/ORAC STT
./deploy_and_test.sh

# Test with topic parameter
curl -X POST "http://192.168.8.191:7272/stt/v1/stream?topic=home_assistant" \
  -F "file=@test_audio.wav"

# Check logs for forwarding
docker logs orac-stt -f | grep "ORAC Core"
```

#### Sprint 4 Success Criteria:
- ✅ Transcriptions are forwarded to ORAC Core
- ✅ Topic is extracted from URL and sent
- ✅ ORAC Core response is logged
- ✅ Errors don't crash STT service

---

## Sprint 5: Update Hey ORAC Configuration
**Goal**: Configure Hey ORAC to send topics with webhook URLs

#### Step 5.1: Update Model Webhook URLs
```bash
# SSH to Raspberry Pi
ssh pi

# Update Hey ORAC settings via API or config file
curl -X POST http://localhost:7171/api/v1/models/computer_v2/settings \
  -H "Content-Type: application/json" \
  -d '{
    "webhook_url": "http://192.168.8.191:7272/stt/v1/stream?topic=home_assistant"
  }'
```

#### Step 5.2: Test Wake Word with Topic
```bash
# Monitor all logs
ssh pi "docker logs -f hey-orac" &
ssh orin3 "docker logs -f orac-stt" &
ssh orin3 "docker logs -f orac-core" &

# Say: "Computer, turn on the bedroom lights"
# Watch logs for topic flow
```

#### Sprint 5 Success Criteria:
- ✅ Hey ORAC sends audio with topic parameter
- ✅ ORAC STT receives and extracts topic
- ✅ ORAC Core receives request with topic
- ✅ Correct grammar is applied based on topic

---

## Sprint 6: End-to-End Testing & Home Assistant Integration
**Goal**: Complete pipeline works and controls Home Assistant

#### Step 6.1: Verify Home Assistant Connection
```bash
# Test ORAC Core can reach Home Assistant
curl http://192.168.8.191:8000/api/homeassistant/entities

# Update grammar from Home Assistant
curl -X POST http://192.168.8.191:8000/api/homeassistant/grammar/update
```

#### Step 6.2: End-to-End Test
```bash
# Open multiple terminals to monitor the flow

# Terminal 1: Monitor Hey ORAC
ssh pi "docker logs -f hey-orac | grep -E 'WAKE|webhook'"

# Terminal 2: Monitor ORAC STT
ssh orin3 "docker logs -f orac-stt | grep -E 'Transcription|ORAC Core'"

# Terminal 3: Monitor ORAC Core
ssh orin3 "docker logs -f orac-core | grep -E 'generate|home_assistant'"

# Terminal 4: Monitor Home Assistant
# Open Home Assistant UI and watch bedroom lights entity
```

#### Step 6.3: Execute Voice Command
1. Say: "Computer, turn on the bedroom lights"
2. Verify flow:
   - Hey ORAC: Wake word detected, audio sent
   - ORAC STT: Audio transcribed, forwarded to Core
   - ORAC Core: Command parsed, JSON generated
   - Home Assistant: Bedroom lights turn on

#### Sprint 6 Success Criteria:
- ✅ Complete voice command flows through all systems
- ✅ ORAC Core generates valid Home Assistant command
- ✅ Bedroom lights actually turn on/off
- ✅ Response time < 5 seconds

---

## Next Steps After All Sprints Complete

### Future Enhancements
1. **Response Flow**: Have ORAC Core execute HA commands directly
2. **Audio Feedback**: Generate TTS responses for command confirmations
3. **Error Handling**: Graceful failures with helpful error messages
4. **Multi-command Support**: Handle multiple commands in one utterance
5. **Context Awareness**: Remember previous commands for follow-ups

---

## 🎯 **PREVIOUS PRIORITY - Working Grammar Implementation**

### Dynamic Grammar Update System - ✅ **COMPLETED**

#### Requirements
- **Daily Updates**: Run entity fetch from Home Assistant once daily at 3am
- **Manual Trigger**: Add button in Web UI to force fetch from Home Assistant
- **Grammar Validation**: After each fetch, validate grammar can be parsed and LLM generation works
- **Test Command**: Use "Turn on the Kitchen lights" as validation test
- **Model Settings Sync**: Ensure Web UI model settings (default model, top-p, top-k, prompt) are used by API

#### Implementation Status: ✅ **COMPLETED**
- Daily scheduled grammar updates at 3am implemented
- Manual grammar update button with force option added to Web UI
- Grammar validation with test generation ("Turn on the Kitchen lights") implemented
- Model settings synchronization between Web UI and API implemented
- Grammar scheduler with status monitoring implemented
- Default grammar file (default.gbnf) created and integrated
- Test script created for validation

#### Files Modified
- `orac/homeassistant/grammar_scheduler.py` - New scheduler module
- `orac/api.py` - Enhanced grammar update endpoints and model settings sync
- `orac/static/js/main.js` - Updated Web UI with force update and scheduler status
- `orac/templates/index.html` - Added force update button
- `data/test_grammars/default.gbnf` - New default grammar file
- `test_grammar_scheduler.py` - Test script for validation

#### Features Implemented
1. **Daily Updates**: Grammar scheduler runs automatically at 3am daily
2. **Manual Updates**: Web UI button to trigger immediate grammar updates
3. **Force Updates**: Force update option to bypass time-based restrictions
4. **Validation**: Post-update validation with test generation
5. **Settings Sync**: Web UI model settings (temperature, top-p, top-k) used by API
6. **Status Monitoring**: Real-time scheduler status in Web UI
7. **Error Handling**: Graceful fallback and error reporting

---

## ✅ **RESOLVED ISSUES**

### API Grammar Formatting Issue - ✅ **RESOLVED**
- API now produces valid JSON responses when using grammar files
- API outputs match CLI test outputs for the same prompts
- Web interface works correctly with grammar-constrained generation
- No more "Invalid JSON response from model" errors

### Model Settings Persistence - ✅ **RESOLVED**
- Fixed API endpoints in reset settings function
- Enhanced settings persistence with robust fallback logic
- Added settings validation and auto-recovery
- Implemented periodic settings validation

### Temperature Grammar Issue - ✅ **RESOLVED**
- Temperature commands now work properly with correct temperature values
- Percentage commands return proper percentage values
- System prompt properly integrated with grammar rules
- Default model properly configured

---

## 📋 **CURRENT DEVELOPMENT STATUS**

### Working Features
- ✅ **Grammar Scheduler**: Daily updates at 3am with manual trigger
- ✅ **Web UI**: Grammar update button with force option
- ✅ **API Integration**: Model settings synchronization
- ✅ **Validation**: Test generation for grammar validation
- ✅ **Error Handling**: Graceful fallback and error reporting
- ✅ **Status Monitoring**: Real-time scheduler status

### Next Steps
- ⚠️ **Monitor production usage** - Verify grammar updates work correctly in real-world scenarios
- ⚠️ **Test with different Home Assistant setups** - Ensure compatibility with various configurations
- ⚠️ **Performance optimization** - Monitor resource usage during grammar updates
- ⚠️ **Documentation updates** - Keep deployment and usage documentation current

---

## 🧹 **Clean Up Tasks - ORAC Core WebGUI**

### Goal: Update ORAC Core to be consistent with other modules
Make ORAC Core WebGUI consistent with Hey ORAC and ORAC STT in terms of styling, status monitoring, and configuration patterns.

### Tasks:
1. **Update Look & Feel** - ✅ **COMPLETED**
   - Implemented green-on-black retro cyberpunk theme
   - Added monospace font (Courier New)
   - Added text shadows and glow effects
   - Added scanline overlay effect
   - Updated all UI components with consistent styling

2. **ORAC STT Connection Status** - ⏳ **PENDING**
   - Add status panel showing ORAC STT connection state
   - Implement periodic health check pings to ORAC STT
   - Show last connection time and received data status
   - Add visual indicators (green/red/amber) for connection state

3. **Display Home Assistant Entity Details** - ⏳ **PENDING**
   - Enhance existing HA status panel to show more entity details
   - Add entity list view with search/filter capability
   - Show entity states and last update times
   - Consider adding entity control capabilities

4. **Verify Configuration File Handling** - ⏳ **PENDING**
   - Check that ORAC Core uses same config pattern as other modules
   - Verify YAML/JSON file handling consistency
   - Ensure settings persistence works the same way
   - Document any differences that need to be maintained

5. **Check WebGUI Pattern Consistency** - ⏳ **PENDING**
   - Compare web server patterns (FastAPI vs Flask)
   - Check API endpoint naming conventions
   - Verify WebSocket usage patterns
   - Document architectural differences

### Implementation Notes:
- **Periodic Pings**: Need to implement bidirectional health checks:
  - Hey ORAC → ORAC STT (every 30 seconds)
  - ORAC STT → ORAC Core (every 30 seconds)
  - Display connection status in each module's UI
- **Documentation**: Update INTEGRATION_CURRENT_FOCUS.md with ping architecture

---

## 📁 **Archive**

For historic development information and resolved issues, see:
- [Critical Path Implementation Archive](docs/archive/CRITICAL_PATH_IMPLEMENTATION_ARCHIVE.md)
- [Development Log Archive](docs/archive/DEVELOPMENT_LOG_ARCHIVE.md) 