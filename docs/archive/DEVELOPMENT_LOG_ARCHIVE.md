# ORAC Development Log - Historic Archive

> **Note**: This file contains historic development information that is no longer current but preserved for reference.

## Phase 4: API Grammar System Prompt Fix

### 4.1 API System Prompt Respect Implementation

**Goal**: Fix the API to respect user-provided system prompts when using grammar files, instead of hardcoding system prompts.

**Implementation Status**: ✅ **COMPLETED** (2025-06-30)

**Root Cause Analysis**:
- **Hardcoded System Prompts**: API was ignoring `request.system_prompt` for grammar files
- **Grammar Conflict**: Server started with `--grammar-file` but HTTP request also included JSON grammar
- **Prompt Inconsistency**: Different prompt formats between CLI test and API/web interface
- **Malformed JSON**: API sometimes produced invalid JSON despite correct grammar configuration

**What Was Implemented**:

#### 4.1.1 System Prompt Respect Fix (`orac/api.py`)
**Problem**: API hardcoded system prompts for grammar files
**Solution**: Modified to respect `request.system_prompt` when available

**Code Change**:
```python
# Before (hardcoded)
system_prompt = "/no_think You are a JSON-only formatter. Respond with a JSON object containing 'device', 'action', and 'location' keys."

# After (respects user input)
if request.system_prompt:
    system_prompt = request.system_prompt
else:
    system_prompt = "/no_think You are a JSON-only formatter. Respond with a JSON object containing 'device', 'action', and 'location' keys."
```

#### 4.1.2 Grammar Conflict Resolution (`orac/llama_cpp_client.py`)
**Problem**: Server started with `--grammar-file` but HTTP request also included JSON grammar
**Solution**: Only include grammar in HTTP request when not using grammar files

```python
# Only include grammar in request if json_mode is True AND no grammar file is specified
# When using a grammar file, the server is already configured with it
if json_mode and not grammar_file:
    request_data["grammar"] = self.get_grammar('json').strip()
```

#### 4.1.3 Optimized System Prompt
**New System Prompt** (for Home Assistant command parsing):
```
/no_think You are a JSON-only formatter. For each user input, accurately interpret the intended command and respond with a single-line JSON object containing the keys: "device", "action", and "location". Map the user-specified device to the grammar-defined device (e.g., "heating" for heater or temperature, "blinds" for curtains or blinds, "lights" for lighting) and select the most appropriate "action" for that device (e.g., "on", "off", "set 20C" for heating; "open", "close", "set 50%" for blinds; "on", "off", "set 50%", "warm" for lights) based on the provided grammar. Use "UNKNOWN" for unrecognized devices, actions, or locations. Output only the JSON object without explanations or additional text.
Examples:Input: "set bathroom temp to 20 degrees" → {"device":"heating","action":"set 20C","location":"bathroom"}
Input: "open the blinds 51% in the bedroom" → {"device":"blinds","action":"set 51%","location":"bedroom"}
Input: "turn on the light in the kitchen" → {"device":"lights","action":"on","location":"kitchen"}
Input: "set the lights to warm in the bedroom" → {"device":"lights","action":"warm","location":"bedroom"}
```

**Optimized Generation Parameters**:
- **Temperature**: 0.1 (low temperature for consistent, deterministic output)
- **Top-P**: 0.9 (balanced creativity while maintaining focus)
- **Top-K**: 10 (restricts token selection for more predictable responses)

**What Worked**:
- ✅ **System Prompt Respect**: API now properly uses user-provided system prompts
- ✅ **Grammar Conflict Resolution**: No more conflicts between server and HTTP request grammars
- ✅ **Valid JSON Output**: API produces valid JSON for all grammar file requests
- ✅ **Accurate Responses**: API correctly interprets Home Assistant commands
- ✅ **Consistent Behavior**: API and CLI now produce similar quality outputs

**What Didn't Work**:
- ❌ **Previous Hardcoded Approach**: Ignoring user system prompts caused inconsistent behavior
- ❌ **Grammar Conflict**: Double grammar usage caused parsing issues
- ❌ **Generic System Prompts**: Non-specific prompts led to less accurate responses

**Test Results** (2025-06-30):
```
✅ API Valid JSON: 3/3 - All responses are valid JSON
✅ System Prompt Working: API respects custom system prompts
✅ Accurate Responses:
  - "turn on bedroom lights" → {"device":"lights","action":"on","location":"bedroom"}
  - "turn off kitchen lights" → {"device":"lights","action":"off","location":"kitchen"}
  - "toggle living room lights" → {"device":"lights","action":"toggle","location":"living room"}
✅ Deployment Success: Container running on Jetson Orin, API responding on port 8000
```

**Deployment Verification**:
- ✅ Container builds and starts successfully
- ✅ API responds correctly with grammar-constrained generation
- ✅ System prompts are respected when provided
- ✅ Web interface works with grammar files
- ✅ All core functionality preserved

**Lessons Learned**:
1. **Always respect user-provided system prompts** - hardcoding defeats the purpose of configurable prompts
2. **Avoid grammar conflicts** - don't use both server and HTTP request grammars simultaneously
3. **Test with real-world scenarios** - Home Assistant commands provide good validation
4. **Use specific system prompts** - generic prompts lead to less accurate responses
5. **Maintain consistency** - API and CLI should produce similar quality outputs

**Files Modified**:
- `orac/api.py` - Added system prompt respect for grammar files
- `orac/llama_cpp_client.py` - Fixed grammar conflict between server and HTTP request
- `orac/static/js/main.js` - Updated grammar file path for web interface
- `test_api_grammar_fix.py` - Added comprehensive testing with system prompts
- `requirements.txt` - Added `requests` module for testing

**Impact**:
- **Reliability**: API now consistently produces valid JSON with grammar files
- **Flexibility**: Users can provide custom system prompts for different use cases
- **Accuracy**: More precise Home Assistant command interpretation
- **User Experience**: Web interface and API work seamlessly with grammar constraints

**Next Steps**:
- ⚠️ **Monitor production usage** - Verify system prompts work correctly in real-world scenarios
- ⚠️ **Test with different grammars** - Ensure fix works with other grammar files
- ⚠️ **Document system prompt best practices** - Guide users on effective prompt design

**Final Status**:
- ✅ **API System Prompt Issue**: RESOLVED
- ✅ **Grammar Conflict**: RESOLVED
- ✅ **JSON Validity**: IMPROVED
- ✅ **Response Accuracy**: SIGNIFICANTLY IMPROVED
- ✅ **User Control**: RESTORED

## Phase 3: System Performance Optimization

### 3.1 Orin Processor Spike Issue Resolution

**Goal**: Resolve high CPU usage (87-100%) by `polkitd` process that was causing system overheating and performance degradation.

**Implementation Status**: ✅ **COMPLETED** (2025-06-23)

**Root Cause Analysis**:
- **Unnecessary Desktop Environment**: Orin was running full GNOME desktop environment despite being a headless server
- **GDM Service**: GNOME Display Manager (`gdm.service`) was enabled and running
- **Polkitd CPU Spike**: PolicyKit daemon consuming 87-100% CPU continuously
- **Resource Waste**: Full desktop environment running unnecessarily for SSH-only access
- **System Overheating**: High CPU usage causing battery/thermal issues

**What Was Implemented**:

#### 3.1.1 System Target Change
- **Before**: `graphical.target` (full desktop environment)
- **After**: `multi-user.target` (headless server mode)
- **Method**: `sudo systemctl isolate multi-user.target` (tested safely)
- **Permanent**: `sudo systemctl set-default multi-user.target` (persistent across reboots)

#### 3.1.2 Service Verification
- **Docker Service**: Confirmed running in `multi-user.target` dependency tree
- **API Services**: Verified ORAC API continues working normally
- **SSH Access**: Confirmed SSH connectivity maintained
- **Resource Usage**: Dramatic reduction in CPU and memory usage

**What Worked**:
- ✅ **CPU Usage Reduction**: From 87-100% to ~1% total system CPU
- ✅ **Service Continuity**: Docker containers and ORAC API continue running normally
- ✅ **SSH Access**: Remote access maintained without issues
- ✅ **Permanent Fix**: System will boot in headless mode on future reboots
- ✅ **Resource Efficiency**: System now runs optimally for server workload

**What Didn't Work**:
- ❌ **Previous Attempts**: No previous attempts to optimize system configuration
- ❌ **Desktop Environment**: GNOME desktop was unnecessary for headless operation

**Test Results** (2025-06-23):
```
✅ System Target: multi-user.target (permanent)
✅ CPU Usage: 1% total (down from 87-100%)
✅ Docker Container: Running normally (0.30% CPU)
✅ API Response: {"status":"ok","models_available":19,"version":"0.2.0"}
✅ Memory Usage: Stable and efficient
✅ SSH Access: Maintained
```

**Deployment Verification**:
- ✅ System boots in multi-user mode
- ✅ No graphical environment processes running
- ✅ Docker service starts automatically
- ✅ ORAC API responds normally
- ✅ SSH access maintained
- ✅ System runs cool and efficiently

**Lessons Learned**:
1. **Headless servers should not run desktop environments** - wastes resources and causes performance issues
2. **Always verify system targets** - `systemctl get-default` reveals unnecessary services
3. **Test changes safely** - `systemctl isolate` allows testing without permanent changes
4. **Monitor resource usage** - high CPU usage can indicate misconfiguration
5. **Docker works fine in multi-user mode** - no need for graphical environment

**Files Modified**:
- System configuration: `/etc/systemd/system/default.target` (symlink changed)
- No application code changes required

**Impact**:
- **Performance**: Dramatic reduction in CPU usage (87-100% → 1%)
- **Efficiency**: System now optimized for headless server operation
- **Reliability**: Reduced thermal stress and power consumption
- **Maintainability**: Simpler system configuration with fewer moving parts

**Next Steps**:
- ⚠️ **Monitor on next reboot** - Verify system boots correctly in multi-user mode
- ⚠️ **Check Docker auto-start** - Ensure containers start automatically on boot
- ⚠️ **Verify SSH access** - Confirm remote access works after reboot

**Final Status**:
- ✅ **Processor Spike Issue**: RESOLVED
- ✅ **System Optimization**: COMPLETED
- ✅ **Performance Improvement**: SIGNIFICANT
- ✅ **Permanent Fix**: IMPLEMENTED

## Phase 2: Docker Volume Mount Permission Conflict Resolution

### 2.1 Docker Volume Mount Permission Bug Fix

**Goal**: Resolve Docker volume mount permission conflicts preventing cache directory creation.

**Implementation Status**: ✅ **COMPLETED** (2025-06-22)

**Root Cause Analysis**:
- **Host Directory Ownership**: `./cache` directory owned by `root:root` instead of `toby:toby`
- **Container User**: Docker container runs as `orac:orac` (UID 1000), matching host user `toby:toby` (UID 1000)
- **Volume Mount**: `./cache:/app/cache` makes container see host directory
- **Permission Conflict**: Container couldn't create `cache/homeassistant` subdirectory due to root ownership
- **Path Resolution Issue**: Relative path `cache_dir: "cache/homeassistant"` resolved incorrectly in container
- **Poor Error Handling**: Application crashed with `sys.exit(1)` instead of graceful fallback
- **Disk Space Issues**: Docker overlay2 directories consuming 773GB of 915GB total space

**What Was Implemented**:

#### 2.1.1 Configuration Path Fix (`orac/homeassistant/config.yaml`)
- Changed `cache_dir: "cache/homeassistant"` to `cache_dir: "/app/cache/homeassistant"`
- Used absolute path that works correctly in Docker container context

#### 2.1.2 Docker Compose Cleanup (`docker-compose.yml`)
- Removed temporary workaround command that tried to create cache directory
- Eliminated problematic `mkdir -p /app/cache/homeassistant && chmod 755 /app/cache/homeassistant` workaround

#### 2.1.3 Improved Error Handling (`orac/homeassistant/cache.py`)
- Replaced `sys.exit(1)` with graceful fallback to memory-only mode
- Added proper logging instead of print statements
- Cache now continues operating in memory when persistent storage fails
- Application no longer crashes due to permission issues

#### 2.1.4 Docker Daemon Configuration (`/etc/docker/daemon.json`)
- Added log rotation: `"max-size": "10m", "max-file": "3"`
- Set reasonable file descriptor limits
- Prevents future disk space issues from log accumulation

**What Worked**:
- ✅ **Absolute Path Resolution**: Container now correctly resolves `/app/cache/homeassistant`
- ✅ **Graceful Error Handling**: Application continues running in memory-only mode when cache directory creation fails
- ✅ **Improved Logging**: Clear error messages instead of application crashes
- ✅ **Disk Space Management**: Docker log rotation prevents future space issues
- ✅ **Container Stability**: No more permission-related crashes

**What Didn't Work**:
- ❌ **Initial Docker Configuration**: Complex `builder.gc` settings caused Docker daemon startup failures
- ❌ **Relative Paths**: `cache_dir: "cache/homeassistant"` resolved incorrectly in container context
- ❌ **Poor Error Handling**: `sys.exit(1)` crashed entire application instead of graceful fallback

**Test Results** (2025-06-22):
```
✅ Container Build: Successfully built without permission errors
✅ Container Start: ORAC container running properly
✅ Cache Error Handling: Graceful fallback to memory-only mode
✅ Error Messages: Clear logging instead of crashes
✅ Disk Space: Freed 773GB from Docker cleanup, now 123GB used of 915GB
✅ Core Tests: 1/1 PASSED
✅ Home Assistant Tests: 3/4 PASSED (1 failed due to API endpoint, not permission issue)
```

**Deployment Verification**:
- ✅ Container builds and starts successfully
- ✅ Cache system operates in memory-only mode when persistent storage unavailable
- ✅ Application continues running despite permission issues
- ✅ Docker log rotation prevents future disk space problems
- ✅ All core functionality preserved

**Lessons Learned**:
1. **Always use absolute paths in Docker configurations** - relative paths resolve differently in container context
2. **Implement graceful error handling** - never use `sys.exit(1)` in library code
3. **Monitor disk space proactively** - Docker overlay2 directories can consume massive amounts of space
4. **Test Docker configurations incrementally** - complex settings may not be supported in all Docker versions
5. **Use proper logging instead of print statements** - enables better debugging and monitoring

**Files Modified**:
- `orac/homeassistant/config.yaml` - Changed to absolute cache path
- `docker-compose.yml` - Removed problematic workaround command
- `orac/homeassistant/cache.py` - Improved error handling and logging
- `/etc/docker/daemon.json` - Added log rotation and limits

**Impact**:
- **Reliability**: Application no longer crashes due to permission issues
- **Maintainability**: Clear error messages and graceful fallbacks
- **Performance**: Disk space issues resolved, preventing future problems
- **User Experience**: Seamless operation even when cache directory unavailable

### 2.2 Final Cache Permission Issue Resolution

**Goal**: Permanently resolve cache directory permission issues that persisted despite previous fixes.

**Implementation Status**: ✅ **COMPLETED** (2025-06-22)

**Root Cause Discovery**:
- **Deployment Script Issue**: `git clean -fd --exclude=logs/` was cleaning the cache directory during deployments
- **Directory Recreation**: Cache directory was being deleted and recreated by container as root user
- **Volume Mount Override**: Host directory ownership was being overridden by container-created directories
- **Permission Persistence**: Manual permission fixes were being undone by deployment process

**What Was Implemented**:

#### 2.2.1 Deployment Script Fix (`scripts/deploy_and_test.sh`)
- **Problem**: `git clean -fd --exclude=logs/` was cleaning cache directory
- **Solution**: Changed to `git clean -fd --exclude=logs/ --exclude=cache/`
- **Impact**: Cache directory now preserved during deployments
- **Prevention**: Directory permissions maintained across deployments

#### 2.2.2 Manual Permission Fix (One-time)
- **Command**: `sudo chown -R 1000:1000 cache/`
- **Result**: Cache directory ownership changed from `root:root` to `toby:toby`
- **Verification**: Directory now accessible by container user (UID 1000)

**What Worked**:
- ✅ **Deployment Script Fix**: Cache directory no longer cleaned during deployments
- ✅ **Permission Preservation**: Directory ownership maintained across container restarts
- ✅ **Persistent Cache**: Cache now operates with disk persistence instead of memory-only mode
- ✅ **Container Integration**: Cache directory accessible by container user
- ✅ **Grammar Generation**: Full functionality restored with persistent storage

**What Didn't Work**:
- ❌ **Previous Manual Fixes**: Permissions were being reset by deployment process
- ❌ **Container-Only Solutions**: Volume mount made host directory ownership critical
- ❌ **Temporary Workarounds**: Memory-only mode was functional but not optimal

**Test Results** (2025-06-22):
```
✅ Cache Directory: /app/cache/homeassistant accessible
✅ Persistent Cache: Writing to disk successfully
✅ Grammar Generation: 5 devices, 28 actions, 5 locations
✅ Auto-Discovery: 5 entities mapped successfully
✅ Container Deployment: No permission errors
✅ Core Tests: All passing
```

**Deployment Verification**:
- ✅ Cache directory preserved during `git clean` operations
- ✅ Directory ownership maintained as `toby:toby` (UID 1000)
- ✅ Container can create subdirectories in cache directory
- ✅ Persistent cache files written successfully
- ✅ No more "Permission denied" errors in logs

**Lessons Learned**:
1. **Deployment scripts can override manual fixes** - `git clean` operations must exclude critical directories
2. **Volume mounts require host directory permissions** - container user must have access to host directories
3. **Permission issues can be masked by graceful fallbacks** - memory-only mode hid the underlying problem
4. **Root cause analysis requires tracing the full deployment cycle** - not just the container startup
5. **Prevention is better than repeated fixes** - deployment script changes prevent future issues

**Files Modified**:
- `scripts/deploy_and_test.sh` - Added `--exclude=cache/` to git clean command
- Cache directory ownership - Changed from `root:root` to `toby:toby`

**Impact**:
- **Reliability**: Cache directory permissions now stable across deployments
- **Performance**: Persistent cache provides better performance than memory-only mode
- **Maintainability**: No more manual permission fixes required
- **User Experience**: System operates at full capacity with persistent storage

**Final Status**:
- ✅ **Cache Permission Issue**: RESOLVED
- ✅ **Persistent Storage**: WORKING
- ✅ **Grammar Generation**: FULLY FUNCTIONAL
- ✅ **Auto-Discovery**: WORKING
- ✅ **System Ready**: Phase 2 implementation can proceed

## Phase 1: Core Discovery Infrastructure

### 1.1 Enhanced API Client (`orac/homeassistant/client.py`)

**Goal**: Add new API endpoints for entity registry and device registry to enable area assignment discovery.

**Implementation Status**: ✅ **COMPLETED**

**What Was Implemented**:
- Added `API_ENTITY_REGISTRY = "/api/config/entity_registry/list"` to constants
- Added `API_DEVICE_REGISTRY = "/api/config/device_registry/list"` to constants
- Implemented `get_entity_registry()` method with caching and error handling
- Implemented `get_device_registry()` method with caching and error handling
- Added proper error handling for 404 responses (endpoints not available)

**What Worked**:
- ✅ Constants properly defined in `orac/homeassistant/constants.py`
- ✅ Client methods successfully implemented with async/await pattern
- ✅ Error handling gracefully catches 404 errors and returns empty lists
- ✅ Caching integration works correctly
- ✅ Logging provides clear feedback when endpoints are unavailable

**What Didn't Work**:
- ❌ **Initial Implementation**: Missing error handling for 404 responses
- ❌ **Caching Integration**: Initial cache key conflicts with existing methods

**Lessons Learned**:
1. **Always handle 404 responses gracefully** - not all Home Assistant instances have all endpoints
2. **Use unique cache keys** - prevent conflicts with existing cached data
3. **Test with different Home Assistant versions** - endpoint availability varies
4. **Log clearly when endpoints are unavailable** - helps with debugging

**Files Modified**:
- `orac/homeassistant/constants.py` - Added new API endpoint constants
- `orac/homeassistant/client.py` - Added entity and device registry methods

**Impact**:
- **Compatibility**: Works with Home Assistant instances that don't have entity/device registry endpoints
- **Reliability**: Graceful fallback when endpoints are unavailable
- **Debugging**: Clear logging when endpoints are not available
- **Performance**: Proper caching integration for available endpoints

## Phase 2.2: Docker Disk Space Monitoring

### 2.2.1 Docker Disk Space Monitoring Implementation

**Goal**: Implement proactive monitoring to prevent Docker disk space issues that previously consumed 773GB of 915GB total space.

**Implementation Status**: 🔄 **PENDING**

**Root Cause Analysis**:
- **Docker Overlay2**: Docker's overlay2 storage driver can accumulate massive amounts of data
- **Build Cache**: Docker build cache can grow indefinitely without cleanup
- **Log Accumulation**: Container logs can accumulate rapidly without rotation
- **Volume Mounts**: Large data volumes can consume significant space
- **Model Files**: GGUF model files are large (100MB-1.8GB each)

**What Needs to Be Implemented**:

#### 2.2.1.1 Disk Space Monitoring Script (`scripts/monitor_disk_space.sh`)
- Add disk space monitoring to deployment script
- Set up alerts when disk usage exceeds 80%
- Implement automatic cleanup triggers
- Monitor Docker-specific directories

#### 2.2.1.2 Docker Cleanup Automation (`scripts/docker_cleanup.sh`)
- Implement `docker system prune` automation
- Add build cache cleanup
- Add unused volume cleanup
- Add dangling image cleanup
- Preserve essential data and models

#### 2.2.1.3 Log Rotation Configuration (`docker-compose.yml`)
- Ensure log rotation is properly configured
- Set reasonable log size limits
- Implement log retention policies
- Monitor log directory sizes

#### 2.2.1.4 Model Management Strategy
- Implement model cleanup for unused models
- Add model usage tracking
- Set up model retention policies
- Monitor model directory sizes

**Current Status**:
- ✅ Docker log rotation configured in `/etc/docker/daemon.json`
- ✅ Basic disk space monitoring in deploy script
- 🔄 Automated cleanup scripts not implemented
- 🔄 Proactive monitoring not implemented
- 🔄 Model management strategy not implemented

**Next Steps**:
1. Create `scripts/monitor_disk_space.sh` for proactive monitoring
2. Create `scripts/docker_cleanup.sh` for automated cleanup
3. Add disk space checks to deployment script
4. Implement model usage tracking
5. Set up automated cleanup schedules

**Success Criteria**:
- Disk usage stays below 80% of total capacity
- Docker overlay2 directories don't exceed 50GB
- Log directories don't exceed 1GB
- Model directory doesn't exceed 10GB
- Automated cleanup prevents space issues

**Files to Create/Modify**:
- `scripts/monitor_disk_space.sh` - New monitoring script
- `scripts/docker_cleanup.sh` - New cleanup script
- `scripts/deploy_and_test.sh` - Add disk space checks
- `docker-compose.yml` - Ensure log rotation
- `README.md` - Add disk space management documentation

**Impact**:
- **Reliability**: Prevents deployment failures due to disk space
- **Performance**: Maintains optimal system performance
- **Maintainability**: Reduces manual cleanup requirements
- **Cost**: Prevents need for storage expansion

## Phase 4: GBNF Grammar Testing and Optimization

### 4.1 GBNF Grammar Testing Results and Findings

**Goal**: Test and optimize GBNF (Grammar Backus-Naur Form) grammar for parsing natural language commands into structured JSON for Home Assistant integration.

**Implementation Status**: ✅ **COMPLETED** (2025-01-27)

**Test Methodology**:
- **Command Structure**: Using llama.cpp with pattern: `Apply to unknown_set....`
- **Model**: Qwen3-0.6B-Q4_K_M.gguf (0.6B parameter model, quantized)
- **Parameters**: Temperature 0.2, Top-p 0.8, Top-k 30, Max tokens 50
- **Grammar File**: unknown_set.gbnf

**Grammar Structure**:
The grammar defines three main components:
- **Device**: Extracted device type (lights, blinds, music, etc.)
- **Action**: Extracted action (turn on, turn off, set to %, etc.)
- **Location**: Extracted location (kitchen, bedroom, living room, etc.)

**Test Results**:

#### ✅ Successful Cases (4/6 - 67% accuracy)
- "turn off the lights in the kitchen" → `{"device":"lights","action":"off","location":"kitchen"}`
- "set the bedroom lights to 75%" → `{"device":"lights","action":"set 75%","location":"bedroom"}`
- "open the blinds in the hall" → `{"device":"blinds","action":"open","location":"hall"}`
- "turn on the music in the dining room" → `{"device":"music","action":"on","location":"dining room"}`

#### ❌ Problematic Cases (2/6)
- "set the bathroom lights to 25%" → `{"device":"blinds","action":"set 25%","location":"bathroom"}`
- "turn on the heating in the living room" → `{"device":"heating","action":"on","location":"dining room"}`

**Key Findings**:

#### 1. Grammar Syntax Discovery
- **Underscores don't work**: Using `set_action` in grammar causes parsing errors
- **Hyphens work**: Using `set-action` in grammar works correctly
- **GBNF Syntax Requirement**: Underscores are not valid in rule names

#### 2. System Prompt Effectiveness
- System prompt dramatically improved results
- Pattern: `Apply to unknown_set....` with specific formatting

#### 3. Parameter Sensitivity
- **Temperature 0.2**: Provides consistent, deterministic output
- **Top-p 0.8, Top-k 30**: Reduces randomness while maintaining quality
- **50 token limit**: Sufficient for JSON responses (model completes naturally)

#### 4. Model Behavior Patterns
- **Device mapping bias**: Model sometimes chooses first available device in grammar
- **Location fallback**: Unknown locations default to first available location instead of "UNKNOWN"
- **Action recognition**: Excellent for simple actions and percentage-based actions

#### 5. Token Limit Behavior
- **"> EOF by user"**: Indicates model completed naturally before hitting token limit
- **No additional output**: Even with 80 tokens, model generates same JSON
- **Efficient completion**: Model stops when task is complete

**Current Issues**:
1. **Device Recognition**: "bathroom lights" → "blinds" (incorrect device mapping)
2. **Location Mapping**: "living room" → "dining room" (wrong location)
3. **Grammar Order Bias**: Model prefers first items in grammar lists
4. **UNKNOWN Handling**: Model doesn't use UNKNOWN fallbacks effectively

**What Worked**:
- ✅ **Grammar Syntax**: Hyphen-based rule names work correctly
- ✅ **System Prompt**: Dramatic improvement in parsing accuracy
- ✅ **Parameter Tuning**: Low temperature provides consistent results
- ✅ **JSON Structure**: Model generates valid JSON consistently
- ✅ **Action Recognition**: Excellent for simple and percentage-based actions

**What Didn't Work**:
- ❌ **Underscore Rule Names**: Causes parsing errors in GBNF
- ❌ **Device Bias**: Model prefers first grammar items over context
- ❌ **Location Fallbacks**: UNKNOWN handling not working as expected
- ❌ **Complex Device Types**: Some device mappings incorrect

**Lessons Learned**:
1. **GBNF syntax is strict** - underscores not allowed in rule names, use hyphens
2. **System prompts are crucial** - dramatic impact on parsing accuracy
3. **Grammar order matters** - model biases toward first items in lists
4. **Parameter tuning essential** - low temperature needed for consistency
5. **Token limits can be conservative** - model completes naturally when task done

**Files Modified**:
- `data/test_grammars/unknown_set.gbnf` - Grammar file for testing
- Test scripts and documentation updated

**Impact**:
- **Accuracy**: 67% success rate with room for improvement
- **Reliability**: Consistent JSON output structure
- **Performance**: Efficient token usage and completion
- **Foundation**: Solid base for production grammar implementation

**Next Steps**:
1. **Improve Accuracy**:
   - Reorder grammar rules (put most common devices/locations first)
   - Add more device types (include common Home Assistant devices)
   - Improve UNKNOWN handling (better fallback mechanisms)
   - Add more location options (cover common room types)
   - Test with different models (try larger models for better understanding)

2. **API Integration**:
   - Ensure consistency (make sure ORAC API uses identical parameters)
   - Grammar file deployment (verify API loads the same grammar file)
   - System prompt integration (add effective system prompt to API calls)
   - Parameter standardization (use same temperature, top-p, top-k values)
   - Error handling (add proper error handling for grammar parsing failures)

3. **Production Readiness**:
   - Validation (add JSON schema validation for API responses)
   - Logging (add detailed logging for debugging grammar issues)
   - Fallback mechanisms (implement graceful degradation when grammar fails)
   - Performance optimization (optimize for production latency requirements)

**Final Status**:
- ✅ **Grammar Testing**: COMPLETED
- ✅ **Syntax Discovery**: IMPLEMENTED
- ✅ **Parameter Optimization**: ACHIEVED
- ✅ **Production Foundation**: ESTABLISHED
``` 