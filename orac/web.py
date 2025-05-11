"""
orac.web
--------
Simple web interface for ORAC.

Provides a minimal HTML interface for interacting with the ORAC API.
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from orac.logger import get_logger

# Get logger for this module
logger = get_logger(__name__)

# Create FastAPI application for web interface
app = FastAPI(
    title="ORAC Web Interface",
    description="Simple web interface for ORAC LLM service",
    version="0.1.0"
)

# Default system prompt
DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant running on a Jetson Orin Nano.
You aim to be concise, accurate, and helpful in your responses."""

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
        </style>
    </head>
    <body>
        <h1>ORAC Web Interface</h1>
        <div class="container">
            <div class="form-group">
                <label for="model">Model:</label>
                <select id="model"></select>
            </div>
            
            <div class="form-group">
                <label for="systemPrompt">System Prompt:</label>
                <textarea id="systemPrompt">""" + DEFAULT_SYSTEM_PROMPT + """</textarea>
            </div>
            
            <div class="form-group">
                <label for="userPrompt">User Prompt:</label>
                <textarea id="userPrompt" placeholder="Enter your prompt here..."></textarea>
            </div>
            
            <button onclick="generate()" id="generateBtn">Generate</button>
            
            <div id="stats"></div>
            <div id="response"></div>
        </div>

        <script>
            // Load available models
            async function loadModels() {
                try {
                    const response = await fetch('http://orac:8000/api/v1/models');
                    const data = await response.json();
                    const select = document.getElementById('model');
                    select.innerHTML = data.models.map(m => 
                        `<option value="${m.name}">${m.name}</option>`
                    ).join('');
                } catch (e) {
                    console.error('Error loading models:', e);
                    document.getElementById('response').innerHTML = 
                        `<span class="error">Error loading models: ${e.message}</span>`;
                }
            }

            // Generate text
            async function generate() {
                const model = document.getElementById('model').value;
                const systemPrompt = document.getElementById('systemPrompt').value;
                const userPrompt = document.getElementById('userPrompt').value;
                const generateBtn = document.getElementById('generateBtn');
                const responseDiv = document.getElementById('response');
                const statsDiv = document.getElementById('stats');
                
                if (!userPrompt.trim()) {
                    responseDiv.innerHTML = '<span class="error">Please enter a prompt</span>';
                    return;
                }

                // Combine prompts
                const fullPrompt = `${systemPrompt}\n\nUser: ${userPrompt}\n\nAssistant:`;
                
                generateBtn.disabled = true;
                responseDiv.textContent = 'Generating...';
                statsDiv.textContent = '';
                
                try {
                    const startTime = performance.now();
                    const response = await fetch('http://orac:8000/api/v1/generate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            model: model,
                            prompt: fullPrompt,
                            temperature: 0.7,
                            max_tokens: 512
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