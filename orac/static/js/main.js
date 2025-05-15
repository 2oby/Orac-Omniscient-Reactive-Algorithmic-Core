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

// Toggle settings panel
settingsToggle.addEventListener('click', () => {
    settingsContent.classList.toggle('active');
});

// Load models and favorites
async function loadModels() {
    try {
        // Load models
        const response = await fetch('/v1/models');
        const data = await response.json();
        
        // Load favorites
        const favResponse = await fetch('/v1/config/favorites');
        const favData = await favResponse.json();
        favorites = favData.favorite_models || [];

        // Load model configs
        const configResponse = await fetch('/v1/config/models');
        const configData = await configResponse.json();
        modelConfigs = configData.models || {};

        // Clear existing options
        modelSelect.innerHTML = '<option value="">Select a model...</option>';

        // Add favorite models first
        const favoriteModels = data.models.filter(model => favorites.includes(model.name));
        const otherModels = data.models.filter(model => !favorites.includes(model.name));

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
    
    // Update settings panel
    systemPrompt.value = config.system_prompt || '';
    systemPromptDisplay.textContent = config.system_prompt || '';
    temperature.value = config.recommended_settings?.temperature || 0.7;
    topP.value = config.recommended_settings?.top_p || 0.7;
    topK.value = config.recommended_settings?.top_k || 40;
    maxTokens.value = config.recommended_settings?.max_tokens || 512;
});

// Reset settings to default
resetSettings.addEventListener('click', () => {
    if (!currentModel) return;
    
    const config = modelConfigs[currentModel] || {};
    systemPrompt.value = config.system_prompt || '';
    systemPromptDisplay.textContent = config.system_prompt || '';
    temperature.value = config.recommended_settings?.temperature || 0.7;
    topP.value = config.recommended_settings?.top_p || 0.7;
    topK.value = config.recommended_settings?.top_k || 40;
    maxTokens.value = config.recommended_settings?.max_tokens || 512;
});

// Save settings
saveSettings.addEventListener('click', async () => {
    if (!currentModel) return;

    const settings = {
        system_prompt: systemPrompt.value,
        recommended_settings: {
            temperature: parseFloat(temperature.value),
            top_p: parseFloat(topP.value),
            top_k: parseInt(topK.value),
            max_tokens: parseInt(maxTokens.value)
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
        } else {
            console.error('Failed to save settings');
        }
    } catch (error) {
        console.error('Error saving settings:', error);
    }
});

// Initialize
loadModels(); 