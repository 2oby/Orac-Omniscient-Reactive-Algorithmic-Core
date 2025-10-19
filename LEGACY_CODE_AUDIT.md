# Legacy Code Audit - October 2025

**Tag:** `sprint1-before-legacy-removal`  
**Date:** 2025-10-19  
**Purpose:** Document all legacy code to be removed after Backend system (Sprint 3-5) implementation

---

## 1. Grammar Scheduler System (OLD HA Auto-Discovery)

### Status: **REPLACED** by BackendGrammarGenerator

### Files to Remove:
- `orac/homeassistant/grammar_scheduler.py` - Daily scheduler at 3am
- `orac/homeassistant/grammar_manager.py` - Grammar generation from HA entities
- `orac/homeassistant/mapping_config.py` - Entity mapping configuration
- `orac/homeassistant/mapping_builder.py` - Mapping builder utilities
- `orac/homeassistant/entity_mappings.yaml` - Old mapping file

### API Endpoints to Remove:
- `POST /v1/homeassistant/grammar/gbnf` (line 584)
- `GET /v1/homeassistant/grammar` (line 1078)
- `POST /v1/homeassistant/grammar/update` (line 1100)
- `GET /v1/homeassistant/grammar/scheduler/status` (line 1118)
- `POST /v1/homeassistant/grammar/scheduler/start` (line 1131)
- `POST /v1/homeassistant/grammar/scheduler/stop` (line 1147)
- `GET /v1/homeassistant/mapping/list` (line 969)
- `GET /v1/homeassistant/mapping/check-null` (line 988)
- `POST /v1/homeassistant/mapping/save` (line 1014)
- `PUT /v1/homeassistant/mapping/update` (line 1032)
- `POST /v1/homeassistant/mapping/auto-discover` (line 1055)

### Code to Remove from api.py:
- Import: `EntityMappingConfig`, `HomeAssistantGrammarManager` (lines 36-37)
- Global vars: `ha_mapping_config`, `ha_grammar_manager`, `ha_grammar_scheduler` (lines 452-454)
- Functions: `get_ha_mapping_config()`, `get_ha_grammar_manager()`, `get_ha_grammar_scheduler()` (lines 490-519)
- Startup code: Grammar scheduler initialization (lines 1217-1224)
- Shutdown code: Grammar scheduler cleanup (lines 1247-1251)

### Replacement:
Backend system generates grammar from manually mapped entities in GUI:
- `orac/backend_grammar_generator.py` ✅ KEEP
- API: `/api/backends/{backend_id}/grammar/generate` ✅ KEEP

---

## 2. Dispatcher Registry (OLD Dispatcher Management)

### Status: **REPLACED** - Dispatchers now integrated into backends (Sprint 5)

### Files to Remove:
- `orac/dispatchers/registry.py` - Dispatcher registry system
- `orac/dispatchers/__init__.py` - Exports dispatcher_registry

### API Endpoints to Remove:
- `GET /v1/dispatchers` (line 101)

### Code to Remove from api.py:
- Commented import: `# from orac.dispatchers import dispatcher_registry` (line 47)
- Endpoint function using `dispatcher_registry.list_available()` (lines 101-112)

### Files to KEEP (used by backends):
- `orac/dispatchers/base.py` ✅ KEEP
- `orac/dispatchers/homeassistant.py` ✅ KEEP (used by HomeAssistantBackend)
- `orac/dispatchers/mapping_generator.py` ✅ KEEP
- `orac/dispatchers/mapping_resolver.py` ✅ KEEP

### Replacement:
Dispatchers are now encapsulated in backends:
- `orac/backends/homeassistant_backend.py` contains integrated dispatcher

---

## 3. HAExecutor (OLD Command Execution)

### Status: **REPLACED** by backend dispatch_command()

### Files to Remove:
- `orac/homeassistant/ha_executor.py` - Legacy HA command executor

### Code to Remove from api.py:
- Import: `from orac.homeassistant.ha_executor import HAExecutor` (line 42)
- Global var: `ha_executor = HAExecutor()` (line 62)
- Legacy execution code (lines 822-850):
  ```python
  # Legacy: If this is a home_assistant topic and no backend, use old HA executor
  if topic_id == "home_assistant" and response_text and not topic.backend_id:
      ...
      ha_result = await ha_executor.execute_json_command(parsed_json)
  ```

### Replacement:
Backend system handles execution:
- `backend.dispatch_command()` (api.py line 803)

---

## 4. Legacy Compatibility Shims

### Status: **KEEP for now** (maintain backward compatibility)

### Files to Keep:
- `orac/config/legacy.py` - Legacy config function wrappers ✅ KEEP
- `orac/backend_manager.py` legacy methods:
  - `update_entity()` → redirects to `update_device_mapping()`
  - `bulk_update_entities()` → redirects to `bulk_update_device_mappings()`
  - `get_entities()` → redirects to `get_device_mappings()`

### Reason:
These provide backward compatibility and don't hurt performance.

---

## 5. Topic Grammar Field (DEPRECATED)

### Status: **DEPRECATED** but keep for backward compatibility

### Location:
- `orac/topic_models/topic.py:30`
  ```python
  grammar: GrammarConfig = Field(default_factory=GrammarConfig, 
                                 description="Grammar configuration (deprecated - use backend_id)")
  ```

### Replacement:
Topics now use `backend_id` which links to backend-generated grammars.

### Action:
Mark as deprecated but keep for old topic configs.

---

## Summary

### High Priority Removal (Actively Running & Wasting Resources):
1. ✅ Grammar Scheduler (runs nightly at 3am)
2. ✅ Old HA mapping/grammar API endpoints (11 endpoints)
3. ✅ HAExecutor system

### Medium Priority Removal (Dead Code):
4. ✅ Dispatcher Registry
5. ✅ Grammar manager/mapping config system

### Keep (Backward Compatibility):
6. ⚠️ Legacy config wrappers
7. ⚠️ Topic grammar field (deprecated)

---

## Estimated Impact:
- **Remove:** ~15 API endpoints
- **Remove:** ~8 files
- **Remove:** ~1500 lines of code
- **Save:** Nightly HA API calls, scheduler overhead
- **Risk:** Low (all functionality replaced by backend system)
