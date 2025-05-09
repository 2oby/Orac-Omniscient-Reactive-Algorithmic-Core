"""
Tests for the model_loader module.

These tests verify that the ModelLoader class works correctly, especially for
loading models on the Jetson Orin Nano platform.
"""

import os
import json
import pytest
import httpx
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from orac.model_loader import ModelLoader, ModelError


# Fixtures
@pytest.fixture
def mock_client():
    """Create a mock httpx.AsyncClient for testing."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.base_url = httpx.URL("http://localhost:11434")
    return client


@pytest.fixture
def model_loader(mock_client):
    """Create a ModelLoader instance with a mock client."""
    return ModelLoader(mock_client)


# Tests for the ModelLoader class
@pytest.mark.asyncio
async def test_get_ollama_version(model_loader, mock_client):
    """Test that version detection works correctly."""
    # Mock the response for version 0.6.0
    mock_response = AsyncMock()
    mock_response.json.return_value = {"version": "0.6.0"}
    mock_response.raise_for_status.return_value = None
    mock_client.get.return_value = mock_response
    
    # Call the method
    version_num, use_new_schema = await model_loader.get_ollama_version()
    
    # Check results
    assert version_num == 0.6
    assert use_new_schema is True
    mock_client.get.assert_called_once_with("/api/version")


@pytest.mark.asyncio
async def test_get_ollama_version_error(model_loader, mock_client):
    """Test that version detection handles errors gracefully."""
    # Mock the client to raise an exception
    mock_client.get.side_effect = httpx.HTTPError("Connection error")
    
    # Call the method
    version_num, use_new_schema = await model_loader.get_ollama_version()
    
    # Check results - should default to new schema
    assert version_num == 0.0
    assert use_new_schema is True


def test_normalize_model_name(model_loader):
    """Test model name normalization."""
    test_cases = [
        # (input, expected_output)
        ("llama2.gguf", "llama2"),
        ("Llama-2-7B.gguf", "llama-2-7b"),
        ("LLAMA_2_7B.GGUF", "llama-2-7b"),
        ("orca_mini_3b-GGUF-v3-q4_0.gguf", "orca-mini-3b-gguf-v3-q4-0"),
        ("&special*chars(model).gguf", "specialcharsmodel"),
        ("1-starts-with-number.gguf", "m-1-starts-with-number"),
        ("very-" + "-long" * 30 + "-name.gguf", "very-long" + "-long" * 21),
    ]
    
    for input_name, expected_output in test_cases:
        assert model_loader.normalize_model_name(input_name) == expected_output


def test_resolve_model_path(model_loader):
    """Test model path resolution."""
    # Test with OLLAMA_MODEL_PATH environment variable
    with patch.dict(os.environ, {"OLLAMA_MODEL_PATH": "/custom/path"}):
        path = model_loader.resolve_model_path("model")
        assert path == "/custom/path/model.gguf"
    
    # Test with existing path
    with patch("os.path.exists", return_value=True):
        path = model_loader.resolve_model_path("model.gguf")
        assert path.endswith("/model.gguf")
    
    # Test with non-existing path
    with patch("os.path.exists", return_value=False):
        path = model_loader.resolve_model_path("model")
        assert path == "/models/gguf/model.gguf"  # Docker default


def test_validate_model_file(model_loader):
    """Test model file validation."""
    # Test with existing, readable file
    with patch("os.path.exists", return_value=True), \
         patch("os.path.isfile", return_value=True), \
         patch("os.access", return_value=True):
        # Should not raise exception
        model_loader.validate_model_file("/path/to/model.gguf")
    
    # Test with non-existing file
    with patch("os.path.exists", return_value=False):
        with pytest.raises(FileNotFoundError):
            model_loader.validate_model_file("/path/to/nonexistent.gguf")
    
    # Test with directory instead of file
    with patch("os.path.exists", return_value=True), \
         patch("os.path.isfile", return_value=False):
        with pytest.raises(FileNotFoundError):
            model_loader.validate_model_file("/path/to/directory")
    
    # Test with unreadable file
    with patch("os.path.exists", return_value=True), \
         patch("os.path.isfile", return_value=True), \
         patch("os.access", return_value=False):
        with pytest.raises(PermissionError):
            model_loader.validate_model_file("/path/to/unreadable.gguf")


def test_create_modelfile(model_loader):
    """Test Modelfile creation."""
    # Test with new schema
    modelfile = model_loader.create_modelfile("/path/to/model.gguf", True)
    assert "FROM model.gguf" in modelfile
    assert "PARAMETER temperature 0.7" in modelfile
    assert "PARAMETER num_ctx 2048" in modelfile
    
    # Check for Jetson-specific optimizations
    with patch.dict(os.environ, {"GPU_LAYERS": "24", "CPU_THREADS": "6"}):
        jetson_loader = ModelLoader(mock_client())
        modelfile = jetson_loader.create_modelfile("/path/to/model.gguf", True)
        assert "PARAMETER gpu_layers 24" in modelfile
        assert "PARAMETER num_thread 6" in modelfile


def test_write_modelfile(model_loader):
    """Test writing Modelfile to disk."""
    # Mock open function
    mock_open = MagicMock()
    with patch("builtins.open", mock_open):
        path, is_temp = model_loader.write_modelfile("FROM model.gguf", "/path/to/model.gguf")
        assert path == "/path/to/Modelfile"
        assert is_temp is True
        mock_open.assert_called_once_with("/path/to/Modelfile", "w")
        mock_open().__enter__().write.assert_called_once_with("FROM model.gguf")
    
    # Test error handling
    mock_open.side_effect = IOError("Permission denied")
    with patch("builtins.open", mock_open):
        with pytest.raises(Exception) as excinfo:
            model_loader.write_modelfile("FROM model.gguf", "/path/to/model.gguf")
        assert "Failed to write Modelfile" in str(excinfo.value)


@pytest.mark.asyncio
async def test_wait_for_model_success(model_loader, mock_client):
    """Test waiting for a model to be ready - success case."""
    # Mock successful show response
    mock_show_response = AsyncMock()
    mock_show_response.status_code = 200
    mock_show_response.json.return_value = {"name": "test-model"}
    mock_client.post.return_value = mock_show_response
    
    # Call the method with shorter timeout
    result = await model_loader.wait_for_model("test-model", max_retries=3, delay=0.1)
    
    # Check results
    assert result is True
    mock_client.post.assert_called_with("/api/show", json={"name": "test-model"})


@pytest.mark.asyncio
async def test_wait_for_model_timeout(model_loader, mock_client):
    """Test waiting for a model to be ready - timeout case."""
    # Mock unsuccessful show response
    mock_show_response = AsyncMock()
    mock_show_response.status_code = 404
    mock_client.post.return_value = mock_show_response
    
    # Mock tags response
    mock_tags_response = AsyncMock()
    mock_tags_response.status_code = 200
    mock_tags_response.json.return_value = {"models": []}
    mock_client.get.return_value = mock_tags_response
    
    # Call the method with very short timeout
    result = await model_loader.wait_for_model("test-model", max_retries=2, delay=0.1)
    
    # Check results
    assert result is False


@pytest.mark.asyncio
async def test_load_model_already_loaded(model_loader, mock_client):
    """Test loading a model that's already loaded."""
    # Mock successful show response
    mock_show_response = AsyncMock()
    mock_show_response.status_code = 200
    mock_show_response.json.return_value = {"name": "test-model"}
    mock_client.post.return_value = mock_show_response
    
    # Call the method
    result = await model_loader.load_model("test-model")
    
    # Check results
    assert result["status"] == "success"
    assert result["message"] == "Model already loaded"


@pytest.mark.asyncio
async def test_load_model_success(model_loader, mock_client):
    """Test successful model loading."""
    # Mock version
    with patch.object(model_loader, "get_ollama_version", 
                     return_value=(0.6, True)), \
         patch.object(model_loader, "normalize_model_name", 
                     return_value="test-model"), \
         patch.object(model_loader, "resolve_model_path", 
                     return_value="/path/to/model.gguf"), \
         patch.object(model_loader, "validate_model_file"), \
         patch.object(model_loader, "create_modelfile", 
                     return_value="FROM model.gguf"), \
         patch.object(model_loader, "write_modelfile", 
                     return_value=("/path/to/Modelfile", True)), \
         patch.object(model_loader, "wait_for_model", 
                     return_value=True):
        
        # Mock initial 404 (not found) for the first show call
        mock_not_found = AsyncMock()
        mock_not_found.status_code = 404
        
        # Mock successful create response
        mock_create_response = AsyncMock()
        mock_create_response.status_code = 200
        mock_create_response.json.return_value = {"status": "success"}
        
        # Set up client responses
        mock_client.post.side_effect = [
            mock_not_found,  # First call to check if model exists
            mock_create_response  # Second call to create model
        ]
        
        # Call the method
        result = await model_loader.load_model("test-model")
        
        # Check results
        assert result["status"] == "success"
        assert mock_client.post.call_count == 2
        # First call to check if model exists
        assert mock_client.post.call_args_list[0][0][0] == "/api/show"
        # Second call to create model
        assert mock_client.post.call_args_list[1][0][0] == "/api/create"


@pytest.mark.asyncio
async def test_load_model_validation_error(model_loader, mock_client):
    """Test model loading with validation error."""
    # Mock validation error
    with patch.object(model_loader, "get_ollama_version", 
                     return_value=(0.6, True)), \
         patch.object(model_loader, "normalize_model_name", 
                     return_value="test-model"), \
         patch.object(model_loader, "resolve_model_path", 
                     return_value="/path/to/model.gguf"), \
         patch.object(model_loader, "validate_model_file", 
                     side_effect=FileNotFoundError("File not found")):
        
        # Mock initial 404 (not found) for the show call
        mock_not_found = AsyncMock()
        mock_not_found.status_code = 404
        mock_client.post.return_value = mock_not_found
        
        # Call the method
        with pytest.raises(ModelError) as excinfo:
            await model_loader.load_model("test-model")
        
        # Check error details
        error = excinfo.value
        assert error.stage == "validation"
        assert "File not found" in error.message


@pytest.mark.asyncio
async def test_unload_model(model_loader, mock_client):
    """Test model unloading."""
    # Mock successful unload response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}
    mock_client.delete.return_value = mock_response
    
    # Mock normalize method
    with patch.object(model_loader, "normalize_model_name", 
                     return_value="test-model"):
        
        # Call the method
        result = await model_loader.unload_model("test-model")
        
        # Check results
        assert result["status"] == "success"
        mock_client.delete.assert_called_once_with(
            "/api/delete", 
            json={"name": "test-model"}
        )


@pytest.mark.asyncio
async def test_unload_model_error(model_loader, mock_client):
    """Test model unloading with error."""
    # Mock error response
    mock_response = AsyncMock()
    mock_response.status_code = 404
    mock_response.text.return_value = "Model not found"
    mock_client.delete.return_value = mock_response
    
    # Mock normalize method
    with patch.object(model_loader, "normalize_model_name", 
                     return_value="test-model"):
        
        # Call the method
        result = await model_loader.unload_model("test-model")
        
        # Check results
        assert result["status"] == "error"
        assert "Model not found" in result["message"]