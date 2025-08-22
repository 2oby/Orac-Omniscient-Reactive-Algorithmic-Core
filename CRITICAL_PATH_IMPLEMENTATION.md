# Critical Path Implementation Plan

> **Development Setup**: For environment setup, deployment procedures, and SSH access to the Jetson Orin, see [ORAC Development Instructions](instructions.md).

## 🚀 **CURRENT PRIORITY - ORAC STT to ORAC Core Integration**

### Goal: Enable end-to-end voice command pipeline
Enable ORAC_STT to send transcribed text to ORAC Core, which will then control Home Assistant entities. Starting with: "Turn on the Bedroom Lights" as the test command.

### Architecture Design Principles
1. **Topic-based routing**: Context flows from Hey ORAC → ORAC STT → ORAC Core via URL parameters
2. **Separation of concerns**: 
   - Hey ORAC: Knows the intent/context (topic)
   - ORAC STT: Handles transcription and routing only
   - ORAC Core: Manages all model-specific logic and settings
3. **User configurability**: ORAC Core URL is configurable in ORAC STT UI
4. **Flexible configuration**: Each topic in ORAC Core can have different models, temperatures, and grammars

### Current System Status
- ✅ Hey ORAC → ORAC STT: **Working** (audio streaming functional)
- ✅ ORAC STT: **Working** (transcribes audio correctly)
- ❌ ORAC Core: **Not Running** (needs to be started on 192.168.8.191:8000)
- ⏳ ORAC STT → ORAC Core: **Not Implemented** (needs integration)
- ⏳ ORAC Core → Home Assistant: **Configured but untested**

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

## Sprint 1: Get ORAC Core Running (Foundation)
**Goal**: Ensure ORAC Core is running and can generate responses

#### Step 1.1: Deploy and Start ORAC Core
**Actions**:
```bash
# From local machine
cd /Users/2oby/pCloud Box/Projects/ORAC/Orac-Omniscient-Reactive-Algorithmic-Core
./scripts/deploy_and_test.sh
```

#### Step 1.2: Verify Basic Functionality
**Test Commands**:
```bash
# Test health endpoint
curl http://192.168.8.191:8000/health

# Test basic generation (no topic yet)
curl -X POST http://192.168.8.191:8000/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "turn on bedroom lights",
    "grammar": "default.gbnf",
    "temperature": 0.1
  }'
```

#### Sprint 1 Success Criteria:
- ✅ ORAC Core container is running
- ✅ Health endpoint returns 200 OK
- ✅ Generate endpoint returns valid JSON response
- ✅ Response follows grammar format: `{"device":"lights","action":"on","location":"bedroom"}`

---

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

## 📁 **Archive**

For historic development information and resolved issues, see:
- [Critical Path Implementation Archive](docs/archive/CRITICAL_PATH_IMPLEMENTATION_ARCHIVE.md)
- [Development Log Archive](docs/archive/DEVELOPMENT_LOG_ARCHIVE.md) 