# Sprint 2 Comprehensive Testing Guide
## Device Type + Location Mapping System

### Test Environment
- **ORAC Server**: http://192.168.8.192:8000 (Jetson Orin)
- **Home Assistant**: http://192.168.8.99:8123
- **Test Date**: 2025-09-23

## Prerequisites

### 1. Get Home Assistant Token
1. Open Home Assistant (http://192.168.8.99:8123)
2. Click your profile (bottom left)
3. Scroll to "Long-Lived Access Tokens"
4. Click "Create Token"
5. Name it "ORAC Sprint 2 Test"
6. Copy the token immediately

### 2. Verify ORAC is Running
```bash
ssh orin4 "docker ps | grep orac"
# Should show the container running on port 8000
```

## Automated Testing

### Option 1: Run Python Test Script
```bash
# Edit the script to add your HA token
nano SPRINT_2_TEST_SCRIPT.py
# Find the line: HA_TOKEN = ""
# Add your token: HA_TOKEN = "your-token-here"

# Run the tests
python3 SPRINT_2_TEST_SCRIPT.py
```

### Option 2: Manual API Testing
```bash
# Set your HA token
export HA_TOKEN="your-token-here"

# Test API availability
curl http://192.168.8.192:8000/api/backends

# Create a test backend
curl -X POST http://192.168.8.192:8000/api/backends \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test HA Backend",
    "type": "homeassistant",
    "connection": {
      "url": "http://192.168.8.99",
      "port": 8123,
      "token": "'$HA_TOKEN'"
    }
  }'
```

## Manual UI Testing

### Test 1: Access Backend Management UI
1. Open browser to: http://192.168.8.192:8000/backends
2. **Expected**: See ORAC Backends page with cyberpunk green theme
3. **Verify**:
   - ✅ Page loads without errors
   - ✅ "+ Add New Backend" card is visible
   - ✅ Any existing backends are displayed

### Test 2: Create Home Assistant Backend
1. Click "+ Add New Backend" card
2. Fill in the form:
   - **Backend Name**: `Home Assistant Main`
   - **Backend Type**: `Home Assistant` (default)
   - **URL/Host**: `http://192.168.8.99`
   - **Port**: `8123`
   - **API Token**: [Your HA token]
3. Click "Test Connection"
4. **Expected**: "✓ Connection successful! Found X entities"
5. Click "Save & Next"
6. **Verify**:
   - ✅ Connection test succeeds
   - ✅ Shows entity count
   - ✅ Redirects to entity configuration page

### Test 3: Entity Configuration Page
1. On the entity configuration page
2. **Verify Sprint 2 UI Elements**:
   - ✅ **Left Panel**: Device Types section
     - Should show: Lights, Heating, Media Player, Blinds, Switches
     - "+ Add Device Type" button
   - ✅ **Right Panel**: Locations section
     - Should show locations from HA areas (if any)
     - "+ Add Location" button
   - ✅ **Center Panel**: Device list
     - Shows all entities from HA
     - Each row has Type and Location drop zones

### Test 4: Fetch Entities from Home Assistant
1. Click "Fetch Entities" button
2. Wait for loading to complete
3. **Verify**:
   - ✅ Entities appear in the center panel
   - ✅ Each entity shows:
     - Entity ID
     - Checkbox for enable/disable
     - Device Type drop zone (empty initially)
     - Location drop zone (empty initially)
   - ✅ Locations panel populates with HA areas
   - ✅ Statistics update (total devices count)

### Test 5: Drag-and-Drop Device Type Assignment
1. Find a light entity in the center panel
2. Drag "Lights" tile from left panel
3. Drop on the entity's Device Type zone
4. **Verify**:
   - ✅ Visual feedback during drag
   - ✅ Device Type zone accepts the drop
   - ✅ Shows "Lights" in the type field
   - ✅ Data saves automatically

### Test 6: Drag-and-Drop Location Assignment
1. Use the same entity from Test 5
2. Drag a Location tile from right panel
3. Drop on the entity's Location zone
4. **Verify**:
   - ✅ Visual feedback during drag
   - ✅ Location zone accepts the drop
   - ✅ Shows location name in the field
   - ✅ Entity is now fully mapped

### Test 7: Duplicate Type + Location Validation
1. Find another entity
2. Try to assign the SAME Device Type + Location combination
3. **Verify**:
   - ✅ System shows warning/error
   - ✅ Prevents duplicate mapping
   - ✅ Clear error message explaining the conflict
   - ✅ Highlights conflicting device

### Test 8: Add Custom Device Type
1. Click "+ Add Device Type" in left panel
2. Enter name: `Security`
3. Click Save/Add
4. **Verify**:
   - ✅ New device type appears in left panel
   - ✅ Can be dragged to devices
   - ✅ Persists after page reload

### Test 9: Add Custom Location
1. Click "+ Add Location" in right panel
2. Enter name: `Office`
3. Click Save/Add
4. **Verify**:
   - ✅ New location appears in right panel
   - ✅ Can be dragged to devices
   - ✅ Persists after page reload

### Test 10: Enable/Disable Devices
1. Click checkbox on any device row
2. **Verify**:
   - ✅ Checkbox toggles state
   - ✅ Enabled devices show visual indicator
   - ✅ Only enabled devices require mapping
   - ✅ Statistics update (enabled count)

### Test 11: Bulk Operations
1. Test "Select All" button
2. Test "Clear All" button
3. **Verify**:
   - ✅ Select All enables all visible devices
   - ✅ Clear All disables all devices
   - ✅ Statistics update correctly

### Test 12: Data Persistence
1. Configure several device mappings
2. Navigate away (go back to /backends)
3. Return to entity configuration
4. **Verify**:
   - ✅ All mappings are preserved
   - ✅ Device Types assignments retained
   - ✅ Locations assignments retained
   - ✅ Enable/disable states preserved

### Test 13: Container Restart Persistence
```bash
# SSH to Orin and restart container
ssh orin4
docker restart orac

# Wait 30 seconds
sleep 30

# Return to UI and verify data persists
```

## Performance Testing

### Load Test with Many Devices
1. If HA has 100+ entities, fetch them all
2. **Measure**:
   - ⏱️ Fetch time: Should be < 5 seconds
   - ⏱️ UI responsiveness with 100+ devices
   - ⏱️ Drag-drop performance
   - ⏱️ Save/update speed

### Concurrent Operations
1. Open two browser tabs
2. Make changes in both
3. **Verify**:
   - ✅ Changes sync properly
   - ✅ No data corruption
   - ✅ Validation works across sessions

## API Endpoint Testing

### Test Backend CRUD Operations
```bash
# List all backends
curl http://192.168.8.192:8000/api/backends

# Get specific backend (use ID from create response)
curl http://192.168.8.192:8000/api/backends/{backend_id}

# Update backend
curl -X PUT http://192.168.8.192:8000/api/backends/{backend_id} \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Name"}'

# Delete backend
curl -X DELETE http://192.168.8.192:8000/api/backends/{backend_id}
```

### Test Entity Operations
```bash
# Fetch entities from HA
curl -X POST http://192.168.8.192:8000/api/backends/{backend_id}/entities/fetch

# Get all entities
curl http://192.168.8.192:8000/api/backends/{backend_id}/entities

# Update entity mapping
curl -X PUT http://192.168.8.192:8000/api/backends/{backend_id}/entities/{entity_id} \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "device_type": "lights",
    "location": "living_room"
  }'
```

### Test Sprint 2 Specific Endpoints
```bash
# Add custom device type
curl -X POST http://192.168.8.192:8000/api/backends/{backend_id}/device-types \
  -H "Content-Type: application/json" \
  -d '{"device_type": "sensors"}'

# Add custom location
curl -X POST http://192.168.8.192:8000/api/backends/{backend_id}/locations \
  -H "Content-Type: application/json" \
  -d '{"location": "garage"}'

# Validate mappings (check for duplicates)
curl -X POST http://192.168.8.192:8000/api/backends/{backend_id}/validate-mappings

# Get all mappings with validation status
curl http://192.168.8.192:8000/api/backends/{backend_id}/mappings
```

## Data Structure Verification

### Check Backend JSON Structure
```bash
ssh orin4
docker exec -it orac bash
cd /app/data/backends/
cat *.json | python -m json.tool
```

### Expected Sprint 2 Structure
```json
{
  "id": "homeassistant_xxxxx",
  "name": "Home Assistant Main",
  "type": "homeassistant",
  "connection": {...},
  "device_mappings": {
    "light.living_room": {
      "enabled": true,
      "device_type": "lights",
      "location": "living_room",
      "original_area": "Living Room"
    },
    "switch.bedroom_fan": {
      "enabled": true,
      "device_type": "switches",
      "location": "bedroom",
      "original_area": "Bedroom"
    }
  },
  "device_types": [
    "lights",
    "heating",
    "media_player",
    "blinds",
    "switches",
    "custom_type_1"
  ],
  "locations": [
    "living_room",
    "bedroom",
    "kitchen",
    "custom_location_1"
  ],
  "statistics": {
    "total_devices": 156,
    "enabled_devices": 45,
    "mapped_devices": 32,
    "last_sync": "2025-09-23T10:30:45Z"
  }
}
```

## Troubleshooting

### Container Not Running
```bash
ssh orin4
docker ps -a | grep orac
docker logs orac --tail 100
docker restart orac
```

### Connection Test Fails
1. Verify HA is accessible from Orin:
```bash
ssh orin4
curl http://192.168.8.99:8123/api/
```

2. Test with token:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://192.168.8.99:8123/api/states
```

### UI Not Loading Properly
1. Check browser console (F12) for JavaScript errors
2. Check network tab for failed API calls
3. Verify static files are being served:
```bash
curl http://192.168.8.192:8000/static/js/backend_entities.js
```

### Drag-and-Drop Not Working
1. Check if JavaScript is loaded:
   - Open browser console
   - Type: `typeof initDragAndDrop`
   - Should return "function"

2. Check for JavaScript errors during drag

### Data Not Persisting
```bash
ssh orin4
docker exec -it orac bash
ls -la /app/data/backends/
# Check file permissions
```

## Success Criteria Checklist

### Core Functionality
- [ ] Backend creation with HA connection works
- [ ] Entity fetching retrieves all HA devices
- [ ] Device Types panel shows default types
- [ ] Locations panel shows HA areas
- [ ] Drag-and-drop assignment works smoothly
- [ ] Duplicate validation prevents conflicts
- [ ] Custom types and locations can be added
- [ ] Enable/disable toggles work
- [ ] Data persists across page reloads
- [ ] Data persists across container restarts

### UI/UX
- [ ] Cyberpunk theme is consistent
- [ ] Visual feedback during drag operations
- [ ] Clear error messages for validation
- [ ] Responsive with 100+ devices
- [ ] Statistics update in real-time
- [ ] Loading indicators show progress

### API
- [ ] All CRUD operations work
- [ ] Validation endpoints return correct data
- [ ] Error handling returns appropriate codes
- [ ] Response times are acceptable

### Data Model
- [ ] Sprint 2 structure is implemented
- [ ] Device mappings store correctly
- [ ] Original HA areas are preserved
- [ ] Custom types/locations are saved

## Test Results Summary

| Test Category | Status | Notes |
|--------------|---------|-------|
| Backend Creation | ⬜ | |
| HA Connection | ⬜ | |
| Entity Fetching | ⬜ | |
| Device Type Assignment | ⬜ | |
| Location Assignment | ⬜ | |
| Duplicate Validation | ⬜ | |
| Custom Types | ⬜ | |
| Custom Locations | ⬜ | |
| Data Persistence | ⬜ | |
| UI Responsiveness | ⬜ | |
| API Performance | ⬜ | |

## Next Steps

After successful Sprint 2 testing:

1. **Document any issues** found during testing
2. **Note performance metrics** for future comparison
3. **Export test backend** for Sprint 3 grammar testing
4. **Prepare device mappings** for grammar generation
5. **Review uniqueness violations** to refine mapping rules

## Sprint 3 Preparation

With Sprint 2 complete, the system should have:
- ✅ All devices mapped with Type + Location
- ✅ No duplicate Type + Location combinations
- ✅ Clear device identity for grammar generation
- ✅ Foundation for voice command mapping

Example voice commands that will work after Sprint 3:
- "Turn on the lights in the living room"
- "Set heating in bedroom to 22 degrees"
- "Play music on media player in kitchen"
- "Close the blinds in the office"

---

Test completed by: _________________
Date: _________________
Overall Result: ⬜ PASS / ⬜ FAIL