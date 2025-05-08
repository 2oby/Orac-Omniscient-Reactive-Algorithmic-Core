import pytest
import respx
from httpx import Response
from orac.ollama_client import OllamaClient
from orac.models import ModelLoadRequest, ModelLoadResponse, ModelUnloadResponse

@pytest.fixture
def ollama_client():
    return OllamaClient()

@respx.mock
def test_real_model_loading_and_prompting():
    # Mock version check
    respx.get("http://orac-ollama:11434/api/version").mock(
        return_value=Response(200, json={"version": "0.6.7"})
    )
    
    # Mock create endpoint with success
    respx.post("http://orac-ollama:11434/api/create").mock(
        return_value=Response(200, json={"status": "success"})
    )
    
    # Mock show endpoint to indicate model is ready
    respx.post("http://orac-ollama:11434/api/show").mock(
        return_value=Response(200, json={"name": "test-model"})
    )
    
    # Mock tags endpoint
    respx.get("http://orac-ollama:11434/api/tags").mock(
        return_value=Response(200, json={"models": [{"name": "test-model"}]})
    )
    
    # Mock generate endpoint
    respx.post("http://orac-ollama:11434/api/generate").mock(
        return_value=Response(200, json={
            "response": "Test response",
            "done": True
        })
    )
    
    # Mock delete endpoint for unloading
    respx.delete("http://orac-ollama:11434/api/delete").mock(
        return_value=Response(200, json={"status": "success"})
    )
    
    client = OllamaClient()
    
    # Test loading
    response = client.load_model("test-model")
    assert response["status"] == "success"
    
    # Test prompting
    prompt_response = client.generate("test-model", "Test prompt")
    assert prompt_response.response == "Test response"
    assert prompt_response.elapsed_ms > 0
    
    # Test unloading
    unload_response = client.unload_model("test-model")
    assert unload_response.status == "success"

@respx.mock
def test_load_model_success():
    # Mock version check
    respx.get("http://orac-ollama:11434/api/version").mock(
        return_value=Response(200, json={"version": "0.6.7"})
    )
    
    # Mock create endpoint with success
    respx.post("http://orac-ollama:11434/api/create").mock(
        return_value=Response(200, json={"status": "success"})
    )
    
    # Mock show endpoint to indicate model is ready
    respx.post("http://orac-ollama:11434/api/show").mock(
        return_value=Response(200, json={"name": "test-model"})
    )
    
    # Mock tags endpoint
    respx.get("http://orac-ollama:11434/api/tags").mock(
        return_value=Response(200, json={"models": [{"name": "test-model"}]})
    )
    
    client = OllamaClient()
    response = client.load_model("test-model")
    assert response["status"] == "success"

@respx.mock
def test_load_model_not_found():
    # Mock model not found error
    respx.post("http://orac-ollama:11434/api/create").mock(
        return_value=Response(404, json={"error": "Model not found"})
    )
    # Mock version check
    respx.get("http://orac-ollama:11434/api/version").mock(
        return_value=Response(200, json={"version": "0.6.7"})
    )
    
    client = OllamaClient()
    with pytest.raises(Exception) as exc_info:
        client.load_model("nonexistent-model")
    assert "Model file not found" in str(exc_info.value)

@respx.mock
def test_unload_model_success():
    # Mock successful model unloading
    respx.delete("http://orac-ollama:11434/api/delete").mock(
        return_value=Response(200, json={"status": "success"})
    )
    
    client = OllamaClient()
    response = client.unload_model("test-model")
    assert response.status == "success"

@respx.mock
def test_unload_model_not_loaded():
    # Mock model not loaded error
    respx.delete("http://orac-ollama:11434/api/delete").mock(
        return_value=Response(404, json={"error": "Model not loaded"})
    )
    
    client = OllamaClient()
    with pytest.raises(Exception) as exc_info:
        client.unload_model("test-model")
    assert "Model not loaded" in str(exc_info.value) 