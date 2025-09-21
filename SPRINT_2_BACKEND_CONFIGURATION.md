# Sprint 2: Backend Configuration & Entity Management

## Overview
Sprint 2 implements the core backend configuration functionality, allowing users to add new backends (initially Home Assistant), test connections, and manage entities through an interactive card-based interface. This sprint focuses on the first step of the wizard: importing, enabling/disabling, and configuring entities from external systems.

## Sprint Goals

### Primary Objectives
1. **Backend Creation Modal**: Implement "Add New Backend" functionality with configuration form
2. **Connection Testing**: Full implementation of backend connection validation
3. **Entity Discovery & Import**: Fetch all entities from Home Assistant
4. **Entity Management Interface**: Card-based UI for enabling/disabling and configuring entities
5. **Backend Persistence**: File-based storage system similar to topics

### User Stories
1. **As a user**, I want to add a new Home Assistant backend by providing connection details
2. **As a user**, I want to test the connection before saving the backend configuration
3. **As a user**, I want to see all available entities from my Home Assistant as cards
4. **As a user**, I want to enable/disable entities with a single click
5. **As a user**, I want to configure friendly names for entities through a settings interface
6. **As a user**, I want my backend and entity configurations to persist between sessions

## Implementation Design

### 1. Add New Backend Modal

#### Modal Structure
```
╔════════════════════════════════════════════════════════════════╗
║                    ADD NEW BACKEND                              ║
╠════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  BACKEND NAME:     [________________________]                   ║
║                                                                  ║
║  BACKEND TYPE:     [▼ Home Assistant        ]                   ║
║                                                                  ║
║  CONNECTION DETAILS                                              ║
║  ─────────────────                                              ║
║                                                                  ║
║  URL/HOST:         [________________________]                   ║
║                    e.g., http://192.168.1.100                   ║
║                                                                  ║
║  PORT:             [________]                                    ║
║                    e.g., 8123                                    ║
║                                                                  ║
║  API TOKEN:        [________________________]                   ║
║                    Long-lived access token from HA              ║
║                                                                  ║
║  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐║
║  │ TEST CONNECTION │  │     CANCEL      │  │   SAVE & NEXT   │║
║  └─────────────────┘  └─────────────────┘  └─────────────────┘║
║                                                                  ║
╚════════════════════════════════════════════════════════════════╝
```

#### Field Specifications
- **Backend Name**: User-friendly identifier (e.g., "Home Assistant Main")
- **Backend Type**: Dropdown (initially only "Home Assistant" option)
- **URL/Host**: Full URL including protocol
- **Port**: Numeric port field
- **API Token**: Password field for security token
- **Additional Fields**: Dynamically added if connection fails (e.g., SSL verification, timeout)

#### Connection Test Flow
```
1. User clicks "TEST CONNECTION"
2. Show loading animation: "Testing connection..."
3. Results displayed:
   - Success: Green checkmark with "Connected successfully!"
   - Failure: Red X with error details and suggestion to add fields
4. If success, enable "SAVE & NEXT" button
5. If failure, show "Add Advanced Settings" option
```

### 2. Entity Configuration Screen

#### Screen Layout
```
╔════════════════════════════════════════════════════════════════╗
║  CONFIGURE ENTITIES: Home Assistant Main                        ║
║  ──────────────────────────────────────────                   ║
║                                                                  ║
║  [FETCH ENTITIES] [SELECT ALL] [CLEAR ALL] [SAVE CONFIG]        ║
║                                                                  ║
║  🔍 Search: [___________________]  Filter: [All Types ▼]        ║
║                                                                  ║
║  Discovered: 156 entities | Enabled: 0 | Configured: 0          ║
╠════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  ┌─────────────────────────────────────────────────────────┐   ║
║  │ ⚡ light.living_room_main                         ⚙️ ✓ │   ║
║  │ Type: Light | Area: Living Room                         │   ║
║  │ State: On | Brightness: 80%                             │   ║
║  │ Friendly Name: [Living Room Main Light___]              │   ║
║  └─────────────────────────────────────────────────────────┘   ║
║                                                                  ║
║  ┌─────────────────────────────────────────────────────────┐   ║
║  │ 🌡️ climate.bedroom_ac                             ⚙️ ☐ │   ║
║  │ Type: Climate | Area: Bedroom                           │   ║
║  │ State: Off | Temperature: 22°C                          │   ║
║  │ Friendly Name: [Not configured___________]              │   ║
║  └─────────────────────────────────────────────────────────┘   ║
║                                                                  ║
║  ┌─────────────────────────────────────────────────────────┐   ║
║  │ 🎬 scene.movie_time                                ⚙️ ✓ │   ║
║  │ Type: Scene | Entities: 12                              │   ║
║  │ Last Activated: 2 days ago                              │   ║
║  │ Friendly Name: [Movie Time Scene__________]              │   ║
║  └─────────────────────────────────────────────────────────┘   ║
║                                                                  ║
╚════════════════════════════════════════════════════════════════╝
```

#### Entity Card Features
- **Click Card Body**: Toggle enable/disable (checkbox ✓/☐)
- **Gear Icon (⚙️)**: Opens entity configuration modal
- **Visual State**:
  - Enabled: Bright green border glow
  - Disabled: Dim/grayed out
  - Configured: Shows friendly name
- **Icon by Type**: Different icons for lights, scenes, switches, climate, etc.
- **Real-time State**: Show current state from HA

#### Entity Configuration Modal (Gear Click)
```
╔════════════════════════════════════════════════════════════════╗
║  CONFIGURE ENTITY: light.living_room_main                       ║
╠════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  ENTITY ID:        light.living_room_main (read-only)           ║
║                                                                  ║
║  FRIENDLY NAME:    [Living Room Main Light___]                  ║
║                    Used for voice commands                      ║
║                                                                  ║
║  ALIASES:          [Living Room Light_________]                 ║
║                    [Main Light________________]                 ║
║                    [+ Add Alias]                                ║
║                                                                  ║
║  ENABLED:          [✓] Include in voice control                 ║
║                                                                  ║
║  ADVANCED:                                                      ║
║  Priority:         [5] (1-10, higher = preferred)               ║
║  Room Override:    [___________] (optional)                     ║
║                                                                  ║
║  [CANCEL]                                     [SAVE]             ║
║                                                                  ║
╚════════════════════════════════════════════════════════════════╝
```

### 3. Data Storage Structure

#### Backend Configuration File
**Location**: `/data/backends/{backend_id}.json`

```json
{
  "id": "ha_main",
  "name": "Home Assistant Main",
  "type": "homeassistant",
  "created_at": "2024-09-21T10:00:00Z",
  "updated_at": "2024-09-21T10:30:00Z",
  "connection": {
    "url": "http://192.168.8.99",
    "port": 8123,
    "token": "eyJ0eXAiOiJKV1QiLCJhbGci...",
    "ssl_verify": true,
    "timeout": 10
  },
  "status": {
    "connected": true,
    "last_check": "2024-09-21T10:30:00Z",
    "version": "2024.9.1",
    "error": null
  },
  "entities": {
    "light.living_room_main": {
      "enabled": true,
      "friendly_name": "Living Room Main Light",
      "aliases": ["Living Room Light", "Main Light"],
      "original_name": "Living Room Main",
      "domain": "light",
      "area": "Living Room",
      "priority": 5,
      "configured_at": "2024-09-21T10:25:00Z"
    },
    "climate.bedroom_ac": {
      "enabled": false,
      "friendly_name": null,
      "aliases": [],
      "original_name": "Bedroom AC",
      "domain": "climate",
      "area": "Bedroom",
      "priority": 5,
      "configured_at": null
    }
  },
  "statistics": {
    "total_entities": 156,
    "enabled_entities": 45,
    "configured_entities": 32,
    "last_sync": "2024-09-21T10:30:00Z"
  }
}
```

### 4. API Endpoints

#### Backend Management
- `POST /api/backends` - Create new backend
- `GET /api/backends/{id}` - Get backend details
- `PUT /api/backends/{id}` - Update backend configuration
- `DELETE /api/backends/{id}` - Delete backend
- `POST /api/backends/{id}/test` - Test backend connection
- `GET /api/backends` - List all backends

#### Entity Management
- `POST /api/backends/{id}/entities/fetch` - Fetch all entities from backend
- `GET /api/backends/{id}/entities` - List configured entities
- `PUT /api/backends/{id}/entities/{entity_id}` - Update entity configuration
- `POST /api/backends/{id}/entities/bulk` - Bulk enable/disable entities
- `GET /api/backends/{id}/entities/stats` - Get entity statistics

### 5. Implementation Flow

#### User Journey
1. **Click "Add New Backend"** → Modal opens
2. **Fill Configuration** → Enter HA details
3. **Test Connection** → Validate credentials and access
4. **Save & Next** → Backend saved, redirect to entity configuration
5. **Fetch Entities** → Load all entities from HA
6. **Configure Entities** → Enable/disable, set friendly names
7. **Save Configuration** → Store entity settings
8. **Ready for Grammar** → Exit point for Sprint 3

#### Error Handling
- **Connection Failed**: Show specific error (timeout, auth, network)
- **Invalid Token**: Prompt to check token and permissions
- **No Entities Found**: Show warning and troubleshooting steps
- **Partial Fetch**: Show what was retrieved, log errors
- **Save Failure**: Retry mechanism with user feedback

### 6. Visual Design Elements

#### Cyberpunk UI Components
- **Loading States**: Matrix-style cascading text
- **Success Feedback**: Green pulse animations
- **Error States**: Red glitch effects
- **Progress Bars**: Segmented neon bars
- **Tooltips**: Terminal-style help text
- **Transitions**: Smooth fade with subtle glow

#### Color Coding
- **Enabled Entities**: Bright green (#00ff41)
- **Disabled Entities**: Dim gray (#444444)
- **Configured**: Cyan accent (#00ffff)
- **Errors**: Red (#ff0040)
- **Warnings**: Orange (#ffa500)
- **Processing**: Pulsing yellow (#ffff00)

## Technical Considerations

### Performance
- **Pagination**: Load entities in batches of 50
- **Virtual Scrolling**: For large entity lists
- **Debounced Search**: 300ms delay on search input
- **Caching**: Store fetched entities for 5 minutes
- **Lazy Loading**: Load entity details on demand

### Security
- **Token Storage**: Encrypted in backend configuration
- **Connection Validation**: SSL certificate verification
- **Input Sanitization**: Prevent XSS in friendly names
- **Rate Limiting**: Prevent API abuse during testing

### Compatibility
- **Home Assistant Versions**: Support 2023.x and 2024.x
- **Browser Support**: Chrome, Firefox, Safari (latest 2 versions)
- **Responsive Design**: Tablet and desktop optimized
- **Accessibility**: Keyboard navigation support

## Testing Requirements

### Unit Tests
- Backend creation validation
- Entity configuration CRUD operations
- Connection testing logic
- File storage operations

### Integration Tests
- Full backend creation flow
- Entity fetch and configuration
- Error handling scenarios
- Data persistence

### Manual Testing
- Various HA configurations
- Large entity counts (500+)
- Network failure scenarios
- Token expiration handling

## Success Criteria

### Sprint Completion
✅ Backend creation modal fully functional
✅ Connection testing with proper error handling
✅ Entity fetching from Home Assistant
✅ Entity enable/disable functionality
✅ Entity configuration (friendly names, aliases)
✅ Data persistence in JSON files
✅ All API endpoints implemented and tested
✅ Cyberpunk UI consistently applied
✅ Error states properly handled
✅ Performance targets met (< 2s entity load)

### Metrics
- Backend creation success rate > 95%
- Entity fetch completion < 5 seconds for 200 entities
- Configuration save success rate = 100%
- UI responsiveness < 100ms for interactions

## Dependencies

### Technical Dependencies
- Home Assistant API access
- File system write permissions
- Async HTTP client for API calls

### Sprint 1 Deliverables
- Navigation buttons (completed)
- Backends screen framework (completed)
- Basic routing (completed)

## Out of Scope (Sprint 3)

The following items are explicitly NOT part of Sprint 2:
- Grammar generation from entities
- Dispatcher configuration
- Topic creation/association
- Voice command testing
- Entity grouping or categorization
- Automated entity discovery
- Multiple backend type support (only HA for now)

## Risk Mitigation

### Identified Risks
1. **Large Entity Count**: Implement pagination and virtual scrolling
2. **HA API Changes**: Version detection and compatibility layer
3. **Network Latency**: Timeout configuration and retry logic
4. **Token Expiration**: Clear error messages and re-authentication flow
5. **File System Issues**: Fallback to memory storage with warning

## Sprint Timeline

### Development Phases
1. **Days 1-2**: Backend creation modal and API
2. **Days 3-4**: Connection testing implementation
3. **Days 5-6**: Entity fetch and display
4. **Days 7-8**: Entity configuration UI
5. **Days 9-10**: Data persistence and testing
6. **Days 11-12**: Bug fixes and polish
7. **Days 13-14**: Integration testing and documentation

## Next Sprint Preview (Sprint 3)

Sprint 3 will build upon the configured entities to:
- Generate GBNF grammars from enabled entities
- Create entity-to-action mappings
- Configure dispatcher rules
- Test voice commands
- Associate backends with topics

The entity configuration from Sprint 2 becomes the input for the grammar generation wizard in Sprint 3.