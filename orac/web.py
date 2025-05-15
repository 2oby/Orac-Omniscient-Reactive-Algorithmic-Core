"""
orac.web
--------
Web interface and API for ORAC.

Provides both the HTML interface and API endpoints in a single server.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from orac.logger import get_logger
from orac.favorites import add_favorite, remove_favorite, is_favorite
from orac.models import ModelListResponse, ModelInfo
from orac.api.routes.models import router as models_router
from orac.api.routes.generate import router as generate_router
from orac.client import client
from orac.middleware import PromptLoggingMiddleware

# Get logger for this module
logger = get_logger(__name__)

# Create FastAPI application
app = FastAPI(
    title="ORAC Web Interface",
    description="Web interface and API for ORAC LLM service",
    version="0.1.0"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(PromptLoggingMiddleware)

# Include the API routers
app.include_router(models_router, prefix="/api/v1")
app.include_router(generate_router, prefix="/api/v1")

@app.get("/api/v1/models", response_model=ModelListResponse)
async def list_models() -> ModelListResponse:
    """List available models."""
    try:
        models = client.list_models()
        # Add favorite status to each model
        models_with_favorites = [
            {**m, "is_favorite": is_favorite(m["name"])} 
            for m in models
        ]
        # Sort models: favorites first, then by name
        sorted_models = sorted(
            models_with_favorites,
            key=lambda x: (not x["is_favorite"], x["name"])
        )
        return {"models": [ModelInfo(**m) for m in sorted_models]}
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/models/{model_name}/favorite")
async def favorite_model(model_name: str):
    """Add a model to favorites."""
    try:
        if add_favorite(model_name):
            return {"status": "success", "message": f"Added {model_name} to favorites"}
        return {"status": "info", "message": f"{model_name} was already in favorites"}
    except Exception as e:
        logger.error(f"Error adding favorite: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/models/{model_name}/favorite")
async def unfavorite_model(model_name: str):
    """Remove a model from favorites."""
    try:
        if remove_favorite(model_name):
            return {"status": "success", "message": f"Removed {model_name} from favorites"}
        return {"status": "info", "message": f"{model_name} was not in favorites"}
    except Exception as e:
        logger.error(f"Error removing favorite: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def web_interface(request: Request):
    """Serve the web interface."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ORAC Web Interface</title>
        <style>
            body { font-family: sans-serif; max-width: 800px; margin: 20px auto; padding: 0 20px; }
            .container { display: flex; flex-direction: column; gap: 20px; }
            .form-group { display: flex; flex-direction: column; gap: 5px; }
            label { font-weight: bold; }
            select, textarea { padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
            textarea { min-height: 100px; }
            button { 
                padding: 10px 20px; 
                background: #0066cc; 
                color: white; 
                border: none; 
                border-radius: 4px; 
                cursor: pointer; 
            }
            button:disabled { background: #ccc; }
            #response { 
                white-space: pre-wrap; 
                background: #f5f5f5; 
                padding: 15px; 
                border-radius: 4px; 
                margin-top: 10px; 
            }
            #stats { 
                font-family: monospace; 
                background: #f0f0f0; 
                padding: 10px; 
                border-radius: 4px; 
                margin-top: 10px; 
            }
            .error { color: red; }
            .model-selector {
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 20px;
            }
            .star-button {
                background: none;
                border: none;
                cursor: pointer;
                font-size: 24px;
                color: #ccc;
                transition: color 0.2s;
                padding: 0;
                display: inline-flex;
                align-items: center;
            }
            .star-button.favorite {
                color: gold;
            }
            .star-button:hover {
                color: gold;
            }
            .model-list {
                margin-top: 20px;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
            }
            .model-item {
                padding: 8px;
                border-bottom: 1px solid #eee;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .model-item:last-child {
                border-bottom: none;
            }
            .model-size {
                color: #666;
                font-size: 0.9em;
            }
            .favorite-model {
                background-color: #fff8e1;
            }
            .config-panel {
                display: none;
                margin-top: 20px;
                padding: 15px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background: #f9f9f9;
            }
            
            .config-panel.active {
                display: block;
            }
            
            .config-form {
                display: grid;
                gap: 10px;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            }
            
            .config-group {
                display: flex;
                flex-direction: column;
                gap: 5px;
            }
            
            .config-group label {
                font-weight: bold;
                color: #333;
            }
            
            .config-group input,
            .config-group select,
            .config-group textarea {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 14px;
            }
            
            .config-group textarea {
                min-height: 100px;
                resize: vertical;
            }
            
            .capability-tags {
                display: flex;
                flex-wrap: wrap;
                gap: 5px;
                margin-top: 5px;
            }
            
            .capability-tag {
                background: #e3f2fd;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 12px;
                color: #1976d2;
            }
            
            .config-actions {
                display: flex;
                gap: 10px;
                margin-top: 15px;
            }
            
            .config-actions button {
                flex: 1;
            }
            
            .config-actions button.secondary {
                background: #757575;
            }
            
            .config-actions button.danger {
                background: #d32f2f;
            }

            .system-prompt-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 5px;
            }

            .system-prompt-actions {
                display: flex;
                align-items: center;
                gap: 10px;
            }

            .system-prompt-source {
                font-size: 0.9em;
                color: #666;
                padding: 2px 8px;
                background: #f0f0f0;
                border-radius: 12px;
            }

            .system-prompt-info {
                font-size: 0.9em;
                color: #666;
                margin-top: 5px;
            }

            .system-prompt-source.user {
                background: #e3f2fd;
                color: #1976d2;
            }

            .system-prompt-source.model {
                background: #f3e5f5;
                color: #7b1fa2;
            }

            .system-prompt-source.default {
                background: #f1f8e9;
                color: #689f38;
            }

            .generation-controls {
                display: flex;
                align-items: flex-end;
                gap: 15px;
                margin: 20px 0;
            }

            .generation-controls .input-group {
                flex: 1;
                max-width: 200px;
            }

            .generation-controls button {
                flex: 0 0 auto;
                min-width: 120px;
            }

            .generation-controls input[type="number"] {
                width: 100%;
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 14px;
            }

            .generation-controls label {
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
                color: #333;
            }
        </style>
    </head>
    <body>
        <h1>ORAC Web Interface</h1>
        <div class="container">
            <div class="model-selector">
                <select id="modelSelect" onchange="updateStarButton(); loadModelConfig();">
                    <option value="">Select a model...</option>
                </select>
                <button id="starButton" class="star-button" onclick="toggleFavorite()" style="display:none">★</button>
                <button id="configButton" class="button" onclick="toggleConfigPanel()" style="display:none">⚙️</button>
            </div>
            
            <div class="config-panel" id="configPanel">
                <h3>Model Configuration</h3>
                <form id="configForm" class="config-form" onsubmit="saveModelConfig(event)">
                    <div class="config-group">
                        <label for="modelType">Model Type:</label>
                        <select id="modelType" name="type" required>
                            <option value="chat">Chat</option>
                            <option value="completion">Completion</option>
                        </select>
                    </div>
                    
                    <div class="config-group">
                        <label for="systemPrompt">System Prompt:</label>
                        <textarea id="systemPrompt" name="system_prompt" rows="3"></textarea>
                    </div>
                    
                    <div class="config-group">
                        <label>Capabilities:</label>
                        <div class="capability-tags" id="capabilityTags">
                            <!-- Capability tags will be added here -->
                        </div>
                    </div>
                    
                    <div class="config-group">
                        <label for="temperature">Temperature:</label>
                        <input type="number" id="temperature" name="settings.temperature" 
                               min="0" max="2" step="0.1" required>
                    </div>
                    
                    <div class="config-group">
                        <label for="maxTokens">Max Tokens:</label>
                        <input type="number" id="maxTokens" name="settings.max_tokens" 
                               min="1" required>
                    </div>
                    
                    <div class="config-group">
                        <label for="topP">Top P:</label>
                        <input type="number" id="topP" name="settings.top_p" 
                               min="0" max="1" step="0.01" required>
                    </div>
                    
                    <div class="config-group">
                        <label for="repeatPenalty">Repeat Penalty:</label>
                        <input type="number" id="repeatPenalty" name="settings.repeat_penalty" 
                               min="0" step="0.1" required>
                    </div>
                    
                    <div class="config-group">
                        <label for="topK">Top K:</label>
                        <input type="number" id="topK" name="settings.top_k" 
                               min="1" required>
                    </div>
                    
                    <div class="config-group">
                        <label for="notes">Notes:</label>
                        <textarea id="notes" name="notes" rows="2"></textarea>
                    </div>
                    
                    <div class="config-actions">
                        <button type="submit">Save Configuration</button>
                        <button type="button" class="secondary" onclick="resetConfig()">Reset</button>
                        <button type="button" class="danger" onclick="deleteConfig()">Delete</button>
                    </div>
                </form>
            </div>
            
            <div class="input-group">
                <label for="promptInput">Prompt:</label>
                <textarea id="promptInput" rows="4" placeholder="Enter your prompt here..."></textarea>
            </div>

            <div id="systemPromptContainer" class="input-group" style="display: none;">
                <div class="system-prompt-header">
                    <label for="systemPromptInput">System Prompt:</label>
                    <div class="system-prompt-actions">
                        <button type="button" class="secondary" onclick="resetSystemPrompt()" id="resetSystemPromptBtn" style="display: none;">
                            Reset to Model Config
                        </button>
                        <span class="system-prompt-source" id="systemPromptSource"></span>
                    </div>
                </div>
                <textarea id="systemPromptInput" rows="3" placeholder="Enter system prompt (optional)"></textarea>
                <div class="system-prompt-info" id="systemPromptInfo"></div>
            </div>

            <div class="generation-controls">
                <div class="input-group">
                    <label for="generationTemperature">Temperature:</label>
                    <input type="number" id="generationTemperature" value="0.7" min="0" max="2" step="0.1">
                </div>
                
                <button onclick="generate()" id="generateBtn">Generate</button>
            </div>
            
            <div id="response" class="response"></div>
            
            <div id="stats"></div>
        </div>

        <script>
            // Format file size in human-readable format
            function formatSize(bytes) {
                const units = ['B', 'KB', 'MB', 'GB'];
                let size = bytes;
                let unitIndex = 0;
                while (size >= 1024 && unitIndex < units.length - 1) {
                    size /= 1024;
                    unitIndex++;
                }
                return `${size.toFixed(1)} ${units[unitIndex]}`;
            }

            // Load available models
            async function loadModels() {
                try {
                    console.log('Fetching models...');
                    const response = await fetch('/api/v1/models');
                    console.log('Response status:', response.status);
                    const data = await response.json();
                    console.log('Models data:', data);
                    
                    if (!data.models) {
                        throw new Error('Invalid response format: missing models array');
                    }
                    
                    // Store models data for later use
                    window.modelsData = data.models;
                    
                    // Clear existing options
                    const select = document.getElementById('modelSelect');
                    select.innerHTML = '<option value="">Select a model...</option>';
                    
                    // Sort models: favorites first, then by name
                    const sortedModels = data.models.sort((a, b) => {
                        if (a.is_favorite && !b.is_favorite) return -1;
                        if (!a.is_favorite && b.is_favorite) return 1;
                        return a.name.localeCompare(b.name);
                    });
                    
                    // Add models to dropdown only
                    sortedModels.forEach(model => {
                        const option = document.createElement('option');
                        option.value = model.name;
                        option.textContent = model.name;
                        select.appendChild(option);
                    });
                    
                    // Update star button for currently selected model
                    updateStarButton();
                    
                } catch (error) {
                    console.error('Error loading models:', error);
                    alert(`Failed to load models: ${error.message}`);
                }
            }
            
            function updateStarButton() {
                const select = document.getElementById('modelSelect');
                const starButton = document.getElementById('starButton');
                const selectedModel = select.value;
                
                if (selectedModel) {
                    starButton.style.display = 'inline-block';
                    // Find the model in the stored models data
                    const modelData = window.modelsData.find(m => m.name === selectedModel);
                    if (modelData) {
                        starButton.className = `star-button ${modelData.is_favorite ? 'favorite' : ''}`;
                    }
                } else {
                    starButton.style.display = 'none';
                }
            }
            
            async function toggleFavorite() {
                const select = document.getElementById('modelSelect');
                const modelName = select.value;
                if (!modelName) return;
                
                const starButton = document.getElementById('starButton');
                const isFavorite = starButton.classList.contains('favorite');
                
                try {
                    const method = isFavorite ? 'DELETE' : 'POST';
                    console.log(`Sending ${method} request to toggle favorite for ${modelName}`);
                    const response = await fetch(`/api/v1/models/${encodeURIComponent(modelName)}/favorite`, {
                        method: method,
                        headers: {
                            'Accept': 'application/json'
                        }
                    });
                    
                    console.log('Response status:', response.status);
                    console.log('Response headers:', Object.fromEntries(response.headers.entries()));
                    
                    if (response.ok) {
                        const contentType = response.headers.get('content-type');
                        console.log('Response content type:', contentType);
                        
                        let data;
                        if (contentType && contentType.includes('application/json')) {
                            data = await response.json();
                            console.log('Parsed JSON response:', data);
                        } else {
                            data = { status: 'success' };
                            console.log('No JSON content, using default success response');
                        }
                        
                        // Update star button and model list
                        starButton.classList.toggle('favorite');
                        await loadModels();  // Reload to update the list
                    } else {
                        console.log('Error response received');
                        const errorText = await response.text();
                        console.log('Error response text:', errorText);
                        let error;
                        try {
                            error = JSON.parse(errorText);
                        } catch (e) {
                            error = { detail: `Failed to ${isFavorite ? 'remove' : 'add'} favorite` };
                        }
                        throw new Error(error.detail || `Failed to ${isFavorite ? 'remove' : 'add'} favorite`);
                    }
                } catch (error) {
                    console.error('Error toggling favorite:', error);
                    alert(`Failed to ${isFavorite ? 'remove' : 'add'} favorite: ${error.message}`);
                }
            }

            // Generate text
            async function generate() {
                const model = document.getElementById('modelSelect').value;
                const systemPrompt = document.getElementById('systemPromptInput').value;
                const userPrompt = document.getElementById('promptInput').value;
                const generateBtn = document.getElementById('generateBtn');
                const responseDiv = document.getElementById('response');
                const statsDiv = document.getElementById('stats');
                
                if (!userPrompt.trim()) {
                    responseDiv.innerHTML = '<span class="error">Please enter a prompt</span>';
                    return;
                }

                generateBtn.disabled = true;
                responseDiv.textContent = 'Generating...';
                statsDiv.textContent = '';
                
                try {
                    const startTime = performance.now();
                    const response = await fetch('/api/v1/generate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            model: model,
                            prompt: userPrompt,
                            system_prompt: systemPrompt,
                            temperature: parseFloat(document.getElementById('generationTemperature').value),
                            max_tokens: 512,
                            top_p: 0.95,
                            stop: null
                        })
                    });
                    
                    const data = await response.json();
                    const endTime = performance.now();
                    
                    if (response.ok) {
                        // Update response text
                        responseDiv.textContent = data.text;
                        
                        // Update system prompt UI based on response
                        updateSystemPromptUI(
                            systemPrompt,
                            data.prompt_state.source === 'user_input' ? 'user' :
                            data.prompt_state.source === 'model_config' ? 'model' :
                            'default'
                        );
                        
                        // Update stats with more detailed information
                        const stats = [
                            `Generation time: ${(data.timing.generation_time * 1000).toFixed(0)}ms`,
                            `Total request time: ${(data.timing.total_time * 1000).toFixed(0)}ms`,
                            `Model: ${data.model}`,
                            `System prompt: ${data.prompt_state.source}`
                        ].join('\n');
                        
                        statsDiv.textContent = stats;
                    } else {
                        responseDiv.innerHTML = `<span class="error">Error: ${data.detail || 'Unknown error'}</span>`;
                    }
                } catch (e) {
                    responseDiv.innerHTML = `<span class="error">Error: ${e.message}</span>`;
                } finally {
                    generateBtn.disabled = false;
                }
            }

            // Model configuration management
            const capabilityOptions = [
                'system_prompt', 'chat_history', 'instruction_following',
                'creative_writing', 'complex_reasoning', 'text_completion'
            ];
            
            function toggleConfigPanel() {
                const panel = document.getElementById('configPanel');
                panel.classList.toggle('active');
            }
            
            function updateCapabilityTags(capabilities) {
                const container = document.getElementById('capabilityTags');
                container.innerHTML = '';
                capabilities.forEach(cap => {
                    const tag = document.createElement('span');
                    tag.className = 'capability-tag';
                    tag.textContent = cap;
                    container.appendChild(tag);
                });
            }
            
            async function loadModelConfig() {
                const modelName = document.getElementById('modelSelect').value;
                if (!modelName) {
                    document.getElementById('configPanel').classList.remove('active');
                    document.getElementById('systemPromptContainer').style.display = 'none';
                    return;
                }
                
                try {
                    // Remove .gguf extension if present
                    const normalizedName = modelName.replace('.gguf', '');
                    const response = await fetch(`/api/v1/models/${encodeURIComponent(normalizedName)}/config`);
                    if (response.ok) {
                        const config = await response.json();
                        populateConfigForm(config);
                        
                        // Show/hide system prompt based on model type
                        const systemPromptContainer = document.getElementById('systemPromptContainer');
                        const shouldShowSystemPrompt = config.type === 'chat' || 
                            (config.capabilities && config.capabilities.includes('system_prompt'));
                        systemPromptContainer.style.display = shouldShowSystemPrompt ? 'block' : 'none';
                        
                        // Store model config system prompt for reset functionality
                        if (shouldShowSystemPrompt) {
                            window.modelConfigSystemPrompt = config.system_prompt;
                            updateSystemPromptUI(config.system_prompt, 'model');
                        }
                    } else if (response.status === 404) {
                        // No config exists, show empty form
                        resetConfig();
                        document.getElementById('systemPromptContainer').style.display = 'none';
                    } else {
                        throw new Error('Failed to load configuration');
                    }
                } catch (error) {
                    console.error('Error loading model config:', error);
                    alert('Failed to load model configuration');
                }
            }
            
            function populateConfigForm(config) {
                document.getElementById('modelType').value = config.type;
                document.getElementById('systemPrompt').value = config.system_prompt || '';
                document.getElementById('temperature').value = config.settings.temperature;
                document.getElementById('maxTokens').value = config.settings.max_tokens;
                document.getElementById('topP').value = config.settings.top_p;
                document.getElementById('repeatPenalty').value = config.settings.repeat_penalty;
                document.getElementById('topK').value = config.settings.top_k;
                document.getElementById('notes').value = config.notes || '';
                updateCapabilityTags(config.capabilities);
            }
            
            function resetConfig() {
                const modelName = document.getElementById('modelSelect').value;
                if (!modelName) return;
                
                // Reset to default values
                document.getElementById('modelType').value = 'chat';
                document.getElementById('systemPrompt').value = 
                    'You are a helpful AI assistant. Provide accurate and concise responses.';
                document.getElementById('temperature').value = '0.7';
                document.getElementById('maxTokens').value = '2048';
                document.getElementById('topP').value = '0.95';
                document.getElementById('repeatPenalty').value = '1.1';
                document.getElementById('topK').value = '40';
                document.getElementById('notes').value = '';
                updateCapabilityTags(['system_prompt', 'chat_history', 'instruction_following']);
            }
            
            async function saveModelConfig(event) {
                event.preventDefault();
                const modelName = document.getElementById('modelSelect').value;
                if (!modelName) return;
                
                const formData = new FormData(event.target);
                const config = {
                    type: formData.get('type'),
                    system_prompt: formData.get('system_prompt'),
                    capabilities: Array.from(document.querySelectorAll('.capability-tag'))
                        .map(tag => tag.textContent),
                    settings: {
                        temperature: parseFloat(formData.get('settings.temperature')),
                        max_tokens: parseInt(formData.get('settings.max_tokens')),
                        top_p: parseFloat(formData.get('settings.top_p')),
                        repeat_penalty: parseFloat(formData.get('settings.repeat_penalty')),
                        top_k: parseInt(formData.get('settings.top_k'))
                    },
                    notes: formData.get('notes')
                };
                
                try {
                    // Remove .gguf extension if present
                    const normalizedName = modelName.replace('.gguf', '');
                    const response = await fetch(
                        `/api/v1/models/${encodeURIComponent(normalizedName)}/config`,
                        {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(config)
                        }
                    );
                    
                    if (response.ok) {
                        alert('Configuration saved successfully');
                    } else {
                        const errorData = await response.json();
                        throw new Error(errorData.detail || 'Failed to save configuration');
                    }
                } catch (error) {
                    console.error('Error saving model config:', error);
                    alert(`Failed to save model configuration: ${error.message}`);
                }
            }
            
            async function deleteConfig() {
                const modelName = document.getElementById('modelSelect').value;
                if (!modelName || !confirm('Are you sure you want to delete this configuration?')) {
                    return;
                }
                
                try {
                    // Remove .gguf extension if present
                    const normalizedName = modelName.replace('.gguf', '');
                    const response = await fetch(
                        `/api/v1/models/${encodeURIComponent(normalizedName)}/config`,
                        { method: 'DELETE' }
                    );
                    
                    if (response.ok) {
                        alert('Configuration deleted successfully');
                        resetConfig();
                    } else {
                        const errorData = await response.json();
                        throw new Error(errorData.detail || 'Failed to delete configuration');
                    }
                } catch (error) {
                    console.error('Error deleting model config:', error);
                    alert(`Failed to delete model configuration: ${error.message}`);
                }
            }
            
            // Update model list to show config button
            function updateModelList() {
                const select = document.getElementById('modelSelect');
                const configButton = document.getElementById('configButton');
                configButton.style.display = select.value ? 'inline-block' : 'none';
            }
            
            // Add config button visibility to existing model selection handlers
            const originalUpdateStarButton = updateStarButton;
            updateStarButton = function() {
                originalUpdateStarButton();
                updateModelList();
            };

            // Load models when page loads
            loadModels();

            function updateSystemPromptUI(prompt, source) {
                const systemPromptInput = document.getElementById('systemPromptInput');
                const systemPromptSource = document.getElementById('systemPromptSource');
                const resetSystemPromptBtn = document.getElementById('resetSystemPromptBtn');
                const systemPromptInfo = document.getElementById('systemPromptInfo');
                
                // Update input value
                systemPromptInput.value = prompt || '';
                
                // Update source indicator
                systemPromptSource.textContent = source === 'user' ? 'User Input' :
                                               source === 'model' ? 'Model Config' :
                                               'Default';
                systemPromptSource.className = `system-prompt-source ${source}`;
                
                // Show/hide reset button
                resetSystemPromptBtn.style.display = 
                    source === 'user' && window.modelConfigSystemPrompt ? 'inline-block' : 'none';
                
                // Update info text
                systemPromptInfo.textContent = 
                    source === 'user' ? 'Using custom system prompt' :
                    source === 'model' ? 'Using model\'s default system prompt' :
                    'Using default system prompt';
            }

            function resetSystemPrompt() {
                if (window.modelConfigSystemPrompt) {
                    updateSystemPromptUI(window.modelConfigSystemPrompt, 'model');
                }
            }

            // Add system prompt input change handler
            document.getElementById('systemPromptInput').addEventListener('input', function(e) {
                if (e.target.value !== window.modelConfigSystemPrompt) {
                    updateSystemPromptUI(e.target.value, 'user');
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html) 