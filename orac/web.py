"""
orac.web
--------
Web interface and API for ORAC.

Provides both the HTML interface and API endpoints in a single server.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from orac.logger import get_logger
from orac.favorites import add_favorite, remove_favorite, is_favorite
from orac.llama_cpp_client import LlamaCppClient
from orac.models import ModelListResponse, ModelInfo
import time

# Get logger for this module
logger = get_logger(__name__)

# Create FastAPI application
app = FastAPI(
    title="ORAC Web Interface",
    description="Web interface and API for ORAC LLM service",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the llama.cpp client
client = LlamaCppClient()

# Default system prompt
DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant running on a Jetson Orin Nano.
You aim to be concise, accurate, and helpful in your responses."""

class GenerateRequest(BaseModel):
    """Request model for text generation."""
    model: str
    prompt: str
    system_prompt: Optional[str] = DEFAULT_SYSTEM_PROMPT
    temperature: float = 0.7
    max_tokens: int = 200
    top_p: float = 0.95
    top_k: int = 40

class GenerateResponse(BaseModel):
    """Response model for text generation."""
    generated_text: str
    model: str
    elapsed_ms: float

@app.get("/api/v1/models", response_model=ModelListResponse)
async def list_models() -> ModelListResponse:
    """List available models."""
    try:
        models = await client.list_models()
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

@app.post("/api/v1/generate", response_model=GenerateResponse)
async def generate_text(request: GenerateRequest) -> GenerateResponse:
    """Generate text using the specified model."""
    try:
        logger.info(f"Generating text with model {request.model}")
        start_time = time.time()
        
        # Generate text
        response = await client.generate(
            model=request.model,
            prompt=request.prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            top_k=request.top_k
        )
        
        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(f"Generation completed in {elapsed_ms:.0f}ms")
        
        return GenerateResponse(
            generated_text=response.response,
            model=request.model,
            elapsed_ms=elapsed_ms
        )
    except Exception as e:
        logger.error(f"Error generating text: {str(e)}")
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
        </style>
    </head>
    <body>
        <h1>ORAC Web Interface</h1>
        <div class="container">
            <div class="model-selector">
                <select id="modelSelect" onchange="updateStarButton()">
                    <option value="">Select a model...</option>
                </select>
                <button id="starButton" class="star-button" onclick="toggleFavorite()" style="display:none">★</button>
            </div>
            
            <div class="model-list" id="modelList">
                <!-- Model list will be populated here -->
            </div>
            
            <div class="form-group">
                <label for="systemPrompt">System Prompt:</label>
                <textarea id="systemPrompt" rows="3"></textarea>
            </div>
            
            <div class="form-group">
                <label for="userPrompt">User Prompt:</label>
                <textarea id="userPrompt" rows="5"></textarea>
            </div>
            
            <button onclick="generate()" id="generateBtn">Generate</button>
            
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
                    
                    // Clear existing options
                    const select = document.getElementById('modelSelect');
                    select.innerHTML = '<option value="">Select a model...</option>';
                    
                    // Clear model list
                    const modelList = document.getElementById('modelList');
                    modelList.innerHTML = '';
                    
                    // Sort models: favorites first, then by name
                    const sortedModels = data.models.sort((a, b) => {
                        if (a.is_favorite && !b.is_favorite) return -1;
                        if (!a.is_favorite && b.is_favorite) return 1;
                        return a.name.localeCompare(b.name);
                    });
                    
                    // Add models to dropdown and list
                    sortedModels.forEach(model => {
                        // Add to dropdown
                        const option = document.createElement('option');
                        option.value = model.name;
                        option.textContent = model.name;
                        select.appendChild(option);
                        
                        // Add to list
                        const modelItem = document.createElement('div');
                        modelItem.className = `model-item ${model.is_favorite ? 'favorite-model' : ''}`;
                        modelItem.innerHTML = `
                            <span>${model.name}</span>
                            <span class="model-size">${formatSize(model.size)}</span>
                        `;
                        modelList.appendChild(modelItem);
                    });
                    
                    // Update star button for currently selected model
                    updateStarButton();
                    
                } catch (error) {
                    console.error('Error loading models:', error);
                    const modelList = document.getElementById('modelList');
                    modelList.innerHTML = `<div class="error">Failed to load models: ${error.message}</div>`;
                }
            }
            
            function updateStarButton() {
                const select = document.getElementById('modelSelect');
                const starButton = document.getElementById('starButton');
                const selectedModel = select.value;
                
                if (selectedModel) {
                    starButton.style.display = 'inline-block';
                    // Find the model in the list to check favorite status
                    const modelItem = Array.from(document.querySelectorAll('.model-item'))
                        .find(item => item.querySelector('span').textContent === selectedModel);
                    if (modelItem) {
                        starButton.className = `star-button ${modelItem.classList.contains('favorite-model') ? 'favorite' : ''}`;
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
                const systemPrompt = document.getElementById('systemPrompt').value;
                const userPrompt = document.getElementById('userPrompt').value;
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
                            temperature: 0.3,
                            max_tokens: 200,
                            top_p: 0.95,
                            top_k: 100
                        })
                    });
                    
                    const data = await response.json();
                    const endTime = performance.now();
                    
                    if (response.ok) {
                        responseDiv.textContent = data.generated_text;
                        statsDiv.textContent = 
                            `Generation time: ${data.elapsed_ms.toFixed(0)}ms\n` +
                            `Total request time: ${(endTime - startTime).toFixed(0)}ms\n` +
                            `Model: ${data.model}`;
                    } else {
                        responseDiv.innerHTML = `<span class="error">Error: ${data.detail || 'Unknown error'}</span>`;
                    }
                } catch (e) {
                    responseDiv.innerHTML = `<span class="error">Error: ${e.message}</span>`;
                } finally {
                    generateBtn.disabled = false;
                }
            }

            // Load models when page loads
            loadModels();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html) 