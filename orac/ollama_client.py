"""
orac.ollama_client
------------------
A thin async wrapper around the local Ollama REST API that provides functionality for:
- Loading and unloading local GGUF models and remote models
- Generating responses from loaded models
- Managing model lifecycle (pull, delete, show)
- Version-aware model loading with support for both pre-0.6.0 and post-0.6.0 Ollama versions

Key features:
- Async HTTP client using httpx
- Automatic model name normalization
- Configurable model paths via environment variables
- Robust error handling and retries
- Streaming support for model responses
- Version detection and schema adaptation
"""

import json
import time
import os
from typing import List, Dict, Any, Optional
import httpx
from .models import ModelLoadResponse, ModelUnloadResponse, PromptResponse
from .model_loader import ModelLoader
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
        self.model_loader = ModelLoader(self.client)

    async def get_version(self) -> str:
        """Get Ollama version."""
        try:
            response = await self.client.get("/api/version")
            response.raise_for_status()
            return response.json().get("version", "unknown")
        except Exception as e:
            return "unknown"

    async def list_models(self) -> List[dict]:
        """List all available models."""
        response = await self.client.get("/api/tags")
        response.raise_for_status()
        return response.json()["models"]

    async def load_model(self, name: str, max_retries: int = 3) -> ModelLoadResponse:
        """Load a model by name."""
        try:
            result = await self.model_loader.load_model(name, max_retries)
            return ModelLoadResponse(status=result["status"])
        except Exception as e:
            return ModelLoadResponse(status="error", error=str(e))

    async def unload_model(self, name: str) -> ModelUnloadResponse:
        """Unload a model by name."""
        try:
            model_name = name.replace(".gguf", "")
            response = await self.client.delete(f"/api/delete", params={"name": model_name})
            response.raise_for_status()
            return ModelUnloadResponse(status="success")
        except Exception as e:
            return ModelUnloadResponse(status="error", error=str(e))

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
                            except json.JSONDecodeError:
                                continue
                
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
                
        except Exception as e:
            return PromptResponse(response="", elapsed_ms=0, error=str(e))

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
