// Backend Entities Management - Device Configuration with Drag and Drop

const backendId = window.location.pathname.split('/')[2];
let deviceMappings = {};
let deviceTypes = [];
let locations = [];
let draggedItem = null;
let draggedType = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadDeviceData();
});

// Load all device data
async function loadDeviceData() {
    showLoading(true);
    try {
        const response = await fetch(`/api/backends/${backendId}/mappings`);
        const data = await response.json();

        if (data.status === 'success') {
            deviceMappings = {};
            data.devices.forEach(device => {
                deviceMappings[device.device_id] = device;
            });

            deviceTypes = data.device_types || [];
            locations = data.locations || [];

            renderDeviceTypes();
            renderLocations();
            renderDevices();
            updateStatistics();

            if (data.validation && !data.validation.valid) {
                showValidationWarnings(data.validation.conflicts);
            }
        } else {
            console.error('Failed to load device data:', data);
            showNotification('Failed to load device data', 'error');
        }
    } catch (error) {
        console.error('Error loading device data:', error);
        showNotification('Error loading device data', 'error');
    } finally {
        showLoading(false);
    }
}

// Render device types panel
function renderDeviceTypes() {
    const container = document.getElementById('device-types-list');
    container.innerHTML = '';

    deviceTypes.forEach(type => {
        const tile = createDraggableTile(type, 'device-type');
        container.appendChild(tile);
    });
}

// Render locations panel
function renderLocations() {
    const container = document.getElementById('locations-list');
    container.innerHTML = '';

    locations.forEach(location => {
        const tile = createDraggableTile(location, 'location');
        container.appendChild(tile);
    });
}

// Create a draggable tile
function createDraggableTile(name, type) {
    const tile = document.createElement('div');
    tile.className = 'draggable-tile';
    tile.draggable = true;
    tile.dataset.value = name;
    tile.dataset.type = type;

    const nameSpan = document.createElement('span');
    nameSpan.className = 'tile-name';
    nameSpan.textContent = name;
    tile.appendChild(nameSpan);

    // Add delete button for custom types/locations
    const isCustom = (type === 'device-type' && !['lights', 'heating', 'media_player', 'blinds', 'switches'].includes(name)) ||
                    (type === 'location');

    if (isCustom) {
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'tile-delete';
        deleteBtn.innerHTML = '×';
        deleteBtn.onclick = (e) => {
            e.stopPropagation();
            removeTile(name, type);
        };
        tile.appendChild(deleteBtn);
    }

    // Drag event handlers
    tile.addEventListener('dragstart', handleDragStart);
    tile.addEventListener('dragend', handleDragEnd);

    return tile;
}

// Drag event handlers
function handleDragStart(e) {
    draggedItem = e.target.dataset.value;
    draggedType = e.target.dataset.type;
    e.target.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'copy';
}

function handleDragEnd(e) {
    e.target.classList.remove('dragging');
}

// Render devices table
function renderDevices() {
    const tbody = document.getElementById('devices-tbody');
    tbody.innerHTML = '';

    Object.entries(deviceMappings).forEach(([deviceId, device]) => {
        const row = createDeviceRow(deviceId, device);
        tbody.appendChild(row);
    });
}

// Create device row
function createDeviceRow(deviceId, device) {
    const row = document.createElement('tr');
    row.dataset.deviceId = deviceId;

    // Checkbox cell
    const checkboxCell = document.createElement('td');
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'device-checkbox';
    checkbox.checked = device.enabled || false;
    checkbox.onchange = () => updateDeviceEnabled(deviceId, checkbox.checked);
    checkboxCell.appendChild(checkbox);
    row.appendChild(checkboxCell);

    // Device ID cell
    const idCell = document.createElement('td');
    const idDiv = document.createElement('div');
    idDiv.className = 'device-id';
    idDiv.textContent = deviceId;
    idCell.appendChild(idDiv);

    if (device.original_name) {
        const nameDiv = document.createElement('div');
        nameDiv.className = 'device-name';
        nameDiv.textContent = device.original_name;
        idCell.appendChild(nameDiv);
    }
    row.appendChild(idCell);

    // Device Type drop zone
    const typeCell = document.createElement('td');
    const typeZone = createDropZone('device-type', deviceId, device.device_type);
    typeCell.appendChild(typeZone);
    row.appendChild(typeCell);

    // Location drop zone
    const locationCell = document.createElement('td');
    const locationZone = createDropZone('location', deviceId, device.location);
    locationCell.appendChild(locationZone);
    row.appendChild(locationCell);

    return row;
}

// Create drop zone
function createDropZone(type, deviceId, currentValue) {
    const zone = document.createElement('div');
    zone.className = 'drop-zone';
    zone.dataset.type = type;
    zone.dataset.deviceId = deviceId;

    if (currentValue) {
        zone.classList.add('has-value');
    }

    const text = document.createElement('span');
    text.className = 'drop-zone-text';
    text.textContent = currentValue || `Drop ${type === 'device-type' ? 'Type' : 'Location'} here`;
    zone.appendChild(text);

    if (currentValue) {
        const clearBtn = document.createElement('button');
        clearBtn.className = 'clear-btn';
        clearBtn.innerHTML = '×';
        clearBtn.onclick = (e) => {
            e.stopPropagation();
            clearDropZone(deviceId, type);
        };
        zone.appendChild(clearBtn);
    }

    // Drop event handlers
    zone.addEventListener('dragover', handleDragOver);
    zone.addEventListener('drop', handleDrop);
    zone.addEventListener('dragleave', handleDragLeave);

    return zone;
}

// Drop event handlers
function handleDragOver(e) {
    e.preventDefault();
    const zone = e.currentTarget;
    const zoneType = zone.dataset.type;

    if (draggedType === zoneType) {
        e.dataTransfer.dropEffect = 'copy';
        zone.classList.add('drag-over');
    }
}

function handleDragLeave(e) {
    e.currentTarget.classList.remove('drag-over');
}

async function handleDrop(e) {
    e.preventDefault();
    const zone = e.currentTarget;
    zone.classList.remove('drag-over');

    const zoneType = zone.dataset.type;
    const deviceId = zone.dataset.deviceId;

    if (draggedType !== zoneType) {
        return;
    }

    // Update the mapping
    if (!deviceMappings[deviceId]) {
        deviceMappings[deviceId] = {};
    }

    if (zoneType === 'device-type') {
        deviceMappings[deviceId].device_type = draggedItem;
    } else {
        deviceMappings[deviceId].location = draggedItem;
    }

    // Save the update
    await updateDeviceMapping(deviceId, deviceMappings[deviceId]);

    // Re-render the device row
    const row = document.querySelector(`tr[data-device-id="${deviceId}"]`);
    if (row) {
        const newRow = createDeviceRow(deviceId, deviceMappings[deviceId]);
        row.replaceWith(newRow);
    }

    // Validate mappings
    validateMappings();
    updateStatistics();
}

// Clear drop zone
async function clearDropZone(deviceId, type) {
    if (type === 'device-type') {
        deviceMappings[deviceId].device_type = null;
    } else {
        deviceMappings[deviceId].location = null;
    }

    await updateDeviceMapping(deviceId, deviceMappings[deviceId]);

    const row = document.querySelector(`tr[data-device-id="${deviceId}"]`);
    if (row) {
        const newRow = createDeviceRow(deviceId, deviceMappings[deviceId]);
        row.replaceWith(newRow);
    }

    validateMappings();
    updateStatistics();
}

// Update device enabled status
async function updateDeviceEnabled(deviceId, enabled) {
    deviceMappings[deviceId].enabled = enabled;
    await updateDeviceMapping(deviceId, { enabled });
    updateStatistics();

    if (enabled) {
        validateMappings();
    }
}

// Update device mapping via API
async function updateDeviceMapping(deviceId, updates) {
    try {
        const response = await fetch(`/api/backends/${backendId}/entities/${deviceId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(updates)
        });

        const data = await response.json();
        if (data.status !== 'success') {
            showNotification('Failed to update device', 'error');
        }
    } catch (error) {
        console.error('Error updating device:', error);
        showNotification('Error updating device', 'error');
    }
}

// Fetch entities from Home Assistant
async function fetchEntities() {
    showLoading(true);
    try {
        const response = await fetch(`/api/backends/${backendId}/entities/fetch`, {
            method: 'POST'
        });

        const data = await response.json();
        if (data.status === 'success') {
            showNotification(`Fetched ${data.result.count} devices`, 'success');
            loadDeviceData();
        } else {
            showNotification('Failed to fetch devices', 'error');
        }
    } catch (error) {
        console.error('Error fetching devices:', error);
        showNotification('Error fetching devices', 'error');
    } finally {
        showLoading(false);
    }
}

// Save all mappings
async function saveAllMappings() {
    showLoading(true);
    try {
        // The mappings are already saved individually when updated
        // This is just to trigger a full save/validation
        const response = await fetch(`/api/backends/${backendId}/validate-mappings`, {
            method: 'POST'
        });

        const data = await response.json();
        if (data.valid) {
            showNotification('Configuration saved successfully', 'success');
        } else {
            showNotification('Configuration saved with validation errors', 'warning');
            showValidationWarnings(data.conflicts);
        }
    } catch (error) {
        console.error('Error saving configuration:', error);
        showNotification('Error saving configuration', 'error');
    } finally {
        showLoading(false);
    }
}

// Validate mappings
async function validateMappings() {
    try {
        const response = await fetch(`/api/backends/${backendId}/validate-mappings`, {
            method: 'POST'
        });

        const data = await response.json();
        if (!data.valid) {
            showValidationWarnings(data.conflicts);
        } else {
            hideValidationWarnings();
        }
    } catch (error) {
        console.error('Error validating mappings:', error);
    }
}

// Show validation warnings
function showValidationWarnings(conflicts) {
    const warningDiv = document.getElementById('validation-warning');
    const warningList = document.getElementById('warning-list');

    warningList.innerHTML = '';
    conflicts.forEach(conflict => {
        const li = document.createElement('li');
        li.textContent = conflict;
        warningList.appendChild(li);
    });

    warningDiv.classList.add('show');
}

// Hide validation warnings
function hideValidationWarnings() {
    const warningDiv = document.getElementById('validation-warning');
    warningDiv.classList.remove('show');
}

// Update statistics
function updateStatistics() {
    const total = Object.keys(deviceMappings).length;
    const enabled = Object.values(deviceMappings).filter(d => d.enabled).length;
    const mapped = Object.values(deviceMappings).filter(d =>
        d.enabled && d.device_type && d.location
    ).length;

    document.getElementById('stat-total').textContent = total;
    document.getElementById('stat-enabled').textContent = enabled;
    document.getElementById('stat-mapped').textContent = mapped;
}

// Filter devices
function filterDevices(searchText) {
    const rows = document.querySelectorAll('#devices-tbody tr');
    const search = searchText.toLowerCase();

    rows.forEach(row => {
        const deviceId = row.dataset.deviceId.toLowerCase();
        const device = deviceMappings[row.dataset.deviceId];
        const originalName = (device.original_name || '').toLowerCase();

        if (deviceId.includes(search) || originalName.includes(search)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

// Modal functions
function showAddDeviceTypeModal() {
    document.getElementById('add-device-type-modal').classList.add('show');
    document.getElementById('new-device-type').focus();
}

function hideAddDeviceTypeModal() {
    document.getElementById('add-device-type-modal').classList.remove('show');
    document.getElementById('new-device-type').value = '';
}

function showAddLocationModal() {
    document.getElementById('add-location-modal').classList.add('show');
    document.getElementById('new-location').focus();
}

function hideAddLocationModal() {
    document.getElementById('add-location-modal').classList.remove('show');
    document.getElementById('new-location').value = '';
}

// Add device type
async function addDeviceType() {
    const input = document.getElementById('new-device-type');
    const deviceType = input.value.trim().toLowerCase();

    if (!deviceType) {
        showNotification('Please enter a device type name', 'error');
        return;
    }

    if (deviceTypes.includes(deviceType)) {
        showNotification('Device type already exists', 'error');
        return;
    }

    try {
        const response = await fetch(`/api/backends/${backendId}/device-types`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ device_type: deviceType })
        });

        const data = await response.json();
        if (data.status === 'success') {
            deviceTypes.push(deviceType);
            renderDeviceTypes();
            hideAddDeviceTypeModal();
            showNotification('Device type added successfully', 'success');
        } else {
            showNotification(data.message || 'Failed to add device type', 'error');
        }
    } catch (error) {
        console.error('Error adding device type:', error);
        showNotification('Error adding device type', 'error');
    }
}

// Add location
async function addLocation() {
    const input = document.getElementById('new-location');
    const location = input.value.trim().toLowerCase();

    if (!location) {
        showNotification('Please enter a location name', 'error');
        return;
    }

    if (locations.includes(location)) {
        showNotification('Location already exists', 'error');
        return;
    }

    try {
        const response = await fetch(`/api/backends/${backendId}/locations`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ location: location })
        });

        const data = await response.json();
        if (data.status === 'success') {
            locations.push(location);
            renderLocations();
            hideAddLocationModal();
            showNotification('Location added successfully', 'success');
        } else {
            showNotification(data.message || 'Failed to add location', 'error');
        }
    } catch (error) {
        console.error('Error adding location:', error);
        showNotification('Error adding location', 'error');
    }
}

// Remove tile (device type or location)
async function removeTile(name, type) {
    // Check if any device is using this type/location
    const inUse = Object.values(deviceMappings).some(device => {
        if (type === 'device-type') {
            return device.device_type === name;
        } else {
            return device.location === name;
        }
    });

    if (inUse) {
        showNotification(`Cannot remove ${name} - it is in use`, 'error');
        return;
    }

    if (confirm(`Are you sure you want to remove "${name}"?`)) {
        if (type === 'device-type') {
            deviceTypes = deviceTypes.filter(t => t !== name);
            renderDeviceTypes();
        } else {
            locations = locations.filter(l => l !== name);
            renderLocations();
        }
        showNotification(`${type === 'device-type' ? 'Device type' : 'Location'} removed`, 'success');
    }
}

// Show loading overlay
function showLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    if (show) {
        overlay.classList.add('show');
    } else {
        overlay.classList.remove('show');
    }
}

// Show notification
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        background: ${type === 'error' ? 'rgba(255, 68, 68, 0.9)' :
                      type === 'success' ? 'rgba(0, 255, 65, 0.9)' :
                      type === 'warning' ? 'rgba(255, 165, 0, 0.9)' :
                      'rgba(0, 123, 255, 0.9)'};
        color: ${type === 'success' ? '#000' : '#fff'};
        border-radius: 4px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Handle Enter key in modals
document.getElementById('new-device-type').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        addDeviceType();
    }
});

document.getElementById('new-location').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        addLocation();
    }
});

// Close modals when clicking outside
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.classList.remove('show');
    }
};