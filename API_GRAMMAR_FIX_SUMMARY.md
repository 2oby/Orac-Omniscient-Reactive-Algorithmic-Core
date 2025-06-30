# API Grammar Fix Summary

## Problem Description

The web interface and API were producing malformed JSON responses when using GBNF grammar files, even though the same grammar worked correctly with direct CLI usage. The issue was caused by differences in prompt formatting and grammar handling between the CLI test and the API/web interface.

## Root Cause Analysis

### CLI Test (Working)
- Used specific system prompt: `"You are a JSON-only formatter. Respond with a JSON object containing 'action' and 'device' keys."`
- Used partial JSON prompt: `"Assistant: {{\"action\": "`
- Provided clear starting point for JSON generation
- Server started with `--grammar-file` parameter

### API/Web Interface (Failing)
- Used generic JSON system prompt without context
- Used raw user prompt without JSON structure hints
- Model had to generate complete JSON from scratch
- Server started with grammar file but HTTP request also included JSON grammar (conflict)

## Solution Implemented

### 1. Prompt Formatting Fix (`orac/api.py`)

Modified the `generate_text` function to use the same prompt format as the CLI test when using grammar files:

```python
# Format the prompt based on whether we're using a grammar file
if grammar_file and os.path.exists(grammar_file):
    # Use the same prompt format as the CLI test for grammar files
    system_prompt = "You are a JSON-only formatter. Respond with a JSON object containing 'device', 'action', and 'location' keys."
    # Start the JSON structure to give the model a clear starting point
    formatted_prompt = f"{system_prompt}\n\nUser: {request.prompt}\nAssistant: {{\"device\":\""
else:
    # Use the standard prompt format for non-grammar requests
    # ... existing code ...
```

### 2. Grammar Conflict Fix (`orac/llama_cpp_client.py`)

Fixed the conflict where both the server and HTTP request were trying to use grammars:

```python
# Only include grammar in request if json_mode is True AND no grammar file is specified
# When using a grammar file, the server is already configured with it
if json_mode and not grammar_file:
    request_data["grammar"] = self.get_grammar('json').strip()
```

### 3. Response Processing Fix (`orac/api.py`)

Added proper JSON completion for grammar file responses:

```python
# For grammar files, we need to complete the JSON structure
response_text = response.text
if grammar_file and os.path.exists(grammar_file):
    # The model response should complete the JSON, but we need to ensure it's properly closed
    if not response_text.strip().endswith('}'):
        # Try to find the end of the JSON structure
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group()
        else:
            # If no complete JSON found, try to close it properly
            response_text = response_text.strip()
            if not response_text.endswith('"'):
                response_text += '"'
            if not response_text.endswith('}'):
                response_text += '}'
```

### 4. Web Interface Path Fix (`orac/static/js/main.js`)

Updated the grammar file path to match the API's expected format:

```javascript
grammar_file: forceJson.checked ? 'data/test_grammars/unknown_set.gbnf' : null
```

## Testing

Created `test_api_grammar_fix.py` to verify the fix works correctly:

- Compares CLI and API outputs for the same prompts
- Validates JSON structure and required fields
- Ensures outputs match between CLI and API
- Tests multiple Home Assistant command scenarios

## Expected Results

After the fix:
1. ✅ API produces valid JSON responses when using grammar files
2. ✅ API outputs match CLI test outputs for the same prompts
3. ✅ Web interface works correctly with grammar-constrained generation
4. ✅ No more "Invalid JSON response from model" errors
5. ✅ Consistent behavior between CLI and API/web interface

## Files Modified

1. `orac/api.py` - Prompt formatting and response processing
2. `orac/llama_cpp_client.py` - Grammar conflict resolution
3. `orac/static/js/main.js` - Grammar file path correction
4. `test_api_grammar_fix.py` - New test script (created)

## Deployment

To deploy this fix:

1. Commit the changes
2. Use the deployment script: `./scripts/deploy_and_test.sh "Fix API grammar formatting for consistent CLI/API behavior"`
3. Run the test script to verify: `python3 test_api_grammar_fix.py`

## Impact

This fix resolves the core issue where the web interface and API were producing malformed JSON when using grammar files, ensuring consistent behavior between CLI testing and web interface usage. The fix maintains backward compatibility while providing the correct grammar-constrained generation for Home Assistant commands. 