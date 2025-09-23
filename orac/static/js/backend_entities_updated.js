// Backend Entities Management - Device Configuration with Drag and Drop
// Updated for card-based UI with click-to-enable functionality

const backendId = window.location.pathname.split('/')[2];
let deviceMappings = {};
let deviceTypes = [];
let locations = [];
let draggedItem = null;
let draggedType = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadDeviceData();
    setupDragAndDrop();
});

// Load all device data
async function loadDeviceData() {
    showLoading(true);
    try {
        const response = await fetch(`/api/backends/${backendId}/mappings`);
        const data = await response.json();

        if (data.status === 'success') {
            deviceMappings = data.device_mappings || {};
            deviceTypes = data.device_types || ['lights', 'heating', 'media_player', 'blinds', 'switches'];
            locations = data.locations || [];

            renderDevices();
            renderDeviceTypes();
            renderLocations();
        }
    } catch (error) {
        console.error('Failed to load device data:', error);
        showNotification('Failed to load device data', 'error');
    } finally {
        showLoading(false);
    }
}

// Render device cards
function renderDevices() {
    const devicesList = document.getElementById('devices-list');
    devicesList.innerHTML = '';

    Object.entries(deviceMappings).forEach(([entityId, mapping]) => {
        const deviceCard = createDeviceCard(entityId, mapping);
        devicesList.appendChild(deviceCard);
    });
}

// Create a device card element
function createDeviceCard(entityId, mapping) {
    const card = document.createElement('div');
    card.className = `device-card ${mapping.enabled ? 'enabled' : 'disabled'}`;
    card.dataset.entityId = entityId;

    // Click handler for the entire card (except specific elements)
    card.addEventListener('click', function(e) {
        // Don't toggle if clicking on drop zones or clear buttons
        if (!e.target.closest('.drop-zone') && !e.target.closest('.clear-btn')) {
            toggleDeviceEnabled(entityId);
        }
    });

    // Enable/Status column
    const enableLabel = document.createElement('div');
    enableLabel.className = 'enable-label';
    enableLabel.textContent = mapping.enabled ? 'ENABLED' : 'DISABLED';

    // Device info
    const deviceInfo = document.createElement('div');
    deviceInfo.className = 'device-info';

    const deviceId = document.createElement('div');
    deviceId.className = 'device-id';
    deviceId.textContent = entityId.toUpperCase();

    const deviceName = document.createElement('div');
    deviceName.className = 'device-name';
    deviceName.textContent = mapping.original_name || mapping.friendly_name || entityId.split('.')[1];

    deviceInfo.appendChild(deviceId);
    deviceInfo.appendChild(deviceName);

    // Device Type drop zone
    const typeDropZone = document.createElement('div');
    typeDropZone.className = 'drop-zone type-drop-zone';
    typeDropZone.dataset.entityId = entityId;
    typeDropZone.dataset.dropType = 'device-type';

    if (mapping.device_type) {
        typeDropZone.classList.add('has-value');
        const valueSpan = document.createElement('span');
        valueSpan.className = 'drop-zone-value';
        valueSpan.textContent = mapping.device_type.toUpperCase();
        typeDropZone.appendChild(valueSpan);

        const clearBtn = document.createElement('button');
        clearBtn.className = 'clear-btn';
        clearBtn.innerHTML = '×';
        clearBtn.onclick = (e) => {
            e.stopPropagation();
            clearDeviceType(entityId);
        };
        typeDropZone.appendChild(clearBtn);
    } else {
        const label = document.createElement('span');
        label.className = 'drop-zone-label';
        label.textContent = 'DROP TYPE HERE';
        typeDropZone.appendChild(label);
    }

    // Location drop zone
    const locationDropZone = document.createElement('div');
    locationDropZone.className = 'drop-zone location-drop-zone';
    locationDropZone.dataset.entityId = entityId;
    locationDropZone.dataset.dropType = 'location';

    if (mapping.location) {
        locationDropZone.classList.add('has-value');
        const valueSpan = document.createElement('span');
        valueSpan.className = 'drop-zone-value';
        valueSpan.textContent = mapping.location.toUpperCase();
        locationDropZone.appendChild(valueSpan);

        const clearBtn = document.createElement('button');
        clearBtn.className = 'clear-btn';
        clearBtn.innerHTML = '×';
        clearBtn.onclick = (e) => {
            e.stopPropagation();
            clearLocation(entityId);
        };
        locationDropZone.appendChild(clearBtn);
    } else {
        const label = document.createElement('span');
        label.className = 'drop-zone-label';
        label.textContent = 'DROP LOCATION HERE';
        locationDropZone.appendChild(label);
    }

    // Add all elements to card
    card.appendChild(enableLabel);
    card.appendChild(deviceInfo);
    card.appendChild(typeDropZone);
    card.appendChild(locationDropZone);

    // Setup drop zones
    setupDropZone(typeDropZone);
    setupDropZone(locationDropZone);

    return card;
}

// Toggle device enabled state
async function toggleDeviceEnabled(entityId) {
    const mapping = deviceMappings[entityId];
    mapping.enabled = !mapping.enabled;

    // Update UI immediately
    const card = document.querySelector(`[data-entity-id="${entityId}"]`);
    if (card) {
        card.classList.toggle('enabled');
        card.classList.toggle('disabled');
        const enableLabel = card.querySelector('.enable-label');
        if (enableLabel) {
            enableLabel.textContent = mapping.enabled ? 'ENABLED' : 'DISABLED';
        }
    }

    // Save to backend
    await updateDeviceMapping(entityId, mapping);
}

// Render device types list
function renderDeviceTypes() {
    const typesList = document.getElementById('device-types-list');
    typesList.innerHTML = '';

    deviceTypes.forEach(type => {
        const item = document.createElement('div');
        item.className = 'draggable-item';
        item.draggable = true;
        item.dataset.type = 'device-type';
        item.dataset.value = type;
        item.textContent = type.toUpperCase();

        // Setup drag events
        item.addEventListener('dragstart', handleDragStart);
        item.addEventListener('dragend', handleDragEnd);

        typesList.appendChild(item);
    });
}

// Render locations list
function renderLocations() {
    const locationsList = document.getElementById('locations-list');
    locationsList.innerHTML = '';

    locations.forEach(location => {
        const item = document.createElement('div');
        item.className = 'draggable-item';
        item.draggable = true;
        item.dataset.type = 'location';
        item.dataset.value = location;
        item.textContent = location.toUpperCase();

        // Setup drag events
        item.addEventListener('dragstart', handleDragStart);
        item.addEventListener('dragend', handleDragEnd);

        locationsList.appendChild(item);
    });
}

// Setup drag and drop functionality
function setupDragAndDrop() {
    // Prevent default drag over behavior
    document.addEventListener('dragover', (e) => e.preventDefault());
}

// Setup individual drop zone
function setupDropZone(dropZone) {
    dropZone.addEventListener('dragover', handleDragOver);
    dropZone.addEventListener('dragleave', handleDragLeave);
    dropZone.addEventListener('drop', handleDrop);
}

// Drag start handler
function handleDragStart(e) {
    draggedItem = e.target;
    draggedType = e.target.dataset.type;
    e.target.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'copy';
}

// Drag end handler
function handleDragEnd(e) {
    e.target.classList.remove('dragging');
    draggedItem = null;
    draggedType = null;
}

// Drag over handler
function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';

    const dropZone = e.currentTarget;
    const dropType = dropZone.dataset.dropType;

    // Check if this is a valid drop target
    if ((draggedType === 'device-type' && dropType === 'device-type') ||
        (draggedType === 'location' && dropType === 'location')) {
        dropZone.classList.add('drag-over');
    }
}

// Drag leave handler
function handleDragLeave(e) {
    e.currentTarget.classList.remove('drag-over');
}

// Drop handler
async function handleDrop(e) {
    e.preventDefault();
    const dropZone = e.currentTarget;
    dropZone.classList.remove('drag-over');

    if (!draggedItem) return;

    const entityId = dropZone.dataset.entityId;
    const dropType = dropZone.dataset.dropType;
    const value = draggedItem.dataset.value;

    // Check if correct type is being dropped
    if ((draggedType === 'device-type' && dropType === 'device-type') ||
        (draggedType === 'location' && dropType === 'location')) {

        // Update the mapping
        if (!deviceMappings[entityId]) {
            deviceMappings[entityId] = {};
        }

        if (dropType === 'device-type') {
            deviceMappings[entityId].device_type = value;
        } else if (dropType === 'location') {
            deviceMappings[entityId].location = value;
        }

        // Check for conflicts
        const conflicts = checkForConflicts(entityId);
        if (conflicts.length > 0) {
            showConflictWarning(conflicts);
            dropZone.classList.add('conflict');
        } else {
            dropZone.classList.remove('conflict');
        }

        // Update UI
        updateDropZone(dropZone, value);

        // Save to backend
        await updateDeviceMapping(entityId, deviceMappings[entityId]);
    }
}

// Update drop zone display
function updateDropZone(dropZone, value) {
    dropZone.innerHTML = '';
    dropZone.classList.add('has-value');

    const valueSpan = document.createElement('span');
    valueSpan.className = 'drop-zone-value';
    valueSpan.textContent = value.toUpperCase();
    dropZone.appendChild(valueSpan);

    const clearBtn = document.createElement('button');
    clearBtn.className = 'clear-btn';
    clearBtn.innerHTML = '×';
    clearBtn.onclick = (e) => {
        e.stopPropagation();
        const entityId = dropZone.dataset.entityId;
        if (dropZone.dataset.dropType === 'device-type') {
            clearDeviceType(entityId);
        } else {
            clearLocation(entityId);
        }
    };
    dropZone.appendChild(clearBtn);
}

// Clear device type
async function clearDeviceType(entityId) {
    if (deviceMappings[entityId]) {
        delete deviceMappings[entityId].device_type;
        await updateDeviceMapping(entityId, deviceMappings[entityId]);
        renderDevices(); // Re-render to update UI
    }
}

// Clear location
async function clearLocation(entityId) {
    if (deviceMappings[entityId]) {
        delete deviceMappings[entityId].location;
        await updateDeviceMapping(entityId, deviceMappings[entityId]);
        renderDevices(); // Re-render to update UI
    }
}

// Check for duplicate Type + Location combinations
function checkForConflicts(currentEntityId) {
    const conflicts = [];
    const current = deviceMappings[currentEntityId];

    if (current && current.device_type && current.location) {
        Object.entries(deviceMappings).forEach(([entityId, mapping]) => {
            if (entityId !== currentEntityId &&
                mapping.device_type === current.device_type &&
                mapping.location === current.location &&
                mapping.enabled) {
                conflicts.push(entityId);
            }
        });
    }

    return conflicts;
}

// Show conflict warning
function showConflictWarning(conflicts) {
    const message = `Warning: Duplicate Type + Location combination detected with: ${conflicts.join(', ')}`;
    showNotification(message, 'warning');
}

// Update device mapping on backend
async function updateDeviceMapping(entityId, mapping) {
    try {
        const response = await fetch(`/api/backends/${backendId}/entities/${entityId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(mapping)
        });

        if (!response.ok) {
            throw new Error(`Failed to update mapping: ${response.statusText}`);
        }

        const data = await response.json();
        if (data.warning) {
            showNotification(data.warning, 'warning');
        }
    } catch (error) {
        console.error('Failed to update device mapping:', error);
        showNotification('Failed to save changes', 'error');
    }
}

// Fetch devices from Home Assistant
async function fetchDevices() {
    showLoading(true);
    try {
        const response = await fetch(`/api/backends/${backendId}/entities/fetch`, {
            method: 'POST'
        });

        const data = await response.json();
        if (data.status === 'success') {
            showNotification(`Fetched ${data.result.total_entities} entities from Home Assistant`, 'success');
            await loadDeviceData(); // Reload all data
        } else {
            showNotification('Failed to fetch entities: ' + data.result.error, 'error');
        }
    } catch (error) {
        console.error('Failed to fetch entities:', error);
        showNotification('Failed to fetch entities', 'error');
    } finally {
        showLoading(false);
    }
}

// Save configuration
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

// Validate all mappings
async function validateMappings() {
    try {
        const response = await fetch(`/api/backends/${backendId}/validate-mappings`, {
            method: 'POST'
        });

        const data = await response.json();
        if (data.conflicts && data.conflicts.length > 0) {
            showNotification(`Found ${data.conflicts.length} conflicts`, 'warning');
            // Highlight conflicting devices
            data.conflicts.forEach(conflict => {
                const card = document.querySelector(`[data-entity-id="${conflict.entity1}"]`);
                if (card) card.classList.add('conflict');
                const card2 = document.querySelector(`[data-entity-id="${conflict.entity2}"]`);
                if (card2) card2.classList.add('conflict');
            });
        } else {
            showNotification('All mappings are valid!', 'success');
        }
    } catch (error) {
        console.error('Failed to validate mappings:', error);
        showNotification('Failed to validate mappings', 'error');
    }
}

// Filter devices
function filterDevices(searchTerm) {
    const cards = document.querySelectorAll('.device-card');
    const term = searchTerm.toLowerCase();

    cards.forEach(card => {
        const entityId = card.dataset.entityId.toLowerCase();
        const deviceName = card.querySelector('.device-name').textContent.toLowerCase();

        if (entityId.includes(term) || deviceName.includes(term)) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}

// Show add device type modal
function showAddDeviceTypeModal() {
    const newType = prompt('Enter new device type name:');
    if (newType && newType.trim()) {
        addDeviceType(newType.trim().toLowerCase());
    }
}

// Add new device type
async function addDeviceType(typeName) {
    try {
        const response = await fetch(`/api/backends/${backendId}/device-types`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ device_type: typeName })
        });

        if (response.ok) {
            deviceTypes.push(typeName);
            renderDeviceTypes();
            showNotification(`Added device type: ${typeName}`, 'success');
        } else {
            showNotification('Failed to add device type', 'error');
        }
    } catch (error) {
        console.error('Failed to add device type:', error);
        showNotification('Failed to add device type', 'error');
    }
}

// Show add location modal
function showAddLocationModal() {
    const newLocation = prompt('Enter new location name:');
    if (newLocation && newLocation.trim()) {
        addLocation(newLocation.trim().toLowerCase());
    }
}

// Add new location
async function addLocation(locationName) {
    try {
        const response = await fetch(`/api/backends/${backendId}/locations`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ location: locationName })
        });

        if (response.ok) {
            locations.push(locationName);
            renderLocations();
            showNotification(`Added location: ${locationName}`, 'success');
        } else {
            showNotification('Failed to add location', 'error');
        }
    } catch (error) {
        console.error('Failed to add location:', error);
        showNotification('Failed to add location', 'error');
    }
}

// Show loading overlay
function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        if (show) {
            overlay.classList.add('show');
        } else {
            overlay.classList.remove('show');
        }
    }
}

// Show notification (you'll need to implement this or use a library)
function showNotification(message, type = 'info') {
    console.log(`[${type.toUpperCase()}] ${message}`);
    // TODO: Implement a proper notification system
    // For now, using alert for errors and warnings
    if (type === 'error' || type === 'warning') {
        alert(message);
    }
}