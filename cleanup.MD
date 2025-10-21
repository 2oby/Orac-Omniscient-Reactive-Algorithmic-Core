# ORAC Core Cleanup and Productionization Plan

## Overview

This document outlines the cleanup and refactoring plan for ORAC Core. The codebase was developed rapidly across multiple sprints and needs sanitization and productionization before being considered production-ready.

## Pre-Work Requirements

**IMPORTANT: Before starting any cleanup work:**

1. **Verify Current State**
   ```bash
   ./deploy_and_test.sh "Pre-cleanup verification"
   ```
   - Ensure all tests pass
   - Verify deployment works
   - Document current working state

2. **Commit All Changes**
   ```bash
   git status
   git add -A
   git commit -m "Pre-cleanup checkpoint - working state"
   git push origin master
   ```

3. **Create Cleanup Branch**
   ```bash
   git checkout -b cleanup/productionization
   ```
   - Create ONE branch for all cleanup work
   - Never work directly on master
   - Deploy and test after each major change

## Cleanup Sprints

### Sprint 1: Configuration Consolidation & Constants (2-3 days)

**Goal:** Eliminate magic numbers and consolidate configuration management.

**Current Issues:**
- Magic numbers scattered throughout code (ports: 8123, 8000; timeouts: 30, 10, 5; temperatures: 0.1, 0.7, 0.9)
- Configuration spread across env vars, YAML files, JSON files, and hardcoded values
- No single source of truth for configuration

**Tasks:**

1.1. **Create centralized configuration module** (orac/config/constants.py)
```python
# All magic numbers should be moved here
class NetworkConfig:
    DEFAULT_HA_PORT = 8123
    DEFAULT_ORAC_PORT = 8000
    DEFAULT_TIMEOUT = 30
    HA_TIMEOUT = 10
    CACHE_TTL = 300

class ModelConfig:
    DEFAULT_TEMPERATURE = 0.7
    GRAMMAR_TEMPERATURE = 0.1
    DEFAULT_TOP_P = 0.9
    DEFAULT_TOP_K = 40
    DEFAULT_MAX_TOKENS = 512
```

1.2. **Replace all hardcoded values** in:
- orac/api.py (lines 758, 1184, 1197, etc.)
- orac/backend_manager.py
- orac/homeassistant/cache.py (line 62: ttl=300, max_size=1000)
- orac/homeassistant/client.py
- orac/dispatchers/homeassistant.py (line 44)

1.3. **Consolidate configuration loading**
- Create orac/config/loader.py for unified config management
- Merge favorites.json, model_configs.yaml, and env var logic
- Define clear precedence: CLI args > Env vars > YAML config > Defaults

1.4. **Update tests**
- Add tests for configuration module
- Update existing tests to use new constants

**Deliverables:**
- orac/config/__init__.py
- orac/config/constants.py
- orac/config/loader.py
- Updated files using constants instead of magic numbers
- Test: python test_config.py

**Testing:**
```bash
# After changes
./deploy_and_test.sh "Sprint 1: Configuration consolidation"
```

---

### Sprint 2: API Decomposition (3-4 days)

**Goal:** Break down the monolithic api.py (1314 lines) into manageable modules.

**Current Issues:**
- api.py handles routes, business logic, initialization, and global state
- 1314 lines is too large to maintain
- Global variables create tight coupling
- Mixed responsibilities violate SRP

**Tasks:**

2.1. **Split API into logical modules:**
```
orac/api/
├── __init__.py           # Main FastAPI app
├── dependencies.py       # Dependency injection (replace global vars)
├── routes/
│   ├── __init__.py
│   ├── system.py         # Status, health endpoints
│   ├── models.py         # Model management endpoints
│   ├── generation.py     # Text generation endpoints
│   ├── backends.py       # Backend management endpoints
│   ├── topics.py         # Topic management endpoints
│   ├── homeassistant.py  # HA-specific endpoints
│   └── web.py            # Web interface routes
├── middleware.py         # CORS, logging, etc.
└── lifecycle.py          # Startup/shutdown events
```

2.2. **Replace global variables with dependency injection**
- Convert client, ha_client, etc. to FastAPI dependencies
- Use contextmanagers for resource lifecycle
- Example:
```python
# dependencies.py
async def get_llama_client() -> LlamaCppClient:
    # Lazy initialization
    ...

# In routes
@app.get("/v1/models")
async def list_models(client: LlamaCppClient = Depends(get_llama_client)):
    ...
```

2.3. **Extract business logic to service layer**
- Create orac/services/ directory
- Move generation logic, mapping logic, etc. out of API routes
- API routes should only handle HTTP concerns

2.4. **Consolidate startup/shutdown logic**
- Move to lifecycle.py
- Clean initialization order
- Proper resource cleanup

**Deliverables:**
- orac/api/ directory structure
- orac/services/ for business logic
- Removed global variables
- Cleaner, focused route handlers
- Test: pytest tests/test_api.py

**Testing:**
```bash
./deploy_and_test.sh "Sprint 2: API decomposition"
```

---

### Sprint 3: Code Cleanup & Legacy Code Removal ✅ COMPLETED (2025-10-19)

**Goal:** Remove dead code, comments, and legacy implementations replaced by Backend system.

**Status:** ✅ **COMPLETED** - All tasks finished and verified on orin4

**Detailed Plan:** See `docs/archive/sprints/sprint_3_detailed.md` for comprehensive task breakdown.

**Baseline Tag:** `sprint1-before-legacy-removal` (created 2025-10-19)

**Actual Impact:**
- ✅ Removed **2,180 lines** of code across **28 files**
- ✅ Removed **15 API endpoints**
- ✅ Removed **8 legacy files**
- ✅ Eliminated nightly 3am scheduler overhead and HA API calls
- ✅ All Sprint X: comments converted to proper documentation
- ✅ Tests organized into tests/ directory
- ✅ Documentation archived to docs/archive/sprints/

**Files Removed:**
- `orac/homeassistant/grammar_scheduler.py` (274 lines)
- `orac/homeassistant/grammar_manager.py` (454 lines)
- `orac/homeassistant/mapping_config.py` (337 lines)
- `orac/homeassistant/mapping_builder.py` (255 lines)
- `orac/homeassistant/entity_mappings.yaml` (17 lines)
- `orac/homeassistant/ha_executor.py` (354 lines)
- `orac/dispatchers/registry.py` (100 lines)

**Deployment Workflow Used:**
```bash
# IMPORTANT: Use deploy script for all commits/deployments
./deploy_and_test.sh "Sprint 3: [description]"

# Access test machine (orin4)
ssh orin4

# No code is ever run on dev machine (Mac)
# All testing happens on orin4 via Docker
```

**Verification:**
```bash
# Verified no scheduler running
ssh orin4 'docker logs orac --since="2025-10-19T15:42:00" 2>&1 | grep -i scheduler'
# Result: No scheduler messages (successfully removed)

# API health check
curl http://192.168.8.192:8000/v1/status
# Result: {"status":"ok","models_available":19,"version":"0.2.0"}

# Backend grammar generation
curl http://192.168.8.192:8000/api/backends/homeassistant_8ca84424/grammar
# Result: Successfully generates GBNF grammar
```

**Deliverables:**
- ✅ Clean `orac/api.py` (reduced from 1314 to 1046 lines)
- ✅ All legacy systems removed
- ✅ Backend grammar generation verified working
- ✅ Organized test directory (3 files moved to tests/)
- ✅ Clean documentation structure (17 files archived)
- ✅ System deployed and verified on orin4

---

### Sprint 4: Duplicate Code & Refactoring (3-4 days)

**Goal:** Eliminate code duplication, improve code reuse, and fix bugs discovered in Sprint 2.

**Current Issues:**
- **TIMEZONE BUG:** Docker container logs in UTC, needs CET (Central European Time) for easier debugging
- **BUG (Sprint 2):** BackendManager.auto_regenerate_grammar() passes string instead of BackendManager instance to BackendGrammarGenerator
- **BUG (Sprint 2):** Generation endpoint sometimes returns "No response generated" - investigate llama.cpp client response handling
- HomeAssistant connection setup duplicated in multiple files
- URL parsing logic repeated
- Error handling patterns duplicated
- Similar validation logic scattered

**Tasks:**

4.0. **FIX: Bugs discovered during Sprint 2**
- Fix BackendManager.auto_regenerate_grammar() to properly instantiate BackendGrammarGenerator with backend_manager instance
- Investigate and fix "No response generated" issue in generation endpoint
- Add error handling and logging around response text extraction
- Test generation endpoints thoroughly after fixes
- **Priority:** HIGH - Core functionality affected

4.1. **FIX: Configure timezone to CET (Central European Time)**
- Update Docker container to use CET timezone
- Configure Python logging to use CET timestamps
- Update all timestamp displays in logs and API responses
- Verify: `docker logs orac` shows correct local time (CET/CEST)
- **Priority:** HIGH - Affects debugging and monitoring

4.2. **Extract HomeAssistant client creation**
- Create orac/homeassistant/factory.py
- Centralize client creation logic
- Used by: backend_manager.py, homeassistant_backend.py, api.py

4.3. **Create common utilities**
```
orac/utils/
├── __init__.py
├── url_parser.py       # URL parsing logic
├── validators.py       # Common validation
└── response_builder.py # Standardized API responses
```

4.4. **Standardize error responses**
- Create consistent error response format
- Example:
```python
{
    "status": "error",
    "error": {
        "code": "BACKEND_NOT_FOUND",
        "message": "Backend abc123 not found",
        "details": {...}
    },
    "request_id": "...",
    "timestamp": "..."
}
```

4.5. **Extract repeated patterns**
- Backend statistics calculation (repeated in multiple backends)
- Device mapping validation logic
- Entity parsing and normalization

4.6. **Consolidate logging setup**
- Create orac/utils/logging.py
- Standardize on single logger type (prefer loguru or stdlib)
- Currently mixing: get_logger(), logging.getLogger(), loguru logger
- Consistent log levels and formatting

**Deliverables:**
- orac/utils/ directory
- orac/homeassistant/factory.py
- Reduced code duplication
- Consistent error responses
- Unified logging approach

**Testing:**
```bash
./deploy_and_test.sh "Sprint 4: Refactoring and deduplication"
```

---

### Sprint 5: Type Hints & Documentation (3-4 days)

**Goal:** Complete type hints and improve documentation quality.

**Current Issues:**
- Inconsistent type hints (some functions have them, others don't)
- Incomplete docstrings
- Outdated documentation
- No type checking in CI

**Tasks:**

5.1. **Add complete type hints**
- Run mypy to find missing annotations
- Add type hints to all public functions
- Add type hints to all class methods
- Focus areas:
  - orac/api/ (after split in Sprint 2)
  - orac/backend_manager.py
  - orac/topic_manager.py
  - orac/homeassistant/

5.2. **Standardize docstrings**
- Use Google or NumPy docstring format consistently
- Include:
  - Function purpose
  - Args with types
  - Returns with type
  - Raises (if applicable)
  - Examples for complex functions

5.3. **Update architecture documentation**
- Create docs/ARCHITECTURE.md
- Document current architecture (post-Sprint 5 backend refactor)
- Include diagrams if helpful:
  - Component interaction
  - Data flow (STT → ORAC → HA)
  - Backend/Dispatcher relationship

5.4. **Add API documentation**
- Use FastAPI's built-in OpenAPI docs
- Add descriptions to all endpoints
- Add request/response examples
- Tag endpoints properly

5.5. **Setup type checking**
- Add mypy.ini configuration
- Add type checking to CI pipeline
- Fix all type errors

**Deliverables:**
- Complete type hints across codebase
- Standardized docstrings
- docs/ARCHITECTURE.md
- mypy.ini
- Updated API documentation (Swagger/OpenAPI)

**Testing:**
```bash
mypy orac/
./deploy_and_test.sh "Sprint 5: Type hints and documentation"
```

---

### Sprint 6: Architectural Improvements (3-4 days)

**Goal:** Fix architectural issues and improve patterns.

**Current Issues:**
- Manual singleton in TopicManager (should use proper pattern)
- Tight coupling between modules
- No clear separation of concerns in some areas
- Inconsistent use of async/await

**Tasks:**

6.1. **Fix TopicManager singleton**
- Replace manual singleton with proper implementation
- Consider using dependency injection instead
- Or use FastAPI's state management

6.2. **Improve async/await consistency**
- Audit all async functions
- Ensure proper async propagation
- Fix blocking calls in async contexts
- Add asyncio best practices

6.3. **Reduce coupling**
- Backend classes shouldn't import from api
- Use interfaces/protocols where appropriate
- Inject dependencies rather than direct imports

6.4. **Improve error handling**
- Custom exception hierarchy
- Example:
```python
class OracException(Exception): pass
class BackendException(OracException): pass
class BackendNotFound(BackendException): pass
class BackendConnectionError(BackendException): pass
```

6.5. **Backend factory improvements**
- Better registration mechanism
- Plugin-style architecture for future backends
- Clear extension points

**Deliverables:**
- Improved TopicManager
- Consistent async/await usage
- Reduced coupling
- Custom exception hierarchy
- Better backend factory

**Testing:**
```bash
./deploy_and_test.sh "Sprint 6: Architectural improvements"
```

---

### Sprint 7: Performance & Optimization (2-3 days)

**Goal:** Optimize performance bottlenecks and resource usage.

**Current Issues:**
- No caching strategy for expensive operations
- Potential N+1 queries
- Unnecessary file I/O
- Large JSON responses

**Tasks:**

7.1. **Implement response caching**
- Cache grammar generation results
- Cache backend entity lists
- Use ETags for conditional requests

7.2. **Optimize database/file operations**
- Batch reads/writes where possible
- Use async file I/O
- Reduce redundant yaml.load() calls

7.3. **Add performance monitoring**
- Add timing middleware
- Log slow operations (>100ms)
- Add prometheus metrics (optional)

7.4. **Optimize large responses**
- Add pagination for entity lists
- Add field filtering (only return requested fields)
- Compress responses (gzip)

7.5. **Resource pooling**
- Connection pooling for HA client
- Thread pool for CPU-bound operations

**Deliverables:**
- Caching layer
- Performance monitoring
- Optimized I/O operations
- Response pagination/filtering

**Testing:**
```bash
./deploy_and_test.sh "Sprint 7: Performance optimizations"
```

---

### Sprint 8: Testing & Quality Assurance (3-4 days)

**Goal:** Improve test coverage and quality.

**Current Issues:**
- Test coverage unknown
- Tests not in consistent location
- Integration tests may be missing
- No CI/CD pipeline

**Tasks:**

8.1. **Measure current coverage**
```bash
pytest --cov=orac --cov-report=html
```

8.2. **Increase test coverage to >80%**
- Add unit tests for untested modules
- Focus on:
  - Backend manager
  - Topic manager
  - Configuration loader
  - Utils

8.3. **Add integration tests**
- Full API workflow tests
- Backend creation → entity fetch → grammar generation → command execution
- Mock external services (HA)

8.4. **Add contract tests**
- Test API request/response schemas
- Ensure backward compatibility

8.5. **Setup CI/CD**
- GitHub Actions or GitLab CI
- Run tests on every PR
- Run type checking (mypy)
- Run linting (ruff or flake8)

8.6. **Add load testing**
- Test concurrent requests
- Test under memory constraints
- Profile memory usage

**Deliverables:**
- >80% test coverage
- Integration test suite
- CI/CD pipeline
- Load test results
- Coverage report

**Testing:**
```bash
pytest --cov=orac --cov-report=term-missing
./deploy_and_test.sh "Sprint 8: Testing improvements"
```

---

### Sprint 9: Security & Best Practices (2-3 days)

**Goal:** Improve security and follow best practices.

**Current Issues:**
- API tokens in logs (potential security issue)
- No input validation in some endpoints
- No rate limiting
- CORS allows all origins

**Tasks:**

9.1. **Audit security issues**
- Scan for exposed secrets
- Check token handling
- Review CORS configuration
- Check for SQL injection (if using DB)

9.2. **Add input validation**
- Validate all user inputs using Pydantic
- Sanitize file paths
- Validate JSON payloads

9.3. **Implement security headers**
- Add security middleware
- HTTPS enforcement (in production)
- HSTS, X-Frame-Options, etc.

9.4. **Add rate limiting**
- Prevent API abuse
- Use slowapi or similar

9.5. **Secrets management**
- Never log tokens/passwords
- Use environment variables properly
- Consider using secrets manager (future)

9.6. **Add request ID tracking**
- Add request ID to all log entries
- Include in error responses
- Useful for debugging

**Deliverables:**
- Security audit report
- Input validation across all endpoints
- Security middleware
- Rate limiting
- Request ID tracking

**Testing:**
```bash
./deploy_and_test.sh "Sprint 9: Security improvements"
```

---

### Sprint 10: Final Polish & Production Readiness (2-3 days)

**Goal:** Final cleanup and production preparation.

**Tasks:**

10.1. **Code review**
- Review all changes from Sprints 1-9
- Ensure consistency
- Check for any remaining issues

10.2. **Performance baseline**
- Document response times
- Document memory usage
- Document startup time

10.3. **Production configuration**
- Create production-ready docker-compose.yml
- Add health checks
- Configure logging for production
- Add restart policies

10.4. **Deployment documentation**
- Update deployment guides
- Add troubleshooting section
- Document environment variables
- Add upgrade guide

10.5. **Create release notes**
- Summarize all changes
- Note breaking changes (if any)
- Migration guide from old version

10.6. **Monitoring setup**
- Add health check endpoint
- Add readiness probe
- Add metrics endpoint (optional)
- Document monitoring setup

**Deliverables:**
- Production-ready configuration
- Comprehensive documentation
- Release notes
- Monitoring setup guide

**Testing:**
```bash
# Final comprehensive test
./deploy_and_test.sh "Production ready - v2.0.0"
```

---

## Progress Tracking

Workflow for each sprint:
1. Complete all tasks in sprint
2. Run `./deploy_and_test.sh "Sprint N: Description"` to verify
3. Commit changes with meaningful message
4. Move to next sprint

All work happens on the `cleanup/productionization` branch until complete, then merge to master.

## Sprint Status

### Cleanup Sprints (Original Plan)

| Sprint | Status | Completion Date | Notes |
|--------|--------|-----------------|-------|
| Sprint 1: Configuration | ✅ Completed | 2025-10-19 | Tag: `sprint1-before-legacy-removal`, all magic numbers replaced |
| Sprint 2: API Decomposition | ✅ Completed | 2025-10-19 | Refactored 995-line api.py into modular structure with routes and services |
| Sprint 3: Code Cleanup | ✅ Completed | 2025-10-19 | Removed 2,180 lines of legacy code across 28 files |
| Sprint 4: Bug Fixes | ✅ Completed | 2025-10-19 | Fixed Bug 1 (grammar generator), Bug 2 (response logging), timezone to CET |
| Sprint 5: Type Hints | 🔄 Deferred | - | Deprioritized in favor of production readiness |
| Sprint 6: Architecture | 🔄 Deferred | - | Deprioritized in favor of production readiness |
| Sprint 7: Performance | 🔄 Deferred | - | Deprioritized in favor of production readiness |
| Sprint 8: Testing | 🔄 Deferred | - | Deprioritized in favor of production readiness |
| Sprint 9: Security | 📋 Planned | - | See CURRENT_EPIC/SPRINT_2_SECURITY_STABILITY.md |
| Sprint 10: Production | 📋 Planned | - | See CURRENT_EPIC/SPRINT_2_SECURITY_STABILITY.md |

### New Epic Structure (Production Readiness)

**Note:** After completing Sprints 1-4, the project transitioned to a new epic-based structure focused on production readiness. See `docs/CURRENT_EPIC/` for current sprint planning.

| Sprint | Status | Completion Date | Notes |
|--------|--------|-----------------|-------|
| **Sprint 1: Documentation** | ✅ Completed | 2025-10-20 | Complete documentation restructuring and cleanup |
| **Sprint 2: Security & Stability** | 📋 Planned | - | See CURRENT_EPIC/SPRINT_2_SECURITY_STABILITY.md |

#### Sprint 1: Documentation - Completed Deliverables

**Audit & Organization:**
- ✅ Audited 42 markdown files and categorized them
- ✅ Archived 14 historical files to `docs/archive/`
- ✅ Deleted 4 obsolete files
- ✅ Merged instructions.md content into DEPLOYMENT.md
- ✅ Removed CONTRIBUTING.md (content in DEVELOPMENT.md)
- ✅ Root directory reduced from 15 to **2 essential markdown files** (README.md, cleanup.MD)

**Core Documentation Created:**
- ✅ README.md (updated - comprehensive project overview)
- ✅ ARCHITECTURE.md (complete system architecture, 500+ lines)
- ✅ API.md (complete REST API reference, 800+ lines)
- ✅ DEPLOYMENT.md (production deployment guide, 600+ lines)
- ✅ CONFIGURATION.md (configuration reference, 600+ lines)
- ✅ TROUBLESHOOTING.md (common issues and solutions, 400+ lines)
- ✅ MONITORING.md (observability guide, 400+ lines)
- ✅ DEVELOPMENT.md (developer guide, 500+ lines)

**How-To Guides Created:**
- ✅ guides/backend-setup.md (Backend setup tutorial)
- ✅ guides/topic-configuration.md (Topic configuration guide)
- ✅ guides/grammar-generation.md (Grammar creation guide)
- ✅ guides/testing.md (Testing guide)

**Documentation Index:**
- ✅ docs/README.md (comprehensive navigation and index)

**Archive Organization:**
- ✅ docs/archive/sprints/ (completed sprints)
- ✅ docs/archive/implementation_prompts/ (old implementation docs)
- ✅ docs/archive/planning/ (historical planning docs)

**Total Documentation:** 12 comprehensive files, 5,700+ lines of high-quality documentation

**Next:** Sprint 2 (Security & Stability) - See `docs/CURRENT_EPIC/SPRINT_2_SECURITY_STABILITY.md`

## Estimated Timeline

- **Total Duration:** 25-35 days (5-7 weeks)
- **Full-time equivalent:** 1 month with 1 developer
- **Part-time (50%):** 2 months

## Success Criteria

Upon completion of all sprints, the codebase should:

- ✅ Have no magic numbers (all in constants)
- ✅ Have modular, focused files (<500 lines each)
- ✅ Have >80% test coverage
- ✅ Pass all type checks (mypy)
- ✅ Have consistent code style
- ✅ Have comprehensive documentation
- ✅ Be production-ready with proper security
- ✅ Have CI/CD pipeline
- ✅ Pass all deployment tests
- ✅ Have clear architecture with low coupling

## Notes for Implementation

- **Do not skip the pre-work requirements** - they are critical for safe refactoring
- **Work on single cleanup branch** - all sprints on `cleanup/productionization` branch
- **Deploy and test after each major change** - use `./deploy_and_test.sh` frequently
- **Keep the test machine (orin4) in sync** - it's the source of truth
- **Commit frequently** with meaningful messages so you can rollback individual changes if needed
- **Document any issues** found during sprints for future reference
- **Communicate changes** that might affect other components (Hay Ora, ORAC STT)
