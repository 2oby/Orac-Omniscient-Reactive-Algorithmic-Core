"""
orac.ollama_client
------------------
Thin async wrapper around the local Ollama REST API.
"""

import json
import time
import os
from typing import List, Dict, Any, Optional
import httpx
from .models import ModelLoadResponse, ModelUnloadResponse, PromptResponse
import asyncio

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "127.0.0.1")
OLLAMA_PORT = os.getenv("OLLAMA_PORT", "11434")
OLLAMA_BASE_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"


async def list_models() -> List[Dict[str, Any]]:
    async with httpx.AsyncClient(base_url=OLLAMA_BASE_URL, timeout=30.0) as client:
        resp = await client.get("/api/tags")
        resp.raise_for_status()
        return resp.json().get("models", [])


async def generate(model: str, prompt: str) -> str:
    payload = {"model": model, "prompt": prompt, "stream": False}
    async with httpx.AsyncClient(base_url=OLLAMA_BASE_URL, timeout=120.0) as client:
        resp = await client.post("/api/generate", json=payload)
        resp.raise_for_status()
        return resp.json()["response"]


async def pull(model: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(base_url=OLLAMA_BASE_URL, timeout=None) as client:
        resp = await client.post("/api/pull", json={"name": model})
        resp.raise_for_status()
        return resp.json()


async def delete(model: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(base_url=OLLAMA_BASE_URL, timeout=30.0) as client:
        resp = await client.delete("/api/delete", json={"name": model})
        resp.raise_for_status()
        return resp.json()


async def show(model: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(base_url=OLLAMA_BASE_URL, timeout=30.0) as client:
        resp = await client.post("/api/show", json={"name": model})
        resp.raise_for_status()
        return resp.json()


class OllamaClient:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or OLLAMA_BASE_URL
        self.client = httpx.AsyncClient(base_url=self.base_url)

    async def get_version(self) -> str:
        """Get Ollama version."""
        try:
            response = await self.client.get("/api/version")
            response.raise_for_status()
            version_info = response.json()
            print(f"Ollama version info: {json.dumps(version_info, indent=2)}")
            return version_info.get("version", "unknown")
        except Exception as e:
            print(f"Failed to get Ollama version: {str(e)}")
            return "unknown"

    async def list_models(self) -> List[dict]:
        """List all available models."""
        response = await self.client.get("/api/tags")
        response.raise_for_status()
        return response.json()["models"]

    async def wait_for_model(self, model_name: str, max_retries: int = 30, delay: float = 2.0) -> bool:
        """Wait for a model to be ready."""
        for i in range(max_retries):
            try:
                # First check if the model exists
                response = await self.client.post("/api/show", json={"name": model_name})
                if response.status_code == 200:
                    print(f"Model {model_name} is ready!")
                    return True
                
                # If not found, check if it's still being created
                response = await self.client.get("/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    for model in models:
                        if model.get("name") == model_name:
                            print(f"Model {model_name} is ready!")
                            return True
                
                print(f"Model {model_name} not ready yet (attempt {i + 1}/{max_retries})")
            except httpx.HTTPStatusError as e:
                print(f"HTTP error checking model status: {str(e)}")
            except Exception as e:
                print(f"Error checking model status: {str(e)}")
            
            if i < max_retries - 1:
                await asyncio.sleep(delay)
            else:
                return False
        return False

    async def load_model(self, name: str, max_retries: int = 3) -> ModelLoadResponse:
        """Load a model by name."""
        # Get and print Ollama version at the start of model loading
        version = await self.get_version()
        print(f"\nAttempting to load model with Ollama version: {version}\n")
        
        retry_count = 0
        last_error = None

        while retry_count < max_retries:
            try:
                # Remove .gguf extension if present
                model_name = name.replace(".gguf", "")
                
                # For local GGUF files, use the create endpoint with local path
                if name.endswith(".gguf"):
                    # Try different path formats
                    path_formats = [
                        f"/models/gguf/{name}",  # Original absolute path
                        f"models/gguf/{name}",   # Relative path without leading slash
                        name,                    # Just the filename
                        f"./models/gguf/{name}"  # Path relative to current directory
                    ]
                    
                    for model_path in path_formats:
                        print(f"\nTrying model path: {model_path}")
                        
                        # Check if file exists and is readable
                        if not os.path.exists(model_path):
                            print(f"Path not found: {model_path}")
                            continue
                        if not os.access(model_path, os.R_OK):
                            print(f"Path not readable: {model_path}")
                            continue
                        
                        # Get file size
                        file_size = os.path.getsize(model_path)
                        print(f"Model file size: {file_size / (1024*1024):.2f} MB")
                        
                        # Debug: Print current working directory and model path
                        print(f"Current working directory: {os.getcwd()}")
                        print(f"Absolute model path: {os.path.abspath(model_path)}")
                        
                        # Try different API request formats
                        request_formats = [
                            # Format 1: Using 'from' parameter
                            {
                                "name": model_name,
                                "from": model_path
                            },
                            
                            # Format 2: Using 'files' parameter
                            {
                                "name": model_name,
                                "files": [model_path]
                            },
                            
                            # Format 3: Using both 'from' and modelfile
                            {
                                "name": model_name,
                                "from": model_path,
                                "modelfile": f"""FROM {model_path}
PARAMETER temperature 0.7
PARAMETER top_p 0.7
PARAMETER stop "</s>"
PARAMETER stop "<|endoftext|>" """
                            }
                        ]
                        
                        format_errors = []
                        for request_data in request_formats:
                            try:
                                print(f"\nTrying request format:\n{json.dumps(request_data, indent=2)}")
                                
                                # Create model using create endpoint
                                async with self.client.stream(
                                    "POST",
                                    "/api/create",
                                    json=request_data,
                                    timeout=120.0  # Increase timeout for large models
                                ) as response:
                                    try:
                                        response.raise_for_status()
                                    except httpx.HTTPStatusError as e:
                                        error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
                                        print(f"HTTP error: {error_msg}")
                                        format_errors.append(error_msg)
                                        continue

                                    create_complete = False
                                    error_message = None
                                    
                                    async for line in response.aiter_lines():
                                        if line:
                                            try:
                                                chunk = json.loads(line)
                                                print(f"Response chunk: {chunk}")  # Debug: Print response chunks
                                                if "error" in chunk:
                                                    error_message = chunk["error"]
                                                    break
                                                if chunk.get("status") == "success":
                                                    create_complete = True
                                                    break
                                                print(f"Loading progress: {chunk.get('status', 'unknown')}")
                                            except json.JSONDecodeError as e:
                                                print(f"Failed to parse loading response: {str(e)}")
                                    
                                    if error_message:
                                        format_errors.append(error_message)
                                        print(f"Error with current format: {error_message}")
                                        continue  # Try next format
                                    
                                    if create_complete:
                                        print(f"Model loading completed, waiting for model to be ready...")
                                        
                                        # Wait for the model to be ready
                                        if not await self.wait_for_model(model_name):
                                            raise Exception(f"Model {model_name} failed to load within timeout")
                                        return ModelLoadResponse(status="success")
                        
                            except httpx.TimeoutException:
                                error_msg = "Request timed out while loading model"
                                print(error_msg)
                                format_errors.append(error_msg)
                                continue
                            except Exception as e:
                                error_msg = f"Unexpected error: {str(e)}"
                                print(error_msg)
                                format_errors.append(error_msg)
                                continue
                        
                        # If we get here, all formats failed
                        last_error = f"All request formats failed. Errors: {', '.join(format_errors)}"
                        print(f"Attempt {retry_count + 1}/{max_retries} failed: {last_error}")
                        retry_count += 1
                        if retry_count < max_retries:
                            await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                            continue
                        raise Exception(last_error)
                else:
                    # For remote models, use the pull endpoint
                    print(f"Pulling remote model: {model_name}")
                    try:
                        response = await self.client.post(
                            "/api/pull", 
                            json={"name": model_name},
                            timeout=120.0
                        )
                        response.raise_for_status()
                        return ModelLoadResponse(status="success")
                    except httpx.HTTPStatusError as e:
                        if e.response.status_code == 404:
                            # For 404 errors, preserve the original error message
                            error_data = e.response.json()
                            if "error" in error_data:
                                raise Exception(error_data["error"])
                            raise Exception("Model not found")
                        raise Exception(f"Failed to pull remote model: {e.response.text}")
                    except httpx.TimeoutException:
                        raise Exception("Request timed out while pulling remote model")
            
            except FileNotFoundError as e:
                raise Exception(f"Model file error: {str(e)}")
            except PermissionError as e:
                raise Exception(f"Model file permission error: {str(e)}")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    # For 404 errors, preserve the original error message
                    error_data = e.response.json()
                    if "error" in error_data:
                        raise Exception(error_data["error"])
                    raise Exception("Model not found")
                raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}")
            except httpx.TimeoutException:
                last_error = "Request timed out"
                print(f"Attempt {retry_count + 1}/{max_retries} failed: {last_error}")
                retry_count += 1
                if retry_count < max_retries:
                    await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                    continue
                raise Exception(f"Failed to load model after {max_retries} attempts: {last_error}")
            except Exception as e:
                # If the error message already contains "Model not found", preserve it
                if "Model not found" in str(e):
                    raise e
                last_error = str(e)
                print(f"Attempt {retry_count + 1}/{max_retries} failed: {last_error}")
                retry_count += 1
                if retry_count < max_retries:
                    await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                    continue
                raise Exception(f"Failed to load model after {max_retries} attempts: {last_error}")
        
        raise Exception(f"Failed to load model after {max_retries} attempts. Last error: {last_error}")

    async def unload_model(self, name: str) -> ModelUnloadResponse:
        """Unload a model by name."""
        try:
            # Remove .gguf extension if present
            model_name = name.replace(".gguf", "")
            response = await self.client.delete(f"/api/delete", params={"name": model_name})
            response.raise_for_status()
            return ModelUnloadResponse(status="success")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise Exception("Model not loaded")
            raise Exception(f"Failed to unload model: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to unload model: {str(e)}")

    async def generate(
        self, 
        model: str, 
        prompt: str, 
        stream: bool = False
    ) -> PromptResponse:
        """Generate a response from the model."""
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        start_time = time.time()
        try:
            # Remove .gguf extension if present
            model_name = model.replace(".gguf", "")
            
            if stream:
                full_response = ""
                async with self.client.stream(
                    "POST",
                    "/api/generate",
                    json={"model": model_name, "prompt": prompt, "stream": True}
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                chunk = json.loads(line)
                                full_response += chunk.get("response", "")
                                if chunk.get("done", False):
                                    break
                            except json.JSONDecodeError as e:
                                raise Exception(f"Failed to parse streaming response: {str(e)}")
                
                elapsed_ms = (time.time() - start_time) * 1000
                return PromptResponse(response=full_response, elapsed_ms=elapsed_ms)
            else:
                response = await self.client.post(
                    "/api/generate",
                    json={"model": model_name, "prompt": prompt, "stream": False}
                )
                response.raise_for_status()
                result = response.json()
                elapsed_ms = (time.time() - start_time) * 1000
                return PromptResponse(response=result["response"], elapsed_ms=elapsed_ms)
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise Exception("Model not loaded")
            raise Exception(f"Generation failed: {str(e)}")
        except Exception as e:
            raise Exception(f"Generation failed: {str(e)}")

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
