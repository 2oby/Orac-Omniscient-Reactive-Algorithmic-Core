# ORAC Core - Next Session Agenda

## Priority Tasks

### 1. Sprint 2: Backend Configuration & Entity Management
**Status**: Not started
**Priority**: HIGH - Core functionality

**Overview**: Implement backend configuration system for Home Assistant integration via the web UI.

**Tasks**:
- [ ] Build Backend Manager module (`orac/backend_manager.py`) - CRUD, connection testing, entity fetching
- [ ] Create Web UI: navigation (MAIN, TOPICS, BACKENDS), Add Backend modal, entity config screen
- [ ] Add API endpoints: `/api/backends`, `/api/backends/{id}/test`, `/api/backends/{id}/entities`
- [ ] Test with actual Home Assistant instance on Pi (192.168.8.99:8123)

### 2. ~~Docker Cleanup Cron on Orin~~ DONE (2026-03-16)
- [x] Add weekly `docker image prune` cron for user `toby` on orin4
