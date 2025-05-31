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
const forceJson = document.getElementById('forceJson');
const setDefault = document.getElementById('setDefault');
const resetSettings = document.getElementById('resetSettings');
const saveSettings = document.getElementById('saveSettings');
const promptInput = document.getElementById('promptInput');
const generateButton = document.getElementById('generateButton');
const responseOutput = document.getElementById('responseOutput');
const generatingIndicator = document.getElementById('generatingIndicator');
const copyResponse = document.getElementById('copyResponse');
const favoriteToggle = document.getElementById('favoriteToggle');

// State
let currentModel = null;
let favorites = [];
let modelConfigs = {};
let defaultSettings = null;
let defaultModel = null;
let currentSettings = null;  // Store current settings for cancel functionality

// Function to collapse settings panel
function collapseSettingsPanel() {
    settingsContent.classList.remove('active');
    settingsToggle.textContent = 'Model Settings';
}

// Function to expand settings panel
function expandSettingsPanel() {
    settingsContent.classList.add('active');
    settingsToggle.textContent = 'Hide Settings';
}

// Settings toggle button click handler
settingsToggle.addEventListener('click', () => {
    if (!settingsContent.classList.contains('active')) {
        // Store current settings before expanding
        currentSettings = {
            systemPrompt: systemPrompt.value,
            temperature: temperature.value,
            topP: topP.value,
            topK: topK.value,
            maxTokens: maxTokens.value,
            forceJson: forceJson.checked,
            isDefault: setDefault.checked
        };
        expandSettingsPanel();
    } else {
        collapseSettingsPanel();
    }
});

// Cancel button click handler
document.getElementById('cancelSettings').addEventListener('click', () => {
    if (currentSettings) {
        // Restore previous settings
        systemPrompt.value = currentSettings.systemPrompt;
        temperature.value = currentSettings.temperature;
        topP.value = currentSettings.topP;
        topK.value = currentSettings.topK;
        maxTokens.value = currentSettings.maxTokens;
        forceJson.checked = currentSettings.forceJson;
        setDefault.checked = currentSettings.isDefault;
    }
    collapseSettingsPanel();
});

// Save settings button click handler
document.getElementById('saveSettings').addEventListener('click', async () => {
    const selectedModel = modelSelect.value;
    if (!selectedModel) {
        alert('Please select a model first');
        return;
    }

    const settings = {
        system_prompt: systemPrompt.value.trim(),
        temperature: parseFloat(temperature.value),
        top_p: parseFloat(topP.value),
        top_k: parseInt(topK.value),
        max_tokens: parseInt(maxTokens.value),
        json_mode: forceJson.checked
    };

    try {
        // First save model settings
        const modelResponse = await fetch('/v1/config/models', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                models: {
                    [selectedModel]: {
                        system_prompt: settings.system_prompt,
                        recommended_settings: {
                            temperature: settings.temperature,
                            top_p: settings.top_p,
                            top_k: settings.top_k,
                            max_tokens: settings.max_tokens,
                            json_mode: settings.json_mode
                        }
                    }
                }
            })
        });

        if (!modelResponse.ok) {
            const error = await modelResponse.json();
            throw new Error(error.detail || 'Failed to save settings');
        }

        // Then update favorites and default model if needed
        const newDefaultModel = setDefault.checked ? selectedModel : (defaultModel === selectedModel ? null : defaultModel);
        const favResponse = await fetch('/v1/config/favorites', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                favorite_models: favorites,
                default_model: newDefaultModel,
                default_settings: defaultSettings
            })
        });

        if (!favResponse.ok) {
            throw new Error('Failed to update default model');
        }

        // Update local state
        modelConfigs[selectedModel] = {
            system_prompt: settings.system_prompt,
            recommended_settings: {
                temperature: settings.temperature,
                top_p: settings.top_p,
                top_k: settings.top_k,
                max_tokens: settings.max_tokens,
                json_mode: settings.json_mode
            }
        };
        defaultModel = newDefaultModel;

        // Update current settings
        currentSettings = {
            systemPrompt: settings.system_prompt,
            temperature: settings.temperature,
            topP: settings.top_p,
            topK: settings.top_k,
            maxTokens: settings.max_tokens,
            forceJson: settings.json_mode,
            isDefault: setDefault.checked
        };

        // Show success message
        const saveButton = document.getElementById('saveSettings');
        const originalText = saveButton.textContent;
        saveButton.textContent = 'Settings Saved!';
        saveButton.disabled = true;
        
        // Collapse the panel after successful save
        collapseSettingsPanel();

        setTimeout(() => {
            saveButton.textContent = originalText;
            saveButton.disabled = false;
        }, 2000);
    } catch (error) {
        console.error('Error saving settings:', error);
        alert('Failed to save settings. Please try again.');
    }
});

// Reset settings button click handler
document.getElementById('resetSettings').addEventListener('click', async () => {
    const selectedModel = modelSelect.value;
    if (!selectedModel) {
        alert('Please select a model first');
        return;
    }

    try {
        // Get model configs to find default settings
        const response = await fetch('/api/models/configs');
        if (!response.ok) {
            throw new Error('Failed to load model configs');
        }
        const configs = await response.json();
        const modelConfig = configs[selectedModel];

        // Get favorites for default settings
        const favResponse = await fetch('/api/favorites');
        if (!favResponse.ok) {
            throw new Error('Failed to load favorites');
        }
        const favorites = await favResponse.json();
        const defaultSettings = favorites.default_settings || {};

        // Update UI with reset values
        systemPrompt.value = modelConfig?.system_prompt || defaultSettings.system_prompt || '';
        temperature.value = modelConfig?.recommended_settings?.temperature || defaultSettings.temperature || 0.7;
        topP.value = modelConfig?.recommended_settings?.top_p || defaultSettings.top_p || 0.9;
        topK.value = modelConfig?.recommended_settings?.top_k || defaultSettings.top_k || 40;
        maxTokens.value = modelConfig?.recommended_settings?.max_tokens || defaultSettings.max_tokens || 2048;
        forceJson.checked = modelConfig?.recommended_settings?.json_mode || defaultSettings.json_mode || false;

        // Update current settings
        currentSettings = {
            systemPrompt: systemPrompt.value,
            temperature: temperature.value,
            topP: topP.value,
            topK: topK.value,
            maxTokens: maxTokens.value,
            forceJson: forceJson.checked
        };

        // Show success message
        const resetButton = document.getElementById('resetSettings');
        const originalText = resetButton.textContent;
        resetButton.textContent = 'Settings Reset!';
        resetButton.disabled = true;

        // Collapse the panel after reset
        collapseSettingsPanel();

        setTimeout(() => {
            resetButton.textContent = originalText;
            resetButton.disabled = false;
        }, 2000);
    } catch (error) {
        console.error('Error resetting settings:', error);
        alert('Failed to reset settings. Please try again.');
    }
});

// Function to update favorite button state
function updateFavoriteButtonState(modelName) {
    console.log('[DEBUG] updateFavoriteButtonState called with modelName:', modelName);
    if (!modelName) {
        favoriteToggle.classList.remove('favorited');
        favoriteToggle.disabled = true;
        favoriteToggle.querySelector('.star-icon').innerText = '';
        console.log('[DEBUG] No model selected. Button disabled:', favoriteToggle.disabled, 'Classes:', favoriteToggle.className);
        return;
    }
    
    favoriteToggle.disabled = false;
    if (favorites.includes(modelName)) {
        favoriteToggle.classList.add('favorited');
    } else {
        favoriteToggle.classList.remove('favorited');
    }
    // Always clear the static star, let CSS handle it
    favoriteToggle.querySelector('.star-icon').innerText = '';
    console.log('[DEBUG] Model selected. Button disabled:', favoriteToggle.disabled, 'Classes:', favoriteToggle.className, 'Favorited:', favorites.includes(modelName));
}

// Function to toggle favorite status
async function toggleFavorite() {
    if (!currentModel) return;
    
    try {
        const isFavorite = favorites.includes(currentModel);
        const newFavorites = isFavorite 
            ? favorites.filter(m => m !== currentModel)
            : [...favorites, currentModel];
        
        const response = await fetch('/v1/config/favorites', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                favorite_models: newFavorites,
                default_settings: defaultSettings
            })
        });

        if (!response.ok) {
            throw new Error('Failed to update favorites');
        }

        // Update local state
        favorites = newFavorites;
        updateFavoriteButtonState(currentModel);
        
        // Re-sort and update the model dropdown
        await loadModels();
        
        // Restore the current model selection
        modelSelect.value = currentModel;
        
        // Show feedback
        const feedback = document.createElement('div');
        feedback.className = 'feedback-message';
        feedback.textContent = isFavorite ? 'Removed from favorites' : 'Added to favorites';
        document.querySelector('.model-selection').appendChild(feedback);
        setTimeout(() => feedback.remove(), 2000);
        
    } catch (error) {
        console.error('Error toggling favorite:', error);
        alert('Failed to update favorites. Please try again.');
    }
}

// Add favorite toggle click handler
favoriteToggle.addEventListener('click', toggleFavorite);

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
        defaultModel = favData.default_model || null;
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

        // Select default model if set
        if (defaultModel) {
            modelSelect.value = defaultModel;
            currentModel = defaultModel;
            updateFavoriteButtonState(defaultModel);
            updateSettingsPanel(defaultModel);
        }
        
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

// Update settings panel with model settings
function updateSettingsPanel(modelName) {
    if (!modelName) return;
    
    const config = modelConfigs[modelName] || {};
    const settings = config.recommended_settings || defaultSettings;
    
    systemPrompt.value = config.system_prompt || '';
    systemPromptDisplay.textContent = config.system_prompt || '';
    temperature.value = settings.temperature || defaultSettings.temperature;
    topP.value = settings.top_p || defaultSettings.top_p;
    topK.value = settings.top_k || defaultSettings.top_k;
    maxTokens.value = settings.max_tokens || defaultSettings.max_tokens;
    forceJson.checked = settings.json_mode || false;
    setDefault.checked = modelName === defaultModel;
}

// Update model selection handler
modelSelect.addEventListener('change', async () => {
    const selectedModel = modelSelect.value;
    if (!selectedModel) {
        currentModel = null;
        updateFavoriteButtonState(null);
        return;
    }

    currentModel = selectedModel;
    updateFavoriteButtonState(selectedModel);
    updateSettingsPanel(selectedModel);
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
                system_prompt: systemPrompt.value.trim(),
                stream: false,  // We'll implement streaming in the next iteration
                temperature: parseFloat(temperature.value),
                top_p: parseFloat(topP.value),
                top_k: parseInt(topK.value),
                max_tokens: parseInt(maxTokens.value),
                json_mode: forceJson.checked
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