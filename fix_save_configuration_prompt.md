# Fix SAVE CONFIGURATION Button - Sprint 2 GUI

## Current Situation
The Sprint 2 GUI is mostly working. Users can:
- ✅ Fetch devices from Home Assistant (30 devices load successfully)
- ✅ Enable/disable devices by clicking cards
- ✅ Drag and drop device types onto devices
- ✅ Drag and drop locations onto devices
- ❌ **SAVE CONFIGURATION fails with "Failed to save configuration" error**

## The Problem
When clicking the "SAVE CONFIGURATION" button at http://192.168.8.192:8000/backends/homeassistant_8ca84424/entities, the system shows an error: "Failed to save configuration"

## Technical Details

### Frontend Code (orac/static/js/backend_entities.js)
```javascript
async function saveConfiguration() {
    showLoading(true);
    try {
        const response = await fetch(`/api/backends/${backendId}/save`, {
            method: 'POST'
        });

        if (response.ok) {
            showNotification('Configuration saved successfully', 'success');
        } else {
            showNotification('Failed to save configuration', 'error');
        }
    } catch (error) {
        console.error('Failed to save configuration:', error);
        showNotification('Failed to save configuration', 'error');
    } finally {
        showLoading(false);
    }
}
```

The frontend is calling `POST /api/backends/{backend_id}/save`

### Investigation Steps
1. Check if this endpoint exists in `orac/api.py`
2. If it doesn't exist, implement it
3. The endpoint should save the current device_mappings to the backend configuration

## Infrastructure Information

### Development Environment
- **Local Dev Machine**: macOS with the code at `/Users/2oby/pCloud Box/Projects/ORAC/Orac-Omniscient-Reactive-Algorithmic-Core/`
- **Production**: NVIDIA Orin Nano (hostname: `orin4`) running Ubuntu
- **Application**: Runs in Docker container named `orac`

### Deployment Process
Use the `deploy_and_test.sh` script which:
1. Commits changes to GitHub
2. SSHs to orin4 (`ssh orin4`)
3. Pulls from GitHub
4. Copies files into Docker container
5. Restarts container
6. Runs tests

### Useful Commands
```bash
# Deploy changes
./deploy_and_test.sh "Fix save configuration endpoint"

# Check API endpoints on Orin
ssh orin4 "docker exec orac grep -n 'save' /app/orac/api.py"

# View Docker logs
ssh orin4 "docker logs orac --tail 50"

# Test the save endpoint directly
curl -X POST http://192.168.8.192:8000/api/backends/homeassistant_8ca84424/save
```

## Task
1. Investigate why the save endpoint is failing
2. Fix or implement the `/api/backends/{backend_id}/save` endpoint
3. Ensure it properly saves the device configurations
4. Test that the save button works
5. Deploy using `deploy_and_test.sh`

## Expected Behavior
When "SAVE CONFIGURATION" is clicked:
1. Loading overlay appears
2. Current device_mappings are saved to the backend configuration file
3. Success notification: "Configuration saved successfully"
4. The saved configuration persists across container restarts

## Files to Check/Modify
- `orac/api.py` - Check if save endpoint exists
- `orac/backend_manager.py` - Implement save logic if needed
- `orac/static/js/backend_entities.js` - Frontend is already correct

## Notes
- The backend manager already has methods for updating individual device mappings
- The save operation should persist all current device_mappings to disk
- Device mappings are stored in JSON files at `/home/toby/ORAC/data/backends/` on the Orin
- Inside Docker, this is mounted at `/app/data/backends/`