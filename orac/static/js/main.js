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

// Home Assistant DOM Elements
const entityMappingModal = document.getElementById('entityMappingModal');
const closeEntityModal = document.getElementById('closeEntityModal');
const mappingProgress = document.getElementById('mappingProgress');
const mappingForm = document.getElementById('mappingForm');
const mappingComplete = document.getElementById('mappingComplete');
const currentEntityId = document.getElementById('currentEntityId');
const currentEntityName = document.getElementById('currentEntityName');
const friendlyNameInput = document.getElementById('friendlyNameInput');
const nameSuggestions = document.getElementById('nameSuggestions');
const skipEntity = document.getElementById('skipEntity');
const saveEntityMapping = document.getElementById('saveEntityMapping');
const closeMappingModal = document.getElementById('closeMappingModal');
const mappingSummary = document.getElementById('mappingSummary');

// Home Assistant Status Panel Elements
const haStatusPanel = document.getElementById('haStatusPanel');
const refreshHAStatus = document.getElementById('refreshHAStatus');
const haConnectionStatus = document.getElementById('haConnectionStatus');
const haEntityCount = document.getElementById('haEntityCount');
const haGrammarStatus = document.getElementById('haGrammarStatus');
const haMappingStatus = document.getElementById('haMappingStatus');
const checkNullMappings = document.getElementById('checkNullMappings');
const runAutoDiscovery = document.getElementById('runAutoDiscovery');
const updateGrammar = document.getElementById('updateGrammar');
const forceUpdateGrammar = document.getElementById('forceUpdateGrammar');

// State
let currentModel = null;
let favorites = [];
let modelConfigs = {};
let defaultSettings = null;
let defaultModel = null;
let currentSettings = null;  // Store current settings for cancel functionality

// Home Assistant State - Improved State Management
let nullEntities = [];
let currentEntityIndex = 0;
let mappingResults = {
    saved: 0,
    skipped: 0,
    total: 0
};

// Modal State Machine
const ModalState = {
    CLOSED: 'closed',
    LOADING: 'loading',
    FORM: 'form',
    COMPLETE: 'complete',
    ERROR: 'error'
};

let modalState = ModalState.CLOSED;
let previousFocusElement = null; // Store element that had focus before modal opened
let modalEventListeners = []; // Track event listeners for cleanup

// Error handling state
let isProcessing = false; // Prevent multiple simultaneous operations
let retryCount = 0;
const MAX_RETRIES = 3;

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
        
        // Validate settings after save to ensure they're properly applied
        setTimeout(validateAndFixSettings, 100);

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
        const response = await fetch('/v1/config/models');
        if (!response.ok) {
            throw new Error('Failed to load model configs');
        }
        const configs = await response.json();
        const modelConfig = configs.models?.[selectedModel] || {};

        // Get favorites for default settings
        const favResponse = await fetch('/v1/config/favorites');
        if (!favResponse.ok) {
            throw new Error('Failed to load favorites');
        }
        const favData = await favResponse.json();
        const defaultSettings = favData.default_settings || {};

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
    console.log('[DEBUG] Current favorites:', favorites);
    console.log('[DEBUG] Button state before update:', {
        disabled: favoriteToggle.disabled,
        classes: favoriteToggle.className,
        isFavorite: favorites.includes(modelName)
    });
    
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
        console.log('[DEBUG] Model is favorited, adding favorited class');
    } else {
        favoriteToggle.classList.remove('favorited');
        console.log('[DEBUG] Model is not favorited, removing favorited class');
    }
    // Always clear the static star, let CSS handle it
    favoriteToggle.querySelector('.star-icon').innerText = '';
    console.log('[DEBUG] Button state after update:', {
        disabled: favoriteToggle.disabled,
        classes: favoriteToggle.className,
        isFavorite: favorites.includes(modelName)
    });
}

// Function to toggle favorite status
async function toggleFavorite() {
    console.log('[DEBUG] toggleFavorite called for model:', currentModel);
    console.log('[DEBUG] Current favorites before toggle:', favorites);
    console.log('[DEBUG] Current default model:', defaultModel);
    
    if (!currentModel) {
        console.log('[DEBUG] No model selected, ignoring toggle');
        return;
    }
    
    try {
        const isFavorite = favorites.includes(currentModel);
        console.log('[DEBUG] Current favorite status:', isFavorite);
        
        // If trying to remove favorite status from default model, prevent it
        if (isFavorite && currentModel === defaultModel) {
            console.log('[DEBUG] Cannot remove favorite status from default model');
            alert('Cannot remove favorite status from default model. Please set a different default model first.');
            return;
        }
        
        const newFavorites = isFavorite 
            ? favorites.filter(m => m !== currentModel)
            : [...favorites, currentModel];
        
        console.log('[DEBUG] New favorites array:', newFavorites);
        
        // Ensure default model is in favorites
        if (defaultModel && !newFavorites.includes(defaultModel)) {
            console.log('[DEBUG] Adding default model to favorites:', defaultModel);
            newFavorites.push(defaultModel);
        }
        
        const response = await fetch('/v1/config/favorites', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                favorite_models: newFavorites,
                default_model: defaultModel,
                default_settings: defaultSettings
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            console.error('[DEBUG] API error response:', errorData);
            throw new Error(errorData.detail || 'Failed to update favorites');
        }

        const responseData = await response.json();
        console.log('[DEBUG] API success response:', responseData);

        // Update local state
        favorites = newFavorites;
        console.log('[DEBUG] Updated local favorites:', favorites);
        
        updateFavoriteButtonState(currentModel);
        console.log('[DEBUG] Updated button state');
        
        // Re-sort and update the model dropdown
        await loadModels();
        console.log('[DEBUG] Reloaded models');
        
        // Restore the current model selection
        modelSelect.value = currentModel;
        console.log('[DEBUG] Restored model selection:', currentModel);
        
        // Show feedback
        const feedback = document.createElement('div');
        feedback.className = 'feedback-message';
        feedback.textContent = isFavorite ? 'Removed from favorites' : 'Added to favorites';
        document.querySelector('.model-selection').appendChild(feedback);
        console.log('[DEBUG] Added feedback message');
        
        setTimeout(() => {
            feedback.remove();
            console.log('[DEBUG] Removed feedback message');
        }, 2000);
        
    } catch (error) {
        console.error('[DEBUG] Error in toggleFavorite:', error);
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
        
        // Ensure settings are properly loaded for the current model
        if (currentModel) {
            console.log('Ensuring settings are loaded for current model:', currentModel);
            updateSettingsPanel(currentModel);
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
    if (!modelName) {
        console.warn('updateSettingsPanel called with no model name');
        return;
    }
    
    console.log(`Updating settings panel for model: ${modelName}`);
    console.log('Available model configs:', Object.keys(modelConfigs));
    console.log('Current model configs:', modelConfigs);
    
    const config = modelConfigs[modelName] || {};
    const settings = config.recommended_settings || {};
    
    // Use fallback chain: model settings -> default settings -> hardcoded defaults
    const fallbackSettings = {
        temperature: 0.7,
        top_p: 0.7,
        top_k: 40,
        max_tokens: 512,
        json_mode: false
    };
    
    // Update UI with robust fallback logic
    systemPrompt.value = config.system_prompt || '';
    systemPromptDisplay.textContent = config.system_prompt || '';
    temperature.value = settings.temperature ?? defaultSettings?.temperature ?? fallbackSettings.temperature;
    topP.value = settings.top_p ?? defaultSettings?.top_p ?? fallbackSettings.top_p;
    topK.value = settings.top_k ?? defaultSettings?.top_k ?? fallbackSettings.top_k;
    maxTokens.value = settings.max_tokens ?? defaultSettings?.max_tokens ?? fallbackSettings.max_tokens;
    forceJson.checked = settings.json_mode ?? defaultSettings?.json_mode ?? fallbackSettings.json_mode;
    setDefault.checked = modelName === defaultModel;
    
    console.log('Settings panel updated with values:', {
        systemPrompt: systemPrompt.value,
        temperature: temperature.value,
        topP: topP.value,
        topK: topK.value,
        maxTokens: maxTokens.value,
        forceJson: forceJson.checked,
        setDefault: setDefault.checked
    });
}

// Update model selection handler
modelSelect.addEventListener('change', async () => {
    const selectedModel = modelSelect.value;
    if (!selectedModel) {
        currentModel = null;
        updateFavoriteButtonState(null);
        return;
    }

    console.log('Model selection changed to:', selectedModel);
    currentModel = selectedModel;
    updateFavoriteButtonState(selectedModel);
    
    // Ensure settings are loaded with a small delay to handle any race conditions
    setTimeout(() => {
        updateSettingsPanel(selectedModel);
        validateAndFixSettings();
    }, 50);
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
                json_mode: forceJson.checked,
                grammar_file: forceJson.checked ? 'data/test_grammars/default.gbnf' : null
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

// Function to validate and fix missing settings
function validateAndFixSettings() {
    if (!currentModel) return;
    
    console.log('Validating settings for current model:', currentModel);
    
    // Check if settings are missing or invalid
    const hasValidSettings = systemPrompt.value && 
                            temperature.value && 
                            topP.value && 
                            topK.value && 
                            maxTokens.value;
    
    if (!hasValidSettings) {
        console.warn('Settings appear to be missing or invalid, reloading...');
        updateSettingsPanel(currentModel);
    }
}

// Initialize
loadModels().then(() => {
    // Validate settings after models are loaded
    setTimeout(validateAndFixSettings, 100);
    
    // Handle page visibility changes to reload settings when user returns
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible' && currentModel) {
            console.log('Page became visible, validating settings...');
            setTimeout(validateAndFixSettings, 500);
        }
    });
});

// Home Assistant Functionality

// Modal Management - Improved State Machine Implementation
function showModal() {
    console.log('=== showModal called ===');
    console.log('Current modal state:', modalState);
    console.log('Modal element:', entityMappingModal);
    console.log('Modal computed display before:', window.getComputedStyle(entityMappingModal).display);
    console.log('Modal has hidden class before:', entityMappingModal.classList.contains('hidden'));
    
    if (modalState !== ModalState.CLOSED) {
        console.warn('Modal is already open, ignoring showModal call');
        return;
    }
    
    // Store current focus element
    previousFocusElement = document.activeElement;
    console.log('Stored previous focus element:', previousFocusElement);
    
    // Update state
    modalState = ModalState.LOADING;
    console.log('Modal state set to LOADING');
    
    // Show modal - CSS specificity issue now fixed
    entityMappingModal.classList.remove('hidden');
    
    console.log('Modal hidden class removed');
    console.log('Modal has hidden class after:', entityMappingModal.classList.contains('hidden'));
    console.log('Modal computed display after:', window.getComputedStyle(entityMappingModal).display);
    console.log('Modal should be visible now');
    
    // Set up focus trap
    setupFocusTrap();
    
    // Add event listeners
    addModalEventListeners();
    
    // Focus first focusable element
    setTimeout(() => {
        const firstFocusable = entityMappingModal.querySelector('button, input, select, textarea');
        if (firstFocusable) {
            firstFocusable.focus();
        }
    }, 100);
    
    console.log('=== showModal completed ===');
}

function hideModal() {
    console.log('=== hideModal called ===');
    console.log('Current modal state:', modalState);
    console.log('Modal element:', entityMappingModal);
    console.log('Modal computed display before:', window.getComputedStyle(entityMappingModal).display);
    console.log('Modal has hidden class before:', entityMappingModal.classList.contains('hidden'));
    
    if (modalState === ModalState.CLOSED) {
        console.log('Modal already closed, returning');
        return;
    }
    
    // Update state
    modalState = ModalState.CLOSED;
    console.log('Modal state set to CLOSED');
    
    // Hide modal - CSS specificity issue now fixed
    entityMappingModal.classList.add('hidden');
    
    console.log('Modal hidden class added');
    console.log('Modal has hidden class after:', entityMappingModal.classList.contains('hidden'));
    console.log('Modal computed display after:', window.getComputedStyle(entityMappingModal).display);
    console.log('Modal should be hidden now');
    
    // Clean up event listeners
    removeModalEventListeners();
    
    // Remove focus trap
    removeFocusTrap();
    
    // Restore previous focus
    if (previousFocusElement && previousFocusElement.focus) {
        previousFocusElement.focus();
    }
    
    // Reset state
    resetMappingState();
    console.log('=== Modal fully closed and reset ===');
}

function setModalState(newState) {
    const previousState = modalState;
    
    // Prevent recursive calls - if trying to set CLOSED state, just call hideModal directly
    if (newState === ModalState.CLOSED) {
        hideModal();
        return;
    }
    
    // Prevent setting same state multiple times
    if (newState === modalState) {
        return;
    }
    
    modalState = newState;
    
    // Update UI based on state
    switch (newState) {
        case ModalState.LOADING:
            mappingProgress.classList.remove('hidden');
            mappingForm.classList.add('hidden');
            mappingComplete.classList.add('hidden');
            break;
            
        case ModalState.FORM:
            mappingProgress.classList.add('hidden');
            mappingForm.classList.remove('hidden');
            mappingComplete.classList.add('hidden');
            // Focus the input field
            setTimeout(() => {
                if (friendlyNameInput) {
                    friendlyNameInput.focus();
                }
            }, 100);
            break;
            
        case ModalState.COMPLETE:
            mappingProgress.classList.add('hidden');
            mappingForm.classList.add('hidden');
            mappingComplete.classList.remove('hidden');
            break;
            
        case ModalState.ERROR:
            // Show error state - could add error display element
            console.error('Modal error state');
            break;
    }
    
    console.log(`Modal state changed: ${previousState} -> ${newState}`);
}

function setupFocusTrap() {
    const focusableElements = entityMappingModal.querySelectorAll(
        'button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    
    if (focusableElements.length === 0) return;
    
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];
    
    const handleTabKey = (e) => {
        if (e.key === 'Tab') {
            if (e.shiftKey) {
                if (document.activeElement === firstElement) {
                    e.preventDefault();
                    lastElement.focus();
                }
            } else {
                if (document.activeElement === lastElement) {
                    e.preventDefault();
                    firstElement.focus();
                }
            }
        }
    };
    
    entityMappingModal.addEventListener('keydown', handleTabKey);
    modalEventListeners.push({ element: entityMappingModal, event: 'keydown', handler: handleTabKey });
}

function removeFocusTrap() {
    // Focus trap cleanup is handled by removeModalEventListeners
}

function addModalEventListeners() {
    // Escape key to close modal
    const handleEscape = (e) => {
        if (e.key === 'Escape') {
            hideModal();
        }
    };
    
    document.addEventListener('keydown', handleEscape);
    modalEventListeners.push({ element: document, event: 'keydown', handler: handleEscape });
    
    // Click outside modal to close
    const handleOutsideClick = (e) => {
        if (e.target === entityMappingModal) {
            hideModal();
        }
    };
    
    entityMappingModal.addEventListener('click', handleOutsideClick);
    modalEventListeners.push({ element: entityMappingModal, event: 'click', handler: handleOutsideClick });
}

function removeModalEventListeners() {
    modalEventListeners.forEach(({ element, event, handler }) => {
        element.removeEventListener(event, handler);
    });
    modalEventListeners = [];
}

function resetMappingState() {
    nullEntities = [];
    currentEntityIndex = 0;
    mappingResults = { saved: 0, skipped: 0, total: 0 };
    retryCount = 0;
    isProcessing = false;
    
    // Reset UI elements
    if (mappingProgress) mappingProgress.classList.remove('hidden');
    if (mappingForm) mappingForm.classList.add('hidden');
    if (mappingComplete) mappingComplete.classList.add('hidden');
    
    // Clear form fields
    if (friendlyNameInput) friendlyNameInput.value = '';
    if (nameSuggestions) nameSuggestions.innerHTML = '';
    
    // Reset progress bar
    const progressFill = document.getElementById('mappingProgressFill');
    if (progressFill) progressFill.style.width = '0%';
}

// Close modal handlers - Updated to use new state machine
closeEntityModal.addEventListener('click', (e) => {
    console.log('=== Close entity modal button clicked ===');
    console.log('Event:', e);
    console.log('Current modal state:', modalState);
    console.log('Modal element:', entityMappingModal);
    console.log('Modal computed display:', window.getComputedStyle(entityMappingModal).display);
    console.log('Modal has hidden class:', entityMappingModal.classList.contains('hidden'));
    inspectModalState(); // Full state inspection
    e.preventDefault();
    e.stopPropagation();
    hideModal();
});

closeMappingModal.addEventListener('click', (e) => {
    console.log('=== Close mapping modal button clicked ===');
    console.log('Event:', e);
    console.log('Current modal state:', modalState);
    console.log('Modal element:', entityMappingModal);
    console.log('Modal computed display:', window.getComputedStyle(entityMappingModal).display);
    console.log('Modal has hidden class:', entityMappingModal.classList.contains('hidden'));
    inspectModalState(); // Full state inspection
    e.preventDefault();
    e.stopPropagation();
    hideModal();
});

// Home Assistant Status Management - Improved Error Handling
async function updateHAStatus() {
    try {
        // Check connection
        const statusResponse = await fetch('/v1/status');
        if (statusResponse.ok) {
            haConnectionStatus.textContent = 'Connected';
            haConnectionStatus.className = 'status-value success';
        } else {
            haConnectionStatus.textContent = 'Disconnected';
            haConnectionStatus.className = 'status-value error';
            return;
        }

        // Get entity mappings with error handling
        try {
            const mappingResponse = await fetch('/v1/homeassistant/mapping/list');
            if (mappingResponse.ok) {
                const mappingData = await mappingResponse.json();
                haMappingStatus.textContent = `${mappingData.entities_with_friendly_names}/${mappingData.total_count}`;
                haEntityCount.textContent = mappingData.total_count;
            } else {
                haMappingStatus.textContent = 'Error';
                haEntityCount.textContent = '-';
                console.warn('Failed to fetch mapping data:', mappingResponse.status);
            }
        } catch (mappingError) {
            haMappingStatus.textContent = 'Error';
            haEntityCount.textContent = '-';
            console.warn('Error fetching mapping data:', mappingError);
        }

        // Get grammar status with error handling
        try {
            const grammarResponse = await fetch('/v1/homeassistant/grammar');
            if (grammarResponse.ok) {
                const grammarData = await grammarResponse.json();
                haGrammarStatus.textContent = `${grammarData.device_count} devices, ${grammarData.action_count} actions`;
            } else {
                haGrammarStatus.textContent = 'Error';
                console.warn('Failed to fetch grammar data:', grammarResponse.status);
            }
        } catch (grammarError) {
            haGrammarStatus.textContent = 'Error';
            console.warn('Error fetching grammar data:', grammarError);
        }

        // Get scheduler status with error handling
        try {
            const schedulerResponse = await fetch('/v1/homeassistant/grammar/scheduler/status');
            if (schedulerResponse.ok) {
                const schedulerData = await schedulerResponse.json();
                const schedulerStatus = schedulerData.scheduler_status;
                if (schedulerStatus.scheduler_running) {
                    const nextUpdate = new Date(schedulerStatus.next_update).toLocaleString();
                    haGrammarStatus.textContent += ` | Scheduler: Running (Next: ${nextUpdate})`;
                } else {
                    haGrammarStatus.textContent += ' | Scheduler: Stopped';
                }
            } else {
                console.warn('Failed to fetch scheduler data:', schedulerResponse.status);
            }
        } catch (schedulerError) {
            console.warn('Error fetching scheduler data:', schedulerError);
        }

    } catch (error) {
        console.error('Error updating HA status:', error);
        haConnectionStatus.textContent = 'Error';
        haConnectionStatus.className = 'status-value error';
        haMappingStatus.textContent = 'Error';
        haEntityCount.textContent = '-';
        haGrammarStatus.textContent = 'Error';
    }
}

// Entity Mapping Functions - Improved Error Handling and State Management
async function checkNullMappingsHandler() {
    console.log('=== checkNullMappingsHandler called ===');
    console.log('Current modal state before opening:', modalState);
    console.log('Modal element:', entityMappingModal);
    console.log('Modal computed display before:', window.getComputedStyle(entityMappingModal).display);
    console.log('Modal has hidden class before:', entityMappingModal.classList.contains('hidden'));
    
    if (isProcessing) {
        console.warn('Already processing, ignoring request');
        return;
    }
    
    console.log('Starting check null mappings process...');
    isProcessing = true;
    retryCount = 0;
    
    // Add timeout to prevent infinite hanging
    const timeoutId = setTimeout(() => {
        if (isProcessing) {
            console.error('Modal operation timed out');
            showModalError('Operation timed out. Please try again.');
            isProcessing = false;
            setTimeout(() => {
                hideModal();
            }, 2000);
        }
    }, 30000);
    
    try {
        console.log('Calling showModal()...');
        showModal();
        console.log('Modal state after showModal():', modalState);
        console.log('Modal computed display after showModal():', window.getComputedStyle(entityMappingModal).display);
        console.log('Modal has hidden class after showModal():', entityMappingModal.classList.contains('hidden'));
        setModalState(ModalState.LOADING);
        clearModalError(); // Clear any previous errors
        
        const response = await fetchWithRetry('/v1/homeassistant/mapping/check-null');
        const data = await response.json();
        
        clearTimeout(timeoutId); // Clear timeout on success
        
        if (data.total_null_count === 0) {
            // No null mappings found
            console.log('No null entities found, showing completion message');
            mappingProgress.innerHTML = '<p>✅ All entities have friendly names!</p>';
            setTimeout(() => {
                setModalState(ModalState.COMPLETE);
            }, 1000);
            return;
        }
        
        nullEntities = data.null_entities;
        mappingResults.total = data.total_null_count;
        
        console.log('Found', nullEntities.length, 'null entities to process');
        
        // Reset state before starting
        currentEntityIndex = 0;
        mappingResults.saved = 0;
        mappingResults.skipped = 0;
        
        // Start processing entities
        processNextEntity();
        
    } catch (error) {
        clearTimeout(timeoutId); // Clear timeout on error
        console.error('Error checking null mappings:', error);
        setModalState(ModalState.ERROR);
        showModalError(`Error checking for entities that need friendly names: ${error.message}. Please try again.`);
        setTimeout(() => {
            hideModal();
        }, 5000); // Give user more time to read the error
    } finally {
        isProcessing = false;
    }
}

// Utility function for fetch with retry logic
async function fetchWithRetry(url, options = {}, maxRetries = MAX_RETRIES) {
    let lastError;
    
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
            const response = await fetch(url, {
                ...options,
                signal: AbortSignal.timeout(30000) // 30 second timeout
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return response;
        } catch (error) {
            lastError = error;
            
            if (attempt === maxRetries) {
                throw error;
            }
            
            // Wait before retrying (exponential backoff)
            const delay = Math.min(1000 * Math.pow(2, attempt), 5000);
            console.warn(`Request failed, retrying in ${delay}ms (attempt ${attempt + 1}/${maxRetries + 1})`);
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }
    
    throw lastError;
}

// Error message display function
function showErrorMessage(message, duration = 5000) {
    // Remove existing error messages
    const existingErrors = document.querySelectorAll('.error-message');
    existingErrors.forEach(error => error.remove());
    
    // Create error message element
    const errorElement = document.createElement('div');
    errorElement.className = 'error-message';
    errorElement.textContent = message;
    errorElement.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background-color: var(--error-color);
        color: white;
        padding: 1rem;
        border-radius: 4px;
        z-index: 10000;
        max-width: 400px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    `;
    
    document.body.appendChild(errorElement);
    
    // Auto-remove after duration
    setTimeout(() => {
        if (errorElement.parentNode) {
            errorElement.parentNode.removeChild(errorElement);
        }
    }, duration);
}

// Modal error display function
function showModalError(message) {
    const modalError = document.getElementById('modalError');
    if (modalError) {
        modalError.textContent = message;
        modalError.classList.remove('hidden');
        modalError.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

// Clear modal error function
function clearModalError() {
    const modalError = document.getElementById('modalError');
    if (modalError) {
        modalError.classList.add('hidden');
        modalError.textContent = '';
    }
}

// Success message display function
function showSuccessMessage(message, duration = 3000) {
    // Remove existing success messages
    const existingSuccess = document.querySelectorAll('.success-message');
    existingSuccess.forEach(success => success.remove());
    
    // Create success message element
    const successElement = document.createElement('div');
    successElement.className = 'success-message';
    successElement.textContent = message;
    successElement.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background-color: var(--success-color);
        color: black;
        padding: 1rem;
        border-radius: 4px;
        z-index: 10000;
        max-width: 400px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    `;
    
    document.body.appendChild(successElement);
    
    // Auto-remove after duration
    setTimeout(() => {
        if (successElement.parentNode) {
            successElement.parentNode.removeChild(successElement);
        }
    }, duration);
}

function processNextEntity() {
    console.log('processNextEntity called - currentEntityIndex:', currentEntityIndex, 'nullEntities.length:', nullEntities.length);
    
    // Safety check for empty entities array
    if (!nullEntities || nullEntities.length === 0) {
        console.log('No entities to process, showing completion');
        showMappingComplete();
        return;
    }
    
    // Safety check for invalid index
    if (currentEntityIndex < 0) {
        console.log('Invalid entity index, resetting to 0');
        currentEntityIndex = 0;
    }
    
    if (currentEntityIndex >= nullEntities.length) {
        // All entities processed
        console.log('All entities processed, showing completion');
        showMappingComplete();
        return;
    }
    
    const entity = nullEntities[currentEntityIndex];
    console.log('Processing entity:', entity.entity_id);
    
    // Update progress with proper ARIA attributes
    updateProgressBar();
    
    // Show entity form
    if (currentEntityId) currentEntityId.textContent = entity.entity_id;
    if (currentEntityName) currentEntityName.textContent = entity.current_name || 'NULL';
    if (friendlyNameInput) {
        friendlyNameInput.value = entity.suggested_name || '';
        // Clear any validation errors
        friendlyNameInput.classList.remove('error');
    }
    
    // Generate suggestions
    generateSuggestions(entity.entity_id);
    
    // Update modal state
    setModalState(ModalState.FORM);
}

// Function to update progress bar with ARIA attributes
function updateProgressBar() {
    const progressFill = document.getElementById('mappingProgressFill');
    const progressBar = document.querySelector('.progress-bar');
    
    if (progressFill && progressBar) {
        // Prevent division by zero
        if (nullEntities.length === 0) {
            progressFill.style.width = '100%';
            progressBar.setAttribute('aria-valuenow', 100);
            progressBar.setAttribute('aria-valuetext', 'No entities to process');
            return;
        }
        
        const progress = ((currentEntityIndex + 1) / nullEntities.length) * 100;
        progressFill.style.width = `${progress}%`;
        
        // Update ARIA attributes
        progressBar.setAttribute('aria-valuenow', Math.round(progress));
        progressBar.setAttribute('aria-valuetext', `${currentEntityIndex + 1} of ${nullEntities.length} entities processed`);
    }
}

function generateSuggestions(entityId) {
    if (!nameSuggestions) return;
    
    const suggestions = [];
    
    // Parse entity ID for suggestions
    const parts = entityId.split('.');
    if (parts.length >= 2) {
        const deviceName = parts[1].replace(/_/g, ' ');
        suggestions.push(deviceName);
        
        // Add domain-specific suggestions
        const domain = parts[0];
        if (domain === 'light') {
            suggestions.push(`${deviceName} lights`);
            suggestions.push(`${deviceName} light`);
        } else if (domain === 'switch') {
            suggestions.push(`${deviceName} switch`);
        } else if (domain === 'input_button') {
            if (deviceName.includes('scene')) {
                suggestions.push(deviceName.replace('scene', '').trim());
                suggestions.push(`${deviceName} scene`);
            }
        }
    }
    
    // Remove duplicates and show suggestions
    const uniqueSuggestions = [...new Set(suggestions)];
    nameSuggestions.innerHTML = '';
    
    uniqueSuggestions.forEach((suggestion, index) => {
        const chip = document.createElement('div');
        chip.className = 'suggestion-chip';
        chip.textContent = suggestion;
        chip.setAttribute('role', 'option');
        chip.setAttribute('tabindex', '0');
        chip.setAttribute('aria-selected', 'false');
        
        // Click handler
        chip.addEventListener('click', () => {
            selectSuggestion(suggestion);
        });
        
        // Keyboard navigation
        chip.addEventListener('keydown', (e) => {
            switch (e.key) {
                case 'Enter':
                case ' ':
                    e.preventDefault();
                    selectSuggestion(suggestion);
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    const nextChip = chip.nextElementSibling;
                    if (nextChip) {
                        nextChip.focus();
                    }
                    break;
                case 'ArrowLeft':
                    e.preventDefault();
                    const prevChip = chip.previousElementSibling;
                    if (prevChip) {
                        prevChip.focus();
                    }
                    break;
            }
        });
        
        // Focus/blur handlers for ARIA
        chip.addEventListener('focus', () => {
            chip.setAttribute('aria-selected', 'true');
        });
        
        chip.addEventListener('blur', () => {
            chip.setAttribute('aria-selected', 'false');
        });
        
        nameSuggestions.appendChild(chip);
    });
}

// Function to select a suggestion
function selectSuggestion(suggestion) {
    if (friendlyNameInput) {
        friendlyNameInput.value = suggestion;
        friendlyNameInput.focus();
        // Clear any validation errors
        friendlyNameInput.classList.remove('error');
        clearModalError();
    }
}

async function saveEntityMappingHandler() {
    if (isProcessing) {
        console.warn('Already processing, ignoring save request');
        return;
    }
    
    const entity = nullEntities[currentEntityIndex];
    const friendlyName = friendlyNameInput ? friendlyNameInput.value.trim() : '';
    
    // Clear any previous errors
    clearModalError();
    
    // Client-side validation
    if (!friendlyName) {
        showModalError('Please enter a friendly name');
        if (friendlyNameInput) {
            friendlyNameInput.classList.add('error');
            friendlyNameInput.focus();
        }
        return;
    }
    
    if (friendlyName.length < 2) {
        showModalError('Friendly name must be at least 2 characters long');
        if (friendlyNameInput) {
            friendlyNameInput.classList.add('error');
            friendlyNameInput.focus();
        }
        return;
    }
    
    isProcessing = true;
    
    try {
        const response = await fetchWithRetry('/v1/homeassistant/mapping/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                entity_id: entity.entity_id,
                friendly_name: friendlyName
            })
        });
        
        if (response.ok) {
            mappingResults.saved++;
            showSuccessMessage(`Saved mapping for ${entity.entity_id}`);
        } else {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Failed to save mapping');
        }
        
        // Move to next entity
        currentEntityIndex++;
        setModalState(ModalState.LOADING);
        processNextEntity();
        
    } catch (error) {
        console.error('Error saving mapping:', error);
        showModalError(`Error saving mapping: ${error.message}. Please try again.`);
    } finally {
        isProcessing = false;
    }
}

function skipEntityHandler() {
    if (isProcessing) {
        console.warn('Already processing, ignoring skip request');
        return;
    }
    
    mappingResults.skipped++;
    currentEntityIndex++;
    setModalState(ModalState.LOADING);
    processNextEntity();
}

function showMappingComplete() {
    setModalState(ModalState.COMPLETE);
    
    if (mappingSummary) {
        mappingSummary.innerHTML = `
            <h4>Mapping Complete</h4>
            <p><strong>Total entities processed:</strong> ${mappingResults.total}</p>
            <p><strong>Mappings saved:</strong> ${mappingResults.saved}</p>
            <p><strong>Entities skipped:</strong> ${mappingResults.skipped}</p>
        `;
    }
    
    // Show success message
    showSuccessMessage(`Mapping complete! Saved ${mappingResults.saved} mappings.`);
}

// Auto-discovery handler - Improved error handling
async function runAutoDiscoveryHandler() {
    if (isProcessing) {
        console.warn('Already processing, ignoring auto-discovery request');
        return;
    }
    
    isProcessing = true;
    
    try {
        const response = await fetchWithRetry('/v1/homeassistant/mapping/auto-discover', {
            method: 'POST'
        });
        
        if (response.ok) {
            const data = await response.json();
            showSuccessMessage(`Auto-discovery completed! Total mappings: ${data.total_mappings}, Entities with names: ${data.entities_with_friendly_names}`);
            updateHAStatus();
        } else {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Auto-discovery failed');
        }
    } catch (error) {
        console.error('Error running auto-discovery:', error);
        showErrorMessage(`Error running auto-discovery: ${error.message}`);
    } finally {
        isProcessing = false;
    }
}

// Update grammar handler - Improved error handling with force option
async function updateGrammarHandler(force = false) {
    if (isProcessing) {
        console.warn('Already processing, ignoring grammar update request');
        return;
    }
    
    isProcessing = true;
    
    try {
        const url = force ? '/v1/homeassistant/grammar/update?force=true' : '/v1/homeassistant/grammar/update';
        const response = await fetchWithRetry(url, {
            method: 'POST'
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.status === 'skipped') {
                showSuccessMessage(`Grammar update skipped: ${data.message}`);
            } else {
                const validationStatus = data.validation?.status || 'unknown';
                const validationMessage = data.validation?.message || '';
                showSuccessMessage(`Grammar updated successfully! Devices: ${data.grammar_stats?.device_count || 'N/A'}, Actions: ${data.grammar_stats?.action_count || 'N/A'}, Locations: ${data.grammar_stats?.location_count || 'N/A'}. Validation: ${validationStatus} - ${validationMessage}`);
            }
            updateHAStatus();
        } else {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Grammar update failed');
        }
    } catch (error) {
        console.error('Error updating grammar:', error);
        showErrorMessage(`Error updating grammar: ${error.message}`);
    } finally {
        isProcessing = false;
    }
}

// Force update grammar handler
async function forceUpdateGrammarHandler() {
    await updateGrammarHandler(true);
}

// Event listeners
console.log('Setting up event listeners...');
console.log('checkNullMappings element:', checkNullMappings);

checkNullMappings.addEventListener('click', (e) => {
    console.log('Check Null Mappings button clicked!');
    checkNullMappingsHandler();
});

runAutoDiscovery.addEventListener('click', runAutoDiscoveryHandler);
updateGrammar.addEventListener('click', () => updateGrammarHandler(false));
forceUpdateGrammar.addEventListener('click', forceUpdateGrammarHandler);
refreshHAStatus.addEventListener('click', updateHAStatus);
saveEntityMapping.addEventListener('click', saveEntityMappingHandler);
skipEntity.addEventListener('click', skipEntityHandler);

// Enter key in friendly name input
friendlyNameInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        saveEntityMappingHandler();
    }
});

// Real-time validation for friendly name input
friendlyNameInput.addEventListener('input', (e) => {
    const value = e.target.value.trim();
    
    // Clear error state if input becomes valid
    if (value.length >= 2) {
        e.target.classList.remove('error');
        clearModalError();
    }
});

// Initialize Home Assistant status
updateHAStatus();

// Utility function to inspect modal state
function inspectModalState() {
    console.log('=== Modal State Inspection ===');
    console.log('Modal element:', entityMappingModal);
    console.log('Modal state variable:', modalState);
    console.log('Modal classes:', entityMappingModal.classList.toString());
    console.log('Modal has hidden class:', entityMappingModal.classList.contains('hidden'));
    console.log('Modal computed display:', window.getComputedStyle(entityMappingModal).display);
    console.log('Modal computed visibility:', window.getComputedStyle(entityMappingModal).visibility);
    console.log('Modal computed opacity:', window.getComputedStyle(entityMappingModal).opacity);
    console.log('Modal computed z-index:', window.getComputedStyle(entityMappingModal).zIndex);
    console.log('Modal offsetParent:', entityMappingModal.offsetParent);
    console.log('Modal offsetWidth:', entityMappingModal.offsetWidth);
    console.log('Modal offsetHeight:', entityMappingModal.offsetHeight);
    console.log('Modal clientWidth:', entityMappingModal.clientWidth);
    console.log('Modal clientHeight:', entityMappingModal.clientHeight);
    console.log('Modal getBoundingClientRect:', entityMappingModal.getBoundingClientRect());
    console.log('=== End Modal State Inspection ===');
}

// Make inspection function globally available for debugging
window.inspectModalState = inspectModalState;
window.inspectModal = inspectModalState; // Alias for convenience 