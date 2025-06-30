# Critical Path Implementation Plan

> **Development Setup**: For environment setup, deployment procedures, and SSH access to the Jetson Orin, see [ORAC Development Instructions](instructions.md).

## ✅ **RESOLVED - API Grammar Formatting Issue**

### API Grammar Formatting Fix - COMPLETED

#### Issue Description
The web interface and API were producing malformed JSON responses when using GBNF grammar files, even though the same grammar worked correctly with direct CLI usage. This caused "Invalid JSON response from model" errors.

#### Root Cause
- **Prompt Formatting**: CLI test used specific system prompt and partial JSON structure, while API used generic prompts
- **Grammar Conflict**: Server started with `--grammar-file` but HTTP request also included JSON grammar
- **Response Processing**: API didn't properly handle partial JSON responses from grammar-constrained generation

#### Solution Implemented
1. **Prompt Formatting Fix** (`orac/api.py`): Use same prompt format as CLI test for grammar files
2. **Grammar Conflict Fix** (`orac/llama_cpp_client.py`): Don't include grammar in HTTP request when using grammar files
3. **Response Processing Fix** (`orac/api.py`): Proper JSON completion for grammar file responses
4. **Web Interface Fix** (`orac/static/js/main.js`): Correct grammar file path

#### Status: ✅ **RESOLVED**
- API now produces valid JSON responses when using grammar files
- API outputs match CLI test outputs for the same prompts
- Web interface works correctly with grammar-constrained generation
- No more "Invalid JSON response from model" errors

#### Files Modified
- `orac/api.py` - Prompt formatting and response processing
- `orac/llama_cpp_client.py` - Grammar conflict resolution  
- `orac/static/js/main.js` - Grammar file path correction
- `test_api_grammar_fix.py` - New test script (created)

#### Test Results
Created comprehensive test script that validates:
- CLI and API produce identical outputs
- JSON structure is valid with required fields
- Multiple Home Assistant command scenarios work correctly

---

## 🚨 **CURRENT PRIORITY ISSUE - GBNF Parsing Bug in llama.cpp v5306**

### GBNF Parsing Issue in llama.cpp Version 5306

#### Overview
The GBNF parser in llama.cpp version 5306 (commit d8794338) fails to parse certain grammars, producing the error `parse: error parsing grammar: expecting newline or end or expecting name`. This issue affects both CLI (--grammar-file) and HTTP API ("grammar" field) invocations, preventing grammar-constrained generation for complex structures like JSON outputs for Home Assistant.

#### What Works
**Simple Grammars:**
- Grammars with a single root rule and no non-terminals, e.g., `root ::= "hello" | "world"` (hello_world.gbnf), parse successfully and produce expected outputs.
- Grammars with minimal non-terminals and fixed JSON strings, e.g., `root ::= "{\"action\":\"turn on\"}"` (simple_json.gbnf), also work, producing valid JSON.

**Model and Environment:**
- The model `distilgpt2.Q3_K_L.gguf` (and previously Q4_0) loads correctly, and inference works without grammars.
- The environment (Ubuntu 22.04, ARM64, cc 11.4.0) is functional for non-grammar tasks.

#### What Does Not Work
**Complex Grammars:**
- Grammars with multiple non-terminals and JSON-like structures, e.g., `static_actions.gbnf` (defining action_value, device_value, action, device rules), fail with:
  ```
  parse: error parsing grammar: expecting newline or end at \"action\"" ws ":" ws action_value
  llama_grammar_init_impl: failed to parse grammar
  ```
- The error occurs at non-terminal references (e.g., `action_value`) or complex token sequences, suggesting a parser bug in `llama_grammar_init_impl`.
- Previous Home Assistant grammars (from grammar_manager.py) and similar JSON-like grammars fail similarly, indicating the issue is specific to non-terminal handling or nested rules.

**Updating llama.cpp:**
- Attempting to update to a newer version (e.g., master build b5754, June 25, 2025) failed due to compatibility issues in a containerized environment, preventing verification of fixes.

#### Likely Root Cause
The bug is a regression in the GBNF parser of version 5306, likely introduced around early 2024 (based on commit d8794338 and GitHub issue #4799). It affects grammars with:
- Multiple non-terminal rules (e.g., `action_value`, `device_value`).
- Complex token sequences involving quoted strings and non-terminals (e.g., `\"action\"" ws ":" ws action_value`).
- The parser misinterprets tokens, expecting a rule to end prematurely, as evidenced by `expecting newline or end`. Community reports (e.g., issues #4799, #7991) confirm similar issues, with fixes likely in later builds (post-January 2024, possibly b5754).

#### Suggested Approach
Since updating llama.cpp is not currently viable due to container compatibility issues, incrementally test grammars of increasing complexity to identify the parser's breaking point and find a workable grammar for your Home Assistant use case.

**Steps:**

1. **Start with Minimal Grammar:**
   - Test a grammar with one non-terminal and a simple structure, e.g., a single JSON field with alternations.
   - Verify it works in version 5306 to establish a baseline.

2. **Gradually Increase Complexity:**
   - Add non-terminals, nested rules, or JSON-like structures one at a time (e.g., add a second field, then multiple alternations).
   - Test each step with llama-cli to pinpoint where the parser fails (e.g., at non-terminal references or specific tokens).

3. **Workaround for Complex Grammars:**
   - If complex grammars fail, use unconstrained generation (--no-grammar) and validate outputs in Python (e.g., check JSON structure and values).
   - Example: Parse output for valid action and device fields using a script like in grammar_manager.py.

4. **Revisit llama.cpp Update:**
   - Resolve container compatibility issues (e.g., check dependencies, compiler versions, or ARM64-specific build flags).
   - Test build b5754 (commit 2bf9d53) or a post-January 2024 commit, as changelog evidence suggests grammar parsing fixes.

5. **Community Engagement:**
   - Check llama.cpp GitHub Issues for updates on #4799 or #7991.
   - If unresolved, open a new issue with your test results, including working and failing grammars, commit d8794338, and error logs.

6. **Debugging (Optional):**
   - If feasible, modify grammar-parser.cpp to log parsing tokens and rebuild to diagnose the failure point (requires C++ expertise).

#### Next Steps
1. Develop a series of test grammars, starting simple and progressively adding complexity (e.g., non-terminals, JSON structures).

2. Test each grammar with:
   ```bash
   ./llama-cli -m /models/gguf/distilgpt2.Q3_K_L.gguf -p "<prompt>" --grammar-file test.gbnf -n 50 --temp 0.1 --repeat-penalty 1.1 --verbose
   ```

3. Document which grammars fail and at what point to identify the parser's limitations.

4. Reattempt updating llama.cpp outside the container or resolve container issues to test build b5754, as it's likely to fix the bug.

This approach maximizes the chance of finding a functional grammar in version 5306 while planning for a future update to a fixed version.

---

## Overview

This document focuses on the three most critical components that must be implemented correctly for the Home Assistant auto-discovery system to work:

## Current Priority: **ACTIVE DEVELOPMENT**

### 🔄 **NEXT - Grammar Accuracy Improvements and API Integration**

#### Current State
- GBNF grammar testing completed with 67% accuracy (4/6 successful cases)
- Grammar syntax and parameter optimization achieved
- System prompt effectiveness validated
- Model behavior patterns documented

#### Implementation Priority: **HIGHEST**

##### 4.1 Grammar Accuracy Improvements

**Goal**: Improve grammar parsing accuracy from 67% to >90% for production use.

**Implementation Plan**:

###### 4.1.1 Grammar Rule Reordering
```python
# orac/homeassistant/grammar_manager.py
class GrammarOptimizer:
    """Optimizes grammar rules for better accuracy"""
    
    # Most common devices first (based on Home Assistant usage)
    DEVICE_PRIORITY = [
        "lights",      # Most common
        "thermostat",  # Climate control
        "blinds",      # Window covers
        "music",       # Media players
        "tv",          # Television
        "fan",         # Fans
        "alarm",       # Security
        "switch"       # Generic switches
    ]
    
    # Most common locations first
    LOCATION_PRIORITY = [
        "living room",   # Most common
        "bedroom",       # Sleeping area
        "kitchen",       # Cooking area
        "bathroom",      # Bathroom
        "dining room",   # Dining area
        "hall",          # Hallway
        "office",        # Work area
        "garage",        # Garage
        "basement",      # Basement
        "attic"          # Attic
    ]
    
    def optimize_grammar_order(self, grammar_content: str) -> str:
        """Reorder grammar rules based on usage frequency"""
        # Implementation to reorder device and location rules
        # Put most common items first to reduce model bias
```

###### 4.1.2 Enhanced Device Type Coverage
```python
# orac/homeassistant/grammar_manager.py
class DeviceTypeExpander:
    """Expands device type coverage for better recognition"""
    
    # Comprehensive device mappings
    DEVICE_ALIASES = {
        "lights": ["light", "lamp", "bulb", "ceiling light", "wall light", "floor lamp"],
        "thermostat": ["heating", "cooling", "climate", "temperature", "ac", "heat"],
        "blinds": ["blind", "curtain", "shade", "window cover", "drape"],
        "music": ["speaker", "audio", "sound system", "stereo", "amp", "receiver"],
        "tv": ["television", "display", "monitor", "screen", "smart tv"],
        "fan": ["ceiling fan", "table fan", "exhaust fan", "ventilation"],
        "alarm": ["security", "burglar alarm", "smoke detector", "carbon monoxide"],
        "switch": ["outlet", "power strip", "smart plug", "relay"]
    }
    
    def expand_device_vocabulary(self, grammar_content: str) -> str:
        """Add device aliases to grammar for better recognition"""
        # Implementation to add device aliases to grammar rules
```

###### 4.1.3 Improved UNKNOWN Handling
```python
# orac/homeassistant/grammar_manager.py
class UnknownHandler:
    """Improves handling of unknown devices and locations"""
    
    def create_fallback_rules(self, grammar_content: str) -> str:
        """Add better fallback mechanisms for unknown values"""
        # Implementation to add UNKNOWN fallbacks with better logic
        # Use context clues to make educated guesses
```

##### 4.2 API Integration and Parameter Standardization

**Goal**: Ensure ORAC API uses identical grammar parameters and system prompts for consistency.

**Implementation Plan**:

###### 4.2.1 Parameter Standardization
```python
# orac/llama_cpp_client.py
class GrammarParameters:
    """Standardized grammar parameters for consistent results"""
    
    # Optimized parameters from testing
    DEFAULT_PARAMS = {
        "temperature": 0.2,      # Low for deterministic output
        "top_p": 0.8,           # Nucleus sampling
        "top_k": 30,            # Limit vocabulary choices
        "max_tokens": 50,       # Safety limit
        "repeat_penalty": 1.1,  # Prevent repetition
        "grammar_file": "unknown_set.gbnf"  # Standard grammar file
    }
    
    def get_grammar_params(self, model_name: str = None) -> dict:
        """Get standardized parameters for grammar generation"""
        params = self.DEFAULT_PARAMS.copy()
        
        # Model-specific adjustments
        if model_name and "qwen" in model_name.lower():
            # Qwen models work well with these parameters
            pass
        elif model_name and "distilgpt2" in model_name.lower():
            # DistilGPT-2 may need different parameters
            params["temperature"] = 0.3  # Slightly higher for variety
        
        return params
```

###### 4.2.2 System Prompt Integration
```python
# orac/llama_cpp_client.py
class SystemPromptManager:
    """Manages system prompts for grammar generation"""
    
    # Effective system prompt from testing
    GRAMMAR_SYSTEM_PROMPT = """Apply to unknown_set....

You are a helpful assistant that extracts structured information from natural language commands for Home Assistant automation. Parse the following command and extract the device, action, and location components."""
    
    def get_grammar_prompt(self, user_command: str) -> str:
        """Generate complete prompt with system prompt and user command"""
        return f"{self.GRAMMAR_SYSTEM_PROMPT}\n\nCommand: {user_command}\n\nJSON:"
```

###### 4.2.3 Grammar File Deployment
```python
# orac/homeassistant/grammar_manager.py
class GrammarDeploymentManager:
    """Manages grammar file deployment and loading"""
    
    def deploy_grammar_file(self, grammar_content: str, filename: str = "unknown_set.gbnf"):
        """Deploy grammar file to correct location for API access"""
        # Implementation to deploy grammar file to /app/data/test_grammars/
        # Ensure API can access the grammar file
    
    def validate_grammar_file(self, grammar_content: str) -> bool:
        """Validate grammar file syntax before deployment"""
        # Implementation to validate GBNF syntax
        # Check for underscore rule names (invalid)
        # Verify JSON structure is correct
```

##### 4.3 Production Readiness Features

**Goal**: Add production-ready features for robust grammar parsing.

**Implementation Plan**:

###### 4.3.1 JSON Schema Validation
```python
# orac/homeassistant/grammar_validator.py
from typing import Dict, Any, Optional
import json
from jsonschema import validate, ValidationError

class GrammarResponseValidator:
    """Validates grammar parsing responses"""
    
    # JSON schema for grammar responses
    GRAMMAR_RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "device": {"type": "string"},
            "action": {"type": "string"},
            "location": {"type": "string"}
        },
        "required": ["device", "action", "location"],
        "additionalProperties": False
    }
    
    def validate_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Validate and parse grammar response"""
        try:
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                return None
            
            json_str = response_text[json_start:json_end]
            parsed_json = json.loads(json_str)
            
            # Validate against schema
            validate(instance=parsed_json, schema=self.GRAMMAR_RESPONSE_SCHEMA)
            
            return parsed_json
            
        except (json.JSONDecodeError, ValidationError) as e:
            # Log validation error
            return None
```

###### 4.3.2 Comprehensive Logging
```python
# orac/homeassistant/grammar_logger.py
import logging
from typing import Dict, Any, Optional

class GrammarLogger:
    """Comprehensive logging for grammar parsing"""
    
    def __init__(self):
        self.logger = logging.getLogger("grammar_parser")
        self.logger.setLevel(logging.DEBUG)
    
    def log_grammar_request(self, command: str, model: str, params: Dict[str, Any]):
        """Log grammar parsing request"""
        self.logger.info(f"Grammar request: command='{command}', model='{model}', params={params}")
    
    def log_grammar_response(self, response: str, parsed_json: Optional[Dict[str, Any]], 
                           success: bool, error: Optional[str] = None):
        """Log grammar parsing response"""
        if success:
            self.logger.info(f"Grammar success: response='{response}', parsed={parsed_json}")
        else:
            self.logger.error(f"Grammar failure: response='{response}', error='{error}'")
    
    def log_grammar_performance(self, command: str, response_time: float, token_count: int):
        """Log grammar parsing performance metrics"""
        self.logger.info(f"Grammar performance: command='{command}', time={response_time:.3f}s, tokens={token_count}")
```

###### 4.3.3 Fallback Mechanisms
```python
# orac/homeassistant/grammar_fallback.py
from typing import Dict, Any, Optional
import re

class GrammarFallbackHandler:
    """Handles fallback when grammar parsing fails"""
    
    def __init__(self):
        # Simple regex patterns for fallback parsing
        self.device_patterns = {
            "lights": r"\b(light|lights|lamp|bulb)\b",
            "thermostat": r"\b(heat|heating|cool|cooling|thermostat|temperature)\b",
            "blinds": r"\b(blind|blinds|curtain|shade)\b",
            "music": r"\b(music|speaker|audio|sound)\b",
            "tv": r"\b(tv|television|display|screen)\b",
            "fan": r"\b(fan|ventilation)\b"
        }
        
        self.action_patterns = {
            "on": r"\b(turn on|switch on|activate|start)\b",
            "off": r"\b(turn off|switch off|deactivate|stop)\b",
            "toggle": r"\b(toggle|switch)\b",
            "open": r"\b(open|raise|lift)\b",
            "close": r"\b(close|lower|shut)\b"
        }
        
        self.location_patterns = {
            "living room": r"\b(living room|living)\b",
            "bedroom": r"\b(bedroom|bed room)\b",
            "kitchen": r"\b(kitchen)\b",
            "bathroom": r"\b(bathroom|bath room)\b",
            "dining room": r"\b(dining room|dining)\b"
        }
    
    def fallback_parse(self, command: str) -> Optional[Dict[str, str]]:
        """Fallback parsing using regex patterns when grammar fails"""
        command_lower = command.lower()
        
        # Extract device
        device = "UNKNOWN"
        for device_type, pattern in self.device_patterns.items():
            if re.search(pattern, command_lower):
                device = device_type
                break
        
        # Extract action
        action = "UNKNOWN"
        for action_type, pattern in self.action_patterns.items():
            if re.search(pattern, command_lower):
                action = action_type
                break
        
        # Extract location
        location = "UNKNOWN"
        for location_type, pattern in self.location_patterns.items():
            if re.search(pattern, command_lower):
                location = location_type
                break
        
        return {
            "device": device,
            "action": action,
            "location": location
        }
```

**Success Criteria**:
- Grammar accuracy improved from 67% to >90%
- API uses standardized parameters and system prompts
- Comprehensive error handling and fallback mechanisms
- Production-ready logging and validation
- Performance optimization for low latency

**Files to Modify**:
- `orac/homeassistant/grammar_manager.py` - Grammar optimization and deployment
- `orac/llama_cpp_client.py` - Parameter standardization and system prompts
- `orac/homeassistant/grammar_validator.py` - JSON schema validation
- `orac/homeassistant/grammar_logger.py` - Comprehensive logging
- `orac/homeassistant/grammar_fallback.py` - Fallback mechanisms
- `data/test_grammars/unknown_set.gbnf` - Optimized grammar file

**Impact**:
- **Accuracy**: Significant improvement in grammar parsing accuracy
- **Reliability**: Robust error handling and fallback mechanisms
- **Consistency**: Standardized parameters across all API calls
- **Production Ready**: Comprehensive logging and validation
- **Performance**: Optimized for production latency requirements

**Next Steps**:
1. Implement grammar rule reordering and device type expansion
2. Add parameter standardization and system prompt integration
3. Implement JSON schema validation and comprehensive logging
4. Add fallback mechanisms for graceful degradation
5. Test all improvements thoroughly with real Home Assistant commands

### 🔄 **NEXT - Domain-to-Device Mapping Logic**

#### Current State
- No domain mapping logic exists
- Need to convert complex HA domains to simple device types
- Must handle edge cases (switches that control lights, media players that are TVs vs speakers)

#### Implementation Priority: **HIGHEST**

##### 2.1 Create Domain Mapping Class
```python
# orac/homeassistant/domain_mapper.py
from typing import Dict, List, Optional, Any
from enum import Enum

class DeviceType(str, Enum):
    """Simplified device types for user-friendly commands"""
    LIGHTS = "lights"
    THERMOSTAT = "thermostat"
    FAN = "fan"
    BLINDS = "blinds"
    TV = "tv"
    MUSIC = "music"
    ALARM = "alarm"
    SWITCH = "switch"  # Generic switches not controlling lights

class DomainMapper:
    """Maps Home Assistant domains to simplified device types"""
    
    # Core domain mappings
    DOMAIN_TO_DEVICE_TYPE = {
        'light': DeviceType.LIGHTS,
        'climate': DeviceType.THERMOSTAT,
        'fan': DeviceType.FAN,
        'cover': DeviceType.BLINDS,
        'alarm_control_panel': DeviceType.ALARM,
    }
    
    # Actions available for each domain
    DOMAIN_ACTIONS = {
        'light': ["turn on", "turn off", "toggle", "dim", "brighten", "set to %"],
        'switch': ["turn on", "turn off", "toggle"],
        'climate': ["turn on", "turn off", "set to %", "increase", "decrease"],
        'fan': ["turn on", "turn off", "toggle", "set to %"],
        'cover': ["open", "close", "raise", "lower", "set to %"],
        'media_player': ["turn on", "turn off", "play", "pause", "stop", "set to %"],
        'alarm_control_panel': ["turn on", "turn off", "toggle"]
    }
    
    def determine_device_type(self, entity: Dict[str, Any], domain: str) -> Optional[DeviceType]:
        """Determine simplified device type from HA entity"""
        
        # Handle media players (TV vs Music)
        if domain == 'media_player':
            return self._determine_media_player_type(entity)
        
        # Handle switches (lights vs generic)
        if domain == 'switch':
            return self._determine_switch_type(entity)
        
        # Handle covers (blinds vs other covers)
        if domain == 'cover':
            return self._determine_cover_type(entity)
        
        # Default domain mapping
        return self.DOMAIN_TO_DEVICE_TYPE.get(domain)
    
    def _determine_media_player_type(self, entity: Dict[str, Any]) -> DeviceType:
        """Determine if media player is TV or music device"""
        entity_id = entity['entity_id'].lower()
        friendly_name = entity.get('attributes', {}).get('friendly_name', '').lower()
        device_class = entity.get('attributes', {}).get('device_class', '').lower()
        
        # TV indicators
        tv_indicators = ['tv', 'television', 'display', 'monitor', 'screen']
        if any(indicator in entity_id for indicator in tv_indicators):
            return DeviceType.TV
        if any(indicator in friendly_name for indicator in tv_indicators):
            return DeviceType.TV
        if 'tv' in device_class:
            return DeviceType.TV
        
        # Music indicators
        music_indicators = ['speaker', 'audio', 'sound', 'music', 'amp', 'receiver']
        if any(indicator in entity_id for indicator in music_indicators):
            return DeviceType.MUSIC
        if any(indicator in friendly_name for indicator in music_indicators):
            return DeviceType.MUSIC
        
        # Default to music for unknown media players
        return DeviceType.MUSIC
    
    def _determine_switch_type(self, entity: Dict[str, Any]) -> Optional[DeviceType]:
        """Determine if switch controls lights or is generic"""
        entity_id = entity['entity_id'].lower()
        friendly_name = entity.get('attributes', {}).get('friendly_name', '').lower()
        
        # Light control indicators
        light_indicators = ['light', 'lamp', 'bulb', 'ceiling', 'wall', 'floor']
        if any(indicator in entity_id for indicator in light_indicators):
            return DeviceType.LIGHTS
        if any(indicator in friendly_name for indicator in light_indicators):
            return DeviceType.LIGHTS
        
        # Skip generic switches (don't include in mapping)
        return None
    
    def _determine_cover_type(self, entity: Dict[str, Any]) -> DeviceType:
        """Determine cover type (default to blinds)"""
        entity_id = entity['entity_id'].lower()
        friendly_name = entity.get('attributes', {}).get('friendly_name', '').lower()
        
        # Non-blind indicators
        non_blind_indicators = ['garage', 'door', 'gate', 'shutter']
        if any(indicator in entity_id for indicator in non_blind_indicators):
            return DeviceType.SWITCH  # Treat as generic switch
        
        return DeviceType.BLINDS
    
    def get_actions_for_device_type(self, device_type: DeviceType) -> List[str]:
        """Get available actions for a device type"""
        actions = set()
        
        # Find which domains map to this device type
        for domain, mapped_type in self.DOMAIN_TO_DEVICE_TYPE.items():
            if mapped_type == device_type:
                actions.update(self.DOMAIN_ACTIONS.get(domain, []))
        
        # Handle special cases
        if device_type == DeviceType.TV:
            actions.update(self.DOMAIN_ACTIONS.get('media_player', []))
        elif device_type == DeviceType.MUSIC:
            actions.update(self.DOMAIN_ACTIONS.get('media_player', []))
        
        return sorted(list(actions))
```

##### 2.2 Add Data Models for Device Types
```python
# orac/homeassistant/models.py
class DeviceMapping(BaseModel):
    """Model for device type mapping"""
    entity_id: str
    device_type: DeviceType
    domain: str
    friendly_name: Optional[str] = None
    area_id: Optional[str] = None
    location: Optional[str] = None
    supported_actions: List[str] = Field(default_factory=list)
```

#### Success Criteria
- [ ] All major HA domains mapped to simplified device types
- [ ] Smart detection for media players (TV vs Music)
- [ ] Smart detection for switches (lights vs generic)
- [ ] Proper action mapping for each device type
- [ ] Edge cases handled correctly

### 🔄 **PENDING - Location Detection Algorithm**

#### Current State
- No location detection logic exists
- Need multiple fallback strategies
- Must handle missing area assignments gracefully

#### Implementation Priority: **HIGHEST**

##### 3.1 Create Location Detection Class
```python
# orac/homeassistant/location_detector.py
from typing import Dict, List, Optional, Any, Set
import re

class LocationDetector:
    """Detects entity locations using multiple strategies"""
    
    def __init__(self):
        # Common location patterns
        self.common_locations = {
            'bedroom': ['bedroom', 'master', 'guest', 'kids', 'child'],
            'kitchen': ['kitchen', 'cooking', 'pantry'],
            'living room': ['living', 'lounge', 'family', 'sitting'],
            'bathroom': ['bathroom', 'toilet', 'shower', 'washroom'],
            'office': ['office', 'study', 'workspace', 'desk'],
            'garage': ['garage', 'carport'],
            'basement': ['basement', 'cellar'],
            'attic': ['attic', 'loft'],
            'hallway': ['hall', 'corridor', 'passage'],
            'dining room': ['dining', 'dinner'],
            'laundry': ['laundry', 'utility', 'washer'],
            'outdoor': ['outdoor', 'outside', 'exterior', 'garden', 'patio']
        }
    
    def detect_location(self, 
                       entity: Dict[str, Any],
                       entity_area_map: Dict[str, str],
                       device_area_map: Dict[str, str],
                       areas: Dict[str, str],
                       entity_registry: List[Dict[str, Any]]) -> Optional[str]:
        """Detect entity location using multiple strategies"""
        
        entity_id = entity['entity_id']
        
        # Strategy 1: Direct entity area assignment
        location = self._check_entity_area_assignment(entity_id, entity_area_map, areas)
        if location:
            return location
        
        # Strategy 2: Device area assignment
        location = self._check_device_area_assignment(entity_id, device_area_map, areas, entity_registry)
        if location:
            return location
        
        # Strategy 3: Parse from entity ID
        location = self._parse_from_entity_id(entity_id)
        if location:
            return location
        
        # Strategy 4: Parse from friendly name
        location = self._parse_from_friendly_name(entity)
        if location:
            return location
        
        # Strategy 5: Parse from device info
        location = self._parse_from_device_info(entity, entity_registry)
        if location:
            return location
        
        return None
    
    def _check_entity_area_assignment(self, entity_id: str, entity_area_map: Dict[str, str], areas: Dict[str, str]) -> Optional[str]:
        """Check if entity has direct area assignment"""
        if entity_id in entity_area_map:
            area_id = entity_area_map[entity_id]
            if area_id in areas:
                return self._normalize_location_name(areas[area_id])
        return None
    
    def _check_device_area_assignment(self, entity_id: str, device_area_map: Dict[str, str], areas: Dict[str, str], entity_registry: List[Dict[str, Any]]) -> Optional[str]:
        """Check if entity's device has area assignment"""
        # Find device ID for this entity
        device_id = None
        for reg_entity in entity_registry:
            if reg_entity['entity_id'] == entity_id and reg_entity.get('device_id'):
                device_id = reg_entity['device_id']
                break
        
        if device_id and device_id in device_area_map:
            area_id = device_area_map[device_id]
            if area_id in areas:
                return self._normalize_location_name(areas[area_id])
        
        return None
    
    def _parse_from_entity_id(self, entity_id: str) -> Optional[str]:
        """Parse location from entity ID"""
        entity_id_lower = entity_id.lower()
        
        for location, patterns in self.common_locations.items():
            for pattern in patterns:
                if pattern in entity_id_lower:
                    return location
        
        return None
    
    def _parse_from_friendly_name(self, entity: Dict[str, Any]) -> Optional[str]:
        """Parse location from friendly name"""
        friendly_name = entity.get('attributes', {}).get('friendly_name', '').lower()
        if not friendly_name:
            return None
        
        for location, patterns in self.common_locations.items():
            for pattern in patterns:
                if pattern in friendly_name:
                    return location
        
        return None
    
    def _parse_from_device_info(self, entity: Dict[str, Any], entity_registry: List[Dict[str, Any]]) -> Optional[str]:
        """Parse location from device information"""
        entity_id = entity['entity_id']
        
        # Find device info for this entity
        for reg_entity in entity_registry:
            if reg_entity['entity_id'] == entity_id:
                device_name = reg_entity.get('name', '').lower()
                if device_name:
                    for location, patterns in self.common_locations.items():
                        for pattern in patterns:
                            if pattern in device_name:
                                return location
                break
        
        return None
    
    def _normalize_location_name(self, area_name: str) -> str:
        """Normalize area name to standard location format"""
        # Convert to lowercase and replace underscores/hyphens with spaces
        normalized = area_name.lower().replace('_', ' ').replace('-', ' ')
        
        # Map common variations to standard names
        location_mapping = {
            'living': 'living room',
            'lounge': 'living room',
            'family room': 'living room',
            'sitting room': 'living room',
            'dining': 'dining room',
            'dinner room': 'dining room',
            'master bedroom': 'bedroom',
            'guest bedroom': 'bedroom',
            'kids bedroom': 'bedroom',
            'child bedroom': 'bedroom',
            'utility room': 'laundry',
            'washer room': 'laundry',
            'garden': 'outdoor',
            'patio': 'outdoor',
            'backyard': 'outdoor',
            'front yard': 'outdoor'
        }
        
        return location_mapping.get(normalized, normalized)
    
    def get_discovered_locations(self, entities: List[Dict[str, Any]], **kwargs) -> Set[str]:
        """Get all discovered locations from entities"""
        locations = set()
        
        for entity in entities:
            location = self.detect_location(entity, **kwargs)
            if location and location not in ['unknown', 'all', 'everywhere']:
                locations.add(location)
        
        return locations
```

##### 3.2 Add Location Validation
```python
def validate_location_detection(self, entities: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
    """Validate location detection results"""
    results = {
        'total_entities': len(entities),
        'entities_with_locations': 0,
        'entities_without_locations': 0,
        'detection_methods': {
            'entity_area': 0,
            'device_area': 0,
            'entity_id_parse': 0,
            'friendly_name_parse': 0,
            'device_info_parse': 0
        },
        'locations_found': set(),
        'entities_without_location': []
    }
    
    for entity in entities:
        # Track which method was used (simplified)
        location = self.detect_location(entity, **kwargs)
        if location:
            results['entities_with_locations'] += 1
            results['locations_found'].add(location)
        else:
            results['entities_without_locations'] += 1
            results['entities_without_location'].append(entity['entity_id'])
    
    return results
```

#### Success Criteria
- [ ] Multiple detection strategies implemented
- [ ] Graceful fallback when area assignments missing
- [ ] Location name normalization
- [ ] Validation and reporting capabilities
- [ ] Handles edge cases and variations

## Integration Testing Plan

### Test Scenarios
1. **Complete Setup**: Entity with area assignment
2. **Device Assignment**: Entity without direct area but device has area
3. **Name Parsing**: Entity with location in name/ID
4. **Missing Data**: Entity with no location information
5. **Edge Cases**: Unusual naming patterns

### Validation Metrics
- Location detection success rate > 90%
- Device type mapping accuracy > 95%
- API endpoint reliability > 99%

## Implementation Order

1. **Week 1**: Entity Registry API Integration ✅ **COMPLETED**
2. **Week 2**: Domain-to-Device Mapping Logic 🔄 **NEXT**
3. **Week 3**: Location Detection Algorithm 🔄 **PENDING**
4. **Week 4**: Integration and Testing 🔄 **PENDING**

---

## ✅ **COMPLETED SECTIONS**

### ✅ **COMPLETED - Git Submodule Approach for llama.cpp Integration**

#### Current State
- Manual llama.cpp binaries are currently in `third_party/llama_cpp/`
- Need to transition to proper Git submodule for version control
- **Target repository**: `https://github.com/2oby/llama-cpp-jetson.git` (custom Jetson-optimized)
- **Key advantage**: Pre-compiled binaries specifically for NVIDIA Jetson Orin with Qwen3 support
- **Repository state**: Only 2 commits, simplified version management
- Jetson-specific builds with CUDA 12.x support

#### Implementation Priority: **HIGHEST** ✅ **COMPLETED**

##### Phase 1: Preparation & Coordination ✅ **COMPLETED**
- **Step 1.1**: Verified current state on both machines
  - Local machine: Commit `0f3b67e` (pre-submodule-setup-23e44c2)
  - Remote machine: Same commit state
  - Manual binaries present in `third_party/llama_cpp/`
  - `.gitmodules` file removed
- **Step 1.2**: Decided on target version
  - **Repository**: `https://github.com/2oby/llama-cpp-jetson.git`
  - **Version**: `v0.1.0-llama-cpp-b5306` (commit `f93f74b`)
  - **Reasoning**: First tagged commit with original build script and working binaries

##### Phase 2: Set up Submodule on Local Machine ✅ **COMPLETED**
- **Step 2.1**: Backup current binaries
  - **Local**: `llama_cpp_backup_20250627_144954`
  - **Remote**: `llama_cpp_backup_20250627_145139`
- **Step 2.2**: Remove current manual installation
  - Cleaned up old binaries and git references
  - Removed from git index
- **Step 2.3**: Add submodule
  - Successfully added `https://github.com/2oby/llama-cpp-jetson.git`
  - Created `.gitmodules` file
- **Step 2.4**: Checkout specific version
  - Checked out tag `v0.1.0-llama-cpp-b5306` (commit `f93f74b`)
  - Confirmed: "Add original build script that produced current working binaries"
- **Step 2.5**: Verify Jetson binaries
  - All expected binaries present: `llama-cli`, `llama-server`, `llama-quantize`, etc.
- **Step 2.6**: Commit the submodule setup
  - Commit `269e466`: "Add llama-cpp-jetson as Git submodule (v0.1.0-llama-cpp-b5306)"

##### Phase 3: Sync to Test Machine ✅ **COMPLETED**
- **Step 3.1**: Push changes from local machine
  - Successfully pushed commit `269e466` to remote repository
- **Step 3.2**: Pull changes on test machine (Jetson)
  - Fast-forward merge from `0f3b67e` to `269e466`
  - `.gitmodules` file created
  - Submodule reference updated
- **Step 3.3**: Initialize submodule on test machine (Jetson)
  - Submodule registered and initialized
  - Checked out commit `f93f74b` (v0.1.0-llama-cpp-b5306)
  - All files present including `bin/`, `lib/`, `include/` directories

##### Phase 4: Verification & Testing ✅ **COMPLETED**
- **Step 4.1**: Verify submodule status on both machines
  - **Local Machine**: Commit `f93f74b` (v0.1.0-llama-cpp-b5306)
  - **Remote Machine**: Same commit `f93f74b` (v0.1.0-llama-cpp-b5306)
  - **Both machines**: Identical submodule state
- **Step 4.2**: Test binary functionality
  - **Mac**: Binaries present but won't run (expected - wrong architecture)
  - **Jetson**: Both `llama-server` and `llama-cli` work correctly
  - **CUDA Support**: Detected Orin with compute capability 8.7
- **Step 4.3**: Integration testing
  - All expected binaries present in submodule
  - Submodule properly integrated into project structure

##### Phase 5: Create Management Scripts ✅ **COMPLETED**
- **Step 5.1**: Create Binary Update Script
- **Step 5.2**: Create Binary Version Check Script
- **Step 5.3**: Create Rollback Script
- **Step 5.4**: Script Design Philosophy

##### Phase 6: Documentation & Cleanup ✅ **COMPLETED**
- **Step 6.1**: Update Documentation
- **Step 6.2**: Clean up Temporary Files

##### Phase 7: Rollback Plan ✅ **COMPLETED**
- **Step 7.1**: Emergency Rollback Script

#### Success Criteria ✅ **ALL COMPLETED**
- ✅ Submodule properly initialized on both machines
- ✅ Latest commit from llama-cpp-jetson checked out
- ✅ All Jetson-optimized binaries present and functional
- ✅ ORAC integration tests pass
- ✅ Management scripts work as expected
- ✅ Documentation updated with Jetson-specific information
- ✅ Rollback plan in place

### ✅ **COMPLETED - Entity Registry API Integration**

#### Current State
- ✅ Current client fetches `/api/states`, `/api/services`, `/api/areas`
- ✅ Added entity registry and device registry endpoints
- ✅ Area assignment data now available

#### Implementation Priority: **HIGHEST** ✅ **COMPLETED**

##### 1.1 Add New API Endpoints to Constants ✅ **COMPLETED**
```python
# orac/homeassistant/constants.py
API_ENTITY_REGISTRY = "/api/config/entity_registry/list"
API_DEVICE_REGISTRY = "/api/config/device_registry/list"
```

##### 1.2 Extend Client with Entity Registry Methods ✅ **COMPLETED**
```python
# orac/homeassistant/client.py
async def get_entity_registry(self, use_cache: bool = True) -> List[Dict[str, Any]]:
    """Get entity registry with area assignments"""
    if use_cache:
        cached_registry = self._cache.get_entity_registry()
        if cached_registry is not None:
            return cached_registry
    
    try:
        registry = await self._request("GET", API_ENTITY_REGISTRY)
        self._cache.set_entity_registry(registry)
        return registry
    except aiohttp.ClientError as e:
        logger.warning(f"Failed to fetch entity registry: {e}")
        return []

async def get_device_registry(self, use_cache: bool = True) -> List[Dict[str, Any]]:
    """Get device registry with area assignments"""
    if use_cache:
        cached_devices = self._cache.get_device_registry()
        if cached_devices is not None:
            return cached_devices
    
    try:
        devices = await self._request("GET", API_DEVICE_REGISTRY)
        self._cache.set_device_registry(devices)
        return devices
    except aiohttp.ClientError as e:
        logger.warning(f"Failed to fetch device registry: {e}")
        return []
```

##### 1.3 Add Cache Support for New Endpoints ✅ **COMPLETED**
```python
# orac/homeassistant/cache.py
def set_entity_registry(self, registry: List[Dict[str, Any]]) -> None:
    """Cache entity registry data"""
    self._cache['entity_registry'] = {
        'data': registry,
        'timestamp': time.time()
    }

def get_entity_registry(self) -> Optional[List[Dict[str, Any]]]:
    """Get cached entity registry data"""
    return self._get_cached_data('entity_registry')

def set_device_registry(self, devices: List[Dict[str, Any]]) -> None:
    """Cache device registry data"""
    self._cache['device_registry'] = {
        'data': devices,
        'timestamp': time.time()
    }

def get_device_registry(self) -> Optional[List[Dict[str, Any]]]:
    """Get cached device registry data"""
    return self._get_cached_data('device_registry')
```

#### Success Criteria ✅ **ALL COMPLETED**
- ✅ Entity registry endpoint returns area assignments
- ✅ Device registry endpoint returns device area mappings
- ✅ Cache properly stores and retrieves registry data
- ✅ Error handling for missing endpoints

## Progress Summary

### ✅ **COMPLETED - Entity Registry API Integration**
- **Constants Updated**: Added `API_ENTITY_REGISTRY` and `API_DEVICE_REGISTRY` endpoints
- **Client Enhanced**: Added `get_entity_registry()` and `get_device_registry()` methods with proper error handling
- **Cache Extended**: Added `set_entity_registry()`, `get_entity_registry()`, `set_device_registry()`, `get_device_registry()` methods
- **Testing**: Updated `test_connection.py` to test new endpoints
- **Error Handling**: Graceful fallback when endpoints are not available (404 errors)

### 🔄 **NEXT STEPS - Domain-to-Device Mapping Logic**
1. Create `orac/homeassistant/domain_mapper.py` with `DomainMapper` class
2. Implement domain-to-device-type mapping logic
3. Add smart detection for media players (TV vs Music)
4. Add smart detection for switches (lights vs generic)
5. Add action mapping for each device type

### 🔄 **PENDING - Location Detection Algorithm**
1. Create `orac/homeassistant/location_detector.py` with `LocationDetector` class
2. Implement multiple fallback strategies for location detection
3. Add location name normalization
4. Add validation and reporting capabilities

This focused approach ensures the core functionality works before adding additional features. 