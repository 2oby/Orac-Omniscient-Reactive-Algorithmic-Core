"""
Tests for the model_loader module.

These tests verify that the ModelLoader class works correctly for
loading and managing GGUF models via llama.cpp.
"""

import os
import json
import pytest
import httpx
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from orac.model_loader import ModelLoader, ModelError


# Fixtures
@pytest.fixture
def mock_client():
    """Create a mock httpx.AsyncClient for testing."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.base_url = httpx.URL("http://localhost:8000")
    return client


@pytest.fixture
def model_loader(mock_client):
    """Create a ModelLoader instance with a mock client."""
    return ModelLoader(mock_client)


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
    # Test with MODEL_PATH environment variable
    with patch.dict(os.environ, {"MODEL_PATH": "/custom/path"}):
        path = model_loader.resolve_model_path("model")
        assert path == "/custom/path/model.gguf"
    
    # Test with existing path
    with patch("os.path.exists", return_value=True):
        path = model_loader.resolve_model_path("model.gguf")
        assert path.endswith("/model.gguf")
    
    # Test with non-existing path
    with patch("os.path.exists", return_value=False):
        path = model_loader.resolve_model_path("model")
        assert path == "/app/models/model.gguf"  # Docker default


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


@pytest.mark.asyncio
async def test_load_model_success(model_loader, mock_client):
    """Test successful model loading."""
    test_model_path = Path("/app/models/test-model.gguf")
    
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.stat") as mock_stat, \
         patch("orac.model_loader.ModelLoader.validate_model_file"), \
         patch("orac.model_loader.ModelLoader._load_model") as mock_load:
        
        mock_stat.return_value.st_size = 1000000
        mock_stat.return_value.st_mtime = 1234567890.0
        mock_load.return_value = {"status": "success"}
        
        result = await model_loader.load_model("test-model")
        assert result["status"] == "success"
        mock_load.assert_called_once_with("test-model")


@pytest.mark.asyncio
async def test_load_model_validation_error(model_loader, mock_client):
    """Test model loading with validation error."""
    with patch("pathlib.Path.exists", return_value=False):
        with pytest.raises(FileNotFoundError):
            await model_loader.load_model("nonexistent-model")


@pytest.mark.asyncio
async def test_unload_model(model_loader, mock_client):
    """Test successful model unloading."""
    with patch("orac.model_loader.ModelLoader._unload_model") as mock_unload:
        mock_unload.return_value = {"status": "success"}
        
        result = await model_loader.unload_model("test-model")
        assert result["status"] == "success"
        mock_unload.assert_called_once_with("test-model")


@pytest.mark.asyncio
async def test_unload_model_error(model_loader, mock_client):
    """Test model unloading with error."""
    with patch("orac.model_loader.ModelLoader._unload_model") as mock_unload:
        mock_unload.side_effect = Exception("Model not loaded")
        
        with pytest.raises(Exception) as exc_info:
            await model_loader.unload_model("test-model")
        assert "Model not loaded" in str(exc_info.value)