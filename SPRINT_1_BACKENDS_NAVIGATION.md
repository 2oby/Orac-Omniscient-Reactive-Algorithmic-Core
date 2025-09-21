# Sprint 1: ORAC Core Backend Navigation Implementation

## Overview
This sprint focuses on implementing the navigation infrastructure between the main ORAC Core screen, Topics screen, and the new Backends screen. The goal is to create a seamless user experience for managing both topics and backends within the ORAC ecosystem.

## Current State Analysis

### Existing Architecture
- **Main Screen**: `/Users/2oby/pCloud Box/Projects/ORAC/Orac-Omniscient-Reactive-Algorithmic-Core/orac/templates/index.html`
- **Topics Screen**: `/Users/2oby/pCloud Box/Projects/ORAC/Orac-Omniscient-Reactive-Algorithmic-Core/orac/templates/topics.html`
- **Styling**: Cyberpunk green-on-black terminal aesthetic with consistent box borders and glowing effects
- **Layout**: Clean grid-based layout with clear navigation patterns

### Current Main Screen Features
- ORAC Core banner/logo
- Last command display with clickable details modal
- Active topics section with dynamic loading
- Settings gear icon navigation to topics
- Status footer with service health indicators
- Real-time health checks for ORAC STT, Hey ORAC, and Home Assistant

## Sprint 1 Goals

### Primary Objectives
1. **Navigation Enhancement**: Add TOPICS and BACKENDS buttons to the main screen header area
2. **Backends Screen Creation**: Develop a new backends management screen
3. **Consistent UI/UX**: Maintain the existing cyberpunk aesthetic and interaction patterns
4. **Backend Management Foundation**: Create the interface framework for backend CRUD operations

### User Stories
1. **As a user**, I want to see TOPICS and BACKENDS buttons on the main screen so I can easily navigate between different management areas
2. **As a user**, I want to click on BACKENDS to access backend management functionality
3. **As a user**, I want to click on TOPICS to access the existing topics management screen
4. **As a user**, I want the navigation to be consistent with the existing ORAC design language

## Implementation Plan

### Task 1: Main Screen Navigation Enhancement
**Location**: `index.html`
**Goal**: Add TOPICS and BACKENDS navigation buttons in the top-right area

**Implementation Details**:
- Position buttons in the top-right corner similar to the settings gear icon
- Use consistent styling with existing topic badges
- Maintain responsive design principles
- Add hover effects and transitions

**Button Specifications**:
- **TOPICS Button**: Links to `/topics` (existing functionality)
- **BACKENDS Button**: Links to `/backends` (new functionality)
- Style: Green border, black background, glowing effects
- Size: Consistent with existing UI elements
- Animation: Pulse glow effect similar to topic badges

### Task 2: Backends Screen Development
**Location**: New file `/backends.html`
**Goal**: Create a comprehensive backend management interface

**Screen Components**:
1. **Header Section**: ORAC Core branding with navigation back to main
2. **Backend List**: Display configured backends with status indicators
3. **Add Backend Button**: Primary action for creating new backends
4. **Backend Cards**: Individual backend displays with:
   - Backend name and type
   - Connection status indicator
   - Entity count
   - Quick actions (Edit, Test, Delete)
5. **Footer**: Consistent status footer with service health

**Backend Card Layout**:
```
┌─ BACKEND NAME ──────────────────────────────────────┐
│ Type: Home Assistant                                │
│ URL: http://192.168.8.99:8123              ● ONLINE│
│ Entities: 24 configured, 12 active                 │
│                                                     │
│ [TEST] [EDIT] [ENTITIES] [DELETE]                   │
└─────────────────────────────────────────────────────┘
```

### Task 3: Backend Management Functionality
**Goal**: Implement core backend operations

**Features**:
1. **Create Backend**: Modal form for adding new backends
2. **Test Connection**: Validate backend connectivity
3. **List Backends**: Display all configured backends
4. **Edit Backend**: Modify backend configuration
5. **Delete Backend**: Remove backend with confirmation

**Backend Types (Initial)**:
- Home Assistant (primary focus)
- Extensible architecture for future backend types

### Task 4: API Endpoint Creation
**Goal**: Develop backend management API endpoints

**Required Endpoints**:
- `GET /api/backends` - List all backends
- `POST /api/backends` - Create new backend
- `GET /api/backends/{id}` - Get backend details
- `PUT /api/backends/{id}` - Update backend
- `DELETE /api/backends/{id}` - Delete backend
- `POST /api/backends/{id}/test` - Test backend connection

## Technical Specifications

### File Structure
```
/orac/
├── templates/
│   ├── index.html          # Enhanced with navigation buttons
│   ├── topics.html         # Existing topics screen
│   └── backends.html       # NEW: Backend management screen
├── static/
│   ├── css/style.css       # Updated with backend styles
│   └── js/
│       ├── main.js         # Updated with navigation
│       └── backends.js     # NEW: Backend management logic
└── api/
    └── backends.py         # NEW: Backend API endpoints
```

### Styling Consistency
**Color Palette**:
- Background: `#000000` (Pure Black)
- Primary: `#00ff41` (Matrix Green)
- Secondary: `#00AA2E` (Dim Green)
- Accent: `#00FFFF` (Cyan)
- Warning: `#ffa500` (Orange)
- Error: `#ff0000` (Red)

**UI Components**:
- Bordered boxes with `border: 3px solid #00ff41`
- Rounded corners with `border-radius: 12px`
- Glow effects with `box-shadow: 0 0 20px rgba(0, 255, 65, 0.5)`
- Pulse animations for active elements
- Monospace font: `'Courier New', monospace`

### Navigation Flow
```
Main Screen
├── TOPICS Button → Topics Screen
│   └── Back to Main
└── BACKENDS Button → Backends Screen
    ├── Add Backend → Backend Creation Modal
    ├── Edit Backend → Backend Edit Modal
    └── Back to Main
```

## Success Criteria

### Definition of Done
1. ✅ TOPICS and BACKENDS buttons visible on main screen
2. ✅ Clicking TOPICS navigates to existing topics screen
3. ✅ Clicking BACKENDS navigates to new backends screen
4. ✅ Backends screen displays placeholder content with proper styling
5. ✅ Navigation maintains consistent cyberpunk aesthetic
6. ✅ All screens are responsive and maintain existing functionality
7. ✅ Backend screen includes framework for future functionality

### Testing Checklist
- [ ] Main screen loads with new navigation buttons
- [ ] TOPICS button navigates correctly
- [ ] BACKENDS button navigates to new screen
- [ ] Backend screen maintains design consistency
- [ ] Responsive design works on different screen sizes
- [ ] Existing functionality remains intact
- [ ] Status footer displays correctly on all screens

## Future Sprint Considerations

### Sprint 2: Backend Core Functionality
- Backend creation and configuration forms
- Home Assistant integration
- Connection testing and validation
- Entity discovery and import

### Sprint 3: Advanced Backend Features
- Backend templates and presets
- Bulk operations
- Advanced filtering and search
- Integration with existing topic system

## Development Notes

### Architecture Decisions
1. **Modular Design**: Keep backend functionality separate from existing topic management
2. **API-First Approach**: Design REST endpoints before implementing UI
3. **Progressive Enhancement**: Build foundation first, add features incrementally
4. **Consistent Patterns**: Follow existing ORAC design and interaction patterns

### Risk Mitigation
- **Backward Compatibility**: Ensure existing topic functionality remains unchanged
- **Error Handling**: Implement proper error states and user feedback
- **Performance**: Optimize for real-time status updates without blocking UI
- **Extensibility**: Design backend system to support multiple backend types

This sprint establishes the foundation for the backend-first architecture described in the main implementation document while maintaining the existing ORAC Core functionality and aesthetic.