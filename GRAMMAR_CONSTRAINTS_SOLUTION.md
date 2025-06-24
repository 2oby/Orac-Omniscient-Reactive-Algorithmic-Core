# Grammar Constraints Solution

## Problem Summary

The LLM was ignoring grammar constraints and generating responses that didn't match the vocabulary:

**Expected vs Actual Behavior:**
- Expected: "turn on the toilet lights" → {"device": "toilet lights", "action": "turn on", "location": "toilet"}
- Actual: "turn on the toilet lights" → {"device": "toilet", "action": "turn on", "location": "toilet"}
- Expected: "turn on the attic lights" → Should fail (not in grammar)
- Actual: "turn on the attic lights" → {"device": "attic", "action": "turn on", "location": "home"}

## Root Causes Identified

1. **No Home Assistant Command Endpoint** - The `/v1/generate` endpoint used basic JSON grammar, not Home Assistant-specific grammar
2. **Static Grammar Constraints** - The `data/grammars.yaml` file had static constraints that didn't include discovered entities
3. **No Dynamic Grammar Integration** - The `HomeAssistantGrammarManager` generated dynamic grammar but it wasn't being used by the LLM
4. **Missing GBNF Grammar Generation** - The grammar manager generated JSON schema, not GBNF strings for llama.cpp

## Solution Implemented

### 1. Created Home Assistant Command Endpoint

**File:** `orac/api.py`
- Added `/v1/homeassistant/command` endpoint
- Uses dynamic grammar from `HomeAssistantGrammarManager`
- Validates responses against grammar constraints
- Returns detailed error messages for violations

```python
@app.post("/v1/homeassistant/command", tags=["Home Assistant"])
async def process_homeassistant_command(request: HomeAssistantCommandRequest) -> Dict[str, Any]:
    """Process a Home Assistant command using dynamic grammar constraints."""
```

### 2. Enhanced LLM Client with Custom Grammar Support

**File:** `orac/llama_cpp_client.py`
- Added `generate_with_custom_grammar()` method
- Accepts custom GBNF grammar strings
- Passes grammar in request instead of server startup
- Maintains backward compatibility

```python
async def generate_with_custom_grammar(
    self,
    prompt: str,
    model: str,
    custom_grammar: str,
    # ... other parameters
) -> PromptResponse:
```

### 3. Added GBNF Grammar Generation

**File:** `orac/homeassistant/grammar_manager.py`
- Added `generate_gbnf_grammar()` method
- Converts JSON schema to GBNF format for llama.cpp
- Creates constrained grammar rules for device, action, and location
- Handles escaping and alternation properly

```python
def generate_gbnf_grammar(self, grammar_dict: Optional[Dict[str, Any]] = None) -> str:
    """Generate a GBNF grammar string from the grammar dictionary."""
```

### 4. Enhanced Grammar Constraints

**File:** `orac/homeassistant/grammar_manager.py`
- Improved location detection to include "toilet", "attic", etc.
- Enhanced device vocabulary generation with friendly names
- Added fallback to entity_id when friendly name is NULL
- Real-time grammar updates from discovered entities

### 5. Auto-Popup System for New Entities

**Files:** `orac/api.py`, `orac/static/js/main.js`, `orac/templates/index.html`
- Added `/v1/homeassistant/mapping/check-auto-popup` endpoint
- Automatic detection of new entities every 30 seconds
- User-friendly popup interface for adding friendly names
- Smart suggestions based on entity ID patterns
- Cooldown system to prevent spam (5 minutes after dismissal)
- Toggle button to enable/disable auto-popup

```python
@app.get("/v1/homeassistant/mapping/check-auto-popup", tags=["Home Assistant"])
async def check_auto_popup() -> Dict[str, Any]:
    """Check if there are new entities that need friendly names and should trigger popup."""
```

## Key Features

### Dynamic Grammar Generation
- Grammar is generated from actual Home Assistant entities
- Includes all discovered devices, actions, and locations
- Updates automatically when new entities are discovered
- No manual configuration required

### Strict Grammar Enforcement
- LLM is constrained to use only vocabulary from discovered entities
- Invalid responses are caught and reported with detailed errors
- Grammar violations show available vocabulary for debugging

### Real-time Entity Discovery
- Auto-discovery finds new entities automatically
- Friendly names are mapped or fallback to entity_id
- Grammar updates immediately when entities change

### Comprehensive Validation
- Response validation against grammar constraints
- JSON structure validation
- Required field validation
- Detailed error reporting

### Auto-Popup System for New Entities
- Automatically detects when new entities are discovered
- Shows popup to prompt user for friendly names
- Checks every 30 seconds for new entities
- Includes cooldown to prevent spam (5 minutes after dismissal)
- User-friendly interface with suggestions and validation
- Can be enabled/disabled via UI toggle

## Testing

### Test Scripts Created

1. **`test_homeassistant_grammar_integration.py`** - Comprehensive end-to-end test
2. **`test_grammar_constraints.py`** - API endpoint testing
3. **`test_auto_popup.py`** - Auto-popup functionality testing
4. **`run_api_server.py`** - Simple server startup script

### Test Cases

```bash
# Start the API server
python run_api_server.py

# Run comprehensive tests
python test_homeassistant_grammar_integration.py

# Test specific commands
curl -X POST "http://localhost:8000/v1/homeassistant/command" \
     -H "Content-Type: application/json" \
     -d '{"command": "turn on the toilet lights"}'
```

## Expected Results

### ✅ Correct Behavior
- "turn on the toilet lights" → {"device": "toilet lights", "action": "turn on", "location": "toilet"}
- "turn on the bedroom lights" → {"device": "bedroom lights", "action": "turn on", "location": "bedroom"}

### ❌ Proper Error Handling
- "turn on the attic lights" → Error: "Device 'attic' not in vocabulary"
- Invalid commands → Clear error messages with available vocabulary

## Benefits

1. **Accurate Responses** - LLM only generates responses with valid vocabulary
2. **Real-time Updates** - Grammar updates automatically when entities change
3. **Clear Error Messages** - Users see exactly what went wrong and what's available
4. **No Manual Configuration** - System discovers and maps entities automatically
5. **Robust Validation** - Multiple layers of validation ensure quality responses
6. **Automatic Entity Management** - Popup system ensures new entities get friendly names
7. **User-Friendly Interface** - Intuitive popup with suggestions and validation

## Usage

### API Endpoint
```bash
POST /v1/homeassistant/command
Content-Type: application/json

{
  "command": "turn on the toilet lights"
}
```

### Response Format
```json
{
  "status": "success",
  "command": "turn on the toilet lights",
  "response": {
    "device": "toilet lights",
    "action": "turn on",
    "location": "toilet"
  },
  "grammar_constraints": {
    "devices": ["toilet lights", "bedroom lights", ...],
    "actions": ["turn on", "turn off", ...],
    "locations": ["toilet", "bedroom", ...]
  },
  "elapsed_ms": 150
}
```

## Conclusion

The grammar constraints are now properly enforced by:

1. **Dynamic grammar generation** from Home Assistant entities
2. **GBNF grammar strings** for llama.cpp compatibility
3. **Custom grammar support** in the LLM client
4. **Comprehensive validation** of LLM responses
5. **Real-time entity discovery** and mapping

The LLM will now only generate responses that use vocabulary from discovered entities, ensuring accurate and valid Home Assistant commands. 