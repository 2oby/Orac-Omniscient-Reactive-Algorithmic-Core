"""
Tests for model management functionality.
"""

import pytest
import os
from orac.llama_cpp_client import LlamaCppClient

@pytest.fixture
def llama_cpp_client():
    """Create a LlamaCppClient instance for testing."""
    return LlamaCppClient()

@pytest.mark.asyncio
async def test_list_models(llama_cpp_client):
    """Test listing available models."""
    models = await llama_cpp_client.list_models()
    assert isinstance(models, list)
    for model in models:
        assert "name" in model
        assert "size" in model
        assert "modified" in model
        assert "backend" in model
        assert model["backend"] == "llama_cpp"

@pytest.mark.asyncio
async def test_real_model_loading_and_prompting(llama_cpp_client):
    """Test loading and prompting with a real model."""
    # Skip if no models are available
    models = await llama_cpp_client.list_models()
    if not models:
        pytest.skip("No models available for testing")
    
    # Use the first available model
    model = models[0]["name"]
    
    # Test generation
    prompt = "Write a haiku about artificial intelligence."
    try:
        response = await llama_cpp_client.generate(model, prompt)
        assert response.response
        assert len(response.response) > 0
        assert response.elapsed_ms > 0
        assert response.model == model
        assert response.prompt == prompt
    except Exception as e:
        if "libgomp.so.1" in str(e):
            pytest.skip("libgomp.so.1 not available")
        raise

@pytest.mark.asyncio
async def test_load_model_success():
    test_model_path = Path("/app/models/test-model.gguf")
    
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.stat") as mock_stat, \
         patch("orac.llama_cpp_client.LlamaCppClient._load_model") as mock_load:
        
        mock_stat.return_value.st_size = 1000000
        mock_stat.return_value.st_mtime = 1234567890.0
        mock_load.return_value = {"status": "success"}
        
        client = LlamaCppClient()
        response = await client.load_model("test-model")
        assert response["status"] == "success"

@pytest.mark.asyncio
async def test_load_model_not_found():
    test_model_path = Path("/app/models/nonexistent-model.gguf")
    
    with patch("pathlib.Path.exists", return_value=False):
        client = LlamaCppClient()
        with pytest.raises(Exception) as exc_info:
            await client.load_model("nonexistent-model")
        assert "Model file not found" in str(exc_info.value)

@pytest.mark.asyncio
async def test_unload_model_success():
    with patch("orac.llama_cpp_client.LlamaCppClient._unload_model") as mock_unload:
        mock_unload.return_value = {"status": "success"}
        
        client = LlamaCppClient()
        response = await client.unload_model("test-model")
        assert response["status"] == "success"

@pytest.mark.asyncio
async def test_unload_model_not_loaded():
    with patch("orac.llama_cpp_client.LlamaCppClient._unload_model") as mock_unload:
        mock_unload.side_effect = Exception("Model not loaded")
        
        client = LlamaCppClient()
        with pytest.raises(Exception) as exc_info:
            await client.unload_model("test-model")
        assert "Model not loaded" in str(exc_info.value) 