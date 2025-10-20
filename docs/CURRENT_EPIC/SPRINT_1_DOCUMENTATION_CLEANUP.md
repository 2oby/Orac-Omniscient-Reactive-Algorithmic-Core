# Sprint 1: Documentation Cleanup & Restructuring

## Epic Context

This sprint is part of the "Production Readiness" epic. After completing Sprints 1-4 of the cleanup plan (Configuration, API Decomposition, Legacy Removal, and Bug Fixes), we're now focusing on making ORAC Core maintainable and production-ready through proper documentation and security.

## Sprint Goal

Clean up, restructure, and modernize ORAC Core documentation to provide clear, accurate, and maintainable documentation for developers, operators, and users.

## Current State (Problems)

### Root Directory Clutter
- **15+ markdown files** in root directory creating confusion
- Mix of old implementation prompts, planning docs, and current guides
- No clear entry point for new developers
- Files like `CURRENT_FOCUS.md`, `CURRENT_STATUS.md`, `DEVELOPMENT_LOG.md` are likely outdated

### Incomplete/Outdated Documentation
- Architecture documentation scattered across multiple files
- No centralized API documentation
- Deployment instructions incomplete
- Backend system (completed in Sprint 5) not properly documented
- Topic management system not explained
- Grammar generation system documentation missing

### Poor Organization
- No clear docs/ structure
- Old sprint planning docs mixed with evergreen documentation
- Archived content not properly separated
- No index or table of contents

### Missing Critical Documentation
- No troubleshooting guide
- No monitoring/observability guide
- No upgrade/migration guide
- Environment variables not documented
- No developer onboarding guide

## Tasks

### Task 1.1: Audit & Categorize Existing Documentation

**Goal:** Create inventory of all documentation files and categorize them.

**Actions:**
1. List all `.md` files in root and `docs/` directory
2. Categorize each file:
   - ✅ **KEEP & UPDATE**: Still relevant, needs updates
   - 📦 **ARCHIVE**: Historical value but not current
   - 🗑️ **DELETE**: Obsolete, superseded, or no value
   - 🔀 **MERGE**: Content should be merged into another doc
3. Create categorization spreadsheet/document

**Files to Review:**
```
Root Directory:
- cleanup.MD → KEEP (update status)
- CRITICAL_PATH_IMPLEMENTATION.md → ARCHIVE?
- CURRENT_FOCUS.md → DELETE (outdated)
- CURRENT_STATUS.md → DELETE (outdated)
- DEVELOPMENT_LOG.md → ARCHIVE
- DISPATCHER_GRAMMAR_OPTIMIZATION.md → ARCHIVE
- DISPATCHER_OPTIMIZATION_PROMPT.md → ARCHIVE
- fix_save_configuration_prompt.md → ARCHIVE
- instructions.md → KEEP & UPDATE
- INTEGRATION.md → ARCHIVE/DELETE
- LEGACY_CODE_AUDIT.md → ARCHIVE
- README.md → KEEP & UPDATE
- SIMPLIFIED_GRAMMAR_GUI_DESIGN.md → ARCHIVE
- TERMINAL_GRAMMAR_GUI_IMPLEMENTATION.md → ARCHIVE
- verify_GUI_sprint2.md → DELETE

Docs Directory:
- docs/INTEGRATION_CURRENT_FOCUS.md → ARCHIVE
- docs/sprint_4_prompt.md → KEEP (active sprint)
- docs/HOME_ASSISTANT_INTEGRATION_PLAN.md → ARCHIVE
- docs/New Feature Confidence.md → DELETE
- docs/DEVELOPER_GUIDE_GRAMMAR_DISPATCHER.md → UPDATE & MERGE
- docs/NEXT_SESSION_TOPIC_PIPELINE.md → ARCHIVE/DELETE
```

**Deliverable:** `docs/AUDIT_2025-10-20.md` with categorization

---

### Task 1.2: Archive Old Documentation

**Goal:** Move historical/completed documentation to archive.

**Actions:**
1. Move implementation prompts to `docs/archive/implementation_prompts/`
2. Move completed sprint docs to `docs/archive/sprints/` (if not already there)
3. Move historical planning docs to `docs/archive/planning/`
4. Keep archive organized by date/sprint

**Files to Archive:**
```bash
# Implementation prompts
docs/archive/implementation_prompts/
├── CRITICAL_PATH_IMPLEMENTATION.md
├── DISPATCHER_GRAMMAR_OPTIMIZATION.md
├── DISPATCHER_OPTIMIZATION_PROMPT.md
├── fix_save_configuration_prompt.md
├── TERMINAL_GRAMMAR_GUI_IMPLEMENTATION.md
├── SIMPLIFIED_GRAMMAR_GUI_DESIGN.md
└── verify_GUI_sprint2.md

# Planning/Historical
docs/archive/planning/
├── DEVELOPMENT_LOG.md
├── INTEGRATION.md
├── HOME_ASSISTANT_INTEGRATION_PLAN.md
├── INTEGRATION_CURRENT_FOCUS.md
├── LEGACY_CODE_AUDIT.md
└── NEXT_SESSION_TOPIC_PIPELINE.md

# Completed sprints (if not already archived)
docs/archive/sprints/
└── sprint_4_prompt.md (when Sprint 4 fully complete)
```

**Deliverable:** Clean root directory with only essential docs

---

### Task 1.3: Create New Documentation Structure

**Goal:** Establish clear, maintainable documentation structure.

**New Structure:**
```
/
├── README.md                          # Updated: Quick start, overview
├── CONTRIBUTING.md                    # New: How to contribute
└── docs/
    ├── README.md                      # New: Docs index/navigation
    ├── ARCHITECTURE.md                # New: System architecture
    ├── API.md                         # New: API documentation
    ├── DEPLOYMENT.md                  # New: Deployment guide
    ├── CONFIGURATION.md               # New: Configuration guide
    ├── TROUBLESHOOTING.md             # New: Common issues & fixes
    ├── MONITORING.md                  # New: Observability guide
    ├── DEVELOPMENT.md                 # New: Developer guide
    │
    ├── guides/                        # New: How-to guides
    │   ├── backend-setup.md          # How to add a backend
    │   ├── topic-configuration.md    # How to configure topics
    │   ├── grammar-generation.md     # How grammar generation works
    │   └── testing.md                # How to run tests
    │
    ├── CURRENT_EPIC/                 # Current sprint planning
    │   ├── SPRINT_1_DOCUMENTATION_CLEANUP.md
    │   └── SPRINT_2_SECURITY_STABILITY.md
    │
    └── archive/                      # Historical documentation
        ├── sprints/                  # Completed sprints
        ├── implementation_prompts/   # Old implementation docs
        └── planning/                 # Old planning docs
```

**Actions:**
1. Create folder structure
2. Create placeholder files for all new docs
3. Add navigation/index to each section

**Deliverable:** New docs/ structure with placeholders

---

### Task 1.4: Write Core Documentation

**Goal:** Create comprehensive core documentation files.

#### 1.4.1: Update README.md
**Content:**
- Project overview (what is ORAC?)
- Key features
- Quick start (5-minute setup)
- Architecture diagram (high-level)
- Link to detailed documentation
- Status badges (if applicable)
- License

#### 1.4.2: Write ARCHITECTURE.md
**Content:**
- System components overview
- Component interaction diagram
- Data flow (STT → ORAC → Backend → Response)
- Backend system architecture
  - Backend abstract class
  - Backend factory
  - Backend-specific implementations (HomeAssistant)
  - Dispatcher pattern
- Topic management system
- Grammar generation system
- LLM integration (llama.cpp)
- Configuration system
- Technology stack

#### 1.4.3: Write API.md
**Content:**
- API overview
- Authentication (if applicable)
- Base URL and versioning
- Endpoint categories:
  - System endpoints (`/v1/status`, `/health`)
  - Model endpoints (`/v1/models`)
  - Generation endpoints (`/v1/generate/*`)
  - Backend endpoints (`/api/backends/*`)
  - Topic endpoints (if exposed)
- Request/response examples
- Error codes and handling
- Rate limiting (if applicable)
- Link to Swagger/OpenAPI docs

#### 1.4.4: Write DEPLOYMENT.md
**Content:**
- Prerequisites (Docker, Docker Compose, hardware requirements)
- Environment variables reference
- Docker deployment
  - Build process
  - docker-compose.yml explanation
  - Volume mounts
- Orin Nano specific setup
- `deploy_and_test.sh` usage
  - Standard deployment: `./deploy_and_test.sh "message"`
  - Rebuild deployment: `./deploy_and_test.sh --rebuild "message"`
- Network configuration
- Timezone configuration
- Model setup and paths
- Health checks
- Logs access (`docker logs orac`)
- Backup and restore procedures

#### 1.4.5: Write CONFIGURATION.md
**Content:**
- Configuration file locations
- Environment variables reference (complete list)
- `model_configs.yaml` structure
- `topics.yaml` structure
- Backend configuration format
- Grammar files configuration
- Network settings
- Model paths (ORAC_MODELS_PATH)
- Logging configuration
- Configuration precedence (CLI > Env > YAML > Defaults)
- Configuration examples for common scenarios

#### 1.4.6: Write TROUBLESHOOTING.md
**Content:**
- Common issues and solutions:
  - Container won't start
  - Model not found errors
  - Backend connection failures
  - Grammar generation errors
  - "No response generated" errors
  - Timezone issues
  - Permission errors
- Debugging commands
  - Check container status
  - View logs
  - Test endpoints manually
  - Inspect configuration
- Performance issues
- Error code reference
- Where to get help

#### 1.4.7: Write MONITORING.md
**Content:**
- Health check endpoints
- Log locations and formats
- Key metrics to monitor
  - API response times
  - Model inference times
  - Backend connection status
  - Memory usage
  - Disk usage
- Log analysis tips
- Setting up alerts (future)
- Performance baselines

#### 1.4.8: Write DEVELOPMENT.md
**Content:**
- Development environment setup
- Code structure overview
- How to run tests
- How to add a new backend
- How to add a new route
- Coding standards
- Branch strategy (master, cleanup, feature branches)
- Git workflow
- Deployment workflow for development
- IDE setup recommendations

#### 1.4.9: Write CONTRIBUTING.md
**Content:**
- How to contribute
- Code of conduct
- Pull request process
- Issue reporting
- Documentation contributions
- Testing requirements
- Code review process

**Deliverable:** 9 comprehensive documentation files

---

### Task 1.5: Write Detailed Guides

**Goal:** Create how-to guides for common tasks.

#### 1.5.1: Backend Setup Guide (`docs/guides/backend-setup.md`)
**Content:**
- What is a backend?
- Creating a backend via API
- Configuring backend connection
- Fetching entities from backend
- Mapping devices
- Generating grammar for backend
- Testing backend commands
- Troubleshooting backend issues

#### 1.5.2: Topic Configuration Guide (`docs/guides/topic-configuration.md`)
**Content:**
- What are topics?
- Topic structure (name, model, settings, backend_id)
- Creating topics
- Linking topics to backends
- Topic settings (temperature, top_p, system_prompt)
- Auto-discovery vs manual topics
- Wake word configuration (for STT integration)
- Testing topics

#### 1.5.3: Grammar Generation Guide (`docs/guides/grammar-generation.md`)
**Content:**
- What is GBNF grammar?
- How ORAC uses grammar to constrain LLM output
- Backend-generated grammars vs static grammars
- Grammar file locations
- How backend device mappings create grammar rules
- Viewing generated grammar
- Debugging grammar issues
- Grammar testing

#### 1.5.4: Testing Guide (`docs/guides/testing.md`)
**Content:**
- Running unit tests
- Running integration tests
- Test coverage
- Writing new tests
- Mocking external services
- Test fixtures
- CI/CD pipeline (future)

**Deliverable:** 4 detailed how-to guides

---

### Task 1.6: Update Existing Documentation

**Goal:** Update files that are being kept to reflect current state.

#### 1.6.1: Update cleanup.MD
**Actions:**
- Update Sprint 4 status to "Completed (Critical Items)"
- Note which tasks were deferred
- Update Sprint 5-10 as "Superseded by new epic structure"
- Add reference to `docs/CURRENT_EPIC/`

#### 1.6.2: Update instructions.md (or merge into README)
**Actions:**
- Evaluate if still needed
- Either update or merge content into README/DEPLOYMENT
- Remove if redundant

**Deliverable:** Updated cleanup.MD and instructions.md decision

---

### Task 1.7: Create Documentation Index

**Goal:** Make documentation easily navigable.

#### 1.7.1: Create docs/README.md
**Content:**
```markdown
# ORAC Core Documentation

Welcome to ORAC Core documentation!

## Getting Started
- [Quick Start](../README.md) - Get ORAC running in 5 minutes
- [Architecture Overview](ARCHITECTURE.md) - Understand how ORAC works
- [Deployment Guide](DEPLOYMENT.md) - Deploy ORAC to production

## Configuration & Setup
- [Configuration Reference](CONFIGURATION.md) - All configuration options
- [Backend Setup](guides/backend-setup.md) - Connect to Home Assistant
- [Topic Configuration](guides/topic-configuration.md) - Configure AI topics

## Development
- [Developer Guide](DEVELOPMENT.md) - Set up development environment
- [API Documentation](API.md) - API reference
- [Contributing](../CONTRIBUTING.md) - How to contribute
- [Testing Guide](guides/testing.md) - Run and write tests

## Operations
- [Monitoring](MONITORING.md) - Monitor ORAC in production
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions

## How-To Guides
- [Backend Setup](guides/backend-setup.md)
- [Topic Configuration](guides/topic-configuration.md)
- [Grammar Generation](guides/grammar-generation.md)
- [Testing](guides/testing.md)

## Reference
- [API Documentation](API.md)
- [Configuration Reference](CONFIGURATION.md)
- [Troubleshooting](TROUBLESHOOTING.md)

## Historical Documentation
- [Archived Sprints](archive/sprints/)
- [Implementation Prompts](archive/implementation_prompts/)
- [Planning Documents](archive/planning/)
```

**Deliverable:** Comprehensive docs/README.md index

---

### Task 1.8: Add Diagrams (Optional but Recommended)

**Goal:** Visual representation of architecture and flows.

**Diagrams to Create:**
1. **System Architecture Diagram**
   - Components: STT, ORAC Core, Backends, LLM
   - Data flow arrows
   - External integrations

2. **Backend System Diagram**
   - BackendFactory
   - AbstractBackend
   - HomeAssistantBackend
   - Dispatcher relationship

3. **Request Flow Diagram**
   - User command → STT → ORAC → LLM → Backend → Response
   - Topic resolution
   - Grammar application

**Tools:**
- Mermaid (embedded in markdown)
- Draw.io
- Excalidraw
- ASCII diagrams

**Deliverable:** Architecture diagrams in ARCHITECTURE.md

---

## Testing & Validation

After completing all tasks:

### Documentation Review Checklist
- [ ] All new docs have clear purpose
- [ ] Navigation is intuitive
- [ ] No broken links
- [ ] Examples are accurate and tested
- [ ] Code snippets are correct
- [ ] Diagrams are clear and accurate
- [ ] No outdated information
- [ ] Consistent formatting
- [ ] No TODO placeholders left

### User Testing
- [ ] New developer can set up ORAC following docs
- [ ] Operator can deploy ORAC following docs
- [ ] Common issues are covered in troubleshooting
- [ ] All configuration options are documented

### Cleanup Verification
- [ ] Root directory has ≤5 markdown files
- [ ] All archives properly organized
- [ ] No duplicate documentation
- [ ] Clear entry points for different audiences

---

## Deliverables

### Primary Deliverables
1. ✅ Clean root directory (≤5 essential files)
2. ✅ Comprehensive `docs/` structure
3. ✅ 9 core documentation files (README, ARCHITECTURE, API, etc.)
4. ✅ 4 detailed how-to guides
5. ✅ Documentation index (docs/README.md)
6. ✅ Archive organized by category
7. ✅ Updated cleanup.MD

### Documentation Files Created
- Root: README.md (updated), CONTRIBUTING.md (new)
- docs/: README.md, ARCHITECTURE.md, API.md, DEPLOYMENT.md, CONFIGURATION.md, TROUBLESHOOTING.md, MONITORING.md, DEVELOPMENT.md
- guides/: backend-setup.md, topic-configuration.md, grammar-generation.md, testing.md

### Archive Organization
- docs/archive/sprints/ (completed sprints)
- docs/archive/implementation_prompts/ (old prompts)
- docs/archive/planning/ (historical planning)

---

## Success Criteria

Sprint 1 is complete when:
- ✅ Root directory has ≤5 markdown files
- ✅ All core documentation written and reviewed
- ✅ Documentation structure is clear and navigable
- ✅ Historical docs properly archived
- ✅ New developer can onboard using documentation alone
- ✅ No broken links or outdated information
- ✅ Documentation committed and pushed to cleanup branch

---

## Estimated Timeline

- **Task 1.1 (Audit):** 2 hours
- **Task 1.2 (Archive):** 2 hours
- **Task 1.3 (Structure):** 1 hour
- **Task 1.4 (Core Docs):** 8-12 hours (most time-intensive)
- **Task 1.5 (Guides):** 4-6 hours
- **Task 1.6 (Updates):** 1 hour
- **Task 1.7 (Index):** 1 hour
- **Task 1.8 (Diagrams):** 2-4 hours (optional)

**Total:** ~20-30 hours (2.5-4 days full-time)

---

## Notes

- This sprint focuses on **clarity and completeness** over perfection
- Documentation should be **practical and actionable**
- Use **real examples** from the actual codebase
- Keep **technical accuracy** as top priority
- **Test all examples** before documenting them
- Commit frequently as docs are completed
- Can be done **incrementally** - core docs first, guides later

---

## Next Sprint

After Sprint 1 completion, move to **Sprint 2: Security & Stability** which will cover:
- Security audit
- Input validation
- Rate limiting
- Error handling improvements
- Stability improvements
