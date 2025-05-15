// DOM Elements
const modelSelect = document.getElementById('modelSelect');
const settingsToggle = document.getElementById('settingsToggle');
const settingsContent = document.getElementById('settingsContent');
const systemPrompt = document.getElementById('systemPrompt');
const systemPromptDisplay = document.getElementById('systemPromptDisplay');
const temperature = document.getElementById('temperature');
const topP = document.getElementById('topP');
const topK = document.getElementById('topK');
const maxTokens = document.getElementById('maxTokens');
const resetSettings = document.getElementById('resetSettings');
const saveSettings = document.getElementById('saveSettings');
const promptInput = document.getElementById('promptInput');
const generateButton = document.getElementById('generateButton');
const responseOutput = document.getElementById('responseOutput');
const generatingIndicator = document.getElementById('generatingIndicator');
const copyResponse = document.getElementById('copyResponse');

// State
let currentModel = null;
let favorites = [];
let modelConfigs = {};
let defaultSettings = null;

// Toggle settings panel
settingsToggle.addEventListener('click', () => {
    settingsContent.classList.toggle('active');
});

// Load models and favorites
async function loadModels() {
    try {
        console.log('Loading models...');
        // Load models
        const response = await fetch('/v1/models');
        const data = await response.json();
        console.log('Models loaded:', data);
        
        // Load favorites
        console.log('Loading favorites...');
        const favResponse = await fetch('/v1/config/favorites');
        const favData = await favResponse.json();
        console.log('Favorites loaded:', favData);
        favorites = favData.favorite_models || [];
        defaultSettings = favData.default_settings || {
            temperature: 0.7,
            top_p: 0.7,
            top_k: 40,
            max_tokens: 512
        };

        // Load model configs
        console.log('Loading model configs...');
        const configResponse = await fetch('/v1/config/models');
        const configData = await configResponse.json();
        console.log('Model configs loaded:', configData);
        modelConfigs = configData.models || {};

        // Clear existing options
        modelSelect.innerHTML = '<option value="">Select a model...</option>';

        // Add favorite models first
        const favoriteModels = data.models.filter(model => favorites.includes(model.name));
        const otherModels = data.models.filter(model => !favorites.includes(model.name));
        console.log('Favorite models:', favoriteModels);
        console.log('Other models:', otherModels);

        // Add favorite models to dropdown
        favoriteModels.forEach(model => {
            const option = createModelOption(model, true);
            modelSelect.appendChild(option);
        });

        // Add other models to dropdown
        otherModels.forEach(model => {
            const option = createModelOption(model, false);
            modelSelect.appendChild(option);
        });
        
        console.log('Dropdown populated with', modelSelect.options.length - 1, 'models');
    } catch (error) {
        console.error('Error loading models:', error);
    }
}

// Create model option element
function createModelOption(model, isFavorite) {
    const option = document.createElement('option');
    const sizeMB = (model.size / (1024 * 1024)).toFixed(1);
    option.value = model.name;
    option.textContent = `${isFavorite ? '★ ' : ''}${model.name} (${sizeMB} MB)`;
    return option;
}

// Handle model selection
modelSelect.addEventListener('change', async () => {
    const selectedModel = modelSelect.value;
    if (!selectedModel) {
        currentModel = null;
        return;
    }

    currentModel = selectedModel;
    const config = modelConfigs[selectedModel] || {};
    const settings = config.recommended_settings || defaultSettings;
    
    // Update settings panel with model-specific settings or defaults
    systemPrompt.value = config.system_prompt || '';
    systemPromptDisplay.textContent = config.system_prompt || '';
    temperature.value = settings.temperature || defaultSettings.temperature;
    topP.value = settings.top_p || defaultSettings.top_p;
    topK.value = settings.top_k || defaultSettings.top_k;
    maxTokens.value = settings.max_tokens || defaultSettings.max_tokens;
});

// Reset settings to default
resetSettings.addEventListener('click', () => {
    if (!currentModel) return;
    
    const config = modelConfigs[currentModel] || {};
    const settings = config.recommended_settings || defaultSettings;
    
    // Update UI with settings
    systemPrompt.value = config.system_prompt || '';
    systemPromptDisplay.textContent = config.system_prompt || '';
    temperature.value = settings.temperature || defaultSettings.temperature;
    topP.value = settings.top_p || defaultSettings.top_p;
    topK.value = settings.top_k || defaultSettings.top_k;
    maxTokens.value = settings.max_tokens || defaultSettings.max_tokens;

    // Show feedback
    const originalText = resetSettings.textContent;
    resetSettings.textContent = 'Settings Reset!';
    resetSettings.disabled = true;
    setTimeout(() => {
        resetSettings.textContent = originalText;
        resetSettings.disabled = false;
    }, 2000);
});

// Save settings
saveSettings.addEventListener('click', async () => {
    if (!currentModel) return;

    const settings = {
        system_prompt: systemPrompt.value.trim(),
        recommended_settings: {
            temperature: parseFloat(temperature.value) || defaultSettings.temperature,
            top_p: parseFloat(topP.value) || defaultSettings.top_p,
            top_k: parseInt(topK.value) || defaultSettings.top_k,
            max_tokens: parseInt(maxTokens.value) || defaultSettings.max_tokens
        }
    };

    try {
        const response = await fetch('/v1/config/models', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                models: {
                    [currentModel]: settings
                }
            })
        });

        if (response.ok) {
            modelConfigs[currentModel] = settings;
            systemPromptDisplay.textContent = settings.system_prompt;
            
            // Show feedback
            const originalText = saveSettings.textContent;
            saveSettings.textContent = 'Settings Saved!';
            saveSettings.disabled = true;
            setTimeout(() => {
                saveSettings.textContent = originalText;
                saveSettings.disabled = false;
            }, 2000);
        } else {
            const error = await response.json();
            console.error('Failed to save settings:', error);
            alert('Failed to save settings: ' + (error.detail || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        alert('Error saving settings: ' + error.message);
    }
});

// Handle generate button click
generateButton.addEventListener('click', async () => {
    if (!currentModel) {
        alert('Please select a model first');
        return;
    }

    const prompt = promptInput.value.trim();
    if (!prompt) {
        alert('Please enter a prompt');
        return;
    }

    // Show generating indicator and hide copy button
    generatingIndicator.classList.remove('hidden');
    copyResponse.classList.add('hidden');
    responseOutput.textContent = '';
    generateButton.disabled = true;

    try {
        const response = await fetch('/v1/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: currentModel,
                prompt: prompt,
                stream: false,  // We'll implement streaming in the next iteration
                temperature: parseFloat(temperature.value),
                top_p: parseFloat(topP.value),
                top_k: parseInt(topK.value),
                max_tokens: parseInt(maxTokens.value)
            })
        });

        const data = await response.json();
        
        if (response.ok) {
            responseOutput.textContent = data.response;
            copyResponse.classList.remove('hidden');
        } else {
            responseOutput.textContent = `Error: ${data.detail || 'Failed to generate response'}`;
        }
    } catch (error) {
        console.error('Error generating response:', error);
        responseOutput.textContent = `Error: ${error.message}`;
    } finally {
        generatingIndicator.classList.add('hidden');
        generateButton.disabled = false;
    }
});

// Initialize
loadModels(); 