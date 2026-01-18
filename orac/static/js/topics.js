// Topics management JavaScript

let topics = {};
let heartbeatStatus = {};

// Load and display topics
async function loadTopics() {
    try {
        const response = await fetch('/api/topics');
        const data = await response.json();
        topics = data.topics;
        displayTopics();
    } catch (error) {
        console.error('Error loading topics:', error);
        showError('Failed to load topics');
    }
}

// Load heartbeat status
async function loadHeartbeatStatus() {
    try {
        const response = await fetch('/v1/topics/heartbeat/status');
        if (response.ok) {
            const data = await response.json();
            heartbeatStatus = data.topics || {};
            updateLiveStatus();
        }
    } catch (error) {
        console.error('Error loading heartbeat status:', error);
    }
}

// Update live status indicators
function updateLiveStatus() {
    Object.keys(heartbeatStatus).forEach(topicId => {
        const status = heartbeatStatus[topicId];
        const card = document.querySelector(`.topic-card[data-topic-id="${topicId}"]`);
        if (card) {
            // Update card status class
            card.className = card.className.replace(/status-\w+/g, '');
            card.classList.add('topic-card');
            card.classList.add(`status-${status.live_status}`);
            
            // Re-add other classes if needed
            if (topics[topicId]) {
                if (!topics[topicId].enabled) {
                    card.classList.add('disabled');
                }
                if (topics[topicId].auto_discovered) {
                    card.classList.add('auto-discovered');
                }
            }
            
            // Update indicator
            const indicator = card.querySelector('.live-status-indicator');
            if (indicator) {
                indicator.className = 'live-status-indicator';
                indicator.classList.add(status.live_status);
                indicator.title = `Last heartbeat: ${status.last_heartbeat || 'Never'}`;
            }
        }
    });
}

// Display topics in grid
function displayTopics() {
    const grid = document.getElementById('topicsGrid');
    grid.innerHTML = '';
    
    // Add each topic card
    Object.keys(topics).forEach(topicId => {
        const topic = topics[topicId];
        const card = createTopicCard(topicId, topic);
        grid.appendChild(card);
    });
    
    // Add the "Add New Topic" card
    const addCard = createAddTopicCard();
    grid.appendChild(addCard);
}

// Create a topic card element
function createTopicCard(topicId, topic) {
    const card = document.createElement('div');
    card.className = 'topic-card';
    card.setAttribute('data-topic-id', topicId);
    
    // Get live status for this topic
    const status = heartbeatStatus[topicId] || {};
    const liveStatus = status.live_status || 'unknown';
    const wakeWord = topic.wake_word || status.wake_word || '';
    
    // Add status class for coloring
    card.classList.add(`status-${liveStatus}`);
    
    // Add disabled class if topic is disabled
    if (!topic.enabled) {
        card.classList.add('disabled');
    }
    
    // Add auto-discovered class if applicable
    if (topic.auto_discovered) {
        card.classList.add('auto-discovered');
    }
    
    // Auto-discovered badge
    const autoBadge = topic.auto_discovered ? 
        '<span class="auto-discovered-badge">AUTO</span>' : '';
    
    card.innerHTML = `
        ${autoBadge}
        <div class="topic-header">
            <div class="live-status-indicator ${liveStatus}" title="Live Status: ${liveStatus}"></div>
            <div class="topic-name">${topic.name || topicId}</div>
        </div>
        ${wakeWord ? `<div class="topic-wake-word">Wake: "${wakeWord}"</div>` : ''}
        <div class="topic-model">Model: ${topic.model || 'Not configured'}</div>
        <div class="topic-description">${topic.description || 'No description available'}</div>
        <div class="topic-status">
            <span class="status-badge ${topic.enabled ? 'enabled' : 'disabled'}">
                ${topic.enabled ? 'Enabled' : 'Disabled'}
            </span>
            <div class="topic-status-buttons">
                <a href="/cache?topic=${topicId}" class="cache-btn" title="View Cache for ${topicId}">Cache</a>
                <button class="topic-config-btn" onclick="configTopic('${topicId}')" title="Configure Topic">
                    ⚙️
                </button>
            </div>
        </div>
    `;
    
    return card;
}

// Create the "Add New Topic" card
function createAddTopicCard() {
    const card = document.createElement('div');
    card.className = 'topic-card add-topic-card';
    card.onclick = addNewTopic;
    
    card.innerHTML = `
        <div class="add-topic-content">
            <div class="add-topic-icon">+</div>
            <div class="add-topic-text">Add New Topic</div>
        </div>
    `;
    
    return card;
}

// Navigate to topic configuration page
function configTopic(topicId) {
    window.location.href = `/topics/${topicId}`;
}

// Add new topic dialog
async function addNewTopic() {
    const topicId = prompt('Enter a unique topic ID (e.g., home_assistant):');
    if (!topicId) return;
    
    // Validate topic ID (alphanumeric and underscores only)
    if (!/^[a-zA-Z0-9_]+$/.test(topicId)) {
        alert('Topic ID must contain only letters, numbers, and underscores');
        return;
    }
    
    // Check if topic already exists
    if (topics[topicId]) {
        alert('Topic already exists!');
        return;
    }
    
    const name = prompt('Enter topic name:') || topicId;
    const description = prompt('Enter topic description:') || '';
    
    try {
        const response = await fetch(`/api/topics?topic_id=${topicId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                description: description,
                model: 'Qwen3-0.6B-Q8_0.gguf',  // Default model
                settings: {},
                grammar: {},
                enabled: true
            })
        });
        
        if (response.ok) {
            // Reload topics to show the new one
            await loadTopics();
            // Navigate to configuration page
            configTopic(topicId);
        } else {
            const error = await response.json();
            alert(`Failed to create topic: ${error.detail}`);
        }
    } catch (error) {
        console.error('Error creating topic:', error);
        alert('Failed to create topic');
    }
}

// Show error message
function showError(message) {
    const grid = document.getElementById('topicsGrid');
    grid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; color: var(--error-color); padding: 2rem;">
            <h3>Error</h3>
            <p>${message}</p>
        </div>
    `;
}

// Auto-refresh topics periodically (to catch auto-discovered topics)
function startAutoRefresh() {
    // Refresh topics every 10 seconds
    setInterval(async () => {
        await loadTopics();
        await loadHeartbeatStatus();
    }, 10000);
    
    // Refresh heartbeat status more frequently (every 3 seconds)
    setInterval(async () => {
        await loadHeartbeatStatus();
    }, 3000);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadTopics();
    loadHeartbeatStatus();
    startAutoRefresh();
});