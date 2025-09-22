# Sprint 3 Implementation Prompt for Next Session

## IMPORTANT: Start with Sprint 2 Testing
Before implementing Sprint 3, you MUST first test the Sprint 2 implementation that's already deployed. Follow the `SPRINT_2_TEST.md` guide to:
1. Create a Home Assistant backend
2. Test the connection
3. Fetch entities from Home Assistant
4. Configure entities with friendly names and aliases
5. Verify data persistence

Only proceed with Sprint 3 after confirming Sprint 2 works correctly.

## Context for Next Session
You are implementing Sprint 3 of the ORAC Core system. Sprints 1 and 2 are complete and deployed. The backend management system is live at http://192.168.8.192:8000/backends and users can create Home Assistant backends, fetch entities, and configure them with friendly names and aliases.

## Your Mission
After testing Sprint 2, implement Sprint 3: Grammar Generation & Dispatcher Integration according to the specification document `SPRINT_3_GRAMMAR_DISPATCHER_INTEGRATION.md`. The primary goal is to generate GBNF grammars from configured Home Assistant entities and enable voice command testing.

## Current System State
- **Completed**:
  - ✅ Backend management with full CRUD operations
  - ✅ Entity fetching and configuration from Home Assistant
  - ✅ Entity enable/disable with friendly names and aliases
  - ✅ Deployed to Jetson Orin at 192.168.8.192

- **Existing Infrastructure**:
  - `HomeAssistantGrammarManager` in `/orac/homeassistant/grammar_manager.py`
  - Dispatcher registry system in `/orac/dispatchers/`
  - Backend data stored in `/data/backends/{backend_id}.json`
  - Topic management system operational

## Sprint 3 Primary Goal: Display Home Assistant Tiles

By the end of Sprint 3, you should see Home Assistant entity tiles displayed in the UI showing:
- Entity state (on/off, temperature, etc.)
- Interactive controls (toggle switches, sliders)
- Real-time updates from Home Assistant
- Grouped by room/area
- Visual feedback for entity status

## Key Implementation Tasks

### Priority 1: Entity Tiles Display
1. Create a new route `/backends/{id}/dashboard` for entity tiles view
2. Implement real-time entity state fetching
3. Create tile components for different entity types:
   - Light tiles (on/off, brightness, color)
   - Switch tiles (on/off toggle)
   - Climate tiles (temperature, mode)
   - Sensor tiles (display only)
   - Scene tiles (activate button)

### Priority 2: Grammar Generation
1. Create `BackendGrammarGenerator` class in `/orac/backend_grammar_generator.py`
2. Generate GBNF grammar from enabled entities
3. Include friendly names and aliases in grammar
4. Store generated grammar in `/data/grammars/`

### Priority 3: Testing Interface
1. Create grammar test console
2. Validate commands against generated grammar
3. Show parsed command structure
4. Display which entity would be controlled

## SSH Access to Jetson Orin

### Connection Method
```bash
ssh orin4
```

This is an SSH alias configured on your Mac that connects to:
- **Host**: Jetson Orin Nano
- **IP**: 192.168.8.192
- **User**: toby
- **Location**: Your local network

### What This Does
The `ssh orin4` command gives you direct terminal access to the Jetson Orin where ORAC is running in Docker containers. From there you can:
- View logs: `docker logs orac`
- Access container: `docker exec -it orac bash`
- Check status: `docker ps`
- Restart services: `docker-compose restart`

## Deployment Process

### The Deploy Script
```bash
cd "/Users/2oby/pCloud Box/Projects/ORAC/Orac-Omniscient-Reactive-Algorithmic-Core"
./scripts/deploy_and_test.sh "Sprint 3: Grammar generation" master orac light
```

### What deploy_and_test.sh Does

1. **Local Git Operations**:
   - Commits all changes with your message
   - Pushes to GitHub repository

2. **Remote Operations via SSH**:
   - Connects to `orin4` (Jetson Orin)
   - Pulls latest code from GitHub
   - Checks system resources (disk, memory, GPU)
   - Rebuilds Docker container if needed
   - Runs automated tests
   - Restarts ORAC service

3. **Parameters**:
   - `"Sprint 3: Grammar generation"` - Git commit message
   - `master` - Git branch to deploy
   - `orac` - Docker service name
   - `light` - Cleanup level (light/normal/aggressive)

### Cleanup Levels
- **light**: Minimal cleanup, preserves images and caches
- **normal**: Removes stopped containers and unused images
- **aggressive**: Full cleanup including build cache

## Entity Tiles Implementation Guide

### Tile Template Structure
```html
<!-- /orac/templates/backend_dashboard.html -->
<div class="entity-grid">
  <!-- Light Tile -->
  <div class="tile light-tile" data-entity-id="light.living_room">
    <div class="tile-icon">💡</div>
    <div class="tile-name">Living Room Light</div>
    <div class="tile-state">On - 75%</div>
    <div class="tile-controls">
      <button class="toggle-btn" onclick="toggleEntity('light.living_room')">
        <span class="toggle-switch on"></span>
      </button>
      <input type="range" class="brightness-slider" min="0" max="100" value="75">
    </div>
  </div>

  <!-- Climate Tile -->
  <div class="tile climate-tile" data-entity-id="climate.bedroom">
    <div class="tile-icon">🌡️</div>
    <div class="tile-name">Bedroom AC</div>
    <div class="tile-state">22°C - Cooling</div>
    <div class="tile-controls">
      <button class="temp-down">-</button>
      <span class="temp-display">22°C</span>
      <button class="temp-up">+</button>
    </div>
  </div>

  <!-- Switch Tile -->
  <div class="tile switch-tile" data-entity-id="switch.garage">
    <div class="tile-icon">🔌</div>
    <div class="tile-name">Garage Door</div>
    <div class="tile-state">Closed</div>
    <div class="tile-controls">
      <button class="action-btn">Open</button>
    </div>
  </div>
</div>
```

### API Endpoints Needed
```python
# Get current entity states
GET /api/backends/{id}/entities/states

# Control entity
POST /api/backends/{id}/entities/{entity_id}/control
Body: {
  "service": "turn_on",
  "data": {"brightness": 128}
}

# Get entity history
GET /api/backends/{id}/entities/{entity_id}/history

# Subscribe to state changes (WebSocket)
WS /api/backends/{id}/entities/stream
```

### Real-time Updates
```javascript
// WebSocket connection for real-time updates
const ws = new WebSocket(`ws://192.168.8.192:8000/api/backends/${backendId}/entities/stream`);

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  updateTile(update.entity_id, update.state);
};

// Fallback polling for non-WebSocket
setInterval(async () => {
  const states = await fetch(`/api/backends/${backendId}/entities/states`);
  updateAllTiles(await states.json());
}, 5000);
```

## Files to Review First

### Sprint 2 Testing
1. **SPRINT_2_TEST.md** - Complete testing guide for Sprint 2
2. **SPRINT_2_TEST.md#troubleshooting** - If anything doesn't work

### Sprint 3 Implementation
1. **Sprint 3 Specification**: `/SPRINT_3_GRAMMAR_DISPATCHER_INTEGRATION.md`
2. **Backend Manager**: `/orac/backend_manager.py` - Understand entity storage
3. **Grammar Manager**: `/orac/homeassistant/grammar_manager.py` - Existing grammar generation
4. **Backend Entities Page**: `/orac/templates/backend_entities.html` - Current entity UI
5. **Home Assistant Client**: `/orac/homeassistant/client.py` - HA API integration

## Implementation Order

### Day 0: Sprint 2 Testing (MUST DO FIRST)
1. Follow `SPRINT_2_TEST.md` completely
2. Create and configure a Home Assistant backend
3. Fetch and configure entities
4. Document any issues found
5. Fix any bugs before proceeding

### Day 1-2: Entity Tiles Dashboard
1. Create `/backends/{id}/dashboard` route
2. Build tile template with cyberpunk styling
3. Implement state fetching from HA
4. Add basic toggle controls

### Day 3-4: Interactive Controls
1. Implement entity control endpoints
2. Add brightness sliders for lights
3. Add temperature controls for climate
4. Add scene activation buttons

### Day 5-6: Grammar Generation
1. Create BackendGrammarGenerator
2. Generate GBNF from enabled entities
3. Store grammar files
4. Add generation status to UI

### Day 7-8: Testing & Polish
1. Create grammar test console
2. Add real-time updates (polling or WebSocket)
3. Group tiles by room
4. Test with actual Home Assistant

## Success Criteria

By the end of Sprint 3, you should be able to:
1. ✅ View all Home Assistant entities as interactive tiles
2. ✅ Control entities directly from tiles (on/off, brightness, temperature)
3. ✅ See real-time state updates
4. ✅ Generate GBNF grammar from configured entities
5. ✅ Test voice commands against generated grammar
6. ✅ Group entities by room/area
7. ✅ Maintain cyberpunk aesthetic

## Testing Checklist

### Sprint 2 Testing (Complete First)
- [ ] Created Home Assistant backend successfully
- [ ] Connection test shows entity count
- [ ] Fetched all entities from Home Assistant
- [ ] Can enable/disable entities
- [ ] Can configure friendly names and aliases
- [ ] Configurations persist after refresh
- [ ] Backend shows as connected

### Sprint 3 Manual Testing
- [ ] Navigate to `/backends/{id}/dashboard`
- [ ] See entity tiles with current states
- [ ] Toggle a light on/off
- [ ] Adjust brightness slider
- [ ] Change climate temperature
- [ ] Activate a scene
- [ ] Verify state updates in real-time
- [ ] Generate grammar from entities
- [ ] Test a voice command in console

### Automated Testing
```bash
# After implementation, run tests on Jetson
ssh orin4
docker exec -it orac pytest tests/test_tiles.py
docker exec -it orac pytest tests/test_grammar_generation.py
```

## Deployment Command

When ready to deploy:
```bash
cd "/Users/2oby/pCloud Box/Projects/ORAC/Orac-Omniscient-Reactive-Algorithmic-Core"
./scripts/deploy_and_test.sh "Sprint 3: Entity tiles and grammar generation" master orac light
```

## Visual Goal

By sprint end, the dashboard should look like:
```
╔════════════════════════════════════════════════════════════════════════╗
║ HOME ASSISTANT DASHBOARD - Living Space                                 ║
╠════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  Living Room                  Kitchen                 Bedroom           ║
║  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 ║
║  │ 💡 Main Light│  │ 💡 Counter   │  │ 🌡️ AC Unit  │                 ║
║  │    ON - 75%  │  │    OFF       │  │   22°C Cool  │                 ║
║  │ [=======|--] │  │ [●        ] │  │  [−][22][+]  │                 ║
║  └──────────────┘  └──────────────┘  └──────────────┘                 ║
║                                                                          ║
║  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 ║
║  │ 🔌 Fan       │  │ 🎬 Movie Time│  │ 💡 Bed Light │                 ║
║  │    ON        │  │    Scene     │  │   OFF        │                 ║
║  │ [●        ] │  │ [ACTIVATE]   │  │ [○        ] │                 ║
║  └──────────────┘  └──────────────┘  └──────────────┘                 ║
║                                                                          ║
║ Grammar: Generated 5 min ago | 45 entities | Test Commands            ║
╚════════════════════════════════════════════════════════════════════════╝
```

## Sprint 2 Prerequisites

### Home Assistant Access Requirements
1. **URL**: Your HA instance at `http://192.168.8.99:8123`
2. **Token**: Get from HA Profile → Long-Lived Access Tokens → Create Token
3. **Access**: Ensure Jetson can reach HA (same network)

### Quick Sprint 2 Test Commands
```bash
# Check if Sprint 2 is deployed
curl http://192.168.8.192:8000/api/backends

# SSH to Orin to check logs if needed
ssh orin4
docker logs orac --tail 50

# Check backend data files
docker exec -it orac ls -la /app/data/backends/
```

## Important Notes

1. **WebSocket vs Polling**: Start with polling for simplicity, add WebSocket if time permits
2. **Entity Types**: Focus on lights, switches, climate, and scenes first
3. **Grammar Complexity**: Start simple (on/off commands), add complexity gradually
4. **Performance**: Cache entity states, update only changed tiles
5. **Error Handling**: Show connection errors clearly, provide retry options

## Questions to Answer During Implementation

1. How many entities should load at once in tile view?
2. Should tiles auto-refresh or require manual refresh?
3. How to handle entities that go offline?
4. Should grammar regenerate automatically on entity changes?
5. What's the optimal tile size for different screen sizes?

---

Good luck with Sprint 3! The main goal is to create a visual, interactive dashboard showing Home Assistant entities as tiles that can be controlled directly from the ORAC interface.