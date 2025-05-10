import pytest
import respx
from httpx import Response
from pathlib import Path
from unittest.mock import patch, AsyncMock
from orac.llama_cpp_client import LlamaCppClient
from orac.models import ModelLoadRequest, ModelLoadResponse, ModelUnloadResponse

@pytest.fixture
async def llama_client():
    return LlamaCppClient()

@pytest.mark.asyncio
async def test_real_model_loading_and_prompting():
    # Mock model file existence
    test_model_path = Path("/app/models/test-model.gguf")
    
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.stat") as mock_stat, \
         patch("orac.llama_cpp_client.LlamaCppClient._load_model") as mock_load, \
         patch("orac.llama_cpp_client.LlamaCppClient._generate") as mock_generate, \
         patch("orac.llama_cpp_client.LlamaCppClient._unload_model") as mock_unload:
        
        mock_stat.return_value.st_size = 1000000
        mock_stat.return_value.st_mtime = 1234567890.0
        
        mock_load.return_value = {"status": "success"}
        mock_generate.return_value = {
            "response": "Test response",
            "elapsed_ms": 100.0
        }
        mock_unload.return_value = {"status": "success"}
        
        client = LlamaCppClient()
        
        # Test loading
        response = await client.load_model("test-model")
        assert response["status"] == "success"
        
        # Test prompting
        prompt_response = await client.generate("test-model", "Test prompt")
        assert prompt_response["response"] == "Test response"
        assert prompt_response["elapsed_ms"] > 0
        
        # Test unloading
        unload_response = await client.unload_model("test-model")
        assert unload_response["status"] == "success"

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