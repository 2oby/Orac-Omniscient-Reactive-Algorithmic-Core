# Sprint 3: Code Cleanup & Legacy Code Removal (DETAILED)

**Status:** Ready to Execute  
**Goal:** Remove dead code, legacy implementations, and outdated systems  
**Duration:** 2-3 days  
**Baseline Tag:** `sprint1-before-legacy-removal` (created 2025-10-19)

---

## Overview

Sprint 3 removes legacy code that was replaced by the Backend system (Sprint 3-5). This includes:
- **Grammar Scheduler** (replaced by BackendGrammarGenerator)
- **HA Executor** (replaced by backend dispatch_command)
- **Dispatcher Registry** (replaced by backend-integrated dispatchers)
- Sprint comments and commented code throughout codebase

**Estimated Impact:**
- Remove ~15 API endpoints
- Remove ~8 files
- Remove ~1500 lines of code
- Save nightly scheduler overhead and unnecessary HA API calls

---

## Task 3.1: Remove Grammar Scheduler System (HIGH PRIORITY)

**Status:** Currently running nightly at 3am, wasting resources!

### Files to Remove:
```bash
rm orac/homeassistant/grammar_scheduler.py
rm orac/homeassistant/grammar_manager.py
rm orac/homeassistant/mapping_config.py
rm orac/homeassistant/mapping_builder.py
rm orac/homeassistant/entity_mappings.yaml
```

### API Endpoints to Remove from `orac/api.py`:

**Old HA Grammar Endpoints (lines 584-600, 1078-1161):**
- `POST /v1/homeassistant/grammar/gbnf` - Generate grammar
- `GET /v1/homeassistant/grammar` - Get grammar rules
- `POST /v1/homeassistant/grammar/update` - Update grammar
- `GET /v1/homeassistant/grammar/scheduler/status` - Scheduler status
- `POST /v1/homeassistant/grammar/scheduler/start` - Start scheduler
- `POST /v1/homeassistant/grammar/scheduler/stop` - Stop scheduler

**Old HA Mapping Endpoints (lines 969-1076):**
- `GET /v1/homeassistant/mapping/list` - List mappings
- `GET /v1/homeassistant/mapping/check-null` - Check null mappings
- `POST /v1/homeassistant/mapping/save` - Save mapping
- `PUT /v1/homeassistant/mapping/update` - Update mappings
- `POST /v1/homeassistant/mapping/auto-discover` - Auto-discover entities

### Code to Remove from `orac/api.py`:

**Imports (lines 36-37):**
```python
from orac.homeassistant.mapping_config import EntityMappingConfig
from orac.homeassistant.grammar_manager import HomeAssistantGrammarManager
```

**Global Variables (lines 452-454):**
```python
ha_mapping_config = None
ha_grammar_manager = None
ha_grammar_scheduler = None
```

**Helper Functions (lines 490-519):**
```python
async def get_ha_mapping_config() -> EntityMappingConfig:
async def get_ha_grammar_manager() -> HomeAssistantGrammarManager:
async def get_ha_grammar_scheduler() -> 'GrammarScheduler':
```

**Startup Code (lines 1217-1224):**
```python
# Start the grammar scheduler for daily updates
try:
    scheduler = await get_ha_grammar_scheduler()
    await scheduler.start_scheduler()
    logger.info("Grammar scheduler started successfully")
except Exception as e:
    logger.error(f"Failed to start grammar scheduler: {e}")
```

**Shutdown Code (lines 1247-1251):**
```python
# Stop grammar scheduler
if ha_grammar_scheduler:
    try:
        await ha_grammar_scheduler.stop_scheduler()
        logger.info("Grammar scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping grammar scheduler: {e}")
```

### Replacement System (KEEP):
- ✅ `orac/backend_grammar_generator.py`
- ✅ `POST /api/backends/{backend_id}/grammar/generate`
- ✅ `GET /api/backends/{backend_id}/grammar`
- ✅ `POST /api/backends/{backend_id}/grammar/test`

---

## Task 3.2: Remove HAExecutor System (HIGH PRIORITY)

### Files to Remove:
```bash
rm orac/homeassistant/ha_executor.py
```

### Code to Remove from `orac/api.py`:

**Import (line 42):**
```python
from orac.homeassistant.ha_executor import HAExecutor
```

**Global Variable (line 62):**
```python
ha_executor = HAExecutor()
```

**Legacy Execution Code (lines 822-850):**
```python
# Legacy: If this is a home_assistant topic and no backend, use old HA executor
if topic_id == "home_assistant" and response_text and not topic.backend_id:
    try:
        import json
        parsed_json = json.loads(response_text)
        last_command_storage["generated_json"] = parsed_json
        
        # Execute the command via HA executor
        logger.info(f"Executing HA command (legacy): {parsed_json}")
        ha_result = await ha_executor.execute_json_command(parsed_json)
        
        # Store HA execution details
        last_command_storage["ha_request"] = ha_result.get("ha_request")
        last_command_storage["ha_response"] = ha_result.get("ha_response")
        last_command_storage["error"] = ha_result.get("error")
        last_command_storage["success"] = ha_result.get("success", False)
        
        if ha_result.get("error"):
            logger.error(f"HA execution failed: {ha_result['error']}")
        else:
            logger.info(f"HA execution successful")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse generated JSON: {e}")
        last_command_storage["error"] = f"Invalid JSON: {str(e)}"
        last_command_storage["success"] = False
    except Exception as e:
        logger.error(f"Failed to execute HA command: {e}")
        last_command_storage["error"] = str(e)
        last_command_storage["success"] = False
```

### Replacement System (KEEP):
- ✅ Backend system handles execution via `backend.dispatch_command()` (line 803)

---

## Task 3.3: Remove Dispatcher Registry (MEDIUM PRIORITY)

### Files to Remove:
```bash
rm orac/dispatchers/registry.py
```

### Update `orac/dispatchers/__init__.py`:
**BEFORE:**
```python
from .base import BaseDispatcher
from .registry import dispatcher_registry

__all__ = ['BaseDispatcher', 'dispatcher_registry']
```

**AFTER:**
```python
from .base import BaseDispatcher

__all__ = ['BaseDispatcher']
```

### API Endpoint to Remove from `orac/api.py`:

**Dispatcher Endpoint (lines 101-112):**
```python
@app.get("/v1/dispatchers", tags=["Dispatchers"])
async def list_dispatchers() -> Dict[str, Any]:
    """List all available dispatchers."""
    try:
        dispatchers = dispatcher_registry.list_available()
        return {
            "status": "success",
            "dispatchers": dispatchers
        }
    except Exception as e:
        logger.error(f"Error listing dispatchers: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Commented Import to Remove (line 47):**
```python
# from orac.dispatchers import dispatcher_registry
```

### Files to KEEP (used by backends):
- ✅ `orac/dispatchers/base.py`
- ✅ `orac/dispatchers/homeassistant.py`
- ✅ `orac/dispatchers/mapping_generator.py`
- ✅ `orac/dispatchers/mapping_resolver.py`

---

## Task 3.4: Remove Sprint Comments

**Search Pattern:**
```bash
grep -rn "Sprint [0-9]:" orac/ --include="*.py"
```

**Action:**
- Convert useful sprint comments to proper documentation
- Remove the rest

**Example Transformation:**
```python
# BEFORE:
# Sprint 5: Dispatcher field removed - backends handle dispatching internally

# AFTER:
# Backends encapsulate dispatcher functionality (architecture refactor)
```

---

## Task 3.5: Remove Commented Code

**Search for:**
```bash
grep -rn "^# from\|^#from" orac/ --include="*.py" | grep import
```

**Action:**
- Review each commented import
- If not needed (check git history), delete
- If needed, uncomment and use it

**Example (api.py line 46-47):**
```python
# Sprint 5: Dispatcher registry no longer needed - backends handle dispatching internally
# from orac.dispatchers import dispatcher_registry
```
Delete both lines completely.

---

## Task 3.6: Move Test Files to tests/ Directory

**Files to Move:**
```bash
mv test_dispatcher_optimization.py tests/
mv test_backend_grammar_generator.py tests/
mv test_grammar_simple.py tests/
```

**Files to Archive (if still needed):**
```bash
mkdir -p archive/sprint_tests/
mv SPRINT_2_TEST_SCRIPT.py archive/sprint_tests/
```

---

## Task 3.7: Clean Up Documentation

**Files to Archive:**
```bash
mkdir -p docs/archive/sprints/
mv sprint_*.md docs/archive/sprints/  # Keep sprint_3_detailed.md for now
```

**Keep in Root:**
- `README.md`
- `cleanup.MD`
- `LEGACY_CODE_AUDIT.md` (for reference)

---

## Testing Checklist

After each removal, test:

```bash
# 1. Verify Python syntax
python3 -m py_compile orac/api.py

# 2. Test imports
python3 -c "from orac.api import app; print('✅ Imports OK')"

# 3. Run local tests (if any)
pytest tests/

# 4. Deploy to orin4
./deploy_and_test.sh "Sprint 3: Remove [component name]"

# 5. Verify API is running
curl -s http://192.168.8.192:8000/v1/status

# 6. Check for errors in logs
ssh orin4 'docker logs orac --tail 50 | grep -i error'
```

---

## Rollback Plan

If something breaks:

```bash
# Restore from tag
git checkout sprint1-before-legacy-removal

# Or restore specific file
git checkout sprint1-before-legacy-removal -- orac/api.py

# Redeploy
./deploy_and_test.sh "Rollback Sprint 3 changes"
```

---

## Order of Execution

**Recommended order (safest to riskiest):**

1. ✅ Remove commented code and sprint comments (low risk)
2. ✅ Remove Dispatcher Registry (low risk, dead code)
3. ✅ Remove HAExecutor (medium risk, has fallback)
4. ✅ Remove Grammar Scheduler (high impact, but clearly unused)
5. ✅ Move test files (no risk)
6. ✅ Clean up documentation (no risk)

---

## Success Criteria

Sprint 3 is complete when:

- ✅ No grammar scheduler running (check `docker logs orac | grep scheduler`)
- ✅ All 15 legacy API endpoints removed
- ✅ All 8 legacy files deleted
- ✅ No commented imports in codebase
- ✅ No "Sprint X:" comments in code
- ✅ Tests pass on orin4
- ✅ API responds normally
- ✅ Backend grammar generation works
- ✅ Backend command execution works

---

## Deliverables

- Clean `orac/api.py` without legacy code
- Removed grammar scheduler system
- Removed HAExecutor system
- Removed dispatcher registry
- Organized test directory
- Clean documentation structure
- Deployment verification on orin4

**Estimated Time:** 2-3 days  
**Estimated Code Reduction:** ~1500 lines  
**Risk:** Low (all functionality already replaced)
