# Sprint 4: Duplicate Code & Refactoring - Execution Prompt

## Context

You are working on the ORAC (Omniscient Reactive Algorithmic Core) project. We've just completed Sprint 2 (API Decomposition) which refactored the monolithic api.py into a modular structure. Sprint 4 focuses on fixing bugs discovered in Sprint 2, eliminating duplicate code, and improving code reuse.

## Environment Setup

- **Development Machine**: Mac (you are here)
- **Test Machine**: Orin Nano (accessible via `ssh orin4`)
- **Deployment Script**: `./deploy_and_test.sh "commit message"`
  - Commits changes to git
  - Pushes to GitHub
  - SSHs to orin4
  - Pulls changes
  - Rebuilds Docker container
  - Runs automated tests

## Current Branch

`cleanup` (all cleanup work happens here, will merge to master when complete)

## Sprint 4 Goals

1. **Fix critical bugs discovered in Sprint 2** (HIGH PRIORITY)
2. **Fix timezone issue** (Docker logs in UTC, need CET)
3. **Eliminate code duplication**
4. **Create common utilities**
5. **Standardize error responses**
6. **Consolidate logging setup**

## Sprint 4 Progress (Updated 2025-10-20)

### ✅ COMPLETED

**Task 4.0: Bug Fixes (HIGH PRIORITY)**
- ✅ **Bug 1 Fixed** - `backend_manager.py:111` - Fixed BackendGrammarGenerator instantiation
  - Changed: `BackendGrammarGenerator(str(self.data_dir))` → `BackendGrammarGenerator(self, str(self.data_dir))`
  - Verified: Logs show "Grammar regenerated successfully" - no more 'str' object error
  - Commit: `898706e`

- ✅ **Bug 2 Improved** - `llama_cpp_client.py:585-596` - Enhanced response logging and extraction
  - Added debug logging to inspect full server responses
  - Added fallback to check multiple response fields (`content`, `text`, `completion`)
  - Will help diagnose empty response issues
  - Commit: `898706e`

**Task 4.1: Timezone to CET (HIGH PRIORITY)**
- ✅ **Dockerfile Updated** - `Dockerfile:16-25`
  - Added tzdata package installation
  - Configured timezone to Europe/Amsterdam (CET/CEST)
  - Set TZ environment variable
  - Verified: Container now shows `CEST 2025` timestamps ✅
  - Commit: `898706e`

**Deployment Infrastructure**
- ✅ **Enhanced deploy_and_test.sh**
  - Added `--rebuild` flag for Dockerfile changes
  - Fixed git pull conflicts with `git reset --hard origin/branch`
  - GitHub enforced as single source of truth
  - Commit: `898706e`

- ✅ **Fixed Import Issues**
  - Removed stale `grammar_manager` import from `orac/homeassistant/__init__.py`
  - Commit: `586c1de`

### ⏭️ SKIPPED / DEFERRED

**Task 4.2: Extract HomeAssistant Client Creation** - SKIPPED
- Rationale: Only duplicated in 2-3 places (~10 lines each)
- Working correctly, not causing issues
- Low impact compared to critical bug fixes
- Can be addressed in future code quality sprint

### 🔄 REMAINING (Deferred to Future Sprint)

**Task 4.3: Create Common Utilities** - DEFERRED
- `orac/utils/response_builder.py`, `validators.py`, `url_parser.py`
- Nice-to-have for consistency, not critical

**Task 4.4: Standardize Error Responses** - DEFERRED
- Consistent error format across endpoints
- Good for API consistency, not blocking

**Task 4.5: Extract Repeated Patterns** - DEFERRED
- Backend statistics, device validation, entity parsing
- Code quality improvement, not urgent

**Task 4.6: Consolidate Logging Setup** - DEFERRED
- Choose one logger approach (loguru vs logging.getLogger)
- Technical debt, can wait

**Final Testing** - PENDING

## Tasks (in order of priority)

### Task 4.0: Fix Bugs Discovered in Sprint 2 (HIGH PRIORITY)

**Bug 1: BackendManager.auto_regenerate_grammar() incorrect instantiation**
- Location: `orac/backend_manager.py`
- Issue: Passes string instead of BackendManager instance to BackendGrammarGenerator
- Error message: `'str' object has no attribute 'get_backend'`
- Fix: Find where `BackendGrammarGenerator` is being instantiated incorrectly and pass the proper `backend_manager` instance

**Bug 2: Generation endpoint returns "No response generated"**
- Location: `orac/services/generation_service.py` and `orac/llama_cpp_client.py`
- Issue: Sometimes the generation endpoint returns "No response generated" instead of actual text
- Investigation needed:
  - Check how `response.text` is extracted from llama.cpp client
  - Add logging around response text extraction
  - Check if it's a timeout issue or empty response issue
  - Test with multiple generation requests

**Testing after fixes:**
```bash
# Test generation endpoint multiple times
for i in {1..5}; do
  echo "Test $i:"
  curl -s -X POST "http://192.168.8.192:8000/v1/generate/homeassistant" \
    -H "Content-Type: application/json" \
    -d '{"prompt": "turn on bedroom light", "max_tokens": 100}' | \
    python3 -m json.tool | grep -E "response|error"
done

# Test backend grammar generation
curl -s -X POST "http://192.168.8.192:8000/api/backends/homeassistant_8ca84424/grammar/generate" | \
  python3 -m json.tool

# Check logs for errors
ssh orin4 'docker logs orac --tail 100 | grep -i "error\|warning"'
```

### Task 4.1: Fix Timezone to CET (HIGH PRIORITY)

**Goal:** Docker container logs should show CET/CEST timestamps instead of UTC for easier debugging.

**Changes needed:**

1. **Update Dockerfile:**
```dockerfile
# Add timezone package and set to CET
RUN apt-get update && \
    apt-get install -y --no-install-recommends tzdata && \
    ln -fs /usr/share/zoneinfo/Europe/Amsterdam /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata
ENV TZ=Europe/Amsterdam
```

2. **Update Python logging to use local timezone:**
- Find where logging is configured
- Ensure timestamps use local timezone
- Test: `docker logs orac --tail 10` should show CET timestamps

3. **Update API timestamp responses:**
- Check `last_command_storage["timestamp"]` formatting
- Ensure all API responses return timestamps in CET

**Testing:**
```bash
# Deploy changes
./deploy_and_test.sh "Sprint 4 Task 4.1: Configure timezone to CET"

# Verify timezone
ssh orin4 'docker exec orac date'
ssh orin4 'docker logs orac --tail 5'

# Should show something like: "2025-10-19 18:30:00 CEST" instead of "16:30:00 UTC"
```

### Task 4.2: Extract HomeAssistant Client Creation

**Goal:** Centralize HA client creation logic to avoid duplication.

**Currently duplicated in:**
- `orac/backend_manager.py`
- `orac/backends/homeassistant_backend.py`
- `orac/api/dependencies.py`

**Create:** `orac/homeassistant/factory.py`

```python
"""
orac.homeassistant.factory
--------------------------
Factory for creating HomeAssistant client instances.
"""

from orac.homeassistant.client import HomeAssistantClient
from orac.homeassistant.config import HomeAssistantConfig

def create_ha_client(config: HomeAssistantConfig) -> HomeAssistantClient:
    """Create a HomeAssistant client from configuration."""
    return HomeAssistantClient(config)

def create_ha_client_from_yaml(config_path: str) -> HomeAssistantClient:
    """Create a HomeAssistant client from YAML config file."""
    config = HomeAssistantConfig.from_yaml(config_path)
    return HomeAssistantClient(config)

def create_ha_client_from_connection(url: str, port: int, token: str) -> HomeAssistantClient:
    """Create a HomeAssistant client from connection parameters."""
    config = HomeAssistantConfig(host=url, port=port, token=token)
    return HomeAssistantClient(config)
```

**Refactor existing code to use the factory.**

### Task 4.3: Create Common Utilities

**Goal:** Extract repeated patterns into utility modules.

**Create:** `orac/utils/` directory with:

1. **`__init__.py`** - Package initialization
2. **`url_parser.py`** - URL parsing logic
3. **`validators.py`** - Common validation functions
4. **`response_builder.py`** - Standardized API responses

**Example: `orac/utils/response_builder.py`**
```python
"""
orac.utils.response_builder
----------------------------
Utilities for building standardized API responses.
"""

from typing import Dict, Any, Optional
from datetime import datetime

def success_response(data: Any, message: Optional[str] = None) -> Dict[str, Any]:
    """Build a success response."""
    response = {
        "status": "success",
        "timestamp": datetime.now().isoformat()
    }
    if message:
        response["message"] = message
    if isinstance(data, dict):
        response.update(data)
    else:
        response["data"] = data
    return response

def error_response(
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    status_code: int = 500
) -> Dict[str, Any]:
    """Build an error response."""
    response = {
        "status": "error",
        "error": {
            "code": code,
            "message": message
        },
        "timestamp": datetime.now().isoformat()
    }
    if details:
        response["error"]["details"] = details
    return response
```

### Task 4.4: Standardize Error Responses

**Goal:** Use consistent error response format across all endpoints.

**Current issues:**
- Some endpoints return `{"status": "error", "detail": "..."}`
- Others return `{"error": "..."}`
- No consistent error codes

**New standard format:**
```json
{
    "status": "error",
    "error": {
        "code": "BACKEND_NOT_FOUND",
        "message": "Backend abc123 not found",
        "details": {}
    },
    "timestamp": "2025-10-19T18:30:00.123456"
}
```

**Error codes to define:**
- `BACKEND_NOT_FOUND`
- `ENTITY_NOT_FOUND`
- `VALIDATION_ERROR`
- `CONNECTION_ERROR`
- `TIMEOUT_ERROR`
- `GRAMMAR_GENERATION_ERROR`
- `MODEL_NOT_FOUND`
- `TOPIC_DISABLED`

**Refactor endpoints to use `response_builder.error_response()`.**

### Task 4.5: Extract Repeated Patterns

**Goal:** Identify and extract duplicate code patterns.

**Patterns to extract:**

1. **Backend statistics calculation** (repeated in multiple backends)
   - Create `orac/utils/backend_stats.py`

2. **Device mapping validation logic**
   - Create `orac/utils/device_validator.py`

3. **Entity parsing and normalization**
   - Create `orac/utils/entity_parser.py`

### Task 4.6: Consolidate Logging Setup

**Goal:** Standardize on single logger type across the codebase.

**Current issues:**
- Mixing `get_logger()`, `logging.getLogger()`, and `loguru` logger
- Inconsistent log levels
- Inconsistent formatting

**Decision:** Choose one approach (recommend `loguru` for simplicity)

**Create:** `orac/utils/logging.py`
```python
"""
orac.utils.logging
------------------
Centralized logging configuration for ORAC.
"""

from loguru import logger
import sys

def setup_logging(level: str = "INFO", log_file: str = None):
    """Configure logging for the application."""
    logger.remove()  # Remove default handler

    # Console handler with color
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=level,
        colorize=True
    )

    # File handler if specified
    if log_file:
        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            level=level,
            rotation="100 MB"
        )

    return logger

def get_logger(name: str):
    """Get a logger instance for a module."""
    return logger.bind(name=name)
```

**Refactor all modules to use the new logging setup.**

## Deployment Strategy

After completing each task:

1. Test locally if possible
2. Deploy to orin4 using `./deploy_and_test.sh "Sprint 4 Task X.Y: Description"`
3. Verify tests pass
4. Check logs for errors
5. Test affected endpoints manually
6. Commit and push to GitHub

## Success Criteria

Sprint 4 is complete when:

- ✅ Bug 1 (BackendManager.auto_regenerate_grammar) is fixed
- ✅ Bug 2 (Generation "No response generated") is fixed and tested
- ✅ Docker logs show CET timestamps
- ✅ HomeAssistant client factory created and used
- ✅ `orac/utils/` directory created with common utilities
- ✅ All error responses use standardized format
- ✅ Duplicate code patterns extracted
- ✅ Logging consolidated to single approach
- ✅ All tests pass on orin4
- ✅ No regression in existing functionality

## Deliverables

- `orac/utils/` directory with utilities
- `orac/homeassistant/factory.py`
- Updated `Dockerfile` with CET timezone
- Refactored error responses across all routes
- Consolidated logging setup
- Updated `cleanup.MD` marking Sprint 4 as complete

## Final Testing

```bash
# Comprehensive test script
./deploy_and_test.sh "Sprint 4: Complete - Duplicate code removed, bugs fixed, utilities created"

# Manual verification
# 1. Check timezone
ssh orin4 'docker logs orac --tail 5'

# 2. Test generation (should not return "No response generated")
curl -s -X POST "http://192.168.8.192:8000/v1/generate/homeassistant" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "turn on lounge light", "max_tokens": 100}' | \
  python3 -m json.tool

# 3. Test backend grammar generation (should not have 'str' object error)
curl -s -X POST "http://192.168.8.192:8000/api/backends/homeassistant_8ca84424/grammar/generate" | \
  python3 -m json.tool

# 4. Test error responses (should use new format)
curl -s "http://192.168.8.192:8000/api/backends/nonexistent" | \
  python3 -m json.tool

# 5. Check for no errors in logs
ssh orin4 'docker logs orac --tail 100 | grep -i "error" | grep -v "ERROR: No"'
```

## Notes

- All work happens on the `cleanup` branch
- Use `./deploy_and_test.sh` for all deployments
- Test on orin4 after each major change
- Keep commits focused and well-documented
- Update `cleanup.MD` when Sprint 4 is complete
