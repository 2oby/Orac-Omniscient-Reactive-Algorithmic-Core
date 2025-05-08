#!/usr/bin/env python3
"""
Diagnostic script for ORAC model loading issues.
This script helps identify and troubleshoot problems with model loading.
"""

import asyncio
import os
import sys
from orac.model_loader import ModelLoader
import httpx

async def diagnose_model_loading(model_name):
    """Diagnose model loading issues."""
    print(f"Diagnosing model loading for: {model_name}")
    
    # Check environment variables
    print("\nEnvironment variables:")
    print(f"OLLAMA_HOST: {os.getenv('OLLAMA_HOST', 'not set')}")
    print(f"OLLAMA_PORT: {os.getenv('OLLAMA_PORT', 'not set')}")
    print(f"OLLAMA_MODEL_PATH: {os.getenv('OLLAMA_MODEL_PATH', 'not set')}")
    print(f"OLLAMA_MODELS: {os.getenv('OLLAMA_MODELS', 'not set')}")
    
    # Check if Ollama is running
    base_url = f"http://{os.getenv('OLLAMA_HOST', '127.0.0.1')}:{os.getenv('OLLAMA_PORT', '11434')}"
    print(f"\nChecking Ollama at: {base_url}")
    
    async with httpx.AsyncClient(base_url=base_url) as client:
        try:
            response = await client.get("/api/version")
            version = response.json().get("version", "unknown")
            print(f"Ollama version: {version}")
        except Exception as e:
            print(f"Failed to connect to Ollama: {str(e)}")
            return
        
        # Create model loader
        loader = ModelLoader(client)
        
        # Check model path
        model_path = loader.resolve_model_path(model_name)
        print(f"\nModel path resolution:")
        print(f"Resolved path: {model_path}")
        print(f"File exists: {os.path.exists(model_path)}")
        if os.path.exists(model_path):
            print(f"File size: {os.path.getsize(model_path)} bytes")
            print(f"File permissions: {oct(os.stat(model_path).st_mode)[-3:]}")
            
            # Check for Modelfile
            model_dir = os.path.dirname(model_path)
            modelfile_path = os.path.join(model_dir, "Modelfile")
            print(f"\nModelfile check:")
            print(f"Modelfile path: {modelfile_path}")
            print(f"Modelfile exists: {os.path.exists(modelfile_path)}")
            if os.path.exists(modelfile_path):
                print(f"Modelfile permissions: {oct(os.stat(modelfile_path).st_mode)[-3:]}")
                try:
                    with open(modelfile_path, 'r') as f:
                        print("\nModelfile contents:")
                        print(f.read())
                except Exception as e:
                    print(f"Failed to read Modelfile: {str(e)}")
        
        # Check existing models
        response = await client.get("/api/tags")
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"\nExisting models ({len(models)}):")
            for model in models:
                print(f"- {model.get('name')}")
        
        # Try loading the model
        print(f"\nAttempting to load model: {model_name}")
        try:
            result = await loader.load_model(model_name)
            print(f"Load result: {result}")
        except Exception as e:
            print(f"Load failed: {str(e)}")
        
        # Print error logs
        print("\nError logs:")
        for log in loader.get_error_logs():
            print(f"- {log}")

if __name__ == "__main__":
    model_name = sys.argv[1] if len(sys.argv) > 1 else "Qwen3-1.7B-Q4_K_M.gguf"
    asyncio.run(diagnose_model_loading(model_name)) 