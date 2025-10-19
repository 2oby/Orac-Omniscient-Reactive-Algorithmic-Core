# Sprint 2: Implementation Update - Device Type + Location Mapping System

## Context
You are updating the existing Sprint 2 implementation to use a new design paradigm focused on Location, Device, and Action. The system needs to be refactored from the previous entity-centric approach to a device-mapping approach with drag-and-drop configuration.

## Current State
- Backend management system is complete with CRUD operations
- Entity fetching from Home Assistant works
- Basic entity configuration exists with friendly names and aliases
- UI uses cyberpunk theme with card-based entity display

## New Design Requirements

### Core Concepts
1. **Device Types**: Categories that define what commands a device can accept (Lights, Heating, Media Player, Blinds, etc.)
2. **Locations**: Physical locations from HA areas plus user-defined custom locations (Lounge, Bedroom, Kitchen, etc.)
3. **Device Mappings**: Each enabled device must have exactly ONE Device Type and ONE Location assigned
4. **Uniqueness Rule**: No two devices can have the same Device Type + Location combination
5. **Actions**: Implicit based on Device Type (determined by grammar generation in Sprint 3)

### Implementation Tasks

## Task 1: Update Backend Data Model
**File**: `/orac/backend_manager.py`

Update the backend storage structure to support the new mapping system:
- Replace `entities` field with `device_mappings`
- Add `device_types` list to store available types
- Add `locations` list to store available locations
- Each device mapping should include: `enabled`, `device_type`, `location`, `original_area`

```python
# Example structure
{
    "device_mappings": {
        "switch.lounge_lamp": {
            "enabled": true,
            "device_type": "lights",
            "location": "lounge",
            "original_area": "living_room"  # From HA
        }
    },
    "device_types": ["lights", "heating", "media_player", "blinds"],
    "locations": ["lounge", "bedroom", "kitchen"]
}
```

## Task 2: Create Device Configuration UI
**File**: `/orac/templates/backend_entities.html`

Replace the current card-based entity display with a new drag-and-drop interface:

### Layout Requirements
1. **Left Panel**: Device Types
   - Display as draggable tiles/cards
   - Include default types: Lights, Heating, Media Player, Blinds
   - Add button to create custom Device Types
   - Make tiles draggable

2. **Right Panel**: Locations
   - Display as draggable tiles/cards
   - Pull initial locations from HA areas
   - Add button to create custom Locations
   - Allow editing of location names
   - Make tiles draggable

3. **Center Panel**: Devices List
   - Show all devices from HA
   - Each device row has:
     - Checkbox to enable/disable
     - Device entity ID
     - Drop zone for Device Type (shows current assignment)
     - Drop zone for Location (shows current assignment)
   - Visual feedback during drag operations
   - Highlight conflicts in real-time

### Interaction Requirements
- Drag Device Type tile and drop on device's Type slot
- Drag Location tile and drop on device's Location slot
- Show warning immediately if Type + Location combination already exists
- Only enabled devices require Type and Location assignment
- Prevent saving if there are conflicts

## Task 3: Add Validation System
**File**: `/orac/backend_manager.py`

Add validation methods:
```python
def validate_device_mappings(self, backend_id: str) -> List[str]:
    """Check for duplicate Type + Location combinations"""
    # Return list of conflicts

def get_device_by_mapping(self, backend_id: str, device_type: str, location: str) -> Optional[str]:
    """Find device with specific Type + Location combination"""
    # Return device entity_id or None
```

## Task 4: Update API Endpoints
**File**: `/orac/api.py`

Modify existing endpoints:
- `PUT /api/backends/{id}/entities/{entity_id}` → Update to handle device_type and location
- Add `POST /api/backends/{id}/device-types` - Add custom device type
- Add `POST /api/backends/{id}/locations` - Add custom location
- Add `POST /api/backends/{id}/validate-mappings` - Check for conflicts
- Add `GET /api/backends/{id}/mappings` - Get all device mappings with validation status

## Task 5: Implement Drag-and-Drop JavaScript
**File**: `/orac/static/js/backend_entities.js` (create if doesn't exist)

Implement drag-and-drop functionality:
```javascript
// Make Device Types and Locations draggable
// Handle drop events on device slots
// Real-time conflict detection
// Visual feedback during drag
// Update backend via API on drop
// Show success/error feedback
```

## Task 6: Update Entity Fetch Logic
**File**: `/orac/backend_manager.py`

When fetching entities from HA:
- Extract areas as initial Locations
- Preserve existing device mappings
- Suggest initial Device Types based on entity domains:
  - `light.*` → "lights"
  - `switch.*` → could be "lights" or other
  - `climate.*` → "heating"
  - `media_player.*` → "media_player"
  - `cover.*` → "blinds"
- Store original HA area for reference

## Visual Design Requirements
Maintain the existing cyberpunk theme:
- Use the same color scheme (electric cyan #0ff9ff, neon pink #ff00ff, etc.)
- Card-based design for Device Types and Locations
- Smooth animations for drag operations
- Clear visual feedback for conflicts (red highlights, warning icons)
- Success states with green accents

## Success Criteria
1. User can drag and drop Device Types onto devices
2. User can drag and drop Locations onto devices
3. System prevents duplicate Type + Location combinations
4. User can add custom Device Types and Locations
5. Mappings persist to backend JSON file
6. Original HA areas are preserved for reference
7. Clear visual feedback for all operations
8. Validation happens in real-time

## Testing Checklist
- [ ] Drag Device Type to device slot
- [ ] Drag Location to device slot
- [ ] Try to create duplicate Type + Location (should show warning)
- [ ] Add custom Device Type
- [ ] Add custom Location
- [ ] Enable/disable devices
- [ ] Save mappings and reload page (should persist)
- [ ] Fetch new entities from HA (should preserve existing mappings)
- [ ] Clear all mappings
- [ ] Bulk assign Location to multiple devices

## Migration Notes
- Existing entity configurations need to be migrated to new format
- Preserve any existing friendly names as part of future grammar generation
- Keep backward compatibility until Sprint 3 is complete

## Important Considerations
1. **Performance**: Handle 200+ devices efficiently
2. **Usability**: Make drag-and-drop intuitive with clear visual cues
3. **Validation**: Real-time feedback prevents user frustration
4. **Flexibility**: Users can create custom Types and Locations as needed
5. **Data Integrity**: Never allow duplicate Type + Location combinations

## Next Steps (Sprint 3 Preview)
Once this implementation is complete, Sprint 3 will:
- Generate GBNF grammars from these mappings
- Create commands like "turn on lights in lounge"
- Ensure unambiguous command execution
- Test grammar with mapped devices

## File Structure Summary
```
/orac/
  backend_manager.py          # Update data model and validation
  api.py                      # Update/add endpoints
  templates/
    backend_entities.html     # New drag-and-drop UI
  static/
    js/
      backend_entities.js     # Drag-and-drop logic (create)
    css/
      backend_entities.css    # Styles for new UI (if needed)
```

## Development Approach
1. Start with data model updates
2. Create basic UI layout
3. Implement drag-and-drop
4. Add validation logic
5. Test with real HA instance
6. Polish UI/UX
7. Document changes

Remember: The goal is to make device configuration intuitive while ensuring the system can generate unambiguous grammars for voice commands. Each device should have a clear identity (Type + Location) that users can reference naturally in speech.