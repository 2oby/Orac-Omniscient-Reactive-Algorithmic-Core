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
    
    // Load available models, dispatchers and grammars
    console.log('Loading models...');
    await loadModels();
    console.log('Loading dispatchers...');
    await loadDispatchers();
    console.log('Loading grammars...');
    await loadGrammars();
    
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

// Load available dispatchers
async function loadDispatchers() {
    try {
        console.log('Loading dispatchers from /v1/dispatchers...');
        const response = await fetch('/v1/dispatchers');
        console.log('Dispatcher response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Dispatcher data:', data);
        
        const select = document.getElementById('dispatcher');
        if (!select) {
            console.error('Dispatcher select element not found!');
            return;
        }
        
        select.innerHTML = '<option value="">None (Display Only)</option>';
        
        if (data.dispatchers && data.dispatchers.length > 0) {
            console.log('Adding', data.dispatchers.length, 'dispatchers to dropdown');
            data.dispatchers.forEach(dispatcher => {
                const option = document.createElement('option');
                option.value = dispatcher.id;
                option.textContent = `${dispatcher.name} - ${dispatcher.description}`;
                select.appendChild(option);
                console.log('Added dispatcher:', dispatcher.id, 'to dropdown');
            });
            console.log('Dispatcher dropdown final HTML:', select.innerHTML);
        } else {
            console.log('No dispatchers found in response');
        }
    } catch (error) {
        console.error('Error loading dispatchers:', error);
        console.error('Stack trace:', error.stack);
        // Show error in UI
        const select = document.getElementById('dispatcher');
        if (select) {
            select.innerHTML = '<option value="">Error loading dispatchers</option>';
        }
    }
}

// Load available grammars
async function loadGrammars() {
    try {
        const response = await fetch('/api/topics/grammars');
        const data = await response.json();
        
        const select = document.getElementById('grammarFile');
        select.innerHTML = '<option value="">No grammar selected</option>';
        
        data.grammars.forEach(grammar => {
            const option = document.createElement('option');
            option.value = grammar;
            option.textContent = grammar;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading grammars:', error);
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
    
    // Dispatcher
    document.getElementById('dispatcher').value = data.dispatcher || '';
    
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
    
    // Grammar configuration
    const grammar = data.grammar || {};
    document.getElementById('grammarEnabled').checked = grammar.enabled || false;
    document.getElementById('grammarFile').value = grammar.file || '';
    document.getElementById('grammarFile').disabled = !grammar.enabled;
    
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
    
    // Grammar enabled checkbox
    document.getElementById('grammarEnabled').addEventListener('change', (e) => {
        document.getElementById('grammarFile').disabled = !e.target.checked;
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
    
    const formData = {
        name: document.getElementById('name').value,
        description: document.getElementById('description').value,
        enabled: document.getElementById('enabled').checked,
        model: document.getElementById('model').value,
        dispatcher: document.getElementById('dispatcher').value || null,
        settings: {
            system_prompt: document.getElementById('systemPrompt').value,
            temperature: parseFloat(document.getElementById('temperature').value),
            top_p: parseFloat(document.getElementById('topP').value),
            top_k: parseInt(document.getElementById('topK').value),
            max_tokens: parseInt(document.getElementById('maxTokens').value),
            no_think: document.getElementById('noThink').checked,
            force_json: document.getElementById('forceJson').checked
        },
        grammar: {
            enabled: document.getElementById('grammarEnabled').checked,
            file: document.getElementById('grammarFile').value || null
        }
    };
    
    console.log('Form data to save:', JSON.stringify(formData, null, 2));
    console.log('Dispatcher field value:', formData.dispatcher);
    
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
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        statusEl.style.display = 'none';
    }, 5000);
}