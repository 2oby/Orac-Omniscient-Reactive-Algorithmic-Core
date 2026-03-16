# ORAC Core — Next Steps

**Last Updated:** 2026-03-16
**Status:** Running, healthy, receiving heartbeats, 4 topics loaded, `computa` active (1460 triggers)

---

## Next Up

### 1. Backend Configuration & Entity Management (Sprint 2)
**Status:** Not started
**Priority:** HIGH — Core functionality
**Historical docs:** `docs/CURRENT_EPIC/` has related sprint plans

**Overview:** Implement backend configuration system for Home Assistant integration via the web UI. Currently backends are configured via env vars and YAML — this sprint adds a UI.

**Tasks:**
- [ ] Build Backend Manager module (`orac/backend_manager.py`) — CRUD, connection testing, entity fetching from HA
- [ ] Add API endpoints: `/api/backends`, `/api/backends/{id}/test`, `/api/backends/{id}/entities`
- [ ] Create Web UI: navigation (MAIN, TOPICS, BACKENDS), Add Backend modal, entity config screen, entity cards with enable/disable toggles
- [ ] Test with actual Home Assistant instance on Pi (192.168.8.99:8123)

### 2. Fix Cache Bugs (3 issues)
**Status:** Open
**Priority:** HIGH — Affects correctness
**Details:** See system-level `../NEXT.md` Bugs section

1. Cache is global, not per-topic (needs `topic_id` field)
2. Cache stores commands without verifying HA state change
3. "Error" rollback command gets cached itself

---

## Deferred

### Documentation Cleanup (Sprint 1)
From `docs/CURRENT_EPIC/SPRINT_1_DOCUMENTATION_CLEANUP.md`:
- 15+ markdown files in root directory, mix of old prompts and current guides
- No clear entry point for new developers
- **When:** Low priority, incremental

### Security & Stability (Sprint 2)
From `docs/CURRENT_EPIC/SPRINT_2_SECURITY_STABILITY.md`:
- No authentication on API endpoints, no CORS review, no rate limiting
- **When:** After core functionality complete

### Performance Optimization (Sprint 3)
From `docs/CURRENT_EPIC/SPRINT_3_PERFORMANCE_OPTIMIZATION.md`:
- Establish baselines, profile critical paths, optimize
- **When:** After security hardening

---

## Completed (2026-03-16)

- ~~**Docker cleanup cron on Orin**~~ — Weekly `docker image prune` cron installed.
- ~~**Project docs bootstrap**~~ — Created CLAUDE.md + NEXT.md matching OpenClaw/VPS structure.
