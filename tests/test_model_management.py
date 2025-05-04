import pytest
import respx
from httpx import Response
from orac.ollama_client import OllamaClient
from orac.models import ModelLoadRequest, ModelLoadResponse, ModelUnloadResponse

@pytest.fixture
def ollama_client():
    return OllamaClient()

@respx.mock
@pytest.mark.asyncio
async def test_load_model_success():
    # Mock successful model loading
    respx.post("http://127.0.0.1:11434/api/pull").mock(
        return_value=Response(200, json={"status": "success"})
    )
    
    client = OllamaClient()
    response = await client.load_model("Qwen3-0.6B-Q4_K_M")
    assert response.status == "success"

@respx.mock
@pytest.mark.asyncio
async def test_load_model_not_found():
    # Mock model not found error
    respx.post("http://127.0.0.1:11434/api/pull").mock(
        return_value=Response(404, json={"error": "Model not found"})
    )
    
    client = OllamaClient()
    with pytest.raises(Exception) as exc_info:
        await client.load_model("nonexistent-model")
    assert "Model not found" in str(exc_info.value)

@respx.mock
@pytest.mark.asyncio
async def test_unload_model_success():
    # Mock successful model unloading
    respx.delete("http://127.0.0.1:11434/api/delete").mock(
        return_value=Response(200, json={"status": "success"})
    )
    
    client = OllamaClient()
    response = await client.unload_model("Qwen3-0.6B-Q4_K_M")
    assert response.status == "success"

@respx.mock
@pytest.mark.asyncio
async def test_unload_model_not_loaded():
    # Mock model not loaded error
    respx.delete("http://127.0.0.1:11434/api/delete").mock(
        return_value=Response(404, json={"error": "Model not loaded"})
    )
    
    client = OllamaClient()
    with pytest.raises(Exception) as exc_info:
        await client.unload_model("Qwen3-0.6B-Q4_K_M")
    assert "Model not loaded" in str(exc_info.value) 