"""
orac.model_loader
----------------
Handles the core logic for loading models into Ollama, including:
- Version detection and schema selection
- Model path resolution and validation
- Modelfile generation
- Model loading and readiness verification

This module separates the model loading concerns from the client API wrapper,
making the code more maintainable and easier to test.
"""

import os
import json
import asyncio
import traceback
from typing import Optional, Tuple, List
import httpx

class ModelLoader:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self._error_logs: List[str] = []

    def _log_error(self, message: str):
        """Add error message to logs."""
        self._error_logs.append(message)

    def get_error_logs(self) -> List[str]:
        """Get collected error logs."""
        return self._error_logs

    async def get_ollama_version(self) -> Tuple[float, bool]:
        """Get Ollama version and determine if new schema should be used."""
        try:
            response = await self.client.get("/api/version")
            response.raise_for_status()
            version = response.json().get("version", "0.0.0")
            
            version_parts = version.split('.')
            if len(version_parts) >= 2:
                major = int(version_parts[0])
                minor = int(version_parts[1])
                version_num = float(f"{major}.{minor}")
                return version_num, version_num >= 0.6
        except Exception as e:
            self._log_error(f"Failed to get Ollama version: {str(e)}")
        return 0.0, True  # Default to new schema on error

    def normalize_model_name(self, name: str) -> str:
        """Convert model name to valid Ollama tag format."""
        return name.replace(".gguf", "").lower().replace("_", "-")

    def resolve_model_path(self, name: str) -> str:
        """Resolve the full path to a model file."""
        model_base_path = os.getenv("OLLAMA_MODEL_PATH", "/models/gguf")
        return os.path.join(model_base_path, name)

    def validate_model_file(self, path: str) -> None:
        """Validate that model file exists and is readable."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model file not found at {path}")
        if not os.access(path, os.R_OK):
            raise PermissionError(f"Model file not readable at {path}")

    def create_modelfile(self, model_path: str, use_new_schema: bool) -> str:
        """Create appropriate Modelfile content based on schema version."""
        return f"FROM {model_path}\n"

    async def wait_for_model(self, model_name: str, max_retries: int = 30, delay: float = 2.0) -> bool:
        """Wait for a model to be ready."""
        for i in range(max_retries):
            try:
                response = await self.client.post("/api/show", json={"name": model_name})
                if response.status_code == 200:
                    return True
                
                response = await self.client.get("/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    if any(model.get("name") == model_name for model in models):
                        return True
            except Exception as e:
                self._log_error(f"Error checking model status: {str(e)}")
            
            if i < max_retries - 1:
                await asyncio.sleep(delay)
        return False

    async def load_model(self, name: str, max_retries: int = 3) -> dict:
        """Load a model into Ollama."""
        try:
            version_num, use_new_schema = await self.get_ollama_version()
            model_name = self.normalize_model_name(name)
            
            if not name.endswith(".gguf"):
                # Handle remote model pull
                try:
                    response = await self.client.post(
                        "/api/pull", 
                        json={"name": model_name},
                        timeout=120.0
                    )
                    response.raise_for_status()
                    return {"status": "success"}
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        raise Exception("Model not found")
                    raise Exception(f"Failed to pull model: {e.response.text}")
                except Exception as e:
                    raise Exception(f"Failed to pull model: {str(e)}")

            # Handle local GGUF file
            model_path = self.resolve_model_path(name)
            self.validate_model_file(model_path)
            
            modelfile = self.create_modelfile(model_path, use_new_schema)
            
            for attempt in range(max_retries):
                try:
                    async with self.client.stream(
                        "POST",
                        "/api/create",
                        json={
                            "name": model_name,
                            "modelfile": modelfile,
                            "stream": False
                        },
                        timeout=120.0
                    ) as response:
                        # If the status code is 4xx/5xx, read the body before raising:
                        if response.status_code >= 400:
                            raw = (await response.aread()).decode(errors="ignore")
                            self._log_error(f"HTTP {response.status_code} response: {raw}")
                            raise Exception(f"HTTP {response.status_code}: {raw}")
                        
                        create_complete = False
                        error_message = None
                        response_chunks = []
                        
                        async for line in response.aiter_lines():
                            if not line:
                                continue
                            try:
                                chunk = json.loads(line)
                                response_chunks.append(chunk)
                                if "error" in chunk:
                                    error_message = chunk["error"]
                                    self._log_error(f"Ollama error response: {json.dumps(chunk, indent=2)}")
                                    break
                                if chunk.get("status") == "success":
                                    create_complete = True
                                    break
                            except json.JSONDecodeError:
                                continue
                        
                        if error_message:
                            # Bubble up server-side error message
                            raise Exception(f"Model create error: {error_message}")
                        
                        if create_complete:
                            if not await self.wait_for_model(model_name):
                                raise Exception(f"Model {model_name} failed to load within timeout")
                            return {"status": "success"}
                        
                except Exception as e:
                    self._log_error(f"[load_model] attempt {attempt+1} failed: {str(e)}")
                    if attempt == max_retries - 1:
                        # Log the full traceback
                        self._log_error("Client-side traceback:")
                        self._log_error("".join(traceback.format_exception(type(e), e, e.__traceback__)))
                        raise Exception(f"Failed to load model after {max_retries} attempts: {str(e)}")
                    await asyncio.sleep(2 ** attempt)
            
            raise Exception(f"Failed to load model after {max_retries} attempts")
        except Exception as e:
            # Log any unhandled exceptions
            self._log_error("Client-side traceback:")
            self._log_error("".join(traceback.format_exception(type(e), e, e.__traceback__)))
            raise 