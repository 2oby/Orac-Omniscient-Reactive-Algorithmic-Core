# CURRENT FOCUS - ORAC Core Configuration & Home Assistant Integration

## Environment Overview

### Infrastructure
- **Jetson Orin (orin4)**: Main deployment target running ORAC Core in Docker
  - Access: `ssh orin4` (configured in local SSH config)
  - Docker deployment with persistent volumes for data/configs
  - Running at http://192.168.8.192:8000
  - Also running ORAC STT on port 7272

- **Raspberry Pi (pi)**: Running Hey ORAC wake word detection
  - Access: `ssh pi`
  - Running Home Assistant on port 8123
  - Hey ORAC on port 7171

- **Deployment**: `./scripts/deploy_and_test.sh` script handles:
  - Git push to GitHub
  - Remote deployment on orin4
  - Docker container rebuild and restart
  - Automated testing

## Problem Statement
Topic configurations (especially Home Assistant dispatcher settings) were being lost:
1. After Docker container restarts
2. When heartbeat updates from ORAC STT overwrote saved configurations

## Work Completed

### 1. Fixed API Models (✅ WORKING)
- Added `dispatcher` field to API request/response models in `/orac/api_topics.py`:
  - `TopicUpdateRequest`
  - `TopicResponse` 
  - `TopicCreateRequest`
- This allows the dispatcher field to be properly serialized/deserialized

### 2. Fixed JavaScript Frontend (✅ WORKING)
- Updated `/orac/static/js/topic_config.js` to properly capture dispatcher dropdown value
- Fixed empty string vs null handling for dispatcher field
- Added comprehensive debug logging to track save operations

### 3. Fixed Heartbeat Overwriting (✅ DEPLOYED)
- Modified `/orac/api_heartbeat.py` to reload topics from disk before updating
- Prevents heartbeat from overwriting user-configured settings like dispatcher
- Code change:
```python
else:
    # Reload topics to get latest saved state (including dispatcher)
    topic_manager.load_topics()
    topic = topic_manager.get_topic(topic_id)
```

### 4. Fixed Configuration Persistence - Singleton Pattern (✅ FIXED 2025-09-06)
- **Root Cause**: Multiple TopicManager instances across modules causing state inconsistency
  - `api.py`, `api_topics.py`, and `api_heartbeat.py` each created their own TopicManager instance
  - Updates via API only affected one instance while heartbeat saved from another
- **Solution**: Implemented singleton pattern for TopicManager
  - Created `/orac/topic_manager_singleton.py` to ensure single shared instance
  - Updated all modules to use the singleton: `from orac.topic_manager_singleton import topic_manager`
- **Result**: Configuration changes now persist correctly through:
  - Heartbeat updates (every 30 seconds)
  - Container restarts
  - Both `general` and `computa` topics retain their dispatcher settings

### 5. System Prompt Configuration (✅ WORKING)
- Configured Home Assistant control prompt:
```
You are a smart home assistant. Convert natural language commands into JSON format for controlling smart home devices. Focus on device control actions like turning lights on/off, adjusting brightness, etc. Output only valid JSON with keys: device, action, location.
```

### 6. Natural Language Parsing (✅ WORKING)
- System correctly parses commands like "turn off the lounge lamp"
- Generates proper JSON: `{"device":"lights","action":"off","location":"living room"}`

## Current Issues

### 1. ~~Configuration Loss on Container Restart~~ (✅ FIXED)
~~Despite volume mounting (`./data:/app/data`), configurations may still be lost on container restart.~~
- **FIXED**: Implemented singleton pattern for TopicManager to ensure consistent state across all modules
- Configuration now persists correctly through restarts and heartbeats

### 2. Home Assistant Command Execution (✅ FIXED 2025-09-06)
- **Problem**: Commands were parsed correctly but lights weren't responding
- **Root Causes**: 
  1. Dispatcher was using wrong environment variable (`HA_HOST` instead of `HA_URL`)
  2. Hardcoded wrong entity ID (`switch.lounge_lamp_plug` instead of `switch.tretakt_smart_plug`)
  3. Dispatcher was doing keyword parsing instead of JSON parsing
- **Solution**: Updated HomeAssistantDispatcher to:
  - Parse JSON output from LLM properly
  - Use correct environment variables (HA_URL, HA_TOKEN)
  - Map entities correctly (living room → switch.tretakt_smart_plug)
- **Result**: Voice commands now successfully control Home Assistant devices

## Next Steps

### Tomorrow's Focus - Deep Dive & UX Improvements

#### 1. **Dispatcher Debugging & Enhancement**
   - Add comprehensive logging to understand HA integration flow
   - Implement proper entity mapping loading from `entity_mappings.yaml`
   - Add support for more device types and actions
   - Test error handling and recovery scenarios
   - Consider implementing status feedback from HA

#### 2. **UX Issues to Address**

##### Hey ORAC (Wake Word Detection)
   - Response time and false positive/negative rates
   - Audio feedback when wake word is detected
   - Visual indicators for listening state
   - Configuration interface improvements

##### ORAC STT (Speech-to-Text)
   - Transcription accuracy improvements
   - Better handling of ambient noise
   - Real-time transcription feedback
   - Error messages and recovery

##### ORAC Core
   - Web UI responsiveness and usability
   - Topic configuration interface improvements
   - Better visualization of command processing pipeline
   - Real-time logs and debugging interface
   - Entity mapping configuration UI

#### 3. **Testing & Documentation**
   - Create comprehensive test suite for HA dispatcher
   - Document the complete voice command flow
   - Create user guide for configuring new devices
   - Add troubleshooting guide

### Code Locations for Investigation

1. **Topic Persistence**: 
   - `/orac/topic_manager.py` - Check `_ensure_default_topic()` and `load_topics()`
   - `/data/topics.yaml` - Verify file persistence on host

2. **Dispatcher Execution**:
   - `/orac/api_generation.py` - Where dispatcher is invoked after LLM generation
   - `/orac/dispatchers/homeassistant.py` - Home Assistant command execution
   - `/orac/homeassistant/client.py` - HA API client

3. **Entity Mapping**:
   - `/orac/homeassistant/entity_mappings.yaml` - Check if Lounge Lamp Plug is mapped
   - Entity ID should be: `switch.tretakt_smart_plug`

## Testing Commands

```bash
# Check if topics.yaml persists on host
cat ./data/topics.yaml | grep dispatcher

# Monitor logs during save
docker logs -f orac

# Test heartbeat doesn't overwrite
# 1. Save configuration with dispatcher
# 2. Wait 30 seconds for heartbeat
# 3. Check if dispatcher still set

# Direct Home Assistant test
curl -X POST http://192.168.8.191:8000/v1/homeassistant/execute \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "switch.tretakt_smart_plug", "action": "turn_off"}'
```

## Success Criteria
1. ✅ Topic configurations persist through Docker container restarts
2. ✅ Heartbeat updates don't overwrite user configurations
3. ✅ Natural language commands control Home Assistant devices
4. ✅ "Turn on the lounge light" successfully controls the lamp

## Achievements (2025-09-06)
- ✅ Fixed configuration persistence with singleton pattern
- ✅ Fixed HomeAssistantDispatcher JSON parsing
- ✅ Corrected entity ID mappings
- ✅ Successfully tested voice control of Home Assistant devices
- ✅ Light responds correctly to "Turn on the lounge light" command

## Related Files Modified Today
- `/orac/dispatchers/homeassistant.py` - **FIXED** - Now parses JSON, uses correct env vars and entity IDs
- Previous fixes (still active):
  - `/orac/api_heartbeat.py` - Fixed heartbeat overwriting, updated to use singleton
  - `/orac/api_topics.py` - Added dispatcher field to models, updated to use singleton
  - `/orac/api.py` - Updated to use singleton TopicManager
  - `/orac/static/js/topic_config.js` - Fixed dropdown value capture
  - `/orac/topic_manager.py` - Added debug logging
  - `/orac/topic_manager_singleton.py` - Singleton wrapper for TopicManager

## Environment Variables Required
```yaml
HA_URL: http://192.168.8.100:8123
HA_TOKEN: [Home Assistant Long-Lived Access Token]
```

## Working Command Example
- Input: "Turn on the lounge light"
- LLM Output: `{"device":"lights","action":"on","location":"living room"}`
- Dispatcher maps to: `switch.tretakt_smart_plug`
- Result: ✅ Lounge lamp successfully turns on/off

---
*Last Updated: 2025-09-06 17:36 UTC*
*Fixed Today: Home Assistant dispatcher now working - lights respond to voice commands*
*Next: Debug dispatcher details and address UX issues across all three modules*