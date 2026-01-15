// Topic Configuration JavaScript

let topicId = null;
let topicData = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', async function() {
    console.log('DOM Content Loaded - Initializing topic config page');
    
    // Get topic ID from URL
    const pathParts = window.location.pathname.split('/');
    topicId = pathParts[pathParts.length - 1];
    console.log('Topic ID:', topicId);
    
    if (!topicId) {
        showStatus('Invalid topic ID', 'error');
        return;
    }
    
    document.getElementById('topicId').textContent = topicId;
    
    // Load available models and backends (Sprint 5: dispatcher removed)
    console.log('Loading models...');
    await loadModels();
    // Sprint 5: Dispatcher loading removed - backends handle dispatching internally
    console.log('Loading backends...');
    await loadBackends();
    
    // Load topic data
    console.log('Loading topic data...');
    await loadTopic();
    
    // Set up event listeners
    setupEventListeners();
    console.log('Initialization complete');
});

// Load topic data
async function loadTopic() {
    try {
        const response = await fetch(`/api/topics/${topicId}`);
        if (!response.ok) {
            if (response.status === 404) {
                showStatus('Topic not found', 'error');
                setTimeout(() => window.location.href = '/topics', 2000);
                return;
            }
            throw new Error('Failed to load topic');
        }
        
        const data = await response.json();
        topicData = data;
        populateForm(data);
    } catch (error) {
        console.error('Error loading topic:', error);
        showStatus('Failed to load topic', 'error');
    }
}

// Load available models
async function loadModels() {
    try {
        const response = await fetch('/api/topics/models');
        const data = await response.json();
        
        const select = document.getElementById('model');
        select.innerHTML = '';
        
        data.models.forEach(model => {
            const option = document.createElement('option');
            option.value = model;
            option.textContent = model;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading models:', error);
    }
}

// Sprint 5: Dispatcher function removed - backends handle dispatching internally

// Sprint 4: Load available backends for topic configuration
async function loadBackends() {
    try {
        const response = await fetch('/api/topics/backends/available');
        const data = await response.json();

        const select = document.getElementById('backendId');
        select.innerHTML = '<option value="">No backend linked</option>';

        if (data.backends && data.backends.length > 0) {
            data.backends.forEach(backend => {
                const option = document.createElement('option');
                option.value = backend.id;
                const deviceInfo = `${backend.total_devices} devices, ${backend.enabled_devices} enabled`;
                option.textContent = `${backend.name} (${backend.type}) - ${deviceInfo}`;
                select.appendChild(option);
            });

            // Add "Create New Backend" option
            const createOption = document.createElement('option');
            createOption.value = 'create_new';
            createOption.textContent = '+ Create New Backend';
            select.appendChild(createOption);
        }
    } catch (error) {
        console.error('Error loading backends:', error);
    }
}

// Populate form with topic data
function populateForm(data) {
    // Basic information
    document.getElementById('name').value = data.name || '';
    document.getElementById('description').value = data.description || '';
    document.getElementById('enabled').checked = data.enabled;
    
    // Model
    document.getElementById('model').value = data.model || '';
    
    // Sprint 5: Dispatcher removed - backends handle dispatching internally
    
    // Generation settings
    const settings = data.settings || {};
    document.getElementById('systemPrompt').value = settings.system_prompt || '';
    document.getElementById('temperature').value = settings.temperature || 0.7;
    document.getElementById('topP').value = settings.top_p || 0.9;
    document.getElementById('topK').value = settings.top_k || 40;
    document.getElementById('maxTokens').value = settings.max_tokens || 500;
    document.getElementById('noThink').checked = settings.no_think || false;
    document.getElementById('forceJson').checked = settings.force_json || false;
    
    // Update slider values
    updateSliderValue('temperature');
    updateSliderValue('topP');
    updateSliderValue('topK');
    
    // Sprint 4: Backend configuration (replaces grammar)
    if (data.backend_id) {
        document.getElementById('backendId').value = data.backend_id;
        loadBackendInfo(data.backend_id);
        // Also load grammar options directly (in case backend info fails)
        loadGrammarOptions();
    } else {
        // No backend linked - hide grammar options
        hideGrammarOptions();
    }
    
    // Disable delete button for general topic
    if (topicId === 'general') {
        document.getElementById('deleteBtn').disabled = true;
        document.getElementById('deleteBtn').title = 'Cannot delete the general topic';
    }
}

// Set up event listeners
function setupEventListeners() {
    // Form submission
    document.getElementById('configForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await saveTopic();
    });
    
    // Delete button
    document.getElementById('deleteBtn').addEventListener('click', deleteTopic);
    
    // Test button
    document.getElementById('testBtn').addEventListener('click', testTopic);
    
    // Sprint 4: Backend selection change
    document.getElementById('backendId').addEventListener('change', async (e) => {
        if (e.target.value === 'create_new') {
            // Redirect to backend creation page
            window.location.href = '/backends';
        } else if (e.target.value) {
            // Load backend info (which also loads grammar options)
            await loadBackendInfo(e.target.value);
        } else {
            // Hide backend status and grammar options
            document.getElementById('backendStatus').style.display = 'none';
            hideGrammarOptions();
        }
    });
    
    // Slider updates
    ['temperature', 'topP', 'topK'].forEach(id => {
        document.getElementById(id).addEventListener('input', () => updateSliderValue(id));
    });
}

// Update slider value display
function updateSliderValue(sliderId) {
    const slider = document.getElementById(sliderId);
    const valueDisplay = document.getElementById(sliderId + 'Value');
    valueDisplay.textContent = slider.value;
}

// Save topic configuration
async function saveTopic() {
    console.log('saveTopic() called');
    
    // Sprint 5: Dispatcher debugging removed - backends handle dispatching internally
    
    const formData = {
        name: document.getElementById('name').value,
        description: document.getElementById('description').value,
        enabled: document.getElementById('enabled').checked,
        model: document.getElementById('model').value,
        backend_id: document.getElementById('backendId').value === '' ? null : document.getElementById('backendId').value,
        // Sprint 5: dispatcher removed - backends handle dispatching internally
        settings: {
            system_prompt: document.getElementById('systemPrompt').value,
            temperature: parseFloat(document.getElementById('temperature').value),
            top_p: parseFloat(document.getElementById('topP').value),
            top_k: parseInt(document.getElementById('topK').value),
            max_tokens: parseInt(document.getElementById('maxTokens').value),
            no_think: document.getElementById('noThink').checked,
            force_json: document.getElementById('forceJson').checked
        },
        grammar: {}  // Sprint 4: Empty grammar object for backward compatibility
    };
    
    console.log('Form data to save:', JSON.stringify(formData, null, 2));
    
    try {
        console.log(`Making PUT request to /api/topics/${topicId}`);
        const response = await fetch(`/api/topics/${topicId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        console.log('Response status:', response.status);
        
        if (response.ok) {
            showStatus('Topic saved successfully!', 'success');
            // Reload topic data
            await loadTopic();
        } else {
            const error = await response.json();
            console.error('Server error response:', error);
            showStatus(`Failed to save: ${error.detail}`, 'error');
        }
    } catch (error) {
        console.error('Error saving topic:', error);
        console.error('Error stack:', error.stack);
        showStatus('Failed to save topic', 'error');
    }
}

// Delete topic
async function deleteTopic() {
    if (topicId === 'general') {
        showStatus('Cannot delete the general topic', 'error');
        return;
    }
    
    if (!confirm(`Are you sure you want to delete the topic "${topicId}"?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/topics/${topicId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showStatus('Topic deleted successfully!', 'success');
            setTimeout(() => {
                window.location.href = '/topics';
            }, 1500);
        } else {
            const error = await response.json();
            showStatus(`Failed to delete: ${error.detail}`, 'error');
        }
    } catch (error) {
        console.error('Error deleting topic:', error);
        showStatus('Failed to delete topic', 'error');
    }
}

// Test topic configuration
async function testTopic() {
    const testPrompt = prompt('Enter a test prompt:');
    if (!testPrompt) return;
    
    try {
        const response = await fetch(`/v1/generate/${topicId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                prompt: testPrompt
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            alert(`Response: ${data.response}`);
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail}`);
        }
    } catch (error) {
        console.error('Error testing topic:', error);
        alert('Failed to test topic');
    }
}

// Show status message
function showStatus(message, type) {
    const statusEl = document.getElementById('statusMessage');
    statusEl.textContent = message;
    statusEl.className = `status-message ${type}`;
    statusEl.style.display = 'block';

    // Scroll to top to ensure message is visible
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Auto-hide after 8 seconds (increased from 5)
    setTimeout(() => {
        statusEl.style.display = 'none';
    }, 8000);
}

// Sprint 4: Load and display backend information
async function loadBackendInfo(backendId) {
    try {
        const response = await fetch(`/api/topics/${topicId}/backend`);

        if (!response.ok) {
            // Backend might not be linked yet, try to link it
            const linkResponse = await fetch(`/api/topics/${topicId}/backend`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({backend_id: backendId})
            });

            if (linkResponse.ok) {
                // Retry loading backend info
                const retryResponse = await fetch(`/api/topics/${topicId}/backend`);
                if (retryResponse.ok) {
                    const data = await retryResponse.json();
                    displayBackendInfo(data);
                }
            }
        } else {
            const data = await response.json();
            displayBackendInfo(data);
        }
    } catch (error) {
        console.error('Error loading backend info:', error);
    }
}

// Display backend information in the UI
function displayBackendInfo(backendInfo) {
    const statusDiv = document.getElementById('backendStatus');
    const infoDiv = document.getElementById('backendInfo');

    if (!backendInfo) {
        statusDiv.style.display = 'none';
        return;
    }

    // Show backend status section
    statusDiv.style.display = 'block';

    // Build info HTML
    const connectionStatus = backendInfo.status?.connected ?
        '<span style="color: #00ff41;">✅ Connected</span>' :
        '<span style="color: #ff4444;">❌ Disconnected</span>';

    const grammarStatus = backendInfo.grammar_generated ?
        '<span style="color: #00ff41;">✅ Generated</span>' :
        '<span style="color: #ffaa00;">⚠️ Not Generated</span>';

    infoDiv.innerHTML = `
        <div style="display: grid; gap: 0.5rem;">
            <div><strong>Name:</strong> ${backendInfo.name}</div>
            <div><strong>Type:</strong> ${backendInfo.type}</div>
            <div><strong>Connection:</strong> ${connectionStatus}</div>
            <div><strong>Devices:</strong> ${backendInfo.statistics.total_devices} total,
                ${backendInfo.statistics.enabled_devices} enabled,
                ${backendInfo.statistics.mapped_devices} mapped</div>
            <div><strong>Device Types:</strong> ${backendInfo.device_types.join(', ') || 'None'}</div>
            <div><strong>Locations:</strong> ${backendInfo.locations.join(', ') || 'None'}</div>
            <div><strong>Grammar:</strong> ${grammarStatus}</div>
        </div>
    `;

    // Update button links
    document.getElementById('configureBackendBtn').href = `/backends/${backendInfo.backend_id}/entities`;
    document.getElementById('testGrammarBtn').href = `/backends/${backendInfo.backend_id}/test-grammar`;

    // Load grammar options for display
    loadGrammarOptions();
}

// Load and display grammar options from backend
async function loadGrammarOptions() {
    const grammarOptionsGroup = document.getElementById('grammarOptionsGroup');
    const grammarOptionsDisplay = document.getElementById('grammarOptionsDisplay');

    try {
        const response = await fetch(`/api/topics/${topicId}/grammar-options`);
        if (!response.ok) {
            console.log('No grammar options available');
            grammarOptionsGroup.style.display = 'none';
            return;
        }

        const data = await response.json();
        console.log('Grammar options:', data);

        if (data.has_grammar && data.auto_prompt) {
            grammarOptionsGroup.style.display = 'block';
            grammarOptionsDisplay.value = data.auto_prompt;
        } else {
            grammarOptionsGroup.style.display = 'none';
            grammarOptionsDisplay.value = '';
        }
    } catch (error) {
        console.error('Error loading grammar options:', error);
        grammarOptionsGroup.style.display = 'none';
    }
}

// Hide grammar options when no backend is selected
function hideGrammarOptions() {
    const grammarOptionsGroup = document.getElementById('grammarOptionsGroup');
    const grammarOptionsDisplay = document.getElementById('grammarOptionsDisplay');
    grammarOptionsGroup.style.display = 'none';
    grammarOptionsDisplay.value = '';
}