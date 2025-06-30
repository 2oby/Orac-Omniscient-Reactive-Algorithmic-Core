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
- The model had to generate the complete JSON from scratch
- **CRITICAL ISSUE**: API was hardcoding system prompts for grammar files instead of respecting user-provided prompts

## ✅ **RESOLUTION - COMPLETED**

### Fix 1: Grammar Conflict Resolution
**Problem**: Server started with `--grammar-file` but HTTP request also included JSON grammar
**Solution**: Modified `llama_cpp_client.py` to not include grammar in HTTP request when using grammar files

### Fix 2: System Prompt Respect ✅
**Problem**: API was hardcoding system prompts for grammar files, ignoring user-provided prompts
**Solution**: Modified `api.py` to respect `request.system_prompt` when available, even for grammar files

**Code Change**:
```python
# Before (hardcoded)
system_prompt = "You are a JSON-only formatter. Respond with a JSON object containing 'device', 'action', and 'location' keys."

# After (respects user input)
if request.system_prompt:
    system_prompt = request.system_prompt
else:
    system_prompt = "You are a JSON-only formatter. Respond with a JSON object containing 'device', 'action', and 'location' keys."
```

### Fix 3: Prompt Formatting Consistency
**Problem**: Different prompt formats between CLI and API
**Solution**: API now uses the same prompt structure as CLI test for grammar files

## Test Results ✅

**API Performance After Fix**:
- ✅ **API Valid JSON: 3/3** - All responses are valid JSON
- ✅ **System Prompt Working**: API respects custom system prompts
- ✅ **Accurate Responses**: 
  - "turn on bedroom lights" → `{"device":"lights","action":"on","location":"bedroom"}`
  - "turn off kitchen lights" → `{"device":"lights","action":"off","location":"kitchen"}`
  - "toggle living room lights" → `{"device":"lights","action":"toggle","location":"living room"}`

## Files Modified

1. **`orac/api.py`**: 
   - Added system prompt respect for grammar files
   - Improved prompt formatting consistency

2. **`orac/llama_cpp_client.py`**: 
   - Fixed grammar conflict between server and HTTP request

3. **`orac/static/js/main.js`**: 
   - Updated grammar file path for web interface

4. **`test_api_grammar_fix.py`**: 
   - Added comprehensive testing with system prompts

5. **`requirements.txt`**: 
   - Added `requests` module for testing

## Deployment Status

✅ **Successfully deployed and tested**
- Container running on Jetson Orin
- API responding correctly on port 8000
- Grammar files working properly
- System prompts being respected

## Conclusion

The API grammar formatting issue has been **completely resolved**. The web interface and API now:
- ✅ Respect user-provided system prompts
- ✅ Produce valid, grammar-constrained JSON
- ✅ Handle Home Assistant commands accurately
- ✅ Maintain consistency with CLI behavior

The system is now ready for production use with grammar-constrained generation. 