"""
orac.ollama_client
------------------
Thin async wrapper around the local Ollama REST API (http://127.0.0.1:11434).
"""

import json
import time
from typing import List, Dict, Any, Optional
import httpx
from .models import ModelLoadResponse, ModelUnloadResponse, PromptResponse

OLLAMA_BASE_URL = "http://127.0.0.1:11434"


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
    def __init__(self, base_url: str = "http://127.0.0.1:11434"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url)

    async def list_models(self) -> List[dict]:
        """List all available models."""
        response = await self.client.get("/api/tags")
        response.raise_for_status()
        return response.json()["models"]

    async def load_model(self, name: str) -> ModelLoadResponse:
        """Load a model by name."""
        try:
            # Remove .gguf extension if present
            model_name = name.replace(".gguf", "")
            response = await self.client.post("/api/pull", json={"name": model_name})
            response.raise_for_status()
            return ModelLoadResponse(status="success")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise Exception("Model not found")
            raise Exception(f"Failed to load model: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to load model: {str(e)}")

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
