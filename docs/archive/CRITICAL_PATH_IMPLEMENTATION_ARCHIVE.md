# Critical Path Implementation - Historic Archive

> **Note**: This file contains historic development information that is no longer current but preserved for reference.

## 🚨 **RESOLVED - GBNF Parsing Bug in llama.cpp v5306**

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
   - Monitor GitHub issues #4799 and #7991 for updates
   - Test with community-provided workarounds or patches
   - Consider contributing to llama.cpp if fixes are identified

#### Status: 🔄 **WORKAROUND IMPLEMENTED**
- Using simplified grammars that work with version 5306
- Fallback to unconstrained generation with post-processing validation
- Monitoring for llama.cpp updates and community fixes

---

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

## Historic Implementation Details

### Temperature Grammar Issue - RESOLVED

#### Problem Identified
- **Temperature commands not working properly** - Most temperature commands return `{"device":"heating","action":"on","location":"living room"}` instead of the temperature value
- **Percentage commands not working** - Percentage commands return heating actions instead of percentage values
- **System prompt overriding grammar** - The model is following the system prompt instructions instead of strictly following the grammar rules
- **Default model missing from config** - `Qwen3-0.6B-Q8_0.gguf` not properly configured in model_configs.yaml

#### Root Cause
The system prompt is too generic and doesn't provide specific guidance for temperature and percentage handling. The grammar has the correct rules, but the model isn't using them properly.

#### Solution
Update the system prompt for the default model to be more specific about temperature and percentage handling:

```
/no_think You are a JSON-only formatter. For each user input, map the device to the grammar-defined device ("heating" for heater/temperature, "blinds" for curtains/blinds, "lights" for lighting) and select the most appropriate action for that device (e.g., "on", "off", "set <temp>" for heating; "open", "close", "set <pct>%" for blinds; "on", "off", "set <pct>%", "warm" for lights) based on the grammar. Use "UNKNOWN" for unrecognized inputs. Output only the single-line JSON object with keys: "device", "action", "location".

Examples:
"set bathroom temp to 20 degrees" → {"device":"heating","action":"set 20C","location":"bathroom"}
"set the lights to warm in the bedroom" → {"device":"lights","action":"warm","location":"bedroom"}
```

#### Recommended Settings
- **Temperature**: 0.1
- **Top P**: 0.2  
- **Top-K**: 10
- **Max Tokens**: 50
- **JSON Mode**: True

#### Status: ✅ **RESOLVED**

### Model Settings Persistence Fixes - RESOLVED

#### Issues Identified
- **Incorrect API endpoints** in reset settings function (`/api/` instead of `/v1/`)
- **Missing error handling** in settings loading
- **Race conditions** between model loading and settings application
- **Insufficient fallback logic** for missing settings

#### Fixes Implemented
- ✅ Fixed API endpoints in reset settings function
- ✅ Enhanced `updateSettingsPanel()` with robust fallback logic
- ✅ Added settings validation and auto-recovery
- ✅ Implemented periodic settings validation (every 30 seconds)
- ✅ Added page visibility change handling
- ✅ Enhanced model selection handler with delay to prevent race conditions
- ✅ Added comprehensive logging for debugging
- ✅ Created settings persistence test script

#### Files Modified
- `orac/static/js/main.js` - Enhanced settings persistence and validation
- `test_settings_persistence.py` - New test script for settings validation

#### Status: ✅ **RESOLVED** 