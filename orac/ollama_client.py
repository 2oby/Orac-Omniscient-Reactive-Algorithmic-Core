"""
orac.ollama_client
------------------
Thin async wrapper around the local Ollama REST API (http://127.0.0.1:11434).
"""

from typing import List, Dict, Any
import httpx

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
