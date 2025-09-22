# Sprint 2 Implementation Prompt for Opus 4.1

## Context
You are implementing Sprint 2 of the ORAC Core Backend Management system. Sprint 1 has been completed, which added navigation buttons (TOPICS and BACKENDS) to the main screen and created a basic backends screen. Now you need to implement the actual backend configuration functionality.

## Your Mission
Implement Sprint 2: Backend Configuration & Entity Management according to the specification document `SPRINT_2_BACKEND_CONFIGURATION.md`. This involves creating the backend creation modal, connection testing, entity fetching from Home Assistant, and the entity configuration interface.

## Current State
- **Completed (Sprint 1)**:
  - ✅ Main screen has TOPICS and BACKENDS navigation buttons
  - ✅ Basic backends screen exists at `/backends`
  - ✅ Route configured in `api.py`
  - ✅ Cyberpunk UI theme established

- **Files to Review First**:
  1. `/SPRINT_2_BACKEND_CONFIGURATION.md` - Your implementation guide
  2. `/orac/templates/backends.html` - Current backends screen to enhance
  3. `/orac/api.py` - Where to add new API endpoints
  4. `/orac/topic_manager.py` - Reference for file-based storage pattern
  5. `/orac/homeassistant/client.py` - Existing HA client to use

## Sprint 2 Implementation Tasks

### Task 1: Backend Creation Modal
1. Update `/orac/templates/backends.html` to include a modal for "Add New Backend"
2. Create form with fields: Backend Name, Type (dropdown), URL, Port, API Token
3. Implement modal show/hide JavaScript functionality
4. Style with cyberpunk green-on-black theme

### Task 2: Backend API Endpoints
Create new file `/orac/backend_manager.py` with:
- `BackendManager` class similar to `TopicManager`
- File-based storage in `/data/backends/` directory
- Methods: create_backend, get_backend, list_backends, update_backend, delete_backend

Add to `/orac/api.py`:
```python
POST   /api/backends              - Create backend
GET    /api/backends              - List backends
GET    /api/backends/{id}         - Get backend
PUT    /api/backends/{id}         - Update backend
DELETE /api/backends/{id}         - Delete backend
POST   /api/backends/{id}/test    - Test connection
```

### Task 3: Connection Testing
1. Implement `test_connection` method in `BackendManager`
2. Use existing `HomeAssistantClient` from `/orac/homeassistant/client.py`
3. Return detailed error messages if connection fails
4. Update UI to show test results (success/failure with details)

### Task 4: Entity Configuration Screen
Create new template `/orac/templates/backend_entities.html`:
1. Card-based layout for entities
2. Click card to enable/disable (checkbox toggle)
3. Gear icon for configuration modal
4. Search and filter functionality
5. Bulk select/deselect options

### Task 5: Entity Management API
Add entity endpoints to `/orac/api.py`:
```python
POST /api/backends/{id}/entities/fetch    - Fetch from HA
GET  /api/backends/{id}/entities          - List configured
PUT  /api/backends/{id}/entities/{eid}    - Update entity
POST /api/backends/{id}/entities/bulk     - Bulk operations
```

### Task 6: Entity Configuration Modal
1. Create modal for individual entity configuration
2. Fields: Friendly Name, Aliases (multiple), Enabled checkbox, Priority
3. Save entity configuration back to backend JSON file

### Task 7: Data Persistence
Structure: `/data/backends/{backend_id}.json`
```json
{
  "id": "ha_main",
  "name": "Home Assistant Main",
  "type": "homeassistant",
  "connection": {...},
  "entities": {...},
  "statistics": {...}
}
```

## Implementation Order
1. **Start with Backend Manager** - Create the backend management class and file storage
2. **Add API Endpoints** - Implement CRUD operations for backends
3. **Build Modal UI** - Create the "Add New Backend" modal
4. **Test Connection** - Implement and test HA connection
5. **Entity Fetch** - Pull entities from HA and display
6. **Entity Configuration** - Enable/disable and configure entities
7. **Polish & Test** - Ensure all features work together

## Testing Checklist
- [ ] Can create a new Home Assistant backend
- [ ] Connection test provides clear success/failure feedback
- [ ] All HA entities are fetched and displayed as cards
- [ ] Clicking entity cards toggles enable/disable
- [ ] Gear icon opens configuration modal
- [ ] Friendly names and aliases can be set and saved
- [ ] Backend configuration persists to JSON file
- [ ] Entity configurations are saved with the backend
- [ ] Search and filter work correctly
- [ ] Bulk select/deselect all functions work
- [ ] UI maintains cyberpunk aesthetic throughout

## Deployment Instructions
After implementation, deploy using:
```bash
cd "/Users/2oby/pCloud Box/Projects/ORAC/Orac-Omniscient-Reactive-Algorithmic-Core"
./scripts/deploy_and_test.sh "Sprint 2: Backend configuration and entity management" master orac light
```

## Important Notes
1. **Use Existing HA Client**: Don't create new HA connection code, use `/orac/homeassistant/client.py`
2. **Follow Topics Pattern**: Mirror the file storage pattern from `topic_manager.py`
3. **Maintain UI Consistency**: Keep the cyberpunk green (#00ff41) on black theme
4. **Entity Cards**: Each entity should be a clickable card with clear enabled/disabled state
5. **Error Handling**: Provide clear, actionable error messages for connection issues
6. **Performance**: Consider pagination for large numbers of entities (100+)

## Visual Reference
The backends screen currently shows example cards. These should become real, data-driven cards that:
- Show actual backend connection status
- Display real entity counts
- Update when entities are configured
- Show last sync time

## Files You'll Create
- `/orac/backend_manager.py` - Backend management class
- `/orac/templates/backend_entities.html` - Entity configuration screen
- `/orac/static/js/backends.js` - Enhanced JavaScript for backends
- `/data/backends/` - Directory for backend JSON files

## Files You'll Modify
- `/orac/templates/backends.html` - Add modal and enhance cards
- `/orac/api.py` - Add all backend and entity endpoints
- `/orac/static/css/style.css` - Add any needed styles (maintain theme)

## Success Criteria
Sprint 2 is complete when:
1. ✅ User can add a new Home Assistant backend
2. ✅ Connection testing works with clear feedback
3. ✅ All entities are fetched and displayed as cards
4. ✅ Entities can be enabled/disabled with a click
5. ✅ Entity friendly names can be configured
6. ✅ All configurations persist to JSON files
7. ✅ The UI maintains the cyberpunk aesthetic
8. ✅ All tests pass on deployment to Jetson Orin

## Questions to Consider
- How many entities should load at once? (Consider pagination)
- Should disabled entities be hidden or just grayed out?
- What happens if HA connection is lost during entity fetch?
- Should there be a "refresh entities" button?
- How to handle entities that disappear from HA?

Good luck with the implementation! Remember to maintain the cyberpunk aesthetic and follow the patterns established in Sprint 1 and the existing ORAC codebase.