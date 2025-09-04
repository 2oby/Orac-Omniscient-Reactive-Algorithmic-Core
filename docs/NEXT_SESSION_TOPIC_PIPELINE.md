# ORAC Topic Pipeline Configuration - Next Session Brief

## 📅 Session Context
**Date**: September 4, 2025
**Previous Session**: Set up Home Assistant integration, configured HA token, updated entity mappings for lounge lamp
**Current Blocker**: The `home_assistant` topic doesn't exist, preventing voice commands from executing

## 🎯 Session Goal
Configure the complete `home_assistant` topic pipeline to enable voice-controlled Home Assistant commands.

## 📊 Current System State

### Infrastructure Status (All Working ✅)
- **Hey ORAC** (192.168.8.99:7171): Wake word detection working
- **ORAC STT** (192.168.8.192:7272): Transcription working, forwarding to Core
- **ORAC Core** (192.168.8.192:8000): Running with HA token configured
- **Home Assistant** (192.168.8.99:8123): Accessible with valid token

### What's Already Configured
1. **HAExecutor Class**: Ready in `orac/homeassistant/ha_executor.py`
2. **Entity Mappings**: Including `switch.lounge_lamp_plug` as "lounge lamp"
3. **HA Token**: Configured in `/home/orin3/ORAC/.env`
4. **Grammar File**: `default.gbnf` exists for JSON generation

### What's Missing
The `home_assistant` topic that would:
- Route wake word "Computer" to HA processing
- Apply grammar constraints for JSON generation
- Use low temperature (0.1) for deterministic output
- Trigger HAExecutor after generation

## 🏗️ Topic Pipeline Architecture

A complete topic pipeline consists of several components:

### 1. **Topic Registration**
```yaml
topic_id: home_assistant
name: "Home Assistant Control"
description: "Voice control for home automation"
enabled: true
```

### 2. **Wake Word Routing**
- Hey ORAC detects "Computer" wake word
- Sends audio to STT with `?topic=home_assistant`
- STT forwards transcription with topic to Core

### 3. **Grammar Configuration**
```yaml
grammar:
  enabled: true
  file: "default.gbnf"  # Or topic-specific grammar
  validation_test: "turn on bedroom lights"
```

### 4. **Model Settings**
```yaml
settings:
  model: "Qwen3-0.6B-Q8_0.gguf"
  system_prompt: "Convert commands to JSON: {device, action, location}"
  temperature: 0.1  # Low for deterministic output
  top_p: 0.9
  max_tokens: 100
  force_json: true
```

### 5. **API Mappers/Executors**
- Post-generation hook to HAExecutor
- Maps generated JSON to HA service calls
- Executes via Home Assistant REST API

### 6. **Entity Resolution**
- Maps friendly names to HA entity IDs
- Handles both lights and switches
- Resolves "lounge lamp" → "switch.lounge_lamp_plug"

## ❓ Key Questions for Next Session

### Topic Creation Method
1. **Manual Creation via API**: POST to `/api/topics`
2. **Auto-discovery**: Let Hey ORAC announce it via heartbeat
3. **Configuration File**: Add to `topics.yaml`

### Grammar Strategy
1. **Static Grammar**: Use existing `default.gbnf`
2. **Dynamic Grammar**: Generate from HA entities
3. **Hybrid**: Static structure with dynamic entities

### Pipeline Integration Points
1. Where does HAExecutor hook into the generation flow?
2. How to handle generation failures?
3. Should we log commands for training/debugging?

### Hey ORAC Configuration
1. How to set topic per wake word model?
2. Can we have multiple topics for different wake words?
3. How to update without restarting Hey ORAC?

## 📝 Test Commands for Validation

Once configured, these should work:
```
"Computer, turn on the lounge lamp"
→ {"device":"lights","action":"on","location":"lounge"}
→ Execute: switch.turn_on(entity_id="switch.lounge_lamp_plug")

"Computer, turn off the bedroom lights"  
→ {"device":"lights","action":"off","location":"bedroom"}
→ Execute: light.turn_off(entity_id="light.bedroom_lights")

"Computer, set living room lights to 50 percent"
→ {"device":"lights","action":"set 50%","location":"living room"}
→ Execute: light.turn_on(entity_id="light.lounge_lights", brightness=127)
```

## 🔧 Implementation Checklist

- [ ] Create `home_assistant` topic in ORAC Core
- [ ] Configure topic with grammar and model settings
- [ ] Update Hey ORAC to send `topic=home_assistant`
- [ ] Verify STT forwards topic correctly
- [ ] Test grammar generation produces valid JSON
- [ ] Confirm HAExecutor receives and executes commands
- [ ] Validate actual device control in Home Assistant
- [ ] Document complete configuration for reproducibility

## 📚 Relevant Files

### Configuration Files
- `/home/orin3/ORAC/.env` - HA token configuration
- `orac/homeassistant/entity_mappings.yaml` - Entity name mappings
- `data/test_grammars/default.gbnf` - Grammar constraints

### Code Files  
- `orac/homeassistant/ha_executor.py` - Command execution
- `orac/api.py` - Generation endpoint with topic handling
- `orac/topic_manager.py` - Topic registration and management
- `orac/api_topics.py` - Topic API endpoints

### Documentation
- `docs/INTEGRATION_CURRENT_FOCUS.md` - Current status
- `docs/HOME_ASSISTANT_INTEGRATION_PLAN.md` - Overall plan
- `CRITICAL_PATH_IMPLEMENTATION.md` - Implementation details

## 🎬 Next Session Starting Point

"I need to configure the `home_assistant` topic pipeline in ORAC Core. The system components are all connected and the HA token is configured, but the topic doesn't exist yet. Help me understand and implement the complete topic pipeline including grammar configuration, API mappers, and Hey ORAC integration."

### Context to Provide
- All components running and connected
- HA token already configured
- Entity mappings include lounge lamp
- Need to create and configure topic pipeline

### Expected Outcome
Voice command "Computer, turn on the lounge lamp" successfully controls the device through the complete pipeline.