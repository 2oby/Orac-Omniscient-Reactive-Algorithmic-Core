"""
Tests for the ollama_client module.

These tests verify that the OllamaClient class works correctly, including model loading,
unloading, and text generation functionality.
"""

import json
import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

import httpx
from orac.ollama_client import OllamaClient
from orac.model_loader import ModelLoader, ModelError


# Fixtures
@pytest.fixture
def mock_model_loader():
    """Create a mock ModelLoader for testing."""
    loader = AsyncMock(spec=ModelLoader)
    return loader


@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx.AsyncClient for testing."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.base_url = httpx.URL("http://localhost:11434")
    return client


@pytest.fixture
def ollama_client(mock_httpx_client, mock_model_loader):
    """Create an OllamaClient with mock dependencies."""
    with patch("orac.ollama_client.httpx.AsyncClient", return_value=mock_httpx_client), \
         patch("orac.ollama_client.ModelLoader", return_value=mock_model_loader):
        client = OllamaClient("http://localhost:11434")
        return client


# Tests for the OllamaClient class
@pytest.mark.asyncio
async def test_get_version(ollama_client, mock_httpx_client):
    """Test getting the Ollama version."""
    # Mock successful response
    mock_response = AsyncMock()
    mock_response.json.return_value = {"version": "0.6.0"}
    mock_response.raise_for_status.return_value = None
    mock_httpx_client.get.return_value = mock_response
    
    # Call the method
    version = await ollama_client.get_version()
    
    # Check results
    assert version == "0.6.0"
    mock_httpx_client.get.assert_called_once_with("/api/version")


@pytest.mark.asyncio
async def test_get_version_error(ollama_client, mock_httpx_client):
    """Test handling errors when getting version."""
    # Mock error
    mock_httpx_client.get.side_effect = httpx.HTTPError("Connection error")
    
    # Call the method
    version = await ollama_client.get_version()
    
    # Check results
    assert version == "unknown"


@pytest.mark.asyncio
async def test_list_models(ollama_client, mock_httpx_client):
    """Test listing models."""
    # Mock successful response
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "models": [
            {"name": "model1", "size": 1000000},
            {"name": "model2", "size": 2000000}
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_httpx_client.get.return_value = mock_response
    
    # Call the method
    models = await ollama_client.list_models()
    
    # Check results
    assert len(models) == 2
    assert models[0]["name"] == "model1"
    assert models[1]["name"] == "model2"
    mock_httpx_client.get.assert_called_once_with("/api/tags")


@pytest.mark.asyncio
async def test_list_models_error(ollama_client, mock_httpx_client):
    """Test handling errors when listing models."""
    # Mock error
    mock_httpx_client.get.side_effect = httpx.HTTPError("Connection error")
    
    # Call the method
    with pytest.raises(Exception) as excinfo:
        await ollama_client.list_models()
    
    # Check error message
    assert "Failed to list models" in str(excinfo.value)


@pytest.mark.asyncio
async def test_load_model(ollama_client, mock_model_loader):
    """Test loading a model."""
    # Mock successful load
    mock_model_loader.load_model.return_value = {
        "status": "success", 
        "elapsed_seconds": 10.5
    }
    
    # Call the method
    result = await ollama_client.load_model("test-model")
    
    # Check results
    assert result["status"] == "success"
    assert result["elapsed_seconds"] == 10.5
    mock_model_loader.load_model.assert_called_once_with("test-model", 3)


@pytest.mark.asyncio
async def test_load_model_error(ollama_client, mock_model_loader):
    """Test handling model loader errors."""
    # Mock model loader error
    mock_model_loader.load_model.side_effect = ModelError(
        "File not found", 
        "validation"
    )
    
    # Call the method
    result = await ollama_client.load_model("test-model")
    
    # Check results
    assert result["status"] == "error"
    assert result["stage"] == "validation"
    assert "File not found" in result["message"]


@pytest.mark.asyncio
async def test_unload_model(ollama_client, mock_model_loader):
    """Test unloading a model."""
    # Mock successful unload
    mock_model_loader.unload_model.return_value = {"status": "success"}
    
    # Call the method
    result = await ollama_client.unload_model("test-model")
    
    # Check results
    assert result["status"] == "success"
    mock_model_loader.unload_model.assert_called_once_with("test-model")


@pytest.mark.asyncio
async def test_generate_complete(ollama_client, mock_httpx_client):
    """Test generating a complete (non-streaming) response."""
    # Set up client to handle a new client creation
    async_client_mock = AsyncMock()
    cm_instance = AsyncMock()
    cm_instance.__aenter__.return_value = async_client_mock
    httpx.AsyncClient.return_value = cm_instance
    
    # Mock successful response
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "response": "Generated text",
        "model": "test-model"
    }
    mock_response.raise_for_status.return_value = None
    async_client_mock.post.return_value = mock_response
    
    # Mock the normalize_model_name method
    ollama_client.model_loader.normalize_model_name.return_value = "test-model"
    
    # Call the method
    result = await ollama_client.generate("test-model", "Test prompt")
    
    # Check results
    assert result["status"] == "success"
    assert result["response"] == "Generated text"
    assert "elapsed_ms" in result
    
    # Verify the correct parameters were passed
    expected_params = {
        "model": "test-model",
        "prompt": "Test prompt",
        "stream": False,
        "temperature": 0.7,
        "top_p": 0.7,
        "top_k": 40
    }
    async_client_mock.post.assert_called_once_with(
        "/api/generate", json=expected_params
    )


@pytest.mark.asyncio
async def test_generate_with_custom_params(ollama_client, mock_httpx_client):
    """Test generating with custom parameters."""
    # Set up client to handle a new client creation
    async_client_mock = AsyncMock()
    cm_instance = AsyncMock()
    cm_instance.__aenter__.return_value = async_client_mock
    httpx.AsyncClient.return_value = cm_instance
    
    # Mock successful response
    mock_response = AsyncMock()
    mock_response.json.return_value = {"response": "Generated text"}
    mock_response.raise_for_status.return_value = None
    async_client_mock.post.return_value = mock_response
    
    # Mock the normalize_model_name method
    ollama_client.model_loader.normalize_model_name.return_value = "test-model"
    
    # Call the method with custom parameters
    result = await ollama_client.generate(
        "test-model", 
        "Test prompt", 
        temperature=0.5,
        top_p=0.8,
        top_k=50,
        stop=["END"],
        max_tokens=100
    )
    
    # Check results
    assert result["status"] == "success"
    
    # Verify the correct parameters were passed
    expected_params = {
        "model": "test-model",
        "prompt": "Test prompt",
        "stream": False,
        "temperature": 0.5,
        "top_p": 0.8,
        "top_k": 50,
        "stop": ["END"],
        "max_tokens": 100
    }
    async_client_mock.post.assert_called_once_with(
        "/api/generate", json=expected_params
    )


@pytest.mark.asyncio
async def test_generate_stream(ollama_client, mock_httpx_client):
    """Test generating a streaming response."""
    # Set up client to handle a new client creation
    async_client_mock = AsyncMock()
    cm_instance = AsyncMock()
    cm_instance.__aenter__.return_value = async_client_mock
    httpx.AsyncClient.return_value = cm_instance
    
    # Mock streaming response
    mock_stream_response = AsyncMock()
    mock_stream_response.raise_for_status.return_value = None
    
    # Create a mock for the stream context manager
    stream_cm = AsyncMock()
    stream_cm.__aenter__.return_value = mock_stream_response
    async_client_mock.stream.return_value = stream_cm
    
    # Set up mock line iteration to return JSON chunks
    chunks = [
        json.dumps({"response": "Hello", "done": False}),
        json.dumps({"response": " world", "done": False}),
        json.dumps({"response": "!", "done": True})
    ]
    mock_stream_response.aiter_lines.return_value = AsyncMock(
        __aiter__=lambda self: self,
        __anext__=AsyncMock(side_effect=chunks + [StopAsyncIteration])
    )
    
    # Mock the normalize_model_name method
    ollama_client.model_loader.normalize_model_name.return_value = "test-model"
    
    # Call the method
    result = await ollama_client.generate("test-model", "Test prompt", stream=True)
    
    # Check results
    assert result["status"] == "success"
    assert result["response"] == "Hello world!"
    assert "elapsed_ms" in result
    
    # Verify the correct parameters were passed
    expected_params = {
        "model": "test-model",
        "prompt": "Test prompt",
        "stream": True,
        "temperature": 0.7,
        "top_p": 0.7,
        "top_k": 40
    }
    async_client_mock.stream.assert_called_once_with(
        "POST", "/api/generate", json=expected_params
    )


@pytest.mark.asyncio
async def test_generate_error(ollama_client, mock_httpx_client):
    """Test error handling during generation."""
    # Set up client to handle a new client creation
    async_client_mock = AsyncMock()
    cm_instance = AsyncMock()
    cm_instance.__aenter__.return_value = async_client_mock
    httpx.AsyncClient.return_value = cm_instance
    
    # Mock error response
    http_error = httpx.HTTPStatusError(
        "Error", 
        request=httpx.Request("POST", "http://localhost:11434/api/generate"),
        response=httpx.Response(500, request=httpx.Request("POST", "http://localhost:11434/api/generate"))
    )
    http_error.response.json = lambda: {"error": "Model crashed"}
    async_client_mock.post.side_effect = http_error
    
    # Mock the normalize_model_name method
    ollama_client.model_loader.normalize_model_name.return_value = "test-model"
    
    # Call the method
    result = await ollama_client.generate("test-model", "Test prompt")
    
    # Check results
    assert result["status"] == "error"
    assert "Model crashed" in result["message"]


@pytest.mark.asyncio
async def test_pull_model(ollama_client, mock_httpx_client):
    """Test pulling a model."""
    # Mock successful response
    mock_response = AsyncMock()
    mock_response.json.return_value = {"status": "success"}
    mock_response.raise_for_status.return_value = None
    mock_httpx_client.post.return_value = mock_response
    
    # Call the method
    result = await ollama_client.pull_model("test-model")
    
    # Check results
    assert result["status"] == "success"
    assert result["model"] == "test-model"
    assert "elapsed_seconds" in result
    mock_httpx_client.post.assert_called_once_with(
        "/api/pull",
        json={"name": "test-model"},
        timeout=None
    )


@pytest.mark.asyncio
async def test_show_model(ollama_client, mock_httpx_client):
    """Test getting model details."""
    # Mock successful response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "name": "test-model",
        "size": 1000000
    }
    mock_httpx_client.post.return_value = mock_response
    
    # Mock the normalize_model_name method
    ollama_client.model_loader.normalize_model_name.return_value = "test-model"
    
    # Call the method
    result = await ollama_client.show_model("test-model")
    
    # Check results
    assert result["status"] == "success"
    assert result["model"]["name"] == "test-model"
    mock_httpx_client.post.assert_called_once_with(
        "/api/show",
        json={"name": "test-model"}
    )


@pytest.mark.asyncio
async def test_show_model_not_found(ollama_client, mock_httpx_client):
    """Test getting details for a non-existent model."""
    # Mock not found response
    mock_response = AsyncMock()
    mock_response.status_code = 404
    mock_httpx_client.post.return_value = mock_response
    
    # Mock the normalize_model_name method
    ollama_client.model_loader.normalize_model_name.return_value = "test-model"
    
    # Call the method
    result = await ollama_client.show_model("test-model")
    
    # Check results
    assert result["status"] == "error"
    assert result["message"] == "Model not found"


@pytest.mark.asyncio
async def test_close(ollama_client, mock_httpx_client):
    """Test closing the client."""
    # Call the method
    await ollama_client.close()
    
    # Check that the client was closed
    mock_httpx_client.aclose.assert_called_once()